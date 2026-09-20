# Knowledge Graph Kernel (KGK) — User & Developer Guide

## Table of Contents
1. [Introduction & Core Philosophy](#1-introduction--core-philosophy)
2. [Kernel Instantiation & Storage](#2-kernel-instantiation--storage)
3. [Ingesting Knowledge](#3-ingesting-knowledge)
4. [Namespaces & Scope Expansion](#4-namespaces--scope-expansion)
5. [Epistemic Modalities & Perspectives](#5-epistemic-modalities--perspectives)
6. [Temporal Modeling: as_of vs as_known_at](#6-temporal-modeling-as_of-vs-as_known_at)
7. [Conflict Detection & Authority Resolution](#7-conflict-detection--authority-resolution)
8. [Hybrid Search, Pathfinding & LLM Context Formatting](#8-hybrid-search-pathfinding--llm-context-formatting)
9. [Building Downstream Agent Clients (Mina Example)](#9-building-downstream-agent-clients-mina-example)
10. [Command-Line Interface (CLI)](#10-command-line-interface-cli)

---

## 1. Introduction & Core Philosophy

KGK is engineered around a core tenet:
> **KGK owns the laws of knowledge. Applications own what the knowledge means.**

KGK does not dictate what is true or false. Instead, it provides the formal mechanics to track:
- **Who asserted what, when, and with what confidence/authority.**
- **How knowledge evolves over time without destructive deletion.**
- **How downstream agents view subsets of knowledge according to their perspective.**

---

## 2. Kernel Instantiation & Storage

### In-Memory (Default for Testing / Fast Workflows)
```python
from kgk import KnowledgeGraphKernel

kgk = KnowledgeGraphKernel()
```

### Persistent SQLite (ACID Durability)
```python
from kgk import KnowledgeGraphKernel

kgk = KnowledgeGraphKernel.persistent("knowledge.db")
```

The persistent constructor opens the graph projection and append-only event ledger as one KGK composition. Namespace registrations and knowledge are restored from that database after restart.

### Hot-Swapping & Live Migration
To migrate an in-memory kernel or another store to SQLite without losing history:
```python
new_sqlite_store = SqliteGraphStore("production.db")
kgk.migrate_to(new_sqlite_store)
```

---

## 3. Ingesting Knowledge

### Basic Statement Ingestion
```python
from kgk import Namespace, StatementCreate, ProvenanceRecord, EpistemicStatus

kgk.register_namespace(Namespace(id="project:mina", parent_id="global"))
mina_knowledge = kgk.scope("project:mina", actor="mina-runtime")

res = mina_knowledge.ingest(
    StatementCreate(
        subject={"label": "Mina", "type": "Person", "namespace": "project:mina"},
        relation={"label": "lives_in", "namespace": "project:mina"},
        object={"label": "Tokyo", "type": "City", "namespace": "project:mina"},
        provenance=ProvenanceRecord(source="interview", confidence=0.9, authority=80),
        namespace="project:mina",
        epistemic_status=EpistemicStatus.FACT,
    )
)
```

### Document & Text Extraction
Ingest raw documents directly using built-in extractors:
```python
from kgk import Document, KeyValueExtractor, PatternExtractor, StructuredJsonExtractor

doc = Document(
    text="role: Captain\nhometown: Neo-Tokyo",
    source_uri="file:///lore/characters/mina.txt",
    namespace="project:mina",
    metadata={"subject": "Mina Park"}
)
results = mina_knowledge.ingest_document(doc, KeyValueExtractor())
```

---

## 4. Namespaces & Scope Expansion

Hierarchical namespaces partition shared durable knowledge with selective inheritance. The host authenticates callers and decides which namespace capability they receive; KGK enforces that capability after it is issued.
```python
from kgk import Namespace

# Register durably: project:mina inherits global knowledge
kgk.register_namespace(Namespace(id="project:mina", parent_id="global"))

# The scoped capability reads project:mina + global and writes only project:mina
mina_knowledge = kgk.scope("project:mina", actor="mina-runtime")
results = mina_knowledge.query(subject_id=entity_id)
```

Sibling namespaces are not visible. Inherited parent knowledge is readable but cannot be retracted, superseded, merged, or otherwise changed through a child capability. Direct graph-store access is reserved for administrative and storage implementation work.

---

## 5. Epistemic Modalities & Perspectives

Every statement carries an `EpistemicStatus`:
- `FACT`: Authoritative truth.
- `BELIEF`: Agent or user subjective belief.
- `HYPOTHESIS`: Unverified assumption or rumor.
- `AXIOM`: Logical kernel rule.

Filter queries through worldviews:
```python
from kgk import Perspective

# Strict canon perspective (only accept FACT and BELIEF)
perspective = Perspective(
    name="strict_canon",
    accepted_statuses={EpistemicStatus.FACT, EpistemicStatus.BELIEF}
)
canon_statements = kgk.view_perspective(perspective, subject_id=entity_id)
```

---

## 6. Temporal Modeling: as_of vs as_known_at

KGK implements full bi-temporal modeling:

1. **`as_of(valid_at)`**: Queries what was true in real-world reality at a specific time:
   ```python
   historical_facts = kgk.as_of(datetime(2025, 6, 1, tzinfo=timezone.utc))
   ```

2. **`as_known_at(system_time)`**: Reconstructs the exact system database state at a historical moment:
   ```python
   historical_db = kgk.as_known_at(datetime(2026, 1, 1, tzinfo=timezone.utc))
   ```

---

## 7. Conflict Detection & Authority Resolution

When a functional predicate (e.g. `birthplace`) is asserted with conflicting values:
```python
# System detects functional violation and tracks a Conflict
conflicts = kgk.conflicts.all_conflicts()

# Automatically resolve based on authority scoring
for c in conflicts:
    kgk.conflicts.resolve_by_authority(c.id)
```

---

## 8. Hybrid Search, Pathfinding & LLM Context Formatting

### Hybrid Retrieval (RRF)
```python
# Fused lexical + vector search
results = kgk.search_hybrid(query_text="Neo-Tokyo", top_k=5)
```

### Multi-Hop Pathfinding
```python
# Find connection chains between distant entities: A -> B -> C
paths = kgk.find_paths(start_id, end_id, max_depth=3)
```

### Prompt Context Formatting
```python
# Markdown bullets
md_context = kgk.format_neighborhood(entity_id, depth=1, format_type="markdown", max_chars=2000)

# Mermaid diagram
mermaid_diagram = kgk.format_neighborhood(entity_id, depth=2, format_type="mermaid")

# JSON-LD
jsonld_graph = kgk.format_neighborhood(entity_id, depth=1, format_type="json_ld")
```

---

## 9. Building Downstream Agent Clients (Mina Example)

```python
from kgk import MinaCanonClient

client = MinaCanonClient()

# Creator canon overrides user rumors
client.record_rumor("Mina", "birthplace", "Mars Colony")
client.assert_canon("Mina", "birthplace", "Neo-Tokyo")

# Generate prompt context for LLM system prompt
prompt = client.build_llm_prompt_context("Mina", max_chars=1500)
```

---

## 10. Command-Line Interface (CLI)

```bash
# Register once, then ingest
kgk --db knowledge.db namespace project:mina
kgk --db knowledge.db ingest -n project:mina -s "Mina" -r "lives_in" -o "Tokyo" --confidence 0.95

# Retract
kgk --db knowledge.db retract -n project:mina <statement_id> -m "Fact outdated"

# Search
kgk --db knowledge.db search -n project:mina -q "Tokyo"

# Path
kgk --db knowledge.db path -n project:mina --start <id1> --end <id2>

# Replay
kgk --db knowledge.db replay
```
