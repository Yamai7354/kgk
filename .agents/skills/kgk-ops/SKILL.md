---
name: kgk-ops
description: >-
  Use this skill when performing knowledge graph operations such as ingestion,
  retrieval, retraction, entity merging, semantic search, or running the database
  CLI utility on the Knowledge Graph Kernel.
---

# Knowledge Graph Kernel Operations (kgk-ops)

This skill provides step-by-step instructions and a CLI utility for interacting with the Knowledge Graph Kernel (KGK) database.

## Prerequisites

Before running any operations, ensure the FastAPI development server is running in the background:
```bash
uv run uvicorn api.app:app --reload
```
This is required because the database defaults to an in-memory store. By running the FastAPI server, the graph state is persisted in the server memory across CLI command executions.

## Utility Script

The skill installs a CLI utility script located at:
[`kgk_cli.py`](./scripts/kgk_cli.py)

Run it with:
```bash
uv run .agents/skills/kgk-ops/scripts/kgk_cli.py <command> [args]
```

### Commands

#### 1. Ingest Statement
Ingests a new subject-relation-object fact with source provenance and optional properties.
```bash
uv run .agents/skills/kgk-ops/scripts/kgk_cli.py ingest \
  --subject-label "Alice" --subject-type "Person" \
  --relation-label "knows" --relation-type "Relation" \
  --object-label "Bob" --object-type "Person" \
  --source "manual-input" --confidence 0.95
```

#### 2. Query Entity Statements
Retrieves statements where the entity is a subject, object, or both.
```bash
uv run .agents/skills/kgk-ops/scripts/kgk_cli.py query <entity_id> --direction both
```

#### 3. Traversal Neighborhood
Fetches a neighborhood subgraph around an entity up to a certain depth.
```bash
uv run .agents/skills/kgk-ops/scripts/kgk_cli.py neighborhood <entity_id> --depth 2
```

#### 4. Retract Statement
Invalidates a statement by its ID, recording a reason.
```bash
uv run .agents/skills/kgk-ops/scripts/kgk_cli.py retract <statement_id> --reason "invalid data"
```

#### 5. Merge Duplicate Entities
Consolidates duplicate entities under a single canonical entity.
```bash
uv run .agents/skills/kgk-ops/scripts/kgk_cli.py merge <canonical_id> <duplicate_id1> [duplicate_id2 ...]
```

#### 6. Embed Entity
Upserts a vector embedding for an entity.
```bash
uv run .agents/skills/kgk-ops/scripts/kgk_cli.py embed <entity_id> --vector 0.1,0.5,-0.2
```

#### 7. Semantic Vector Search
Searches entities semantically using a query vector.
```bash
uv run .agents/skills/kgk-ops/scripts/kgk_cli.py search --vector 0.11,0.49,-0.21 --top-k 3
```

## Common Mistakes

- **Running CLI without server**: Since `InMemoryGraphStore` is the default, running the CLI when the FastAPI server is offline will interact with an empty, volatile graph. Always ensure `uvicorn` is running first!
- **Manually editing DB state**: Avoid modifying python objects directly in storage. Always use the provided services or REST/CLI utilities to ensure correct provenance tracking.
