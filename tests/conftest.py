import pytest

from kernel import KnowledgeGraphKernel
from provenance import ProvenanceRecord


@pytest.fixture
def kgk() -> KnowledgeGraphKernel:
    return KnowledgeGraphKernel()


@pytest.fixture
def provenance() -> ProvenanceRecord:
    return ProvenanceRecord(source="test", confidence=0.9)
