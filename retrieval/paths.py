from collections import deque

from graph.store import GraphStore
from models.statement import StatementStatus
from retrieval.engine import RetrievalEngine, RetrievalResult


class PathFinder:
    """Finds directed and undirected path chains between entities in the knowledge graph."""

    def __init__(self, store: GraphStore, engine: RetrievalEngine | None = None) -> None:
        self._store = store
        self._engine = engine or RetrievalEngine(store)

    def find_shortest_path(
        self,
        start_entity_id: str,
        end_entity_id: str,
        *,
        max_depth: int = 4,
        directed: bool = True,
    ) -> list[RetrievalResult] | None:
        """Finds the shortest path of statements connecting start_entity_id to end_entity_id."""
        paths = self.find_all_paths(
            start_entity_id, end_entity_id, max_depth=max_depth, directed=directed
        )
        if not paths:
            return None
        return min(paths, key=len)

    def find_all_paths(
        self,
        start_entity_id: str,
        end_entity_id: str,
        *,
        max_depth: int = 3,
        directed: bool = True,
        predicate_whitelist: list[str] | None = None,
    ) -> list[list[RetrievalResult]]:
        """Finds all paths of statement hops from start_entity_id to end_entity_id up to max_depth."""
        if start_entity_id == end_entity_id:
            return []

        whitelist = set(predicate_whitelist) if predicate_whitelist else None
        all_paths: list[list[RetrievalResult]] = []

        # Queue contains: (current_node_id, path_of_results, visited_node_ids)
        queue: deque[tuple[str, list[RetrievalResult], set[str]]] = deque(
            [(start_entity_id, [], {start_entity_id})]
        )

        while queue:
            curr_id, path, visited = queue.popleft()

            if len(path) >= max_depth:
                continue

            # Forward edges (subject -> object)
            for stmt in self._store.statements_for_subject(curr_id, status=StatementStatus.ACTIVE):
                rel = self._store.get_relation(stmt.relation_id)
                if whitelist and rel and rel.label not in whitelist:
                    continue

                next_node = stmt.object_id
                hydrated = self._engine._hydrate(stmt)
                new_path = path + [hydrated]

                if next_node == end_entity_id:
                    all_paths.append(new_path)
                elif next_node not in visited and len(new_path) < max_depth:
                    queue.append((next_node, new_path, visited | {next_node}))

            # Backward edges (object -> subject) if undirected
            if not directed:
                for stmt in self._store.statements_for_object(
                    curr_id, status=StatementStatus.ACTIVE
                ):
                    rel = self._store.get_relation(stmt.relation_id)
                    if whitelist and rel and rel.label not in whitelist:
                        continue

                    next_node = stmt.subject_id
                    hydrated = self._engine._hydrate(stmt)
                    new_path = path + [hydrated]

                    if next_node == end_entity_id:
                        all_paths.append(new_path)
                    elif next_node not in visited and len(new_path) < max_depth:
                        queue.append((next_node, new_path, visited | {next_node}))

        return all_paths
