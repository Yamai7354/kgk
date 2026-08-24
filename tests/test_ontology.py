import pytest

from models import EntityCreate, RelationCreate, StatementCreate
from ontology.models import RelationDefinition


def test_ontology_schema_validation_success_and_failure(kgk, provenance):
    # Register Person --has_injury--> Injury
    kgk.ontology.register(
        RelationDefinition(
            id="rel:has_injury",
            label="has_injury",
            subject_types=["Person"],
            object_types=["Injury"],
            is_functional=False,
        )
    )

    # Valid statement
    valid_stmt = StatementCreate(
        subject=EntityCreate(label="Mina", type="Person"),
        relation=RelationCreate(label="has_injury"),
        object=EntityCreate(label="Fracture", type="Injury"),
        provenance=provenance,
    )
    result = kgk.ingest(valid_stmt)
    assert result.statement.id is not None

    # Invalid statement: Location --has_injury--> CalendarEvent
    invalid_stmt = StatementCreate(
        subject=EntityCreate(label="Tokyo", type="Location"),
        relation=RelationCreate(label="has_injury"),
        object=EntityCreate(label="Meeting", type="CalendarEvent"),
        provenance=provenance,
    )

    with pytest.raises(TypeError, match="Invalid subject type 'Location'"):
        kgk.ingest(invalid_stmt)


def test_ontology_strict_mode_rejects_unregistered_relations(kgk, provenance):
    unregistered_stmt = StatementCreate(
        subject=EntityCreate(label="A"),
        relation=RelationCreate(label="unknown_predicate"),
        object=EntityCreate(label="B"),
        provenance=provenance,
    )

    # Loose mode (default) allows unregistered relations
    loose_res = kgk.ingest(unregistered_stmt, strict_schema=False)
    assert loose_res.statement.id is not None

    # Strict mode rejects unregistered relations
    with pytest.raises(ValueError, match="not defined in strict schema mode"):
        kgk.ingest(unregistered_stmt, strict_schema=True)
