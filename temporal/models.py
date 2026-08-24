from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TimeInterval(BaseModel):
    """An interval of time with optional open bounds."""

    model_config = ConfigDict(frozen=True)

    start: datetime | None = None
    end: datetime | None = None

    def contains(self, dt: datetime) -> bool:
        if self.start and dt < self.start:
            return False
        if self.end and dt > self.end:
            return False
        return True

    def overlaps(self, other: "TimeInterval") -> bool:
        """Determines if two intervals share any common point in time."""
        if self.start and other.end and self.start > other.end:
            return False
        if self.end and other.start and self.end < other.start:
            return False
        return True
