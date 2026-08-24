# Milestone Report: KGK v0.3 — Namespaces, Entity Resolution & Relation Ontology

- **Milestone Version**: `v0.3.0`
- **Milestone Code**: `KGK-007` through `KGK-013` (Phases 3, 4, 5)
- **Status**: Completed & Verified
- **Date**: 2026-08-18

---

## 1. Executive Summary

Milestone v0.3 extends KGK to support **multi-tenant application boundaries**, **non-destructive entity identity management**, and **predicate ontology enforcement**.

With these capabilities:
- Applications (e.g., character canon, user memory, project workspaces) can operate in **isolated or hierarchical namespaces** without cross-polluting global state.
- Entity aliases and multi-hop canonical merge chains ($A \rightarrow B \rightarrow C$) are resolved transparently without destroying original historical entity records.
- Predicates are governed by formal schemas that validate entity types and support inverse relations and logical properties.

```
                    APPLICATION TENANCY / NAMESPACES
    ┌───────────────────────────┬───────────────────────────┐
    │  Namespace: "global"      │  Namespace: "project:mina"│
    │  (Shared World Rules)     │  (Character Canon Facts)  │
    └─────────────┬─────────────┴─────────────┬─────────────┘
                  │                           │
                  ▼                           ▼
      ┌───────────────────────────────────────────────────────┐
      │             KnowledgeGraphKernel (KGK)                │
      │                                                       │
      │  ┌─────────────────┐ ┌─────────────────────────────┐  │
      │  │ EntityService   │ │ RelationRegistry (Ontology) │  │
      │  │ - Aliasing      │ │ - Type Schema Validation    │  │
      │  │ - Merge Chains  │ │ - Inverse Relations         │  │
      │  │ - Candidates    │ │ - Strict / Loose Modes      │  │
      │  └─────────────────┘ └─────────────────────────────┘  │
      └───────────────────────────────────────────────────────┘
```

---

## 2. Component Breakdown & Implementation Details

### 2.1 Phase 3: Namespaces System (`namespaces/`)
- **`Namespace` Model**:
  - `id: str`: Unique identifier (e.g., `global`, `user:randy`, `project:mina`, `project:jade`)
  - `parent_id: str | None`: Pointer to parent namespace in the hierarchy
  - `priority: int`: Inheritance resolution order
  - `is_read_only: bool`: Write protection flag
  - `metadata: dict[str, Any]`
- **`NamespacePolicy` Model**:
  - `default_namespace: str = "global"`
  - `inherit_global: bool = True`
- **`NamespaceManager` (`kgk.namespaces`)**:
  - Manages registration and validation of namespace trees.
  - **Hierarchical Read Scope Expansion (`resolve_read_scope(scope)`)**:
    - Expands child namespaces to include all inherited parent namespaces:
      $$\text{"project:mina"} \implies [\text{"global"}, \text{"user:randy"}, \text{"project:mina"}]$$
    - Allows child projects to inherit shared world knowledge while writing exclusively to their isolated namespace.
- **Namespace Scoped Queries (`kgk.query_scoped(...)`)**:
  - Added multi-namespace filtering directly to `RetrievalEngine` methods (`by_subject`, `by_object`, `by_relation`, `neighborhood`).

---

### 2.2 Phase 4: Non-Destructive Entity Identity & Resolution (`entities/`)
- **`EntityAlias` Model**:
  - `alias: str`: Alternative name or identifier (e.g., `"Mina Park"`, `"Mina-chan"`)
  - `canonical_id: str`: Pointer to canonical `Entity.id`
  - `namespace: str`: Tenant scope
  - `source: str`: Provenance of alias
  - `confidence: float`: Match confidence ($0.0 \le c \le 1.0$)
- **`EntityResolutionResult` Model**:
  - Returns resolved `Entity` along with `match_type` (`"exact_id"`, `"alias"`, `"normalized_label"`, `"canonical_merge"`).
