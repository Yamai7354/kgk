from pydantic import BaseModel, ConfigDict, Field

from models.ids import new_id


class RelationDefinition(BaseModel):
    """Formal predicate specification defining inverse labels, type schemas, and logical traits."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=new_id)
    label: str
    inverse_label: str | None = None
    subject_types: list[str] = Field(default_factory=list)
    object_types: list[str] = Field(default_factory=list)
    is_functional: bool = False
    is_symmetric: bool = False
    is_transitive: bool = False
    namespace: str = "global"
    description: str | None = None
