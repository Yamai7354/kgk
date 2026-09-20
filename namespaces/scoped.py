from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from drivers.extractors import Extractor
from drivers.models import Document
from epistemic.models import Perspective
from events.models import KnowledgeEvent
from ingestion.pipeline import IngestionResult
from models.entity import Entity
from models.statement import Statement, StatementCreate
from retraction.service import RetractionResult
from retrieval.engine import RetrievalResult
from retrieval.hybrid import HybridSearchResult

if TYPE_CHECKING:
    from kernel import KnowledgeGraphKernel


class NamespaceAccessError(PermissionError):
    """Raised when an operation crosses the namespace capability boundary."""


@dataclass(frozen=True)
class NamespaceScope:
    """A host-issued capability that binds KGK operations to one namespace."""

    kernel: "KnowledgeGraphKernel"
    namespace: str
    actor: str = "system"

    def __post_init__(self) -> None:
        self.kernel.namespaces.require(self.namespace)

    @property
    def read_namespaces(self) -> list[str]:
        return self.kernel.namespaces.resolve_read_scope(self.namespace)

    def _require_write(self) -> None:
        if not self.kernel.namespaces.is_writable(self.namespace):
            raise NamespaceAccessError(f"Namespace is read-only: {self.namespace}")

    def _require_read_namespace(self, namespace: str) -> None:
        if namespace not in self.read_namespaces:
            raise NamespaceAccessError(
                f"Namespace {namespace!r} is outside read scope for {self.namespace!r}"
            )

    def _require_owned_namespace(self, namespace: str) -> None:
        if namespace != self.namespace:
            raise NamespaceAccessError(
                f"Namespace {namespace!r} is not writable through {self.namespace!r}"
            )

    def ingest(
        self, payload: StatementCreate, strict_schema: bool | None = None
    ) -> IngestionResult:
        self._require_write()
        self._require_owned_namespace(payload.namespace)
        for value in (payload.subject, payload.relation, payload.object):
            self._require_owned_namespace(value.namespace)
        return self.kernel.ingest(payload, strict_schema=strict_schema)

    def ingest_document(
        self, document: Document, extractor: Extractor
    ) -> list[IngestionResult]:
        self._require_write()
        self._require_owned_namespace(document.namespace)
        return self.kernel.ingest_document(document, extractor)

    def ingest_batch(self, statements: list[StatementCreate]) -> list[IngestionResult]:
        return [self.ingest(statement) for statement in statements]

    def get_statement(self, statement_id: str) -> RetrievalResult | None:
        result = self.kernel.retrieve.get_statement(statement_id)
        if result is None:
            return None
        self._require_read_namespace(result.statement.namespace)
        return result

    def get_entity(self, entity_id: str) -> Entity | None:
        entity = self.kernel.store.get_entity(entity_id)
        if entity is None:
            return None
        self._require_read_namespace(entity.namespace)
        return entity

    def all_entities(self) -> list[Entity]:
        allowed = set(self.read_namespaces)
        return [entity for entity in self.kernel.store.all_entities() if entity.namespace in allowed]

    def query(
        self,
        subject_id: str | None = None,
        object_id: str | None = None,
        relation_id: str | None = None,
        *,
        include_retracted: bool = False,
    ) -> list[RetrievalResult]:
        return self.kernel.query_scoped(
            subject_id=subject_id,
            object_id=object_id,
            relation_id=relation_id,
            namespaces=self.read_namespaces,
            include_retracted=include_retracted,
        )

    def search_hybrid(
        self,
        query_text: str | None = None,
        query_vector: list[float] | None = None,
        *,
        top_k: int = 10,
    ) -> list[HybridSearchResult]:
        return self.kernel.search_hybrid(
            query_text=query_text,
            query_vector=query_vector,
            top_k=top_k,
            namespaces=self.read_namespaces,
        )

    def find_paths(
        self,
        start_entity_id: str,
        end_entity_id: str,
        *,
        max_depth: int = 3,
        directed: bool = True,
        predicate_whitelist: list[str] | None = None,
    ) -> list[list[RetrievalResult]]:
        start = self.get_entity(start_entity_id)
        end = self.get_entity(end_entity_id)
        if start is None:
            raise KeyError(f"Entity not found: {start_entity_id}")
        if end is None:
            raise KeyError(f"Entity not found: {end_entity_id}")
        return self.kernel.find_paths(
            start_entity_id,
            end_entity_id,
            max_depth=max_depth,
            directed=directed,
            predicate_whitelist=predicate_whitelist,
            namespaces=self.read_namespaces,
        )

    def format_neighborhood(
        self,
        entity_id: str,
        depth: int = 1,
        *,
        max_chars: int = 4000,
        format_type: str = "markdown",
    ) -> str | list[dict[str, Any]]:
        entity = self.get_entity(entity_id)
        if entity is None:
            raise KeyError(f"Entity not found: {entity_id}")
        return self.kernel.format_neighborhood(
            entity_id,
            depth=depth,
            max_chars=max_chars,
            format_type=format_type,
            namespaces=self.read_namespaces,
        )

    def as_of(
        self, valid_at: datetime, *, subject_id: str | None = None
    ) -> list[RetrievalResult]:
        return self.kernel.as_of(
            valid_at, subject_id=subject_id, namespaces=self.read_namespaces
        )

    def view_perspective(
        self, perspective: Perspective, *, subject_id: str | None = None
    ) -> list[RetrievalResult]:
        return self.kernel.view_perspective(
            perspective, subject_id=subject_id, namespaces=self.read_namespaces
        )

    def events(self) -> list[KnowledgeEvent]:
        allowed = set(self.read_namespaces)
        return [event for event in self.kernel.events.all_events() if event.namespace in allowed]

    def retract(self, statement_id: str, reason: str, **kwargs: Any) -> RetractionResult:
        self._require_write()
        statement = self.kernel.store.get_statement(statement_id)
        if statement is None:
            raise KeyError(f"Statement not found: {statement_id}")
        self._require_owned_namespace(statement.namespace)
        return self.kernel.retract(
            statement_id,
            reason,
            actor=kwargs.pop("actor", self.actor),
            namespace=self.namespace,
            **kwargs,
        )

    def supersede(
        self,
        old_statement_id: str,
        new_statement: Statement,
        reason: str = "superseded",
        **kwargs: Any,
    ) -> tuple[Statement, Statement]:
        self._require_write()
        old_statement = self.kernel.store.get_statement(old_statement_id)
        if old_statement is None:
            raise KeyError(f"Statement not found: {old_statement_id}")
        self._require_owned_namespace(old_statement.namespace)
        self._require_owned_namespace(new_statement.namespace)
        return self.kernel.supersede(
            old_statement_id,
            new_statement,
            reason=reason,
            actor=kwargs.pop("actor", self.actor),
            namespace=self.namespace,
            **kwargs,
        )

    def merge_entities(self, canonical_id: str, duplicate_ids: list[str]):
        self._require_write()
        for entity_id in [canonical_id, *duplicate_ids]:
            entity = self.kernel.store.get_entity(entity_id)
            if entity is None:
                raise KeyError(f"Entity not found: {entity_id}")
            self._require_owned_namespace(entity.namespace)
        return self.kernel.merge_entities(
            canonical_id,
            duplicate_ids,
            actor=self.actor,
            namespace=self.namespace,
        )