- **`EntityService` (`kgk.entities`)**:
  - **`alias(entity_id, alias_label, ...)`**: Records explicit alias and emits `ENTITY_ALIAS` event into `EventStore`.
  - **`resolve(identifier, ...)`**: Resolves identifiers against:
    1. Exact ID
    2. Canonical merge chains
    3. Explicit aliases
    4. Normalized labels
  - **`candidates(label, entity_type, namespace)`**: Finds fuzzy and substring matches across both primary entity labels and alias registries.
  - **Multi-Hop Merge Resolution & Cycle Rejection**:
    - Resolves multi-hop entity consolidation ($A \rightarrow B, B \rightarrow C \implies \text{resolve}(A) == C$).
    - Cycle check: Rejects circular merge attempts ($A \rightarrow B, B \rightarrow A$) with `ValueError`.
    - Non-destructive: Original entity records ($A$ and $B$) remain preserved in graph and event history.

---

### 2.3 Phase 5: Relation Ontology & Schema Validation (`ontology/`)
- **`RelationDefinition` Model**:
  - `id: str`: Predicate identifier (e.g. `rel:has_injury`)
  - `label: str`: Predicate label (e.g. `has_injury`)
  - `inverse_label: str | None`: Inverse predicate label (e.g. `injury_of`)
  - `subject_types: list[str]`: Allowed entity types for subject
  - `object_types: list[str]`: Allowed entity types for object
  - Logical traits: `is_functional: bool`, `is_symmetric: bool`, `is_transitive: bool`
  - `namespace: str = "global"`
- **`RelationRegistry` (`kgk.ontology`)**:
  - Predicate catalog and validation engine.
  - **`validate_statement(subject_type, relation_label, object_type, strict)`**:
    - **Valid Schema**: Allows statements conforming to type rules (e.g. `Person --has_injury--> Injury`).
    - **Type Mismatch**: Raises `TypeError` on invalid assertions (e.g. `Location --has_injury--> CalendarEvent`).
    - **Strict Mode (`strict=True`)**: Rejects unregistered predicates with `ValueError`.
    - **Loose Mode (`strict=False`)**: Allows ad-hoc predicates to facilitate exploratory knowledge capture.

---

### 2.4 Ingestion & Pipeline Integration
- **`IngestionPipeline`**:
  - Wired to `EntityService` and `RelationRegistry`.
  - Automatically resolves entity aliases during ingestion to prevent fragmenting canonical entities across alternate names.
  - Validates assertions against registered relation schemas before graph commit and event emission.

---

## 3. Verification & Test Matrix

Executed full test suite via `uv run pytest`:

| Test Module | Focus Area | Result |
| :--- | :--- | :--- |
| `tests/test_namespaces.py` | Namespace registration, hierarchy expansion, and isolated tenant queries | **PASS** |
| `tests/test_entity_resolution.py` | Entity aliasing, candidate discovery, multi-hop merge chains ($A \rightarrow B \rightarrow C$), and cycle prevention | **PASS** |
| `tests/test_ontology.py` | Predicate registration, schema type validation, and strict vs. loose modes | **PASS** |
| `tests/test_invariants.py` | Regression verification of all 10 core kernel invariants | **PASS** |
| `tests/test_events.py` | Event append queries and replay graph reconstruction | **PASS** |
| `tests/test_supersession_chains.py` | Multi-hop supersession resolution ($S_1 \rightarrow S_2 \rightarrow S_3$) | **PASS** |
| `tests/test_api.py` | FastAPI REST endpoints | **PASS** |
| `tests/test_kernel.py` | End-to-end kernel operations | **PASS** |
| `tests/test_graph.py` | Graph store adjacency and neighborhood queries | **PASS** |
| `tests/test_models.py` | Pydantic data models | **PASS** |

**Summary**: 34 passing tests (0 failures, 0 warnings).

---

## 4. Architectural Outcomes

1. **Multi-Tenancy**: Multiple applications can share a single KGK instance with customized isolation, inheritance, and scoping policies.
2. **Identity Integrity**: Identities are unified through aliases and canonical merge chains without destroying source evidence.
3. **Semantic Correctness**: Predicate schemas prevent corrupting the knowledge graph with malformed relations while preserving optional flexibility for loose data sources.
