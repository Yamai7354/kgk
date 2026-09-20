# KGK Project Charter

## Coordinates

KGK exists to give local AI systems one durable, inspectable knowledge authority. Projects and agents keep ownership of what their knowledge means and what may be admitted; KGK preserves accepted knowledge, provenance, time, conflicts, corrections, and retrieval through explicit namespaces.

## Why it matters

Without a shared knowledge authority, each application quietly creates another memory implementation and the infrastructure loses continuity. Without namespace boundaries, a shared store becomes an undifferentiated pool that callers can accidentally read or change.

## Complete-system picture

A host application opens a namespace-scoped KGK capability, admits provenance-bearing knowledge, restarts, and retrieves the same knowledge from durable storage. A different project namespace cannot see or mutate it. Deliberately inherited parent knowledge remains visible, and every correction retains its event history.

## Ownership

KGK owns:

- durable knowledge events and their projections;
- namespace registration, hierarchy, scoped reads, and scoped writes;
- immutable statements, provenance, temporal history, conflict records, retraction, supersession, and retrieval semantics.

Calling projects own:

- domain meaning and operational state;
- admission and promotion decisions;
- user, agent, or service authentication;
- which validated namespace capability a caller receives.

KGK namespaces enforce the capability supplied by the host. They do not replace transport authentication or application authorization.

## Infrastructure position

APE, MAP, Mina, Enterprise, and other consumers may share a KGK composition without sharing all knowledge. Each integrates through a namespace-scoped client or capability. MAR may expose KGK through a replaceable memory boundary but does not become the knowledge authority.

## Important assumptions

- `global` is the root namespace and is readable through inheritance when policy allows it.
- Project and agent namespaces must be registered before scoped use.
- SQLite is the initial durable local composition; storage remains replaceable.
- Direct store access is an administrative/internal boundary. Application code uses scoped KGK access.
- Published GitHub history is the baseline, while `E:\ai\kgk` is the only active working checkout.
