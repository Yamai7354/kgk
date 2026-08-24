from models.entity import Entity
from models.relation import Relation
from models.statement import Statement, StatementStatus


class InMemoryGraphStore:
    """Simple in-memory graph backend for development and testing."""

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._relations: dict[str, Relation] = {}
        self._statements: dict[str, Statement] = {}

    def add_entity(self, entity: Entity) -> Entity:
        self._entities[entity.id] = entity
        return entity

    def get_entity(self, entity_id: str) -> Entity | None:
        return self._entities.get(entity_id)

    def update_entity(self, entity: Entity) -> Entity:
        if entity.id not in self._entities:
            raise KeyError(f"Entity not found: {entity.id}")
        self._entities[entity.id] = entity
        return entity

    def add_relation(self, relation: Relation) -> Relation:
        self._relations[relation.id] = relation
        return relation

    def get_relation(self, relation_id: str) -> Relation | None:
        return self._relations.get(relation_id)

    def add_statement(self, statement: Statement) -> Statement:
        self._statements[statement.id] = statement
        return statement

    def get_statement(self, statement_id: str) -> Statement | None:
        return self._statements.get(statement_id)

    def update_statement(self, statement: Statement) -> Statement:
        if statement.id not in self._statements:
            raise KeyError(f"Statement not found: {statement.id}")
        self._statements[statement.id] = statement
        return statement

    def _filter_by_status(
        self, statements: list[Statement], status: StatementStatus | None
    ) -> list[Statement]:
        if status is None:
            return statements
        return [s for s in statements if s.status == status]

    def statements_for_subject(
        self, subject_id: str, *, status: StatementStatus | None = StatementStatus.ACTIVE
    ) -> list[Statement]:
        matches = [s for s in self._statements.values() if s.subject_id == subject_id]
        return self._filter_by_status(matches, status)

    def statements_for_object(
        self, object_id: str, *, status: StatementStatus | None = StatementStatus.ACTIVE
    ) -> list[Statement]:
        matches = [s for s in self._statements.values() if s.object_id == object_id]
        return self._filter_by_status(matches, status)

    def statements_by_relation(
        self, relation_id: str, *, status: StatementStatus | None = StatementStatus.ACTIVE
    ) -> list[Statement]:
        matches = [s for s in self._statements.values() if s.relation_id == relation_id]
        return self._filter_by_status(matches, status)

    def all_entities(self) -> list[Entity]:
        return list(self._entities.values())

    def all_relations(self) -> list[Relation]:
        return list(self._relations.values())

    def all_statements(self, *, status: StatementStatus | None = None) -> list[Statement]:
        return self._filter_by_status(list(self._statements.values()), status)
