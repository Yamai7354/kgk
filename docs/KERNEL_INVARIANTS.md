# Knowledge Graph Kernel (KGK) — Kernel Invariants

**Version:** 0.2.0-draft  
**Status:** Authoritative  

> *"KGK stores evidence and knowledge history. KGK computes current knowledge views. KGK never rewrites history to make the current view convenient."*

---

## The Invariants of Knowledge

These laws are non-negotiable architectural invariants governing all KGK modules, storage backends, and extensions.

### 1. Statements Never Disappear
Once a statement is asserted and recorded in the event history, it cannot be deleted. All queries against historical snapshots will observe the fact as it existed.

### 2. Historical Assertions Never Change Identity
A statement ID ($S_{id}$) and its underlying proposition $(Subject, Predicate, Object)$ are immutable. A statement record represents a historical observation, not a mutable cell in memory.

### 3. Retraction Never Deletes the Original Assertion
Retraction is modeled as an append-only `RETRACT` event pointing to a statement ID with an actor, timestamp, and audit reason. A retracted statement remains present in historical lineage.

### 4. Supersession Preserves the Superseded Assertion
When statement $S_1$ is superseded by $S_2$, both $S_1$ and $S_2$ remain intact. A `SUPERSEDE` event records the transition $S_1 \rightarrow S_2$, enabling deterministic resolution of supersession chains ($S_1 \rightarrow S_2 \rightarrow S_3$).

### 5. Entity Merging Preserves Every Original Entity
Consolidation and alias resolution merge the active graph representation of duplicate entities into a canonical identity while preserving the original identity records ($E_1, E_2$) and their historical references.

### 6. Every Assertion Has Provenance
No statement can enter the kernel without an explicit `ProvenanceRecord` detailing its source, confidence, and observation metadata.

### 7. Every Mutation Creates an Auditable Event
The kernel state is event-sourced. Every assertion, retraction, supersession, entity creation, and merge creates an immutable, timestamped `KnowledgeEvent`.

### 8. Derived Knowledge is Distinguishable from Observed Knowledge
Inferred or derived statements must explicitly reference their derivation lineage and upstream premises. Retracting an upstream premise invalidates downstream derived conclusions.

### 9. Confidence is Strictly Separated from Authority
- **Confidence ($0.0 \le c \le 1.0$):** Measures extraction accuracy ("Did we correctly understand what the source stated?").
- **Authority ($0 \le a \le 100+$):** Measures policy control over current truth ("How much should this source override other sources?").

### 10. Storage Implementations Cannot Change KGK Semantics
Any storage backend (in-memory, relational, graph database, vector store) serves strictly as a projectable query view. The authoritative truth remains the ordered event stream.

### 11. Namespace Capabilities Bound Application Access
Supported application reads and writes operate through a registered namespace capability. A namespace may read deliberately inherited parent knowledge, but it cannot read or mutate sibling knowledge and cannot mutate inherited parent knowledge. Authentication and capability assignment remain the host application's responsibility.
