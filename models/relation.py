from datetime import datetime, timezone

from pydantic import BaseModel, Field

from models.ids import new_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RelationCreate(BaseModel):
    label: str
    type: str = "Relation"
    inverse_label: str | None = None
    namespace: str = "global"


class Relation(RelationCreate):
    id: str = Field(default_factory=new_id)
    created_at: datetime = Field(default_factory=_utcnow)
