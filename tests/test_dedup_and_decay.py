from datetime import datetime, timedelta, timezone

from epistemic.decay import compute_effective_confidence
from models import EntityCreate, RelationCreate, StatementCreate
from provenance.models import ProvenanceRecord


def test_statement_deduplication_reinforces_confidence(kgk):
    prov1 = ProvenanceRecord(source="source_a", confidence=0.8)
    prov2 = ProvenanceRecord(source="source_b", confidence=0.8)

    # Ingest statement 1
    res1 = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="hobby"),
            object=EntityCreate(label="Guitar"),
            provenance=prov1,
        )
    )
    stmt_id_1 = res1.statement.id

    # Ingest identical statement from source 2
    res2 = kgk.ingest(
        StatementCreate(
            subject=res1.subject,
            relation=RelationCreate(label="hobby"),
            object=EntityCreate(label="Guitar"),
            provenance=prov2,
        )
    )
    stmt_id_2 = res2.statement.id

    # Must be idempotent - same statement ID reused
    assert stmt_id_1 == stmt_id_2
    assert len(kgk.store.all_statements()) == 1

    # Confidence must be reinforced: 1 - (1 - 0.8)*(1 - 0.8) = 0.96
    assert res2.statement.provenance.confidence == 0.96

    # Both provenance records tracked in lineage
    events = kgk.provenance.lineage_for(stmt_id_1)
    assert len(events) >= 2


def test_confidence_decay_over_time(kgk, provenance):
    now = datetime.now(timezone.utc)

    # Ingest dynamic fact with half-life of 3600s (1 hour)
    stmt = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="mood"),
            object=EntityCreate(label="Excited"),
            provenance=provenance,
            properties={"half_life_seconds": 3600.0},
        )
    ).statement

    # Initial confidence
    initial_conf = compute_effective_confidence(stmt, as_of=now)
    assert initial_conf == 0.9

    # Confidence after 1 half-life (1 hour later) -> 0.9 * 0.5 = 0.45
    t_1h = now + timedelta(hours=1)
    conf_1h = compute_effective_confidence(stmt, as_of=t_1h)
    assert conf_1h == 0.45

    # Confidence after 2 half-lives (2 hours later) -> 0.9 * 0.25 = 0.225
    t_2h = now + timedelta(hours=2)
    conf_2h = compute_effective_confidence(stmt, as_of=t_2h)
    assert conf_2h == 0.225
