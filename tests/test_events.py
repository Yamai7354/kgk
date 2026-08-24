from events.models import EventType, KnowledgeEvent
from events.store import InMemoryEventStore
from models import EntityCreate, RelationCreate, StatementCreate


def test_event_store_append_and_query():
    store = InMemoryEventStore()
    e1 = store.append(
        KnowledgeEvent(event_type=EventType.ASSERT, target_id="S1", payload={"key": "val1"})
    )
    e2 = store.append(
        KnowledgeEvent(event_type=EventType.RETRACT, target_id="S1", payload={"key": "val2"})
    )

    assert store.get(e1.event_id) == e1
    assert store.get(e2.event_id) == e2
    assert len(store.events_for_target("S1")) == 2
    assert len(store.events_by_type(EventType.ASSERT)) == 1
    assert len(store.events_by_type(EventType.RETRACT)) == 1


def test_kernel_event_replay_reconstruction(kgk, provenance):
    # Ingest facts
    s1_res = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="lives_in"),
            object=EntityCreate(label="Tokyo"),
            provenance=provenance,
        )
    )
    s2_res = kgk.ingest(
        StatementCreate(
            subject=s1_res.subject,
            relation=RelationCreate(label="lives_in"),
            object=EntityCreate(label="Omaha"),
            provenance=provenance,
        )
    )

    # Supersede S1 -> S2
    kgk.supersede(s1_res.statement.id, s2_res.statement, reason="Moved")

    # Ingest duplicate Mina Park and merge
    mina_dup = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina Park"),
            relation=RelationCreate(label="hobby"),
            object=EntityCreate(label="Coding"),
            provenance=provenance,
        )
    )
    kgk.merge_entities(s1_res.subject.id, [mina_dup.subject.id])

    # Replay event stream to reconstruct graph from scratch
    reconstructed_store = kgk.replay()

    # Verify reconstructed graph matches exactly
    canonical = reconstructed_store.get_entity(s1_res.subject.id)
    assert canonical is not None
    assert canonical.label == "Mina"

    dup = reconstructed_store.get_entity(mina_dup.subject.id)
    assert dup is not None
    assert dup.merged_into == s1_res.subject.id

    s1 = reconstructed_store.get_statement(s1_res.statement.id)
    assert s1.status.value == "superseded"
    assert s1.superseded_by == s2_res.statement.id

    active_stmts = reconstructed_store.statements_for_subject(s1_res.subject.id)
    rels = {s.relation_id for s in active_stmts}
    assert s2_res.relation.id in rels
    assert mina_dup.relation.id in rels
