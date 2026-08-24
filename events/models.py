from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models.ids import new_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EventType(str, Enum):
    ASSERT = "assert"
    RETRACT = "retract"
    SUPERSEDE = "supersede"
    ENTITY_CREATE = "entity_create"
    ENTITY_ALIAS = "entity_alias"
    ENTITY_MERGE = "entity_merge"
    RELATION_CREATE = "relation_create"
    PROVENANCE_ATTACH = "provenance_attach"
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"


class KnowledgeEvent(BaseModel):
    """Immutable audit event representing a single transition in knowledge history."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=new_id)
    event_type: EventType
    namespace: str = "global"
    timestamp: datetime = Field(default_factory=_utcnow)
    actor: str = "system"
    target_id: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
