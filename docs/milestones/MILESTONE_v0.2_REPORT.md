# Milestone Report: KGK v0.2 — Event-Sourced Knowledge Infrastructure & Invariant Enforcement

- **Milestone Version**: `v0.2.0`
- **Milestone Code**: `KGK-001` through `KGK-006` (Phases 1 & 2)
- **Status**: Completed & Verified
- **Date**: 2026-08-18

---

## 1. Executive Summary

Milestone v0.2 transforms the Knowledge Graph Kernel from a standard graph database wrapper into an **authoritative, event-sourced knowledge infrastructure library**.

### Core Guiding Law
> *"KGK stores evidence and knowledge history. KGK computes current knowledge views. KGK never rewrites history to make the current view convenient."*

In this architecture, the **event stream is the sole source of truth**. Graph indices, adjacency lists, and embedding vector spaces are treated as **materialized projections** that can be destroyed and deterministically reconstructed by replaying the event log.

```
                   AUTHORITATIVE EVENT STREAM
           [ENTITY_CREATE] -> [ASSERT] -> [SUPERSEDE] -> [RETRACT]
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
       Graph Store Projection                      Embedding Store Projection
    (Nodes, Edges, Neighborhoods)                     (Dense Vector Index)
```

---

## 2. Component Breakdown & Implementation Details

### 2.1 Kernel Invariants (`docs/KERNEL_INVARIANTS.md`, `tests/test_invariants.py`)
Formalized the 10 Core Invariants of Knowledge that govern all future modules:
1. **Statements Never Disappear**: Assertions remain in history forever.
2. **Historical Assertions Never Change Identity**: Statement UUIDs and created timestamps are immutable.
3. **Retraction Never Deletes**: Retracting a statement changes its status to `retracted`, logs a `RETRACT` event with the reason and actor, and preserves historical discoverability.
4. **Supersession Preserves Both Assertions**: Updating a fact produces a new assertion linked to the prior assertion via `superseded_by`, creating an unbroken lineage.
5. **Entity Merging Preserves Identities**: Duplicate entities are marked with `merged_into = canonical_id`. Original entity records and timestamps are preserved.
6. **Mandatory Provenance**: Ingestion cannot occur without explicit source tracking.
7. **Every Mutation Creates an Auditable Event**: Ingestions, retractions, supersessions, merges, and aliases emit append-only events.
8. **Derived vs. Observed Separation**: Inferences are explicitly distinguishable from primary observations.
9. **Confidence vs. Authority Separation**: Extraction accuracy ($0.0 \le c \le 1.0$) is strictly decoupled from policy authority ($0 \le a \le 100+$).
10. **Storage Subservience**: Storage backends cannot alter the semantics of KGK operations.

---

### 2.2 Knowledge Event Spine (`events/models.py`, `events/store.py`)
- **`EventType` Enum**: Enumerates core transitions:
  - `ASSERT`: Statement creation
  - `RETRACT`: Statement invalidation
  - `SUPERSEDE`: Statement replacement
  - `ENTITY_CREATE`: Entity introduction
  - `ENTITY_ALIAS`: Entity alias binding
  - `ENTITY_MERGE`: Entity consolidation
  - `RELATION_CREATE`: Predicate introduction
  - `PROVENANCE_ATTACH`: Metadata binding
  - `CONFLICT_DETECTED` / `CONFLICT_RESOLVED`: Multi-source dispute management
- **`KnowledgeEvent` Model**: Frozen Pydantic model (`ConfigDict(frozen=True)`):
  - `event_id: str`: Unique event identifier (UUID4)
  - `event_type: EventType`: Transition classification
  - `namespace: str`: Tenant/Domain boundary
  - `timestamp: datetime`: UTC observation timestamp
  - `actor: str`: Ingestion agent/service
  - `target_id: str | None`: Affected statement or entity ID
  - `reason: str | None`: Justification for retraction/supersession
  - `metadata: dict[str, Any]`: Contextual metadata
  - `payload: dict[str, Any]`: Snapshot of affected data
