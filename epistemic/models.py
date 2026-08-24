from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EpistemicStatus(str, Enum):
    """Categorization of an assertion's certainty and truth modality."""

    FACT = "fact"
    HYPOTHESIS = "hypothesis"
    ASSUMPTION = "assumption"
    BELIEF = "belief"
    CONJECTURE = "conjecture"
    RUMOR = "rumor"


class Perspective(BaseModel):
    """A worldview or lens through which truth and authority are evaluated."""

    model_config = ConfigDict(frozen=True)

    name: str
    preferred_sources: list[str] = Field(default_factory=list)
    accepted_statuses: list[EpistemicStatus] = Field(
        default_factory=lambda: [
            EpistemicStatus.FACT,
            EpistemicStatus.HYPOTHESIS,
            EpistemicStatus.ASSUMPTION,
            EpistemicStatus.BELIEF,
            EpistemicStatus.CONJECTURE,
            EpistemicStatus.RUMOR,
        ]
    )
    authority_overrides: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
