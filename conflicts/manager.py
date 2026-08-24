from datetime import datetime, timezone
from typing import TYPE_CHECKING

from conflicts.models import Conflict, ConflictStatus
from epistemic.models import Perspective
from epistemic.resolver import AuthorityResolver
from events.models import EventType, KnowledgeEvent
from events.store import EventStore
from graph.store import GraphStore
from retraction.service import RetractionService

if TYPE_CHECKING:
    pass


class ConflictManager:
    """Tracks, inspects, and executes resolution policies for detected knowledge conflicts."""

    def __init__(
        self,
        store: GraphStore,
        retraction: RetractionService,
        events: EventStore | None = None,
        resolver: AuthorityResolver | None = None,
    ) -> None:
        self._store = store
        self._retraction = retraction
        self._events = events
        self._resolver = resolver or AuthorityResolver()
        self._conflicts: dict[str, Conflict] = {}

    def add_conflict(self, conflict: Conflict) -> Conflict:
        self._conflicts[conflict.id] = conflict
        return conflict

    def get_conflict(self, conflict_id: str) -> Conflict | None:
        return self._conflicts.get(conflict_id)

    def all_conflicts(self, status: ConflictStatus | None = None) -> list[Conflict]:
        if status is None:
            return list(self._conflicts.values())
        return [c for c in self._conflicts.values() if c.status == status]

    def resolve_by_authority(
        self,
        conflict_id: str,
        perspective: Perspective | None = None,
        retract_losing: bool = True,
        actor: str = "conflict-manager",
    ) -> Conflict:
        conflict = self.get_conflict(conflict_id)
        if conflict is None:
            raise KeyError(f"Conflict not found: {conflict_id}")
        if conflict.status == ConflictStatus.RESOLVED:
            return conflict

        statements = [
            self._store.get_statement(sid)
            for sid in conflict.statement_ids
            if self._store.get_statement(sid) is not None
        ]

        winner = self._resolver.resolve_winner(statements, perspective=perspective)
        if winner is None:
            raise ValueError(f"No viable candidate could be resolved for conflict {conflict_id}")

        if retract_losing:
            for stmt in statements:
                if stmt.id != winner.id and stmt.is_active:
                    self._retraction.retract(
                        stmt.id,
                        reason=f"Resolved conflict {conflict_id} in favor of statement {winner.id}",
                        actor=actor,
                    )

        resolved_conflict = conflict.model_copy(
            update={
                "status": ConflictStatus.RESOLVED,
                "winning_statement_id": winner.id,
                "resolution_reason": f"Resolved by authority weighting (winner={winner.id})",
                "resolved_at": datetime.now(timezone.utc),
            }
        )
        self._conflicts[conflict_id] = resolved_conflict

        if self._events is not None:
            self._events.append(
                KnowledgeEvent(
                    event_type=EventType.CONFLICT_RESOLVED,
                    target_id=conflict_id,
                    actor=actor,
                    payload=resolved_conflict.model_dump(mode="json"),
                )
            )

        return resolved_conflict
