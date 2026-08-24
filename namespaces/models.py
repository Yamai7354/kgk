from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Namespace(BaseModel):
    """An isolated domain/tenant of knowledge."""

    model_config = ConfigDict(frozen=True)

    id: str
    parent_id: str | None = None
    description: str | None = None
    priority: int = 50
    is_read_only: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class NamespacePolicy(BaseModel):
    """Defines inheritance rules, visibility, and priority across namespaces."""

    default_namespace: str = "global"
    inherit_global: bool = True
