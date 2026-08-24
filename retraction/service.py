from dataclasses import dataclass
from datetime import datetime, timezone

from events.models import EventType, KnowledgeEvent
from events.store import EventStore
from graph.store import GraphStore
from models.statement import Statement, StatementStatus
from provenance.models import ProvenanceRecord
from provenance.tracker import ProvenanceTracker


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RetractionResult:
    statement: Statement
    reason: str


class RetractionService:
    """Invalidate statements while preserving audit history via events."""

    def __init__(
        self,
        store: GraphStore,
        provenance: ProvenanceTracker,
        events: EventStore | None = None,
    ) -> None:
        self._store = store
        self._provenance = provenance
        self._events = events

    def retract(
        self,
        statement_id: str,
        reason: str,
        *,
        source: str = "retraction-service",
        actor: str = "system",
        namespace: str = "global",
    ) -> RetractionResult:
        statement = self._store.get_statement(statement_id)
        if statement is None:
            raise KeyError(f"Statement not found: {statement_id}")
        if statement.status != StatementStatus.ACTIVE:
            raise ValueError(f"Statement {statement_id} is already {statement.status.value}")

        # 1. Authoritative Event
        if self._events is not None:
            self._events.append(
                KnowledgeEvent(
                    event_type=EventType.RETRACT,
                    target_id=statement_id,
                    namespace=namespace,
                    actor=actor,
                    reason=reason,
                    payload={"statement_id": statement_id},
                )
            )

        # 2. Provenance audit
        audit = ProvenanceRecord(source=source, metadata={"retraction_reason": reason})
        self._provenance.record_retraction(statement_id, audit, reason)

        # 3. Projected View Update
        updated = statement.model_copy(
            update={
                "status": StatementStatus.RETRACTED,
                "retracted_at": _utcnow(),
                "retraction_reason": reason,
            }
        )
        self._store.update_statement(updated)

        return RetractionResult(statement=updated, reason=reason)

    def supersede(
        self,
        old_statement_id: str,
        new_statement: Statement,
        reason: str = "superseded",
        *,
        source: str = "retraction-service",
        actor: str = "system",
        namespace: str = "global",
    ) -> tuple[Statement, Statement]:
        old = self._store.get_statement(old_statement_id)
        if old is None:
            raise KeyError(f"Statement not found: {old_statement_id}")

        # 1. Authoritative Event
        if self._events is not None:
            self._events.append(
                KnowledgeEvent(
                    event_type=EventType.SUPERSEDE,
                    target_id=old_statement_id,
                    namespace=namespace,
                    actor=actor,
                    reason=reason,
                    payload={
                        "old_statement_id": old_statement_id,
                        "new_statement_id": new_statement.id,
                    },
                )
            )

        # 2. Provenance audit
        audit = ProvenanceRecord(source=source, metadata={"supersede_reason": reason})
        self._provenance.record_superseded(old_statement_id, audit, reason)

        # 3. Projected View Update
        updated_old = old.model_copy(
            update={
                "status": StatementStatus.SUPERSEDED,
                "superseded_by": new_statement.id,
                "retraction_reason": reason,
            }
        )
        self._store.update_statement(updated_old)

        return updated_old, new_statement

    def resolve_chain(self, statement_id: str) -> list[str]:
        """Resolves the sequence of supersession transitions starting from statement_id."""
        chain = [statement_id]
        visited = {statement_id}
        current_id = statement_id

        while True:
            stmt = self._store.get_statement(current_id)
            if stmt is None or stmt.superseded_by is None:
                break
            next_id = stmt.superseded_by
            if next_id in visited:
                raise ValueError(f"Cycle detected in supersession chain at {next_id}")
            chain.append(next_id)
            visited.add(next_id)
            current_id = next_id

        return chain
