# KGK System Map

## Responsibility

KGK turns admitted statements into durable, provenance-bearing knowledge and makes that knowledge retrievable within explicit namespace boundaries.

## Components

| Component | Responsibility |
|---|---|
| Namespace registry | Registered namespace hierarchy, inheritance, and writable state |
| Scoped capability | The supported application boundary for namespace-limited reads and writes |
| Ingestion | Entity/relation resolution, statement validation, deduplication, and event emission |
| Event store | Append-only authority for knowledge transitions and namespace registration |
| Graph store | Queryable projection of entities, relations, and statements |
| Retrieval | Scoped lookup, hybrid search, neighborhoods, paths, temporal views, and formatting |
| Knowledge lifecycle | Conflict detection, retraction, supersession, consolidation, and provenance |
| HTTP and CLI adapters | Local interfaces that select a namespace scope before accessing knowledge; network hosts may bind selection to authentication through an authorizer callback |

## Flow

1. The host authenticates or otherwise identifies its caller.
2. The host selects a registered namespace capability for that caller.
3. The application decides which knowledge may be admitted and supplies provenance.
4. KGK validates the namespace boundary, appends knowledge events, and updates its projection.
5. Retrieval expands only the selected namespace’s permitted parent scope.
6. On restart, the namespace registry and knowledge projection reopen from the same durable SQLite composition.

## State and authority

The append-only event store is KGK’s history authority. The graph store is the current query projection. Namespace registration is part of the durable knowledge history. Embeddings are derived indexes and may be rebuilt. Application databases remain authoritative for operational or business state that has not been promoted into KGK.

## External boundaries

Applications supply domain admission policy and a validated namespace selection. KGK supplies scoped durable knowledge operations. Transport authentication, user accounts, and business authorization remain with the composition host.

## Intended and current topology

The target is a durable local KGK composition shared through scoped capabilities. The published baseline has the individual storage and namespace pieces but currently connects them as optional filters around an in-memory default. Current implementation work is closing that gap.
