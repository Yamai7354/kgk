from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Namespace(BaseModel):
    """An isolated domain/tenant of knowledge."""

    model_config = ConfigDict(frozen=True)

    id: str
    parent_id: str | None = None
    description: str | None = None
    priority: int = 50
    is_read_only: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Namespace id cannot be empty")
        return normalized


class NamespacePolicy(BaseModel):
    """Defines inheritance rules, visibility, and priority across namespaces."""

    default_namespace: str = "global"
    inherit_global: bool = True
