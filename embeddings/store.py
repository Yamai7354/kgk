from dataclasses import dataclass
from typing import Protocol


@dataclass
class EmbeddingRecord:
    entity_id: str
    vector: list[float]
    model: str = "default"


@dataclass
class SimilarityResult:
    entity_id: str
    score: float


class EmbeddingStore(Protocol):
    """Abstract interface for entity vector indexes."""

    def upsert(self, record: EmbeddingRecord) -> EmbeddingRecord: ...

    def get(self, entity_id: str) -> EmbeddingRecord | None: ...

    def delete(self, entity_id: str) -> bool: ...

    def search(self, query_vector: list[float], *, top_k: int = 10) -> list[SimilarityResult]: ...


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class InMemoryEmbeddingStore:
    """Simple brute-force vector store for development."""

    def __init__(self) -> None:
        self._records: dict[str, EmbeddingRecord] = {}

    def upsert(self, record: EmbeddingRecord) -> EmbeddingRecord:
        self._records[record.entity_id] = record
        return record

    def get(self, entity_id: str) -> EmbeddingRecord | None:
        return self._records.get(entity_id)

    def delete(self, entity_id: str) -> bool:
        return self._records.pop(entity_id, None) is not None

    def search(self, query_vector: list[float], *, top_k: int = 10) -> list[SimilarityResult]:
        scored = [
            SimilarityResult(entity_id=eid, score=_cosine_similarity(query_vector, rec.vector))
            for eid, rec in self._records.items()
        ]
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]