- **`InMemoryEventStore`**:
  - Append-only event ledger.
  - Indexed queries: `events_for_target(target_id)`, `events_by_type(event_type)`, `events_for_namespace(namespace)`.

---

### 2.3 Provenance v2 (`provenance/models.py`, `provenance/tracker.py`)
- **`Source` Model**: First-class entity for tracking information origins:
  - `id: str`: Source identifier (e.g. `character_card_v1`, `discord_chat_session_4`)
  - `type: str`: Source classification (e.g. `canon_document`, `chat_log`, `agent_inference`)
  - `authority: float`: Source policy weight ($0 \le a \le 100+$)
- **Decoupling Confidence and Authority**:
  - `confidence` ($0.0 \le c \le 1.0$): Statistical metric of extraction quality ("Did the model transcribe the statement accurately?").
  - `authority` ($0 \le a \le 100+$): Policy metric of domain precedence ("Does a primary author document override a secondary chat comment?").

---

### 2.4 Statement Immutability & Replay Architecture (`models/statement.py`, `kernel.py`)
- **Frozen Statements**: `Statement` models use `ConfigDict(frozen=True)` to prevent in-place mutation of historical records.
- **Computed Projections**: `ProjectedStatement` represents the computed current state derived from the event history.
- **Deterministic Replay (`kgk.replay()`)**:
  - Clears all in-memory graph state.
  - Iterates through the ordered event stream.
  - Materializes entities, relations, statements, retractions, supersessions, and entity rewires step-by-step.
  - Guarantees 1:1 projection parity.

---

### 2.5 Multi-Hop Supersession Chains (`retraction/service.py`)
- Updated `RetractionService.supersede(old_id, new_statement, reason, actor)`:
  - Ingests the new assertion $S_{\text{new}}$.
  - Emits a `SUPERSEDE` event containing both statement IDs and the reason.
  - Updates the projection of $S_{\text{old}}$ with `status = StatementStatus.SUPERSEDED` and `superseded_by = S_{\text{new}}.id`.
- **Chain Resolution (`resolve_chain(statement_id)`)**:
  - Traverses `superseded_by` links across arbitrary hops ($S_1 \rightarrow S_2 \rightarrow S_3 \rightarrow \dots$).
  - Terminal resolution: Returns the complete history chain `[S1, S2, S3]` and identifies the active statement ($S_3$).
  - **Cycle Detection**: Detects and raises `ValueError` if a circular loop ($S_1 \rightarrow S_2 \rightarrow S_1$) is encountered.

---

## 3. Verification & Test Matrix

A comprehensive test suite was executed via `uv run pytest`:

| Test Module | Focus Area | Result |
| :--- | :--- | :--- |
| `tests/test_invariants.py` | Verified all 10 kernel laws: retraction preservation, supersession history, non-destructive merges, confidence vs. authority | **PASS** |
| `tests/test_events.py` | Event append, query by target/type, and full graph reconstruction via `kgk.replay()` | **PASS** |
| `tests/test_supersession_chains.py` | 3-hop supersession resolution ($S_1 \rightarrow S_2 \rightarrow S_3$) and cycle detection | **PASS** |
| `tests/test_api.py` | FastAPI endpoints for ingestion, retraction, supersession, merge, search, and events | **PASS** |
| `tests/test_kernel.py` | End-to-end kernel orchestration | **PASS** |
| `tests/test_graph.py` | Graph store adjacency queries and neighborhood traversal | **PASS** |
| `tests/test_models.py` | Pydantic model validation and serialization | **PASS** |

**Summary**: 27 passing tests (0 failures, 0 warnings).

---

## 4. Architectural Outcomes

1. **Auditability**: Every modification to knowledge state is now traceable to an immutable timestamped event with actor, source, and reason annotations.
2. **Reversibility**: Historical assertions can be queried as they existed at any point in time.
3. **Resilience**: The graph store is no longer a single point of truth; it can be blown away and completely rebuilt from the event log at any time.
