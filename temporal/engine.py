from datetime import datetime

from events.models import EventType, KnowledgeEvent
from graph.in_memory import InMemoryGraphStore
from models.entity import Entity
from models.relation import Relation
from models.statement import Statement, StatementStatus


class TemporalEngine:
    """Bi-temporal query engine for real-world validity (`as_of`) and system belief replay (`as_known_at`)."""

    def filter_valid_at(self, statements: list[Statement], valid_at: datetime) -> list[Statement]:
        """Returns statements that were true in the real world at `valid_at`."""
        return [s for s in statements if s.is_active and s.is_valid_at(valid_at)]

    def reconstruct_as_known_at(
        self, events: list[KnowledgeEvent], system_dt: datetime
    ) -> InMemoryGraphStore:
        """Reconstructs the exact graph projection as known by the system at `system_dt`."""
        reconstructed = InMemoryGraphStore()

        for event in events:
            if event.timestamp > system_dt:
                continue

            if event.event_type == EventType.ENTITY_CREATE:
                entity = Entity.model_validate(event.payload)
                reconstructed.add_entity(entity)
            elif event.event_type == EventType.RELATION_CREATE:
                relation = Relation.model_validate(event.payload)
                reconstructed.add_relation(relation)
            elif event.event_type == EventType.ASSERT:
                statement = Statement.model_validate(event.payload)
                reconstructed.add_statement(statement)
            elif event.event_type == EventType.RETRACT:
                target_id = event.target_id or event.payload.get("statement_id")
                if target_id:
                    stmt = reconstructed.get_statement(target_id)
                    if stmt:
                        reconstructed.update_statement(
                            stmt.model_copy(
                                update={
                                    "status": StatementStatus.RETRACTED,
                                    "retraction_reason": event.reason,
                                    "retracted_at": event.timestamp,
                                }
                            )
                        )
            elif event.event_type == EventType.SUPERSEDE:
                old_id = event.target_id or event.payload.get("old_statement_id")
                new_id = event.payload.get("new_statement_id")
                if old_id:
                    stmt = reconstructed.get_statement(old_id)
                    if stmt:
                        reconstructed.update_statement(
                            stmt.model_copy(
                                update={
                                    "status": StatementStatus.SUPERSEDED,
                                    "superseded_by": new_id,
                                    "retraction_reason": event.reason,
                                }
                            )
                        )
            elif event.event_type == EventType.ENTITY_MERGE:
                canonical_id = event.target_id or event.payload.get("canonical_id")
                merged_ids = event.payload.get("merged_ids", [])
                for dup_id in merged_ids:
                    dup = reconstructed.get_entity(dup_id)
                    if dup:
                        reconstructed.update_entity(
                            dup.model_copy(
                                update={"merged_into": canonical_id, "updated_at": event.timestamp}
                            )
                        )
                    for stmt in reconstructed.all_statements(status=StatementStatus.ACTIVE):
                        updates = {}
                        if stmt.subject_id == dup_id:
                            updates["subject_id"] = canonical_id
                        if stmt.object_id == dup_id:
                            updates["object_id"] = canonical_id
                        if updates:
                            reconstructed.update_statement(stmt.model_copy(update=updates))

        return reconstructed
