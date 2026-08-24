---
name: kgk-domain
description: Domain knowledge for the Knowledge Graph Kernel: graph theory, provenance, retraction, consolidation, embeddings
---

# KGK Domain Knowledge

## Core Concepts

### Knowledge Graph
A directed labeled multigraph where:
- **Nodes** are `Entity` instances (label, type, properties)
- **Edges** are `Relation` instances (label, type, inverse_label)
- **Facts** are `Statement` instances (subject_id, relation_id, object_id, provenance)

### Provenance-First Design
Every statement carries:
- **Source**: who/what created it (e.g., "manual", "llm-extraction", "api-v1")
- **Confidence**: float [0.0, 1.0] — trust in the fact
- **Observed at**: timestamp
- **Metadata**: arbitrary key-value pairs

Provenance is append-only. Retractions generate new `ProvenanceEvent` records rather than mutating existing ones.

### Statement Lifecycle
```
ACTIVE → RETRACTED (soft delete, reason required)
ACTIVE → SUPERSEDED (replaced by new statement)
RETRACTED → (terminal)
SUPERSEDED → (terminal)
```

### Retraction vs Deletion
| Operation | Effect | Audit Trail |
|-----------|--------|-------------|
| Retract | Sets `status=RETRACTED`, records reason | New `ProvenanceEvent(event_type="retracted")` |
| Supersede | Sets `status=SUPERSEDED`, links new statement | Two events: retract old, ingest new |
| Delete | **Not implemented** | N/A |

### Entity Consolidation
Merging duplicate entities:
1. Mark duplicate with `merged_into = canonical_id`
2. Rewire all statements referencing duplicate → canonical
3. Return `ConsolidationResult` with rewired statement IDs

### Embeddings
Semantic similarity search via `EmbeddingStore`:
- `upsert(EmbeddingRecord)` — store vector
- `search(query_vector, top_k)` — cosine similarity ranking
- `delete(entity_id)` — remove vector

## Module Contracts

### GraphStore Protocol
```python
class GraphStore(Protocol):
    def add_entity(self, entity: Entity) -> Entity: ...
    def get_entity(self, entity_id: str) -> Entity | None: ...
    def update_entity(self, entity: Entity) -> Entity: ...
    def add_relation(self, relation: Relation) -> Relation: ...
    def get_relation(self, relation_id: str) -> Relation | None: ...
    def add_statement(self, statement: Statement) -> Statement: ...
    def get_statement(self, statement_id: str) -> Statement | None: ...
    def update_statement(self, statement: Statement) -> Statement: ...
    def statements_for_subject(self, subject_id: str, *, status: StatementStatus | None) -> list[Statement]: ...
    def statements_for_object(self, object_id: str, *, status: StatementStatus | None) -> list[Statement]: ...
    def statements_by_relation(self, relation_id: str, *, status: StatementStatus | None) -> list[Statement]: ...
    def all_entities(self) -> list[Entity]: ...
    def all_statements(self, *, status: StatementStatus | None) -> list[Statement]: ...
```

### Ingestion Flow
1. Resolve subject entity (create if not exists, by ID)
2. Resolve relation (create if not exists, by ID)
3. Resolve object entity (create if not exists, by ID)
4. Create `Statement` with resolved IDs
5. Add statement to store
6. Record provenance event
7. Return `IngestionResult`

## Common Pitfalls

- **Never mutate Pydantic models in-place**: Use `model_copy(update={...})`
- **Never use raw status strings**: Always use `StatementStatus.ACTIVE`, etc.
- **Always record provenance**: Missing provenance breaks audit trails
- **Don't filter at query layer only**: Status filtering should be in `GraphStore` methods
- **Watch for circular imports**: `kernel.py` imports modules; modules must not import `kernel.py`

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | /health | Health check |
| POST | /statements | Ingest a new statement |
| GET | /statements/{id} | Get statement by ID |
| GET | /entities/{id}/statements | Get statements where entity is subject |
| GET | /entities/{id}/neighborhood | Get subgraph up to depth N |
| POST | /statements/{id}/retract | Retract a statement |
