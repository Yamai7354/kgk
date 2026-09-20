from conflicts.models import Conflict, ConflictType
from events.models import EventType, KnowledgeEvent
from events.store import EventStore
from graph.store import GraphStore
from models.statement import Statement, StatementStatus
from ontology.registry import RelationRegistry
from temporal.models import TimeInterval


class ConflictDetector:
    """Scans for functional predicate violations, multi-value contradictions, and temporal overlaps."""

    def __init__(
        self,
        store: GraphStore,
        ontology: RelationRegistry,
        events: EventStore | None = None,
    ) -> None:
        self._store = store
        self._ontology = ontology
        self._events = events

    def check_statement_conflicts(self, statement: Statement) -> list[Conflict]:
        """Checks if a newly asserted statement introduces a conflict with existing active statements."""
        rel = self._store.get_relation(statement.relation_id)
        if rel is None:
            return []

        rel_defn = self._ontology.get(rel.label)
        if rel_defn is None or not rel_defn.is_functional:
            return []

        # Find all active statements for the same subject and relation (matching label)
        active_stmts = []
        for s in self._store.statements_for_subject(
            statement.subject_id, status=StatementStatus.ACTIVE
        ):
            if s.namespace != statement.namespace:
                continue
            s_rel = self._store.get_relation(s.relation_id)
            if s_rel and s_rel.label.lower() == rel.label.lower():
                active_stmts.append(s)

        if len(active_stmts) <= 1:
            return []

        # Check for different object values with overlapping temporal validity
        conflicts: list[Conflict] = []
        stmt_interval = TimeInterval(start=statement.valid_from, end=statement.valid_until)

        for other in active_stmts:
            if other.id == statement.id:
                continue
            if other.object_id == statement.object_id:
                continue

            other_interval = TimeInterval(start=other.valid_from, end=other.valid_until)
            if stmt_interval.overlaps(other_interval):
                conflict = Conflict(
                    conflict_type=ConflictType.FUNCTIONAL_VIOLATION,
                    subject_id=statement.subject_id,
                    relation_id=statement.relation_id,
                    statement_ids=[statement.id, other.id],
                    metadata={
                        "relation_label": rel.label,
                        "objects": [statement.object_id, other.object_id],
                    },
                )
                conflicts.append(conflict)

                if self._events is not None:
                    self._events.append(
                        KnowledgeEvent(
                            event_type=EventType.CONFLICT_DETECTED,
                            target_id=conflict.id,
                            namespace=statement.namespace,
                            payload=conflict.model_dump(mode="json"),
                        )
                    )

        return conflicts
