# KGK Course Log

## 2026-09-19 - Restore namespaces as the shared-memory boundary

- **Previous understanding:** The public v1 release described multi-tenant namespaces, but namespace registration lived only in memory and most interfaces could read or mutate knowledge without a namespace.
- **New understanding:** KGK is the shared durable knowledge authority. Applications retain admission and authentication policy, then use a host-issued KGK namespace capability for every supported knowledge operation.
- **Evidence or reason:** The public API, kernel convenience methods, pathfinding, temporal views, events, and storage access contained unscoped paths; namespace hierarchy disappeared on restart.
- **Effect on destination, route, ownership, or boundaries:** Namespace registration is now event-backed, SQLite composition restores it, application operations are capability-scoped, sibling access is rejected, and inherited parent knowledge is read-only through child capabilities.
- **Affected projects:** KGK directly. APE, MAP, Mina, Enterprise, and MAR integrations can adopt the scoped client boundary in later project-owned work.
