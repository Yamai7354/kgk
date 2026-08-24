from epistemic.models import EpistemicStatus, Perspective
from models import EntityCreate, RelationCreate, StatementCreate
from provenance.models import ProvenanceRecord


def test_authority_resolution_higher_authority_wins(kgk):
    # High authority source (Canon Card, authority=100)
    canon_prov = ProvenanceRecord(
        source="canon_card",
        source_id="card_v1",
        confidence=0.9,
        authority=100.0,
    )
    # Low authority source (Rumor Chat, authority=10)
    chat_prov = ProvenanceRecord(
        source="discord_chat",
        source_id="msg_99",
        confidence=0.95,
        authority=10.0,
    )

    s_canon = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="age"),
            object=EntityCreate(label="24"),
            provenance=canon_prov,
            epistemic_status=EpistemicStatus.FACT,
        )
    ).statement

    s_chat = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="age"),
            object=EntityCreate(label="28"),
            provenance=chat_prov,
            epistemic_status=EpistemicStatus.RUMOR,
        )
    ).statement

    winner = kgk.epistemic.resolve_winner([s_canon, s_chat])
    assert winner is not None
    assert winner.id == s_canon.id


def test_perspective_filtering(kgk):
    prov = ProvenanceRecord(source="test", confidence=0.8)

    # Ingest FACT, HYPOTHESIS, and RUMOR
    s_fact = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="role"),
            object=EntityCreate(label="Captain"),
            provenance=prov,
            epistemic_status=EpistemicStatus.FACT,
        )
    ).statement

    s_rumor = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="secret"),
            object=EntityCreate(label="Spy"),
            provenance=prov,
            epistemic_status=EpistemicStatus.RUMOR,
        )
    ).statement

    # Strict perspective only accepts FACT
    strict_perspective = Perspective(
        name="strict_canon",
        accepted_statuses=[EpistemicStatus.FACT],
    )

    view = kgk.view_perspective(strict_perspective, subject_id=s_fact.subject_id)
    retrieved_ids = {r.statement.id for r in view}
    assert s_fact.id in retrieved_ids
    assert s_rumor.id not in retrieved_ids
