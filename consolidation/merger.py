from dataclasses import dataclass, field
from datetime import datetime, timezone

from events.models import EventType, KnowledgeEvent
from events.store import EventStore
from graph.store import GraphStore
from models.entity import Entity
from models.statement import Statement, StatementStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ConsolidationResult:
    canonical_id: str
    merged_ids: list[str]
    rewired_statements: list[Statement] = field(default_factory=list)


class ConsolidationService:
    """Merge duplicate entities and rewire affected statements with event provenance."""

    def __init__(self, store: GraphStore, events: EventStore | None = None) -> None:
        self._store = store
        self._events = events

    def merge_entities(
        self,
        canonical_id: str,
        duplicate_ids: list[str],
        *,
        actor: str = "system",
        namespace: str = "global",
    ) -> ConsolidationResult:
        canonical = self._store.get_entity(canonical_id)
        if canonical is None:
            raise KeyError(f"Canonical entity not found: {canonical_id}")
        if canonical.merged_into is not None:
            raise ValueError(f"Entity {canonical_id} was already merged away")

        merged: list[str] = []
        rewired: list[Statement] = []

        for dup_id in duplicate_ids:
            if dup_id == canonical_id:
                continue
            duplicate = self._store.get_entity(dup_id)
            if duplicate is None:
                raise KeyError(f"Duplicate entity not found: {dup_id}")

            tombstone = duplicate.model_copy(
                update={"merged_into": canonical_id, "updated_at": _utcnow()}
            )
            self._store.update_entity(tombstone)
            merged.append(dup_id)

            for stmt in self._store.all_statements(status=StatementStatus.ACTIVE):
                updated = self._rewire_statement(stmt, dup_id, canonical_id)
                if updated is not None:
                    self._store.update_statement(updated)
                    rewired.append(updated)

        if merged and self._events is not None:
            self._events.append(
                KnowledgeEvent(
                    event_type=EventType.ENTITY_MERGE,
                    target_id=canonical_id,
                    namespace=namespace,
                    actor=actor,
                    payload={"canonical_id": canonical_id, "merged_ids": merged},
                )
            )

        return ConsolidationResult(
            canonical_id=canonical_id,
            merged_ids=merged,
            rewired_statements=rewired,
        )

    def find_duplicates_by_label(self, label: str) -> list[Entity]:
        normalized = label.strip().lower()
        return [
            e
            for e in self._store.all_entities()
            if e.is_active and e.label.strip().lower() == normalized
        ]

    def _rewire_statement(self, statement: Statement, old_id: str, new_id: str) -> Statement | None:
        updates = {}
        if statement.subject_id == old_id:
            updates["subject_id"] = new_id
        if statement.object_id == old_id:
            updates["object_id"] = new_id
        if updates:
            return statement.model_copy(update=updates)
        return None
