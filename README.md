# Knowledge Graph Kernel (KGK) v1.1

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **"KGK owns the laws of knowledge. Applications own what the knowledge means."**

KGK is an event-sourced, bi-temporal, namespace-partitioned Knowledge Graph Kernel for durable AI agent memory, character lore, project graphs, and autonomous intelligence systems. Hosts authenticate callers and issue namespace capabilities; KGK enforces those capabilities across its supported knowledge operations.

## Project navigation

- [Project Charter](docs/PROJECT_CHARTER.md) — the destination and ownership boundary
- [Project Status](docs/PROJECT_STATUS.md) — intended versus current reality
- [System Map](docs/SYSTEM_MAP.md) — components, state, and cross-project flow
- [Course Log](docs/COURSE_LOG.md) — meaningful changes in project direction
- [Kernel Invariants](docs/KERNEL_INVARIANTS.md) — non-negotiable knowledge laws
- [User and Developer Guide](docs/USER_GUIDE.md) — usage details

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
10. **Durable Namespace Capabilities**: Registered namespace hierarchies survive restart, constrain reads and writes, and support deliberate parent inheritance without exposing sibling knowledge.

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
                    KnowledgeGraphKernel (v1.1)
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
from kgk import KnowledgeGraphKernel, Namespace, StatementCreate, ProvenanceRecord, EpistemicStatus

# 1. Open one durable local composition
kernel = KnowledgeGraphKernel.persistent("data/kgk.db")

# 2. Register once, then obtain a project-scoped capability
kernel.register_namespace(Namespace(id="project:ape", parent_id="global"))
ape_knowledge = kernel.scope("project:ape", actor="ape-runtime")

# 3. Ingest knowledge through that capability
result = ape_knowledge.ingest(
    StatementCreate(
        subject={"label": "APE", "type": "Project", "namespace": "project:ape"},
        relation={"label": "owns", "namespace": "project:ape"},
        object={"label": "character meaning", "namespace": "project:ape"},
        provenance=ProvenanceRecord(source="creator_canon", authority=100, confidence=1.0),
        namespace="project:ape",
        epistemic_status=EpistemicStatus.FACT,
    )
)

# 4. Retrieval stays inside project:ape plus inherited parent knowledge
search_results = ape_knowledge.search_hybrid(query_text="character", top_k=5)
prompt_md = ape_knowledge.format_neighborhood(result.subject.id, format_type="markdown")
print(prompt_md)
kernel.close()
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
# Register once, then use the same durable database and namespace
kgk --db data/kgk.db namespace project:ape
kgk --db data/kgk.db ingest -n project:ape -s "APE" -r "owns" -o "character meaning"

# Hybrid Search
kgk --db data/kgk.db search -n project:ape -q "character"

# Path Finding
kgk --db data/kgk.db path -n project:ape --start <id1> --end <id2> --max-depth 3

# Replay & Verify Event Ledger
kgk --db data/kgk.db replay
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
11. **Namespace Capability**: Application access is explicitly scoped; sibling namespaces cannot read or mutate each other, while configured parent knowledge may be inherited.

## HTTP composition

Set `KGK_DB_PATH` before starting the FastAPI application to use the durable shared SQLite composition. Every knowledge endpoint requires `X-KGK-Namespace`; hosts may also provide `X-KGK-Actor` for audit attribution. The bundled app treats those headers as trusted local input. A host exposing KGK across a trust boundary must construct the app with `create_app(..., authorize_namespace=...)` so its authentication system approves `(actor, namespace, operation)` before KGK issues the scope. Namespace registration is an administrative operation.

---

## 🧪 Testing

```bash
uv run python -m pytest
```

## 📄 License
MIT License.
