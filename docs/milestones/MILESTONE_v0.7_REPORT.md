# Milestone Report: KGK v0.7 — Mina Character Canon Client & Production CLI Tooling

- **Milestone Version**: `v0.7.0`
- **Milestone Code**: `KGK-035` through `KGK-040` (Phases 13 & 14)
- **Status**: Completed & Verified
- **Date**: 2026-08-18

---

## 1. Executive Summary

Milestone v0.7 realizes the core design thesis of the Knowledge Graph Kernel:

> **"KGK should own the laws of knowledge. Applications should own what the knowledge means."**

This milestone introduces the **Mina Character Canon Client (`clients/mina/`)**, demonstrating how downstream agents can define domain-specific authority tiers, automated canon-over-rumor conflict resolution, and LLM system prompt formatting while leveraging KGK's underlying invariants. It also packages the library with the **production CLI utility (`kgk`)**.

```
                  DOWNSTREAM APPLICATIONS
           ┌─────────────────┼─────────────────┐
           ▼                                   ▼
   Mina Character App                  CLI Management Tool
  (clients.mina.MinaCanonClient)       (kgk ingest/search/replay)
           │                                   │
           └─────────────────┬─────────────────┘
                             ▼
                 KnowledgeGraphKernel (v0.7)
                             │
     ┌──────────────┬────────┼──────────────┬──────────────┐
     ▼              ▼        ▼              ▼              ▼
  Events         Graph    Epistemic     Namespaces      Storage
(EventStore)  (GraphStore) (Resolver)   (Hierarchical) (SQLite/Memory)
```

---

## 2. Component Breakdown & Implementation Details

### 2.1 Phase 13: Mina Character Canon Client (`clients/mina/`)
- **Authority Tiers**:
  - `CANON_AUTHORITY = 100` (`FACT`): Creator truths that overwrite conflicting assertions.
  - `NARRATIVE_AUTHORITY = 80` (`FACT`): Official plot events.
  - `OBSERVER_AUTHORITY = 50` (`BELIEF`): User interaction observations.
  - `RUMOR_AUTHORITY = 20` (`HYPOTHESIS`): Unconfirmed community rumors.
- **Automated Conflict Resolution**:
  - Automatically registers functional schemas for unique character properties (`birthplace`, `real_name`).
  - When creator canon is asserted, any conflicting lower-authority rumors are soft-retracted via KGK's `ConflictManager` and `AuthorityResolver`.
- **Character Profile & LLM Context Generation**:
  - `client.get_character_profile(name)`: Grouped facts, observations, and rumors.
  - `client.build_llm_prompt_context(name, max_chars, include_rumors)`: Generates clean, token-budgeted Markdown ready for LLM prompt injection.

---

### 2.2 Phase 14: Production CLI Tooling (`cli/`)
- **CLI Executable (`kgk`)**:
  - Subcommands:
    - `kgk ingest -s <Subj> -r <Rel> -o <Obj> [-c <Conf>] [-a <Auth>]`: Ingests assertion with provenance.
    - `kgk retract <StmtID> -m "<Reason>"`: Soft retractions preserving audit trails.
    - `kgk search -q "<Query>" [-k 10]`: Fused hybrid lexical + vector search.
    - `kgk path --start <ID> --end <ID>`: Multi-hop graph relation traversal.
    - `kgk format <ID> [--format markdown|mermaid|json_ld]`: Token-budgeted context formatting.
    - `kgk replay`: Replays event ledger to rebuild store projections.
  - Persistent SQLite backend support via `--db <path.db>`.

---

## 3. Verification & Test Matrix

Executed complete test suite via `uv run pytest`:

| Test Module | Focus Area | Result |
| :--- | :--- | :--- |
| `tests/test_mina_client.py` | Authority tier resolution, canon overriding rumors, character profile, prompt generation | **PASS** |
| `tests/test_cli.py` | CLI subcommands (`ingest`, `search`, `replay`) over SQLite database | **PASS** |
| `tests/test_drivers_and_extraction.py` | Document drivers, key-value/pattern/JSON extractors, span provenance | **PASS** |
| `tests/test_sqlite_storage.py` | SQLite GraphStore & EventStore, schema indices, storage migration | **PASS** |
| `tests/test_dedup_and_decay.py` | Statement idempotency, Bayesian confidence reinforcement, exponential decay | **PASS** |
| `tests/test_hybrid_search.py` | RRF fusion of lexical keywords and vector embeddings | **PASS** |
| `tests/test_paths_and_subgraphs.py` | Multi-hop pathfinding, shortest path search, context formatting | **PASS** |
| `tests/test_temporal.py` | Point-in-time real-world queries (`as_of`) and system replay (`as_known_at`) | **PASS** |
| `tests/test_epistemic.py` | Epistemic modalities and perspective filtering | **PASS** |
| `tests/test_conflicts.py` | Automated functional conflict detection and authority resolution | **PASS** |
| `tests/test_namespaces.py` | Multi-tenant namespace hierarchy and query isolation | **PASS** |
| `tests/test_entity_resolution.py` | Aliasing, candidates, and multi-hop canonical merge resolution | **PASS** |
| `tests/test_ontology.py` | Predicate schemas and type validation | **PASS** |
| `tests/test_invariants.py` | 10 core kernel invariants | **PASS** |
| `tests/test_events.py` | Event queries and deterministic replay | **PASS** |
| `tests/test_supersession_chains.py` | Multi-hop supersession resolution | **PASS** |
| `tests/test_api.py` | FastAPI REST endpoints | **PASS** |
| `tests/test_kernel.py` | Kernel orchestration | **PASS** |
| `tests/test_graph.py` | Graph store adjacency and neighborhood queries | **PASS** |
| `tests/test_models.py` | Pydantic data models | **PASS** |

**Summary**: 53 passing tests (0 failures, 0 warnings).

---

## 4. Architectural Outcomes

1. **Proof of Extensibility**: Demonstrated that applications (such as Mina) can implement custom epistemic authority policies without modifying the underlying kernel code.
2. **Production-Ready**: KGK provides both library and CLI interfaces for development, inspection, and production deployment.
