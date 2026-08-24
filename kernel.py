"""Central orchestrator wiring all KGK modules together."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from conflicts import ConflictDetector, ConflictManager
from consolidation import ConsolidationService
from drivers.extractors import Extractor
from drivers.models import Document
from drivers.pipeline import DocumentPipeline
from embeddings import EmbeddingStore, InMemoryEmbeddingStore
from entities import EntityService
from epistemic import AuthorityResolver, Perspective, compute_effective_confidence
from events import EventStore, EventType, InMemoryEventStore
from graph import GraphStore, InMemoryGraphStore
from ingestion import IngestionPipeline, IngestionResult
from models import Entity, Relation, Statement, StatementCreate, StatementStatus
from namespaces import NamespaceManager
from ontology import RelationRegistry
from provenance import ProvenanceTracker
from retraction import RetractionResult, RetractionService
from retrieval import (
    HybridSearchEngine,
    HybridSearchResult,
    PathFinder,
    RetrievalEngine,
    RetrievalResult,
    SubgraphFormatter,
)
from temporal import TemporalEngine


@dataclass
class KnowledgeGraphKernel:
    """Authoritative event-sourced facade over all KGK subsystems."""

    events: EventStore = field(default_factory=InMemoryEventStore)
    store: GraphStore = field(default_factory=InMemoryGraphStore)
    provenance: ProvenanceTracker = field(default_factory=ProvenanceTracker)
    embeddings: EmbeddingStore = field(default_factory=InMemoryEmbeddingStore)

    def __post_init__(self) -> None:
        self.namespaces = NamespaceManager()
        self.ontology = RelationRegistry()
        self.temporal = TemporalEngine()
        self.epistemic = AuthorityResolver()
        self.consolidation = ConsolidationService(self.store, self.events)
        self.entities = EntityService(self.store, self.consolidation, self.events)
        self.retraction = RetractionService(self.store, self.provenance, self.events)
        self.conflicts = ConflictManager(
            self.store, self.retraction, self.events, resolver=self.epistemic
        )
        self.conflict_detector = ConflictDetector(self.store, self.ontology, self.events)
        self.ingestion = IngestionPipeline(
            self.store,
            self.provenance,
            self.events,
            entity_service=self.entities,
            ontology=self.ontology,
        )
        self.retrieve = RetrievalEngine(self.store)
        self.hybrid_search = HybridSearchEngine(self.store, self.embeddings)
        self.path_finder = PathFinder(self.store, self.retrieve)
        self.formatter = SubgraphFormatter()
        self.document_pipeline = DocumentPipeline(self)

    def ingest(
        self, payload: StatementCreate, strict_schema: bool | None = None
    ) -> IngestionResult:
        result = self.ingestion.ingest(payload, strict_schema=strict_schema)
        # Automatic conflict detection for functional relations
        detected = self.conflict_detector.check_statement_conflicts(result.statement)
        for c in detected:
            self.conflicts.add_conflict(c)
        return result

    def ingest_document(self, document: Document, extractor: Extractor) -> list[IngestionResult]:
        """Extracts and ingests structured statements from raw documents."""
        return self.document_pipeline.ingest_document(document, extractor)

    def ingest_batch(self, statement_creates: list[StatementCreate]) -> list[IngestionResult]:
        """Ingests a batch of statements atomically with event emission."""
        return self.document_pipeline.ingest_batch(statement_creates)

    def retract(self, statement_id: str, reason: str, **kwargs) -> RetractionResult:
        return self.retraction.retract(statement_id, reason, **kwargs)

    def supersede(
        self, old_statement_id: str, new_statement: Statement, reason: str = "superseded", **kwargs
    ) -> tuple[Statement, Statement]:
        return self.retraction.supersede(old_statement_id, new_statement, reason, **kwargs)

    def merge_entities(self, canonical_id: str, duplicate_ids: list[str]):
        return self.entities.merge(canonical_id, duplicate_ids)

    def resolve_supersession(self, statement_id: str) -> list[str]:
        return self.retraction.resolve_chain(statement_id)

    def search_hybrid(
        self,
        query_text: str | None = None,
        query_vector: list[float] | None = None,
        *,
        top_k: int = 10,
        namespaces: str | list[str] | None = None,
    ) -> list[HybridSearchResult]:
        """Performs RRF-fused lexical keyword and dense vector semantic search."""
        resolved_scopes = self.namespaces.resolve_read_scope(namespaces) if namespaces else None
        return self.hybrid_search.search(
            query_text=query_text,
            query_vector=query_vector,
            top_k=top_k,
            namespaces=resolved_scopes,
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
        """Finds all multi-hop paths between two entities."""
        return self.path_finder.find_all_paths(
            start_entity_id,
            end_entity_id,
            max_depth=max_depth,
            directed=directed,
            predicate_whitelist=predicate_whitelist,
        )

    def shortest_path(
        self,
        start_entity_id: str,
        end_entity_id: str,
        *,
        max_depth: int = 4,
        directed: bool = True,
    ) -> list[RetrievalResult] | None:
        """Finds the shortest path of relations between two entities."""
        return self.path_finder.find_shortest_path(
            start_entity_id,
            end_entity_id,
            max_depth=max_depth,
            directed=directed,
        )

    def format_neighborhood(
        self,
        entity_id: str,
        depth: int = 1,
        *,
        max_chars: int = 4000,
        format_type: str = "markdown",
    ) -> str | list[dict[str, Any]]:
        """Extracts and formats an entity neighborhood for context windows."""
        subgraph = self.retrieve.neighborhood(entity_id, depth=depth)
        if format_type == "mermaid":
            return self.formatter.format_mermaid(subgraph.statements, max_chars=max_chars)
        elif format_type == "json_ld":
            return self.formatter.format_json_ld(subgraph.statements)
        return self.formatter.format_markdown(subgraph.statements, max_chars=max_chars)

    def effective_confidence(
        self,
        statement: Statement,
        *,
        half_life_seconds: float | None = None,
        as_of: datetime | None = None,
    ) -> float:
        """Computes time-decayed confidence for dynamic facts."""
        return compute_effective_confidence(
            statement, half_life_seconds=half_life_seconds, as_of=as_of
        )

    def as_of(
        self,
        valid_at: datetime,
        *,
        subject_id: str | None = None,
        namespaces: str | list[str] | None = None,
    ) -> list[RetrievalResult]:
        """Query knowledge that was valid in reality at `valid_at`."""
        if subject_id:
            results = self.query_scoped(subject_id=subject_id, namespaces=namespaces)
        else:
            all_stmts = self.store.all_statements(status=StatementStatus.ACTIVE)
            results = [self.retrieve._hydrate(s) for s in all_stmts]

        valid_results = [r for r in results if r.statement.is_valid_at(valid_at)]
        return valid_results

    def as_known_at(self, system_time: datetime) -> InMemoryGraphStore:
        """Point-in-time graph state reconstruction at historical system time."""
        return self.temporal.reconstruct_as_known_at(self.events.all_events(), system_time)

    def view_perspective(
        self,
        perspective: Perspective,
        *,
        subject_id: str | None = None,
        namespaces: str | list[str] | None = None,
    ) -> list[RetrievalResult]:
        """Query knowledge filtered and prioritized according to a worldview/perspective."""
        results = (
            self.query_scoped(subject_id=subject_id, namespaces=namespaces)
            if subject_id
            else [
                self.retrieve._hydrate(s)
                for s in self.store.all_statements(status=StatementStatus.ACTIVE)
            ]
        )
        return [r for r in results if r.statement.epistemic_status in perspective.accepted_statuses]

    def query_scoped(
        self,
        subject_id: str | None = None,
        object_id: str | None = None,
        relation_id: str | None = None,
        *,
        namespaces: str | list[str] | None = None,
        include_retracted: bool = False,
    ) -> list[RetrievalResult]:
        """Query knowledge with automatic hierarchical namespace expansion."""
        resolved_scopes = self.namespaces.resolve_read_scope(namespaces) if namespaces else None

        if subject_id:
            return self.retrieve.by_subject(
                subject_id, include_retracted=include_retracted, namespaces=resolved_scopes
            )
        if object_id:
            return self.retrieve.by_object(
                object_id, include_retracted=include_retracted, namespaces=resolved_scopes
            )
        if relation_id:
            return self.retrieve.by_relation(
                relation_id, include_retracted=include_retracted, namespaces=resolved_scopes
            )
        return []

    def migrate_to(self, target_store: GraphStore) -> GraphStore:
        """Migrates current graph projections into a target storage backend via deterministic event replay."""
        for event in self.events.all_events():
            if event.event_type == EventType.ENTITY_CREATE:
                entity = Entity.model_validate(event.payload)
                target_store.add_entity(entity)
            elif event.event_type == EventType.RELATION_CREATE:
                relation = Relation.model_validate(event.payload)
                target_store.add_relation(relation)
            elif event.event_type == EventType.ASSERT:
                statement = Statement.model_validate(event.payload)
                target_store.add_statement(statement)
            elif event.event_type == EventType.RETRACT:
                target_id = event.target_id or event.payload.get("statement_id")
                if target_id:
                    stmt = target_store.get_statement(target_id)
                    if stmt:
                        target_store.update_statement(
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
                    stmt = target_store.get_statement(old_id)
                    if stmt:
                        target_store.update_statement(
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
                    dup = target_store.get_entity(dup_id)
                    if dup:
                        target_store.update_entity(
                            dup.model_copy(
                                update={"merged_into": canonical_id, "updated_at": event.timestamp}
                            )
                        )
                    # Rewire active statements
                    for stmt in target_store.all_statements(status=StatementStatus.ACTIVE):
                        updates = {}
                        if stmt.subject_id == dup_id:
                            updates["subject_id"] = canonical_id
                        if stmt.object_id == dup_id:
                            updates["object_id"] = canonical_id
                        if updates:
                            target_store.update_statement(stmt.model_copy(update=updates))

        self.store = target_store
        self.retrieve = RetrievalEngine(self.store)
        self.retraction = RetractionService(self.store, self.provenance, self.events)
        self.consolidation = ConsolidationService(self.store, self.events)
        self.entities = EntityService(self.store, self.consolidation, self.events)
        self.conflicts = ConflictManager(
            self.store, self.retraction, self.events, resolver=self.epistemic
        )
        self.conflict_detector = ConflictDetector(self.store, self.ontology, self.events)
        self.ingestion = IngestionPipeline(
            self.store,
            self.provenance,
            self.events,
            entity_service=self.entities,
            ontology=self.ontology,
        )
        self.hybrid_search = HybridSearchEngine(self.store, self.embeddings)
        self.path_finder = PathFinder(self.store, self.retrieve)
        self.formatter = SubgraphFormatter()
        self.document_pipeline = DocumentPipeline(self)
        return target_store

    def replay(self) -> InMemoryGraphStore:
        """Reconstructs the current GraphStore projection by replaying authoritative event history."""
        reconstructed = InMemoryGraphStore()
        return self.migrate_to(reconstructed)  # type: ignore
