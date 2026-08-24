from models import Entity, EntityCreate, RelationCreate, StatementCreate
from provenance import ProvenanceRecord


def test_entity_create_defaults():
    entity = EntityCreate(label="Alice", type="Person")
    assert entity.type == "Person"
    assert entity.properties == {}


def test_entity_gets_unique_id():
    a = Entity(label="A")
    b = Entity(label="B")
    assert a.id != b.id


def test_statement_create_accepts_nested_models():
    payload = StatementCreate(
        subject=EntityCreate(label="Alice"),
        relation=RelationCreate(label="knows"),
        object=EntityCreate(label="Bob"),
        provenance=ProvenanceRecord(source="unit-test"),
    )
    assert payload.subject.label == "Alice"
