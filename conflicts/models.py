from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models.ids import new_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConflictType(str, Enum):
    FUNCTIONAL_VIOLATION = "functional_violation"
    MUTUAL_EXCLUSION = "mutual_exclusion"
    VALUE_DISAGREEMENT = "value_disagreement"


class ConflictStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class Conflict(BaseModel):
    """Represents a detected contradiction or rule violation across assertions."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=new_id)
    conflict_type: ConflictType = ConflictType.FUNCTIONAL_VIOLATION
    subject_id: str
    relation_id: str
    statement_ids: list[str]
    detected_at: datetime = Field(default_factory=_utcnow)
    status: ConflictStatus = ConflictStatus.OPEN
    winning_statement_id: str | None = None
    resolution_reason: str | None = None
    resolved_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
