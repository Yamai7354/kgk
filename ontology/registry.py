from ontology.models import RelationDefinition


class RelationRegistry:
    """Registry of predicate definitions and schema validation engine."""

    def __init__(self) -> None:
        self._definitions: dict[str, RelationDefinition] = {}

    def register(self, definition: RelationDefinition) -> RelationDefinition:
        self._definitions[definition.id] = definition
        self._definitions[definition.label.lower()] = definition
        return definition

    def get(self, identifier: str) -> RelationDefinition | None:
        return self._definitions.get(identifier) or self._definitions.get(identifier.lower())

    def all_relations(self) -> list[RelationDefinition]:
        # Deduplicate values
        unique = {d.id: d for d in self._definitions.values()}
        return list(unique.values())

    def validate_statement(
        self,
        subject_type: str,
        relation_label: str,
        object_type: str,
        *,
        strict: bool = False,
    ) -> None:
        """Validates that subject and object types satisfy the registered predicate schema."""
        defn = self.get(relation_label)
        if defn is None:
            if strict:
                raise ValueError(
                    f"Relation '{relation_label}' is not defined in strict schema mode"
                )
            return

        if defn.subject_types and subject_type not in defn.subject_types:
            raise TypeError(
                f"Invalid subject type '{subject_type}' for relation '{relation_label}'. "
                f"Expected one of: {defn.subject_types}"
            )

        if defn.object_types and object_type not in defn.object_types:
            raise TypeError(
                f"Invalid object type '{object_type}' for relation '{relation_label}'. "
                f"Expected one of: {defn.object_types}"
            )
