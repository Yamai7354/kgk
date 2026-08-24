from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from models.ids import new_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EntityCreate(BaseModel):
    label: str
    type: str = "Thing"
    namespace: str = "global"
    properties: dict[str, Any] = Field(default_factory=dict)


class Entity(EntityCreate):
    id: str = Field(default_factory=new_id)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    merged_into: str | None = None

    @property
    def is_active(self) -> bool:
        return self.merged_into is None
