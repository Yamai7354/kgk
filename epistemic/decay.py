from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.statement import Statement


class DecayModel:
    """Computes exponential half-life confidence decay for dynamic knowledge."""

    def __init__(self, half_life_seconds: float = 86400.0) -> None:
        self.half_life_seconds = half_life_seconds

    def compute_decay(self, initial_confidence: float, elapsed_seconds: float) -> float:
        if elapsed_seconds <= 0:
            return initial_confidence
        decay_factor = 0.5 ** (elapsed_seconds / self.half_life_seconds)
        decayed = initial_confidence * decay_factor
        return round(max(0.01, min(1.0, decayed)), 4)


def compute_effective_confidence(
    statement: "Statement",
    half_life_seconds: float | None = None,
    as_of: datetime | None = None,
) -> float:
    """Calculates the time-decayed effective confidence of a statement."""
    base_confidence = (
        statement.provenance.confidence if statement.provenance.confidence is not None else 1.0
    )

    hl = half_life_seconds or statement.properties.get("half_life_seconds")
    if hl is None:
        return base_confidence

    target_dt = as_of or datetime.now(timezone.utc)
    elapsed = (target_dt - statement.created_at).total_seconds()
    if elapsed <= 0:
        return base_confidence

    model = DecayModel(half_life_seconds=float(hl))
    return model.compute_decay(base_confidence, elapsed)
