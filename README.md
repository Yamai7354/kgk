# Knowledge Graph Kernel (KGK) v1.0

[![Tests](https://img.shields.io/badge/tests-55%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **"KGK owns the laws of knowledge. Applications own what the knowledge means."**

KGK is an event-sourced, bi-temporal, multi-tenant Knowledge Graph Kernel designed as a foundational infrastructure library for AI agent memory, character lore, project graphs, and autonomous intelligence systems.

---

## 🌟 Key Capabilities

1. **Event-Sourced Primacy**: Append-only authoritative event ledger (`EventStore`) guarantees 100% deterministic replayability.
2. **Immutable Assertions & Soft Retractions**: Facts are never destructively erased; they are superseded or retracted with full lineage audit trails.
3. **Bi-Temporal Reasoning**: Distinguishes between real-world event validity (`as_of`) and system observation time (`as_known_at`).
4. **Epistemic Perspectives & Modalities**: Supports facts, hypotheses, beliefs, and rumors with authority-weighted truth resolution.
5. **Bayesian Deduplication & Confidence Decay**: Merges identical triples to reinforce confidence ($c = 1 - (1 - c_1)(1 - c_2)$) while decaying ephemeral assertions via exponential half-life models.
6. **Multi-Modal Hybrid Retrieval & Pathfinding**: Reciprocal Rank Fusion (RRF) over lexical keywords and dense vector embeddings, with multi-hop BFS pathfinding and LLM prompt context formatting (Markdown, Mermaid, JSON-LD).
7. **Document Drivers & Span Provenance**: Ingests raw text, markdown key-values, regex patterns, or JSON entity cards with character/line span citations.
8. **ACID Storage Backends**: Ships with ephemeral In-Memory and persistent SQLite graph and event stores with live migration.
9. **Domain Client Layer**: High-level character canon clients (e.g. `MinaCanonClient`) demonstrate application-specific authority tiers.

---

## 🏛 Architecture

```text
                      APPLICATIONS & AGENTS
        ┌───────────────────────┼───────────────────────┐
   Mina Lore Agent         Work Memory Agent       CLI Utility
  (clients.mina.Client)      (Custom Client)          (kgk CLI)
        │                       │                       │
        └───────────────────────┴───────────────────────┘
                                │
                    KnowledgeGraphKernel (v1.0)
                                │
   ┌────────────┬───────────────┼───────────────┬────────────┐
   ▼            ▼               ▼               ▼            ▼
 Events       Graph         Epistemic       Temporal      Storage
(Append-Only (Adjacency &   (Perspectives  (as_of vs    (SQLite /
 Ledger)      Traversal)     & Conflicts)   as_known_at) In-Memory)
```

---

## 🚀 Quick Start

### Installation

```bash
# Clone and install in virtual environment
uv pip install -e .
```

### Basic Python Usage

```python
import kgk
from kgk import KnowledgeGraphKernel, StatementCreate, ProvenanceRecord, EpistemicStatus

# 1. Initialize Kernel
kernel = KnowledgeGraphKernel()

# 2. Ingest Fact with Provenance
result = kernel.ingest(
    StatementCreate(
        subject={"label": "Mina Park", "type": "Character"},
        relation={"label": "lives_in"},
        object={"label": "Neo-Tokyo", "type": "Location"},
        provenance=ProvenanceRecord(source="creator_canon", authority=100, confidence=1.0),
        namespace="canon",
        epistemic_status=EpistemicStatus.FACT,
    )
)

# 3. Hybrid Search & Subgraph Extraction
search_results = kernel.search_hybrid(query_text="Neo-Tokyo", top_k=5)
prompt_md = kernel.format_neighborhood(result.subject.id, format_type="markdown")
print(prompt_md)
# Output: - [Mina Park] --(lives_in)--> [Neo-Tokyo] (status=fact, conf=1.0, auth=100.0)
```

### Mina Character Canon Client

```python
from kgk import MinaCanonClient

client = MinaCanonClient()

# Record rumor vs creator canon
client.record_rumor("Mina", "birthplace", "Mars Colony")  # authority 20
client.assert_canon("Mina", "birthplace", "Neo-Tokyo")   # authority 100

# Conflict automatically resolves in favor of high-authority canon
profile = client.get_character_profile("Mina")
print(profile["canon_facts"]["birthplace"])  # ['Neo-Tokyo']

# Generate prompt context ready for LLM injection
context = client.build_llm_prompt_context("Mina", max_chars=1000)
```

---

## 💻 CLI Utility

The `kgk` command-line utility provides instant management over graphs:

```bash
# Ingest statement
kgk ingest -s "Mina" -r "hobby" -o "Guitar" --confidence 0.95 --db canon.db

# Hybrid Search
kgk search -q "Mina" --db canon.db

# Path Finding
kgk path --start <id1> --end <id2> --max-depth 3 --db canon.db

# Replay & Verify Event Ledger
kgk replay --db canon.db
```

---

## 📜 Invariants of Knowledge

1. **Statement Immutability**: Historical statements cannot be modified.
2. **Non-Destructive Invalidation**: Statements are retracted, never deleted.
3. **Lineage Completeness**: Every statement has full provenance.
4. **Dual Temporal Dimensions**: Real-world time (`valid_from`/`valid_until`) vs Observation time (`created_at`).
5. **Perspective Modality**: Queries can be filtered by accepted epistemic statuses (`FACT`, `BELIEF`, `HYPOTHESIS`).
6. **Acyclic Consolidation**: Merges preserve identity records without circular pointer loops.
7. **Event Primacy**: State is a deterministic projection of append-only events.
8. **Ingestion Idempotency**: Duplicate assertions reinforce confidence without edge duplication.
9. **Explicit Conflict Lifecycle**: Contradictions are tracked as first-class entities with authority-based resolution.
10. **Storage Subservience**: Storage engines are interchangeable projections.

---

## 🧪 Testing

```bash
uv run pytest
# 55 passed in 1.00s (100% green)
```

## 📄 License
MIT License.
