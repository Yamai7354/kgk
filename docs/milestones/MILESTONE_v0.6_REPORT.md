# Milestone Report: KGK v0.6 — Ingestion Drivers, Document Extraction & Persistent Storage (SQLite)

- **Milestone Version**: `v0.6.0`
- **Milestone Code**: `KGK-029` through `KGK-034` (Phases 11 & 12)
- **Status**: Completed & Verified
- **Date**: 2026-08-18

---

## 1. Executive Summary

Milestone v0.6 transitions KGK from an in-memory knowledge graph kernel to a **full production library** equipped with **multi-format document ingestion drivers**, **pluggable statement extractors with span-level provenance linking**, and **persistent ACID storage backends using SQLite**.

### Core Enhancements
- **Document & Extraction Protocol (`drivers/`)**: Ingests raw text, markdown key-values, regex patterns, or structured JSON cards into knowledge statements, preserving exact source URI and line/character spans.
- **Persistent ACID Graph Storage (`storage/sqlite/`)**: Fully compliant `SqliteGraphStore` and append-only `SqliteEventStore` with indexed relational schemas.
- **Zero-Downtime Event Replay Migration**: `kgk.migrate_to(target_store)` migrates all active assertions and historical state from any store to another via deterministic event replay.

```
          RAW DOCUMENT / UNSTRUCTURED TEXT
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   KeyValue          Pattern         Structured
   Extractor        Extractor        JSON Extractor
        │                │                │
        └────────────────┼────────────────┘
                         ▼
             Statements with Spans
                         │
                         ▼
               KnowledgeGraphKernel
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
   InMemoryStore                   SqliteGraphStore
  (Ephemeral/Tests)                 (Persistent ACID)
```

---

## 2. Component Breakdown & Implementation Details

### 2.1 Phase 11: Document Ingestion Drivers & Extraction (`drivers/`)
- **`Document` & `Span` Models (`drivers/models.py`)**:
  - `Document`: Captures `id`, `text`, `source_type`, `source_uri`, `namespace`, `metadata`, and timestamp.
  - `Span`: Line number, character offsets (`start_char`, `end_char`), and exact text snippets attached to statement `ProvenanceRecord`.
- **Pluggable Extractors (`drivers/extractors.py`)**:
  - **`KeyValueExtractor`**: Parses key-value lines (`Key: Value` or `Key = Value`).
  - **`PatternExtractor`**: Extracts triples from narrative text using configurable regex capture groups.
  - **`StructuredJsonExtractor`**: Transforms JSON payloads (e.g. character profiles, cards) into atomic $(S, R, O)$ statements.
- **`DocumentPipeline` (`drivers/pipeline.py`)**:
  - **`kgk.ingest_document(document, extractor)`**: Processes documents end-to-end and emits provenance events for each extracted statement.
  - **`kgk.ingest_batch(statement_creates)`**: Ingests multiple statement assertions atomically.

---

### 2.2 Phase 12: Persistent SQLite Storage Backends (`storage/sqlite/`)
- **Relational Schema (`storage/sqlite/schema.py`)**:
  - `entities`: `id`, `label`, `type`, `namespace`, `properties_json`, `merged_into`, timestamps.
  - `relations`: `id`, `label`, `type`, `inverse_label`, `namespace`, timestamp.
  - `statements`: `id`, `subject_id`, `relation_id`, `object_id`, `provenance_json`, `namespace`, `properties_json`, `status`, timestamps, validity interval (`valid_from`, `valid_until`), `epistemic_status`.
  - `events`: Append-only immutable ledger table (`event_id`, `event_type`, `namespace`, `actor`, `target_id`, `payload_json`, `timestamp`).
- **Store Implementations (`storage/sqlite/graph_store.py`, `storage/sqlite/event_store.py`)**:
  - `SqliteGraphStore`: Full implementation of `GraphStore` protocol with indexed queries on subject, object, relation, and status.
  - `SqliteEventStore`: Full implementation of `EventStore` protocol with query filtering by target, type, and namespace.
- **Storage Migration (`kgk.migrate_to(target_store)`)**:
  - Replays authoritative event history into `target_store` and hot-swaps all kernel subsystems to use the new backend without losing state.

---

## 3. Verification & Test Matrix

Executed complete test suite via `uv run pytest`:

| Test Module | Focus Area | Result |
| :--- | :--- | :--- |
| `tests/test_drivers_and_extraction.py` | Key-value, JSON, pattern extractors, document spans, and batch ingestion | **PASS** |
| `tests/test_sqlite_storage.py` | Persistent SQLite GraphStore & EventStore, schema indices, and storage migration | **PASS** |
| `tests/test_dedup_and_decay.py` | Statement idempotency, Bayesian confidence reinforcement, and exponential half-life decay | **PASS** |
| `tests/test_hybrid_search.py` | RRF fusion of lexical keywords and vector embeddings | **PASS** |
| `tests/test_paths_and_subgraphs.py` | Multi-hop pathfinding, shortest path search, and context formatting (Markdown/Mermaid/JSON-LD) | **PASS** |
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

**Summary**: 50 passing tests (0 failures, 0 warnings).

---

## 4. Architectural Outcomes

1. **Persistent Memory**: KGK can now persist graphs and event ledgers across application restarts using SQLite files.
2. **Span-Level Auditability**: Facts extracted from documents maintain explicit line and character references back to their original text source.
3. **Pluggable Architecture**: Extractors and storage backends can be swapped without modifying application logic.
