from typing import TYPE_CHECKING

from drivers.extractors import Extractor
from drivers.models import Document
from ingestion.pipeline import IngestionResult
from models.statement import StatementCreate

if TYPE_CHECKING:
    from kernel import KnowledgeGraphKernel


class DocumentPipeline:
    """Orchestrates document extraction and atomic statement batch ingestion."""

    def __init__(self, kernel: "KnowledgeGraphKernel") -> None:
        self._kernel = kernel

    def ingest_document(self, document: Document, extractor: Extractor) -> list[IngestionResult]:
        statements = extractor.extract(document)
        return self.ingest_batch(statements)

    def ingest_batch(self, statement_creates: list[StatementCreate]) -> list[IngestionResult]:
        results: list[IngestionResult] = []
        for stmt_create in statement_creates:
            res = self._kernel.ingest(stmt_create)
            results.append(res)
        return results
