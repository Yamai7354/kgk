# Milestone Report: KGK v0.4 — Temporal Modeling, Epistemic Status & Conflict Resolution

- **Milestone Version**: `v0.4.0`
- **Milestone Code**: `KGK-014` through `KGK-022` (Phases 6, 7, 8)
- **Status**: Completed & Verified
- **Date**: 2026-08-18

---

## 1. Executive Summary

Milestone v0.4 introduces **bitemporal knowledge modeling**, **epistemic certainty and multi-perspective truth resolution**, and **automated conflict detection** for functional relations.

### Core Philosophy
- **Bi-Temporal Decoupling**: What was true in reality at time $T_{\text{valid}}$ is separate from what the system believed at observation time $T_{\text{system}}$.
- **Perspective Pluralism**: Multiple agents, worldviews, or canon rules can project distinct subjective truths from the same underlying evidence graph without mutating history.
- **Rule-Based Conflict Governance**: When functional rules (e.g. single birthplace) are violated by multiple assertions, conflicts are formally recorded and resolved via authority weighting or supersession.

```
                                  ASSERTION INPUT
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
     Bi-Temporal Coordinates                          Epistemic Modality
   - valid_from / valid_until                       - FACT, HYPOTHESIS, BELIEF,
   - observed_at / system_time                        ASSUMPTION, CONJECTURE, RUMOR
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         ▼
                             CONFLICT DETECTION ENGINE
                         (Functional Overlap Evaluation)
                                         │
                      ┌──────────────────┴──────────────────┐
                      ▼                                     ▼
               No Conflict                          Conflict Detected
             (Commit to Graph)                 (Emit CONFLICT_DETECTED Event
                                                & Register Open Conflict)
                                                            │
                                                            ▼
                                                AUTHORITY RESOLVER
                                             (Perspective-Weighted Win)
                                                            │
                                                            ▼
                                               Emit CONFLICT_RESOLVED Event
```

---

## 2. Component Breakdown & Implementation Details

### 2.1 Phase 6: Bi-Temporal Knowledge Modeling (`temporal/`)
- **`TimeInterval` Model**:
  - `start: datetime | None`, `end: datetime | None`.
  - `contains(dt)`: Evaluates if a point-in-time falls inside the real-world validity window.
  - `overlaps(other)`: Determines if two validity windows share overlapping intervals.
- **Statement Bi-Temporal Attributes (`models/statement.py`)**:
  - `valid_from: datetime | None`: Real-world validity start.
  - `valid_until: datetime | None`: Real-world validity end.
  - `is_valid_at(target_dt: datetime) -> bool`: Helper for point-in-time filtering.
- **`TemporalEngine` (`temporal/engine.py`)**:
  - **`as_of(valid_at=...)`**: Queries statements that were valid in reality at a historical or future timestamp (e.g., querying where Mina lived in 2021 vs. 2023).
  - **`as_known_at(system_time=...)`**: Reconstructs the exact in-memory graph state as it was known to the kernel at past timestamp $T_{\text{system}}$ by replaying events up to that timestamp.

---

### 2.2 Phase 7: Epistemic Status & Authority Resolution (`epistemic/`)
- **`EpistemicStatus` Enum**:
  - `FACT`: High-confidence, authoritative observation.
  - `HYPOTHESIS`: Unverified proposition or testable hypothesis.
  - `ASSUMPTION`: Working premise for planning.
  - `BELIEF`: Conviction held by a specific agent.
  - `CONJECTURE`: Exploratory speculation.
  - `RUMOR`: Unverified multi-source chatter.
- **`Perspective` Model**:
  - Defines a worldview/lens:
    - `name: str` (e.g. `perspective:mina`, `perspective:strict_canon`).
    - `preferred_sources: list[str]`: Priority sources.
    - `accepted_statuses: list[EpistemicStatus]`: Filter of permissible modalities.
    - `authority_overrides: dict[str, float]`: Custom weights per source.
- **`AuthorityResolver` (`epistemic/resolver.py`)**:
  - Computes statement scores using a strict priority order:
    1. **Authority (Primary)**: Higher source authority wins ($a \times 10000$).
    2. **Confidence (Secondary)**: Higher extraction confidence breaks ties ($c \times 100$).
    3. **Recency (Tertiary)**: Newer observation timestamp breaks remaining ties.
  - `resolve_winner(statements, perspective)`: Returns the winning statement according to the perspective policy.
  - `kgk.view_perspective(perspective)`: Projects the knowledge graph through a specific perspective filter.

---

### 2.3 Phase 8: Conflict Detection & Resolution (`conflicts/`)
- **`Conflict` Model**:
  - `id: str`, `conflict_type: ConflictType` (`FUNCTIONAL_VIOLATION`, `MUTUAL_EXCLUSION`, `VALUE_DISAGREEMENT`).
  - `subject_id: str`, `relation_id: str`, `statement_ids: list[str]`.
  - `status: ConflictStatus` (`OPEN`, `RESOLVED`, `IGNORED`).
  - `winning_statement_id: str | None`, `resolution_reason: str | None`, `resolved_at: datetime | None`.
- **`ConflictDetector` (`conflicts/detector.py`)**:
  - Automatically triggered during `kgk.ingest()`.
  - Identifies functional predicates (`is_functional=True` in `ontology`).
  - Flags contradictions when multiple active statements for an entity and predicate point to distinct object values with overlapping temporal validity.
  - Emits `CONFLICT_DETECTED` event to `EventStore`.
- **`ConflictManager` (`conflicts/manager.py`)**:
  - Tracks open conflicts across the kernel.
  - **`resolve_by_authority(conflict_id, perspective)`**:
    - Selects the winning assertion using `AuthorityResolver`.
    - Retracts losing statements with explanatory audit reasons.
    - Updates conflict status to `RESOLVED` and emits `CONFLICT_RESOLVED` event.

---

## 3. Verification & Test Matrix

Executed complete test suite via `uv run pytest`:

| Test Module | Focus Area | Result |
| :--- | :--- | :--- |
| `tests/test_temporal.py` | Real-world validity windows (`as_of`) and historical system state reconstruction (`as_known_at`) | **PASS** |
| `tests/test_epistemic.py` | Epistemic status tracking, authority resolution, and perspective filtering | **PASS** |
| `tests/test_conflicts.py` | Automated functional conflict detection, `CONFLICT_DETECTED` / `CONFLICT_RESOLVED` events, and authority resolution | **PASS** |
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

**Summary**: 39 passing tests (0 failures, 0 warnings).

---

## 4. Architectural Outcomes

1. **Bi-Temporal Precision**: Full clarity between "when did this fact happen in the world" and "when did the system learn this fact".
2. **Epistemic Modality**: Hypotheses, beliefs, and rumors can be recorded safely without polluting hard canonical facts.
3. **Automated Dispute Governance**: Contradictions are surfaced immediately through structured events and resolved deterministically without silent data corruption.
