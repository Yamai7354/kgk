from consolidation import ConsolidationResult, ConsolidationService
from entities.models import EntityAlias, EntityResolutionResult
from events.models import EventType, KnowledgeEvent
from events.store import EventStore
from graph.store import GraphStore
from models.entity import Entity


class EntityService:
    """Non-destructive entity identity management, aliasing, candidate discovery, and merge resolution."""

    def __init__(
        self,
        store: GraphStore,
        consolidation: ConsolidationService,
        events: EventStore | None = None,
    ) -> None:
        self._store = store
        self._consolidation = consolidation
        self._events = events
        self._aliases: list[EntityAlias] = []

    def alias(
        self,
        entity_id: str,
        alias_label: str,
        *,
        namespace: str = "global",
        source: str = "manual",
        actor: str = "system",
    ) -> EntityAlias:
        entity = self._store.get_entity(entity_id)
        if entity is None:
            raise KeyError(f"Entity not found: {entity_id}")

        alias_obj = EntityAlias(
            alias=alias_label.strip(),
            canonical_id=entity.id,
            namespace=namespace,
            source=source,
        )
        self._aliases.append(alias_obj)

        if self._events is not None:
            self._events.append(
                KnowledgeEvent(
                    event_type=EventType.ENTITY_ALIAS,
                    target_id=entity_id,
                    namespace=namespace,
                    actor=actor,
                    payload={"alias": alias_label, "canonical_id": entity.id},
                )
            )

        return alias_obj

    def add_alias(
        self,
        entity_id: str,
        alias_label: str,
        *,
        namespace: str = "global",
        source: str = "manual",
        actor: str = "system",
    ) -> EntityAlias:
        """Alias for alias()."""
        return self.alias(
            entity_id,
            alias_label,
            namespace=namespace,
            source=source,
            actor=actor,
        )

    def resolve(
        self, identifier: str, *, namespace: str | None = None
    ) -> EntityResolutionResult | None:
        """Resolves an ID, alias, or label to a canonical active Entity."""
        # 1. Exact ID check
        entity = self._store.get_entity(identifier)
        if entity is not None:
            if entity.merged_into is not None:
                canonical = self._resolve_merge_chain(entity.id)
                return EntityResolutionResult(entity=canonical, match_type="canonical_merge")
            return EntityResolutionResult(entity=entity, match_type="exact_id")

        # 2. Alias match
        normalized = identifier.strip().lower()
        for a in self._aliases:
            if a.alias.strip().lower() == normalized:
                if namespace is None or a.namespace == namespace or a.namespace == "global":
                    canonical = self._resolve_merge_chain(a.canonical_id)
                    return EntityResolutionResult(
                        entity=canonical, match_type="alias", confidence=a.confidence
                    )

        # 3. Normalized label match
        for e in self._store.all_entities():
            if e.is_active and e.label.strip().lower() == normalized:
                if namespace is None or getattr(e, "namespace", "global") == namespace:
                    return EntityResolutionResult(entity=e, match_type="normalized_label")

        return None

    def candidates(
        self, label: str, *, entity_type: str | None = None, namespace: str | None = None
    ) -> list[Entity]:
        """Find candidate entities matching by label or alias."""
        normalized = label.strip().lower()
        matches: list[Entity] = []
        seen_ids = set()

        # Check direct entities
        for e in self._store.all_entities():
            if not e.is_active:
                continue
            if entity_type and e.type != entity_type:
                continue
            if namespace and getattr(e, "namespace", "global") not in (namespace, "global"):
                continue

            if normalized in e.label.strip().lower():
                matches.append(e)
                seen_ids.add(e.id)

        # Check aliases
        for a in self._aliases:
            if normalized in a.alias.strip().lower() and a.canonical_id not in seen_ids:
                canonical = self._store.get_entity(a.canonical_id)
                if canonical and canonical.is_active:
                    if entity_type and canonical.type != entity_type:
                        continue
                    matches.append(canonical)
                    seen_ids.add(canonical.id)

        return matches

    def merge(self, canonical_id: str, duplicate_ids: list[str]) -> ConsolidationResult:
        # Filter out self-merges
        valid_dups = [d for d in duplicate_ids if d != canonical_id]
        if not valid_dups:
            return ConsolidationResult(canonical_id=canonical_id, merged_ids=[])

        # Check cycle prevention before merge
        for dup_id in valid_dups:
            curr = canonical_id
            while curr:
                e = self._store.get_entity(curr)
                if e and e.merged_into == dup_id:
                    raise ValueError(
                        f"Cycle detected: {canonical_id} was already merged into {dup_id}"
                    )
                curr = e.merged_into if e else None

        return self._consolidation.merge_entities(canonical_id, valid_dups)

    def _resolve_merge_chain(self, entity_id: str) -> Entity:
        visited = {entity_id}
        current_id = entity_id
        current_entity = self._store.get_entity(entity_id)

        while current_entity and current_entity.merged_into:
            next_id = current_entity.merged_into
            if next_id in visited:
                raise ValueError(f"Cycle detected in entity merge chain at {next_id}")
            visited.add(next_id)
            current_id = next_id
            current_entity = self._store.get_entity(next_id)

        if current_entity is None:
            raise KeyError(f"Terminal entity in merge chain not found: {current_id}")
        return current_entity
