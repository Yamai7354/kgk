# Knowledge Graph Kernel (KGK) Agent Instructions

Welcome, agent! This project implements a modular Knowledge Graph Kernel. When operating inside this workspace, you must adhere to the following rules, architectural standards, and operational guidelines.

---

## 1. Architectural Principles

- **Soft Retractions**: Never delete statements from the graph. Always use the `retraction` service or the `/statements/{id}/retract` endpoint. Facts are invalidated with a clear reason and source annotation, leaving an audit trail.
- **Entity Consolidation**: When equivalent entities (duplicates) are identified, merge them using the `consolidation` service. This redirects all statements referencing the duplicate entity (in both subject and object positions) to the canonical entity, marks the duplicate entity as merged, and updates timestamps.
- **Lineage Verification**: Every statement ingestion, retraction, and supersession must write events to the `provenance` tracker. Always query the lineage of a statement before altering it.

---

## 2. API & Database Interfaces

When interacting with the database, you have two primary methods:

1. **REST API Interface (FastAPI)**:
   - Run the server using: `uvicorn api.app:app --reload`
   - Use the REST endpoints to read and write data (`/statements`, `/entities`, `/entities/search`, etc.).
2. **Local CLI Tool**:
   - Use the custom CLI tool at `.agents/skills/kgk-ops/scripts/kgk_cli.py` to execute graph operations directly.
   - Run the CLI using: `uv run .agents/skills/kgk-ops/scripts/kgk_cli.py <command>`

---

## 3. Coding Guidelines

### Graph Modifications
- **Ingestion**: Use `kgk.ingest(StatementCreate(...))`. Never add statements directly to the `InMemoryGraphStore` without passing through the ingestion pipeline, as doing so bypasses the provenance tracking.
- **Self-Loops & Rewiring**: If an entity is merged, verify that all self-loops (statements where the entity is both subject and object) are rewired correctly to the canonical entity.
- **Superseding**: When updating facts, use `kgk.retraction.supersede(old_id, new_statement, reason)`. Do not just ingest the new statement and retract the old one separately; linking them via `superseded_by` is critical.

### Python Imports and Executions
- **Venv/Tooling**: Always execute commands using `uv run`. For example: `uv run pytest`.
- **Package Imports**: Avoid cross-module circular imports. Import specific models from `models` and logic from the corresponding directories (`ingestion`, `retrieval`, `provenance`, etc.).

### Testing & Cleanup
- **Cleanup Rule**: If you run any tests (automated or manual) that generate temporary files or modify database/knowledge graph state, you MUST clean up all temporary test files left behind and revert any database/knowledge graph additions or mutations after you finish testing.

---

## 4. KGK Architecture Rules

- Statements are immutable historical assertions.
- Retraction MUST NOT delete statements.
- Entity consolidation MUST NOT destroy original identity records.
- Every statement MUST have provenance.
- Historical representations and current projections are separate concepts.
- Graph storage implementations MUST conform to `GraphStore`.
- Embedding implementations MUST conform to `EmbeddingStore`.
