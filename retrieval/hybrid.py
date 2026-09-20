from dataclasses import dataclass

from embeddings.store import EmbeddingStore
from graph.store import GraphStore
from models.entity import Entity


@dataclass
class HybridSearchResult:
    entity: Entity
    score: float
    lexical_rank: int | None = None
    vector_rank: int | None = None


class HybridSearchEngine:
    """Fuses keyword lexical search and dense embedding vector search using Reciprocal Rank Fusion (RRF)."""

    def __init__(self, store: GraphStore, embeddings: EmbeddingStore) -> None:
        self._store = store
        self._embeddings = embeddings

    def search(
        self,
        query_text: str | None = None,
        query_vector: list[float] | None = None,
        *,
        top_k: int = 10,
        namespaces: str | list[str] | None = None,
    ) -> list[HybridSearchResult]:
        candidate_entities = self._store.all_entities()
        if namespaces:
            ns_set = {namespaces} if isinstance(namespaces, str) else set(namespaces)
            candidate_entities = [
                e for e in candidate_entities if getattr(e, "namespace", "global") in ns_set
            ]
        allowed_entity_ids = {entity.id for entity in candidate_entities}

        lexical_ranks: dict[str, int] = {}
        if query_text:
            normalized_query = query_text.strip().lower()
            scored: list[tuple[Entity, float]] = []

            for entity in candidate_entities:
                if not entity.is_active:
                    continue
                label_norm = entity.label.strip().lower()
                score = 0.0
                if normalized_query == label_norm:
                    score = 10.0
                elif normalized_query in label_norm:
                    score = 5.0
                elif any(word in label_norm for word in normalized_query.split()):
                    score = 2.0

                # Search properties
                for prop_val in entity.properties.values():
                    if str(prop_val).strip().lower() in normalized_query:
                        score += 1.0

                if score > 0.0:
                    scored.append((entity, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            for rank, (entity, _) in enumerate(scored, start=1):
                lexical_ranks[entity.id] = rank

        vector_ranks: dict[str, int] = {}
        if query_vector:
            raw_vec_results = self._embeddings.search(query_vector, top_k=top_k * 3)
            for rank, v_record in enumerate(raw_vec_results, start=1):
                vector_ranks[v_record.entity_id] = rank

        # Combine via Reciprocal Rank Fusion (RRF)
        all_candidate_ids = set(lexical_ranks.keys()) | set(vector_ranks.keys())
        if not all_candidate_ids and not query_text and not query_vector:
            # Return active entities if query is empty
            return [
                HybridSearchResult(entity=e, score=1.0)
                for e in candidate_entities[:top_k]
                if e.is_active
            ]

        rrf_scores: list[HybridSearchResult] = []
        k_constant = 60.0

        for eid in all_candidate_ids:
            if eid not in allowed_entity_ids:
                continue
            entity = self._store.get_entity(eid)
            if entity is None or not entity.is_active:
                continue

            l_rank = lexical_ranks.get(eid)
            v_rank = vector_ranks.get(eid)

            score = 0.0
            if l_rank is not None:
                score += 1.0 / (k_constant + l_rank)
            if v_rank is not None:
                score += 1.0 / (k_constant + v_rank)

            rrf_scores.append(
                HybridSearchResult(
                    entity=entity,
                    score=round(score, 6),
                    lexical_rank=l_rank,
                    vector_rank=v_rank,
                )
            )

        rrf_scores.sort(key=lambda x: x.score, reverse=True)
        return rrf_scores[:top_k]
