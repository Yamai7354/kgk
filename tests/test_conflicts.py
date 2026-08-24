from conflicts.models import ConflictStatus, ConflictType
from events.models import EventType
from models import EntityCreate, RelationCreate, StatementCreate
from ontology.models import RelationDefinition
from provenance.models import ProvenanceRecord


def test_functional_relation_conflict_detection_and_resolution(kgk):
    # Register functional relation: birthplace (can only have 1 birthplace)
    kgk.ontology.register(
        RelationDefinition(
            id="rel:birthplace",
            label="birthplace",
            is_functional=True,
        )
    )

    prov_high = ProvenanceRecord(source="official_bio", authority=100.0, confidence=1.0)
    prov_low = ProvenanceRecord(source="fan_speculation", authority=10.0, confidence=0.8)

    # Ingest birthplace = Tokyo (high authority)
    s1 = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="birthplace"),
            object=EntityCreate(label="Tokyo"),
            provenance=prov_high,
        )
    )

    # Ingest birthplace = Omaha (low authority) -> introduces conflict!
    s2 = kgk.ingest(
        StatementCreate(
            subject=s1.subject,
            relation=RelationCreate(label="birthplace"),
            object=EntityCreate(label="Omaha"),
            provenance=prov_low,
        )
    )

    # Verify conflict was automatically detected
    open_conflicts = kgk.conflicts.all_conflicts(status=ConflictStatus.OPEN)
    assert len(open_conflicts) == 1
    conflict = open_conflicts[0]
    assert conflict.conflict_type == ConflictType.FUNCTIONAL_VIOLATION
    assert s1.statement.id in conflict.statement_ids
    assert s2.statement.id in conflict.statement_ids

    # Verify CONFLICT_DETECTED event was logged
    detected_events = kgk.events.events_by_type(EventType.CONFLICT_DETECTED)
    assert len(detected_events) >= 1

    # Resolve conflict by authority
    resolved = kgk.conflicts.resolve_by_authority(conflict.id)
    assert resolved.status == ConflictStatus.RESOLVED
    assert resolved.winning_statement_id == s1.statement.id

    # Verify losing statement (s2) was retracted
    s2_retrieved = kgk.retrieve.get_statement(s2.statement.id)
    assert not s2_retrieved.statement.is_active

    # Verify winning statement (s1) remains active
    s1_retrieved = kgk.retrieve.get_statement(s1.statement.id)
    assert s1_retrieved.statement.is_active

    # Verify CONFLICT_RESOLVED event was logged
    resolved_events = kgk.events.events_by_type(EventType.CONFLICT_RESOLVED)
    assert len(resolved_events) >= 1
