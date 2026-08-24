from graph import InMemoryGraphStore
from models import Entity, Relation, Statement, new_id
from models.statement import StatementStatus
from provenance import ProvenanceRecord


def test_in_memory_store_round_trip():
    store = InMemoryGraphStore()
    alice = Entity(label="Alice")
    knows = Relation(label="knows")
    bob = Entity(label="Bob")

    store.add_entity(alice)
    store.add_entity(bob)
    store.add_relation(knows)

    stmt = Statement(
        subject_id=alice.id,
        relation_id=knows.id,
        object_id=bob.id,
        provenance=ProvenanceRecord(source="test"),
    )
    store.add_statement(stmt)

    assert store.get_entity(alice.id) == alice
    assert len(store.statements_for_subject(alice.id)) == 1


def test_filter_retracted_statements():
    store = InMemoryGraphStore()
    alice = Entity(label="Alice")
    bob = Entity(label="Bob")
    knows = Relation(label="knows")
    store.add_entity(alice)
    store.add_entity(bob)
    store.add_relation(knows)

    active = Statement(
        subject_id=alice.id,
        relation_id=knows.id,
        object_id=bob.id,
        provenance=ProvenanceRecord(source="test"),
    )
    retracted = active.model_copy(
        update={
            "id": new_id(),
            "status": StatementStatus.RETRACTED,
            "retraction_reason": "bad data",
        }
    )
    store.add_statement(active)
    store.add_statement(retracted)

    assert len(store.statements_for_subject(alice.id)) == 1
    assert len(store.statements_for_subject(alice.id, status=None)) == 2
