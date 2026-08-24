from events.models import EventType
from models import EntityCreate, RelationCreate, StatementCreate
from provenance.models import ProvenanceRecord, Source


def test_invariant_statements_never_disappear_on_retract(kgk, provenance):
    """Law 1 & 3: Retraction never deletes statements from history."""
    result = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="likes"),
            object=EntityCreate(label="Coffee"),
            provenance=provenance,
        )
    )
    stmt_id = result.statement.id

    # Retract statement
    kgk.retract(stmt_id, reason="Changed mind")

    # Historical retrieval by ID still finds the assertion
    retrieved = kgk.retrieve.get_statement(stmt_id)
    assert retrieved is not None
    assert retrieved.statement.id == stmt_id
    assert not retrieved.statement.is_active

    # Authoritative event stream contains ASSERT and RETRACT
    events = kgk.events.events_for_target(stmt_id)
    assert any(e.event_type == EventType.ASSERT for e in events)
    assert any(e.event_type == EventType.RETRACT for e in events)


def test_invariant_supersession_preserves_both_assertions(kgk, provenance):
    """Law 4: Supersession preserves both old and new assertions."""
    s1 = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="lives_in"),
            object=EntityCreate(label="Tokyo"),
            provenance=provenance,
        )
    ).statement

    s2 = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="lives_in"),
            object=EntityCreate(label="Omaha"),
            provenance=provenance,
        )
    ).statement

    kgk.supersede(s1.id, s2, reason="Relocated")

    # S1 still exists historically, but marked superseded
    retrieved_s1 = kgk.retrieve.get_statement(s1.id)
    assert retrieved_s1 is not None
    assert retrieved_s1.statement.superseded_by == s2.id

    # S2 exists and is active
    retrieved_s2 = kgk.retrieve.get_statement(s2.id)
    assert retrieved_s2 is not None
    assert retrieved_s2.statement.is_active


def test_invariant_entity_merging_preserves_original_identities(kgk, provenance):
    """Law 5: Merging entities preserves original identity records."""
    e1 = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="role"),
            object=EntityCreate(label="Protagonist"),
            provenance=provenance,
        )
    ).subject

    e2 = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina Park"),
            relation=RelationCreate(label="origin"),
            object=EntityCreate(label="Earth"),
            provenance=provenance,
        )
    ).subject

    kgk.merge_entities(e1.id, [e2.id])

    # Both entities exist in store
    orig_e1 = kgk.store.get_entity(e1.id)
    orig_e2 = kgk.store.get_entity(e2.id)
    assert orig_e1 is not None
    assert orig_e2 is not None
    assert orig_e2.merged_into == e1.id


def test_invariant_confidence_vs_authority_separation():
    """Law 9: Confidence measures extraction accuracy; Authority measures policy control."""
    source = Source(id="character_card_v1", type="canon_card", authority=100.0)
    record = ProvenanceRecord(
        source="character_card_v1",
        source_id=source.id,
        confidence=0.95,
        authority=source.authority,
    )

    assert record.confidence == 0.95
    assert record.authority == 100.0
    assert record.confidence != record.authority


def test_invariant_every_mutation_creates_auditable_event(kgk, provenance):
    """Law 7: Every mutation generates an immutable KnowledgeEvent."""
    kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Alice"),
            relation=RelationCreate(label="knows"),
            object=EntityCreate(label="Bob"),
            provenance=provenance,
        )
    )

    all_events = kgk.events.all_events()
    event_types = {e.event_type for e in all_events}
    assert EventType.ENTITY_CREATE in event_types
    assert EventType.RELATION_CREATE in event_types
    assert EventType.ASSERT in event_types
