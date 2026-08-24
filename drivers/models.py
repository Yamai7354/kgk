from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models.ids import new_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Span(BaseModel):
    """Specific location span within a source document."""

    model_config = ConfigDict(frozen=True)

    start_char: int | None = None
    end_char: int | None = None
    line_number: int | None = None
    text_snippet: str | None = None


class Document(BaseModel):
    """Raw source document payload to be processed by extractors."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=new_id)
    text: str
    source_uri: str | None = None
    source_type: str = "document"
    namespace: str = "global"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
