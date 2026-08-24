---
name: kgk-patterns
description: Design patterns and conventions used in KGK development
---

# KGK Design Patterns

## Protocol-Based Storage
Use `typing.Protocol` to define interfaces, allowing multiple implementations:

```python
class GraphStore(Protocol):
    def add_entity(self, entity: Entity) -> Entity: ...
    def get_entity(self, entity_id: str) -> Entity | None: ...
```

Consumers depend on the protocol, not the implementation.

## Immutable Updates (Pydantic v2)
Always use `model_copy(update={...})` for mutations:

```python
# Correct
updated = statement.model_copy(
    update={
        "status": StatementStatus.RETRACTED,
        "retracted_at": _utcnow(),
        "retraction_reason": reason,
    }
)

# Incorrect — mutates in place
statement.status = StatementStatus.RETRACTED
```

## Result Containers
Use `@dataclass` for operation results:

```python
@dataclass
class IngestionResult:
    statement: Statement
    subject: Entity
    relation: Relation
    object: Entity
    created_entities: list[Entity] = field(default_factory=list)
    created_relations: list[Relation] = field(default_factory=list)
```

## Facade Pattern
`KnowledgeGraphKernel` in `kernel.py` is a facade:

```python
@dataclass
class KnowledgeGraphKernel:
    store: GraphStore = field(default_factory=InMemoryGraphStore)
    provenance: ProvenanceTracker = field(default_factory=ProvenanceTracker)
    embeddings: EmbeddingStore = field(default_factory=InMemoryEmbeddingStore)

    def __post_init__(self) -> None:
        self.ingestion = IngestionPipeline(self.store, self.provenance)
        self.retrieve = RetrievalEngine(self.store)
        self.retraction = RetractionService(self.store, self.provenance)
        self.consolidation = ConsolidationService(self.store)
```

## Append-Only Provenance
Provenance is append-only. Never modify or delete `ProvenanceEvent` records:

```python
class ProvenanceTracker:
    def __init__(self) -> None:
        self._events: list[ProvenanceEvent] = []

    def record_ingestion(self, statement_id: str, record: ProvenanceRecord) -> ProvenanceEvent:
        event = ProvenanceEvent(
            statement_id=statement_id,
            event_type="ingested",
            record=record,
        )
        self._events.append(event)  # Always append, never replace
        return event
```

## Dependency Injection via Constructor
All services receive dependencies via constructor injection:

```python
class IngestionPipeline:
    def __init__(self, store: GraphStore, provenance: ProvenanceTracker) -> None:
        self._store = store
        self._provenance = provenance
```

This enables:
- Easy testing with mock stores
- Swappable backends
- Clear dependency graph

## Factory Pattern for API
The API uses a factory function to allow dependency injection:

```python
def create_app(kernel: KnowledgeGraphKernel | None = None) -> FastAPI:
    kgk = kernel or KnowledgeGraphKernel()
    ...
```

## Hydration Pattern
Retrieval engines return `RetrievalResult` with hydrated related entities:

```python
def _hydrate(self, statement: Statement) -> RetrievalResult:
    return RetrievalResult(
        statement=statement,
        subject=self._store.get_entity(statement.subject_id),
        relation=self._store.get_relation(statement.relation_id),
        object=self._store.get_entity(statement.object_id),
    )
```

## Directory Layout Convention
- Each module has `__init__.py` re-exporting public API
- Module private names use `_prefix` (e.g., `_store`, `_resolve_entity`)
- Tests mirror module structure in `tests/`
