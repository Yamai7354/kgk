from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Source(BaseModel):
    """Authoritative producer of knowledge assertions with a distinct authority rating."""

    id: str
    type: str = "generic"
    authority: float = Field(default=50.0, ge=0.0)
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProvenanceRecord(BaseModel):
    """Observation metadata for an assertion, separating confidence from authority."""

    source: str
    source_id: str | None = None
    source_uri: str | None = None
    extractor: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    authority: float | None = None
    observed_at: datetime = Field(default_factory=_utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProvenanceEvent(BaseModel):
    statement_id: str
    event_type: str
    record: ProvenanceRecord
    timestamp: datetime = Field(default_factory=_utcnow)
