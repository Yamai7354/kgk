# Milestone Report: KGK v0.5 — Deduplication, Confidence Decay & Hybrid Subgraph Search

- **Milestone Version**: `v0.5.0`
- **Milestone Code**: `KGK-023` through `KGK-028` (Phases 9 & 10)
- **Status**: Completed & Verified
- **Date**: 2026-08-18

---

## 1. Executive Summary

Milestone v0.5 equips KGK with **idempotent statement deduplication**, **Bayesian multi-source confidence reinforcement**, **exponential half-life confidence decay**, and a **hybrid search and pathfinding query engine**.

### Core Enhancements
- **Knowledge Fusion without Fragmentation**: Re-asserting an identical $(S, R, O)$ triple reinforces confidence rather than cluttering the graph with redundant edges.
- **Dynamic Knowledge Modeling**: Fast-moving ephemeral facts (e.g. status, mood) decay smoothly over time.
- **Hybrid Multi-Modal Retrieval**: Combines keyword text matching and dense embedding similarity via **Reciprocal Rank Fusion (RRF)**.
- **Context-Window Awareness**: Formats subgraphs into LLM-ready context in Markdown, Mermaid diagrams, or JSON-LD, bound by token/character limits.

```
                              INCOMING ASSERTION
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
       Already Exists?                                Brand New Triple
               │                                             │
      ┌────────┴────────┐                                    ▼
      │  REINFORCE      │                             Create Statement &
      │  CONFIDENCE     │                             Emit ASSERT Event
      │  c = 1-(1-c1)   │
      │       *(1-c2)   │
      └────────┬────────┘
               ▼
     Emit PROVENANCE_ATTACH
          Event
```

---

## 2. Component Breakdown & Implementation Details

### 2.1 Phase 9: Statement Deduplication & Confidence Reinforcement (`ingestion/`)
- **Idempotency Guarantee**:
  - Ingesting an already-active statement with identical subject, relation, object, namespace, and validity window reuses the existing statement record.
  - Updates the statement's confidence using the Bayesian combination formula:
    $$c_{\text{reinforced}} = 1.0 - (1.0 - c_{\text{existing}}) \times (1.0 - c_{\text{incoming}})$$
  - Records the new source in `ProvenanceTracker` and emits a `PROVENANCE_ATTACH` knowledge event.

---

### 2.2 Phase 9: Confidence Decay Model (`epistemic/decay.py`)
- **`DecayModel` & `compute_effective_confidence`**:
  - Implements continuous exponential decay:
    $$c(t) = c_0 \cdot \left(\frac{1}{2}\right)^{\Delta t / t_{1/2}}$$
  - Computes time-decayed confidence for statements configured with `half_life_seconds` property without mutating the immutable base assertion record.

---

### 2.3 Phase 10: Hybrid Search Engine (`retrieval/hybrid.py`)
- **`HybridSearchEngine` (`kgk.search_hybrid(...)`)**:
  - Combines:
    1. **Lexical Matching**: Exact, substring, and property token matches over entity labels and properties.
    2. **Vector Similarity**: Dense cosine distance search from `EmbeddingStore`.
  - **Reciprocal Rank Fusion (RRF)**:
    $$\text{RRF}(d) = \sum_{m \in \{\text{lexical}, \text{vector}\}} \frac{1}{60 + \text{rank}_m(d)}$$
  - Returns ranked candidates balancing semantic intent and exact keyword matches.

---

### 2.4 Phase 10: Path Finding & Subgraph Formatting (`retrieval/`)
- **`PathFinder` (`retrieval/paths.py`)**:
  - **`kgk.find_paths(start, end, max_depth, directed, predicate_whitelist)`**: Breadth-First Search discovering all relational chains between two entities.
  - **`kgk.shortest_path(start, end)`**: Finds the optimal shortest path hop between entities.
- **`SubgraphFormatter` (`retrieval/formatter.py`)**:
  - **`kgk.format_neighborhood(entity_id, depth, format_type)`**:
    - **`markdown`**: Generates clean bullet points:
      `- [Mina] --(lives_in)--> [Tokyo] (status=fact, conf=0.95)`
    - **`mermaid`**: Generates diagram syntax:
      `graph LR; N1["Mina"] -->|lives_in| N2["Tokyo"]`
    - **`json_ld`**: Generates semantic web JSON-LD objects.
  - Truncates automatically to adhere to `max_chars` / context window budgets.

---

## 3. Verification & Test Matrix

Executed complete test suite via `uv run pytest`:

| Test Module | Focus Area | Result |
| :--- | :--- | :--- |
| `tests/test_dedup_and_decay.py` | Statement idempotency, Bayesian confidence reinforcement, and exponential half-life decay | **PASS** |
| `tests/test_hybrid_search.py` | RRF fusion of lexical keywords and vector embeddings | **PASS** |
| `tests/test_paths_and_subgraphs.py` | Multi-hop pathfinding, shortest path search, and context formatting (Markdown/Mermaid/JSON-LD) | **PASS** |
| `tests/test_temporal.py` | Point-in-time real-world queries (`as_of`) and system replay (`as_known_at`) | **PASS** |
| `tests/test_epistemic.py` | Epistemic modalities and perspective filtering | **PASS** |
| `tests/test_conflicts.py` | Automated functional conflict detection and authority resolution | **PASS** |
| `tests/test_namespaces.py` | Multi-tenant namespace hierarchy and query isolation | **PASS** |
| `tests/test_entity_resolution.py` | Aliasing, candidates, and multi-hop canonical merge resolution ($A \rightarrow B \rightarrow C$) | **PASS** |
| `tests/test_ontology.py` | Predicate schemas and type validation | **PASS** |
| `tests/test_invariants.py` | 10 core kernel invariants | **PASS** |
| `tests/test_events.py` | Event queries and deterministic replay | **PASS** |
| `tests/test_supersession_chains.py` | Multi-hop supersession resolution ($S_1 \rightarrow S_2 \rightarrow S_3$) | **PASS** |
| `tests/test_api.py` | FastAPI REST endpoints | **PASS** |
| `tests/test_kernel.py` | Kernel orchestration | **PASS** |
| `tests/test_graph.py` | Graph store adjacency and neighborhood queries | **PASS** |
| `tests/test_models.py` | Pydantic data models | **PASS** |

**Summary**: 44 passing tests (0 failures, 0 warnings).

---

## 4. Architectural Outcomes

1. **Non-Fragmenting Ingestion**: Duplicate assertions seamlessly strengthen knowledge confidence instead of introducing duplicated nodes or relations.
2. **Context-Optimized Output**: Subgraphs are immediately ingestible by downstream LLM prompts in multiple structured formats.
3. **Multi-Hop Traversal**: Agents can query relation chains to discover indirect connections between distant knowledge entities.
