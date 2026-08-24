from pydantic import BaseModel, ConfigDict, Field

from models.entity import Entity


class EntityAlias(BaseModel):
    """An explicit alias pointing to a canonical entity."""

    model_config = ConfigDict(frozen=True)

    alias: str
    canonical_id: str
    namespace: str = "global"
    source: str = "manual"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class EntityResolutionResult(BaseModel):
    """Result of entity resolution explaining how a match was established."""

    entity: Entity
    match_type: str  # "exact_id", "alias", "normalized_label", "canonical_merge"
    confidence: float = 1.0
