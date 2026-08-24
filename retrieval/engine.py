from dataclasses import dataclass, field

from graph.store import GraphStore
from models.entity import Entity
from models.relation import Relation
from models.statement import Statement, StatementStatus


@dataclass
class RetrievalResult:
    statement: Statement
    subject: Entity | None = None
    relation: Relation | None = None
    object: Entity | None = None


@dataclass
class SubgraphResult:
    root_entity_id: str
    depth: int
    statements: list[RetrievalResult] = field(default_factory=list)


class RetrievalEngine:
    """Query the knowledge graph by node, edge, neighborhood, and namespace scopes."""

    def __init__(self, store: GraphStore) -> None:
        self._store = store

    def by_subject(
        self,
        subject_id: str,
        *,
        include_retracted: bool = False,
        namespaces: str | list[str] | None = None,
    ) -> list[RetrievalResult]:
        status = None if include_retracted else StatementStatus.ACTIVE
        statements = self._store.statements_for_subject(subject_id, status=status)
        filtered = self._filter_namespaces(statements, namespaces)
        return [self._hydrate(s) for s in filtered]

    def by_object(
        self,
        object_id: str,
        *,
        include_retracted: bool = False,
        namespaces: str | list[str] | None = None,
    ) -> list[RetrievalResult]:
        status = None if include_retracted else StatementStatus.ACTIVE
        statements = self._store.statements_for_object(object_id, status=status)
        filtered = self._filter_namespaces(statements, namespaces)
        return [self._hydrate(s) for s in filtered]

    def by_relation(
        self,
        relation_id: str,
        *,
        include_retracted: bool = False,
        namespaces: str | list[str] | None = None,
    ) -> list[RetrievalResult]:
        status = None if include_retracted else StatementStatus.ACTIVE
        statements = self._store.statements_by_relation(relation_id, status=status)
        filtered = self._filter_namespaces(statements, namespaces)
        return [self._hydrate(s) for s in filtered]

    def get_statement(self, statement_id: str) -> RetrievalResult | None:
        statement = self._store.get_statement(statement_id)
        if statement is None:
            return None
        return self._hydrate(statement)

    def neighborhood(
        self,
        entity_id: str,
        depth: int = 1,
        *,
        namespaces: str | list[str] | None = None,
    ) -> SubgraphResult:
        if depth < 1:
            raise ValueError("depth must be >= 1")

        visited_statement_ids: set[str] = set()
        frontier: set[str] = {entity_id}
        collected: list[Statement] = []

        for _ in range(depth):
            next_frontier: set[str] = set()
            for node_id in frontier:
                for stmt in self._store.statements_for_subject(node_id):
                    if stmt.id not in visited_statement_ids:
                        visited_statement_ids.add(stmt.id)
                        collected.append(stmt)
                        next_frontier.add(stmt.object_id)
                for stmt in self._store.statements_for_object(node_id):
                    if stmt.id not in visited_statement_ids:
                        visited_statement_ids.add(stmt.id)
                        collected.append(stmt)
                        next_frontier.add(stmt.subject_id)
            frontier = next_frontier

        filtered = self._filter_namespaces(collected, namespaces)
        return SubgraphResult(
            root_entity_id=entity_id,
            depth=depth,
            statements=[self._hydrate(s) for s in filtered],
        )

    def _filter_namespaces(
        self, statements: list[Statement], namespaces: str | list[str] | None
    ) -> list[Statement]:
        if namespaces is None:
            return statements
        ns_set = {namespaces} if isinstance(namespaces, str) else set(namespaces)
        return [s for s in statements if getattr(s, "namespace", "global") in ns_set]

    def _hydrate(self, statement: Statement) -> RetrievalResult:
        return RetrievalResult(
            statement=statement,
            subject=self._store.get_entity(statement.subject_id),
            relation=self._store.get_relation(statement.relation_id),
            object=self._store.get_entity(statement.object_id),
        )
