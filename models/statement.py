from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from epistemic.models import EpistemicStatus
from models.entity import Entity, EntityCreate
from models.ids import new_id
from models.relation import Relation, RelationCreate
from provenance.models import ProvenanceRecord


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StatementStatus(str, Enum):
    ACTIVE = "active"
    RETRACTED = "retracted"
    SUPERSEDED = "superseded"


class StatementCreate(BaseModel):
    subject: Entity | EntityCreate
    relation: Relation | RelationCreate
    object: Entity | EntityCreate
    provenance: ProvenanceRecord
    namespace: str = "global"
    properties: dict[str, Any] = Field(default_factory=dict)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    epistemic_status: EpistemicStatus = EpistemicStatus.FACT


class Statement(BaseModel):
    """Immutable historical assertion with bitemporal timestamps and epistemic modality."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=new_id)
    subject_id: str
    relation_id: str
    object_id: str
    provenance: ProvenanceRecord
    namespace: str = "global"
    properties: dict[str, Any] = Field(default_factory=dict)
    status: StatementStatus = StatementStatus.ACTIVE
    created_at: datetime = Field(default_factory=_utcnow)
    retracted_at: datetime | None = None
    retraction_reason: str | None = None
    superseded_by: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    epistemic_status: EpistemicStatus = EpistemicStatus.FACT

    @property
    def is_active(self) -> bool:
        return self.status == StatementStatus.ACTIVE

    def is_valid_at(self, target_dt: datetime) -> bool:
        """Determines if the real-world fact was valid at target_dt."""
        if self.valid_from and target_dt < self.valid_from:
            return False
        if self.valid_until and target_dt > self.valid_until:
            return False
        return True


class ProjectedStatement(BaseModel):
    """Projected view of a statement computed from authoritative event history."""

    statement: Statement
    current_status: StatementStatus
    superseded_by_id: str | None = None
    retraction_reason: str | None = None
    supersession_chain: list[str] = Field(default_factory=list)
