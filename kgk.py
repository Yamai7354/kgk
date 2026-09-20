"""Knowledge Graph Kernel (KGK) - Top-Level Package Interface."""

from clients.mina import (
    CANON_AUTHORITY,
    NARRATIVE_AUTHORITY,
    OBSERVER_AUTHORITY,
    RUMOR_AUTHORITY,
    MinaCanonClient,
)
from conflicts import (
    Conflict,
    ConflictDetector,
    ConflictManager,
    ConflictStatus,
    ConflictType,
)
from consolidation import ConsolidationService
from drivers import (
    Document,
    DocumentPipeline,
    Extractor,
    KeyValueExtractor,
    PatternExtractor,
    Span,
    StructuredJsonExtractor,
)
from embeddings import EmbeddingRecord, EmbeddingStore, InMemoryEmbeddingStore
from entities import EntityAlias, EntityResolutionResult, EntityService
from epistemic import (
    AuthorityResolver,
    DecayModel,
    EpistemicStatus,
    Perspective,
    compute_effective_confidence,
)
from events import EventStore, EventType, InMemoryEventStore, KnowledgeEvent
from graph import GraphStore, InMemoryGraphStore
from ingestion import IngestionPipeline, IngestionResult
from kernel import KnowledgeGraphKernel
from models import (
    Entity,
    EntityCreate,
    ProjectedStatement,
    Relation,
    RelationCreate,
    Statement,
    StatementCreate,
    StatementStatus,
)
from namespaces import (
    Namespace,
    NamespaceAccessError,
    NamespaceManager,
    NamespacePolicy,
    NamespaceScope,
)
from ontology import RelationDefinition, RelationRegistry
from provenance import ProvenanceEvent, ProvenanceRecord, ProvenanceTracker, Source
from retraction import RetractionResult, RetractionService
from retrieval import (
    HybridSearchEngine,
    HybridSearchResult,
    PathFinder,
    RetrievalEngine,
    RetrievalResult,
    SubgraphFormatter,
    SubgraphResult,
)
from storage.sqlite import SqliteEventStore, SqliteGraphStore
from temporal import TemporalEngine, TimeInterval

__version__ = "1.1.0"

__all__ = [
    # Kernel
    "KnowledgeGraphKernel",
    "__version__",
    # Models
    "Entity",
    "EntityCreate",
    "Relation",
    "RelationCreate",
    "Statement",
    "StatementCreate",
    "StatementStatus",
    "ProjectedStatement",
    # Events
    "KnowledgeEvent",
    "EventType",
    "EventStore",
    "InMemoryEventStore",
    # Graph & Embeddings
    "GraphStore",
    "InMemoryGraphStore",
    "EmbeddingStore",
    "InMemoryEmbeddingStore",
    "EmbeddingRecord",
    # Provenance
    "ProvenanceRecord",
    "ProvenanceEvent",
    "ProvenanceTracker",
    "Source",
    # Ingestion & Retraction
    "IngestionPipeline",
    "IngestionResult",
    "RetractionService",
    "RetractionResult",
    "ConsolidationService",
    "EntityService",
    "EntityAlias",
    "EntityResolutionResult",
    # Namespaces & Ontology
    "Namespace",
    "NamespaceManager",
    "NamespaceScope",
    "NamespaceAccessError",
    "NamespacePolicy",
    "RelationDefinition",
    "RelationRegistry",
    # Temporal & Epistemic & Conflicts
    "TimeInterval",
    "TemporalEngine",
    "EpistemicStatus",
    "Perspective",
    "AuthorityResolver",
    "DecayModel",
    "compute_effective_confidence",
    "Conflict",
    "ConflictType",
    "ConflictStatus",
    "ConflictManager",
    "ConflictDetector",
    # Retrieval
    "RetrievalEngine",
    "RetrievalResult",
    "SubgraphResult",
    "HybridSearchEngine",
    "HybridSearchResult",
    "PathFinder",
    "SubgraphFormatter",
    # Document Drivers
    "Document",
    "Span",
    "Extractor",
    "KeyValueExtractor",
    "PatternExtractor",
    "StructuredJsonExtractor",
    "DocumentPipeline",
    # Storage Backends
    "SqliteGraphStore",
    "SqliteEventStore",
    # Application Clients
    "MinaCanonClient",
    "CANON_AUTHORITY",
    "NARRATIVE_AUTHORITY",
    "OBSERVER_AUTHORITY",
    "RUMOR_AUTHORITY",
]
