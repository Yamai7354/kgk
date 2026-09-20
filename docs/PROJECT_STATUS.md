# KGK Project Status

## Current position

The working repository began from the public `Yamai7354/kgk` release at commit `918cdfd` and is now continued on `codex/kgk-namespaced-memory`. KGK 1.1 adds durable namespace registration, a supported namespace capability, namespace-scoped HTTP and CLI access, and a persistent SQLite composition.

## Intended versus current composition

The intended composition is one durable KGK runtime serving explicitly scoped project or agent capabilities. That composition is now implemented in KGK itself. Existing consumer projects have not yet been migrated to the new scoped capability, so shared infrastructure adoption remains separate project-owned work.

## Current focus

Review and publish the KGK 1.1 change, then let each consumer adopt it through its own boundary work rather than changing other repositories from inside KGK.

## Recent learning

The public repository already contained the namespace model and did not need to be replaced or recloned. The missing work was composition and enforcement. “Namespace-partitioned” now describes the kernel accurately; authenticated multi-tenant deployment remains a host responsibility.

## Evidence and uncertainty

- GitHub and the local checkout both identify `918cdfd` as the sole public release commit.
- Namespace registration is recorded in the event ledger and restored with persistent SQLite state.
- The repository suite passes, including restart persistence, sibling isolation, inherited global reads, read-only namespaces, API enforcement, and cross-namespace identity protection.
- Low-level stores and administrative kernel surfaces remain available for implementation and recovery work; application-facing access is through `KnowledgeGraphKernel.scope(...)`.
- Authentication remains deliberately outside KGK; the host must bind identities to namespace capabilities.
