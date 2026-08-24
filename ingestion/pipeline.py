from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from events.models import EventType, KnowledgeEvent
from events.store import EventStore
from graph.store import GraphStore
from models.entity import Entity, EntityCreate
from models.relation import Relation, RelationCreate
from models.statement import Statement, StatementCreate, StatementStatus
from ontology.registry import RelationRegistry
from provenance.tracker import ProvenanceTracker

if TYPE_CHECKING:
    from entities.service import EntityService


@dataclass
class IngestionResult:
    statement: Statement
    subject: Entity
    relation: Relation
    object: Entity
    created_entities: list[Entity] = field(default_factory=list)
    created_relations: list[Relation] = field(default_factory=list)


class IngestionPipeline:
    """Validate and persist statements, enforce schema ontologies, resolve aliases, and emit events."""

    def __init__(
        self,
        store: GraphStore,
        provenance: ProvenanceTracker,
        events: EventStore | None = None,
        entity_service: "EntityService | None" = None,
        ontology: RelationRegistry | None = None,
        strict_schema: bool = False,
    ) -> None:
        self._store = store
        self._provenance = provenance
        self._events = events
        self._entity_service = entity_service
        self._ontology = ontology or RelationRegistry()
        self.strict_schema = strict_schema

    def ingest(
        self, payload: StatementCreate, strict_schema: bool | None = None
    ) -> IngestionResult:
        subject, subject_created = self._resolve_entity(
            payload.subject, namespace=payload.namespace
        )
        relation, relation_created = self._resolve_relation(payload.relation)
        obj, object_created = self._resolve_entity(payload.object, namespace=payload.namespace)

        # Validate against Relation Ontology
        is_strict = self.strict_schema if strict_schema is None else strict_schema
        self._ontology.validate_statement(
            subject_type=subject.type,
            relation_label=relation.label,
            object_type=obj.type,
            strict=is_strict,
        )

        created_entities = [
            e for e, created in [(subject, subject_created), (obj, object_created)] if created
        ]
        created_relations = [relation] if relation_created else []

        # Deduplication & Confidence Reinforcement Check
        existing_stmts = self._store.statements_for_subject(
            subject.id, status=StatementStatus.ACTIVE
        )
        for existing in existing_stmts:
            if (
                existing.relation_id == relation.id
                and existing.object_id == obj.id
                and getattr(existing, "namespace", "global") == payload.namespace
                and existing.valid_from == payload.valid_from
                and existing.valid_until == payload.valid_until
            ):
                # Reinforce confidence via Bayesian fusion
                c1 = (
                    existing.provenance.confidence
                    if existing.provenance.confidence is not None
                    else 0.8
                )
                c2 = (
                    payload.provenance.confidence
                    if payload.provenance.confidence is not None
                    else 0.8
                )
                reinforced_c = round(1.0 - (1.0 - c1) * (1.0 - c2), 4)

                new_prov = existing.provenance.model_copy(update={"confidence": reinforced_c})
                reinforced_stmt = existing.model_copy(update={"provenance": new_prov})
                self._store.update_statement(reinforced_stmt)

                self._provenance.record_ingestion(existing.id, payload.provenance)

                if self._events is not None:
                    self._events.append(
                        KnowledgeEvent(
                            event_type=EventType.PROVENANCE_ATTACH,
                            target_id=existing.id,
                            namespace=payload.namespace,
                            actor="ingestion-pipeline",
                            payload={
                                "source": payload.provenance.source,
                                "source_id": payload.provenance.source_id,
                                "reinforced_confidence": reinforced_c,
                            },
                        )
                    )

                return IngestionResult(
                    statement=reinforced_stmt,
                    subject=subject,
                    relation=relation,
                    object=obj,
                    created_entities=created_entities,
                    created_relations=created_relations,
                )

        statement = Statement(
            subject_id=subject.id,
            relation_id=relation.id,
            object_id=obj.id,
            provenance=payload.provenance,
            namespace=payload.namespace,
            properties=payload.properties,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
            epistemic_status=payload.epistemic_status,
        )
        self._store.add_statement(statement)

        # Emit authoritative ASSERT event
        if self._events is not None:
            self._events.append(
                KnowledgeEvent(
                    event_type=EventType.ASSERT,
                    target_id=statement.id,
                    namespace=payload.namespace,
                    actor="ingestion-pipeline",
                    payload=statement.model_dump(mode="json"),
                )
            )

        self._provenance.record_ingestion(statement.id, payload.provenance)

        return IngestionResult(
            statement=statement,
            subject=subject,
            relation=relation,
            object=obj,
            created_entities=created_entities,
            created_relations=created_relations,
        )

    def _resolve_entity(
        self, value: Entity | EntityCreate, namespace: str = "global"
    ) -> tuple[Entity, bool]:
        if isinstance(value, Entity):
            existing = self._store.get_entity(value.id)
            if existing is not None:
                return existing, False

        # If EntityService is present, attempt alias and merge resolution
        if self._entity_service is not None:
            match = self._entity_service.resolve(value.label, namespace=namespace)
            if match is not None and match.match_type in ("exact_id", "alias", "canonical_merge"):
                return match.entity, False

        # Check if an active entity with the exact same label already exists in the same namespace
        for existing in self._store.all_entities():
            if (
                existing.is_active
                and existing.label == value.label
                and getattr(existing, "namespace", "global") == namespace
            ):
                return existing, False

        dumped = value.model_dump()
        dumped["namespace"] = namespace
        entity = Entity.model_validate(dumped) if not isinstance(value, Entity) else value
        if getattr(entity, "namespace", "global") != namespace:
            entity = entity.model_copy(update={"namespace": namespace})

        self._store.add_entity(entity)
        if self._events is not None:
            self._events.append(
                KnowledgeEvent(
                    event_type=EventType.ENTITY_CREATE,
                    target_id=entity.id,
                    namespace=namespace,
                    payload=entity.model_dump(mode="json"),
                )
            )
        return entity, True

    def _resolve_relation(self, value: Relation | RelationCreate) -> tuple[Relation, bool]:
        if isinstance(value, Relation):
            existing = self._store.get_relation(value.id)
            if existing is not None:
                return existing, False

        # Check if relation with same label already exists
        for existing in self._store.all_relations():
            if existing.label.lower() == value.label.lower():
                return existing, False

        relation = Relation.model_validate(value.model_dump())
        self._store.add_relation(relation)
        if self._events is not None:
            self._events.append(
                KnowledgeEvent(
                    event_type=EventType.RELATION_CREATE,
                    target_id=relation.id,
                    payload=relation.model_dump(mode="json"),
                )
            )
        return relation, True
