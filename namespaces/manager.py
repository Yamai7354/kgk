from namespaces.models import Namespace, NamespacePolicy


class NamespaceManager:
    """Manages namespace registration, parent inheritance chains, and query scope resolution."""

    def __init__(self, policy: NamespacePolicy | None = None) -> None:
        self._policy = policy or NamespacePolicy()
        self._namespaces: dict[str, Namespace] = {
            "global": Namespace(id="global", description="Root global namespace", priority=0)
        }

    def register(self, namespace: Namespace) -> Namespace:
        existing = self._namespaces.get(namespace.id)
        if existing is not None:
            if existing == namespace:
                return existing
            raise ValueError(f"Namespace already registered with different settings: {namespace.id}")
        if namespace.parent_id and namespace.parent_id not in self._namespaces:
            raise KeyError(f"Parent namespace not found: {namespace.parent_id}")
        if namespace.id == "global" and namespace.parent_id is not None:
            raise ValueError("The global namespace cannot have a parent")
        if namespace.parent_id == namespace.id:
            raise ValueError("A namespace cannot inherit from itself")
        self._namespaces[namespace.id] = namespace
        return namespace

    def require(self, namespace_id: str) -> Namespace:
        namespace = self.get(namespace_id)
        if namespace is None:
            raise KeyError(f"Namespace not registered: {namespace_id}")
        return namespace

    def get(self, namespace_id: str) -> Namespace | None:
        return self._namespaces.get(namespace_id)

    def all_namespaces(self) -> list[Namespace]:
        return list(self._namespaces.values())

    def resolve_read_scope(self, scope: str | list[str] | None) -> list[str]:
        """Expands namespace scope to include all inherited parent namespaces."""
        if scope is None:
            return ["global"]

        initial_scopes = [scope] if isinstance(scope, str) else list(scope)
        resolved: set[str] = set()

        for ns_id in initial_scopes:
            self.require(ns_id)
            current = ns_id
            visited = set()
            while current:
                if current in visited:
                    break
                visited.add(current)
                resolved.add(current)
                ns_obj = self._namespaces.get(current)
                if ns_obj and ns_obj.parent_id:
                    current = ns_obj.parent_id
                else:
                    break

            if self._policy.inherit_global:
                resolved.add("global")

        return sorted(list(resolved))

    def is_writable(self, namespace_id: str) -> bool:
        ns = self._namespaces.get(namespace_id)
        if ns is None:
            return False
        return not ns.is_read_only
