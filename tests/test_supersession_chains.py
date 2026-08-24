import pytest

from models import EntityCreate, RelationCreate, StatementCreate


def test_multi_hop_supersession_chain_resolution(kgk, provenance):
    # S1: Mina lives in Tokyo
    s1 = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="lives_in"),
            object=EntityCreate(label="Tokyo"),
            provenance=provenance,
        )
    ).statement

    # S2: Mina lives in Omaha
    s2 = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="lives_in"),
            object=EntityCreate(label="Omaha"),
            provenance=provenance,
        )
    ).statement

    # S3: Mina lives in Kyoto
    s3 = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="lives_in"),
            object=EntityCreate(label="Kyoto"),
            provenance=provenance,
        )
    ).statement

    # S1 -> S2 -> S3
    kgk.supersede(s1.id, s2, reason="First move")
    kgk.supersede(s2.id, s3, reason="Second move")

    # Resolve chain starting at S1
    chain = kgk.resolve_supersession(s1.id)
    assert chain == [s1.id, s2.id, s3.id]

    # Resolve chain starting at S2
    assert kgk.resolve_supersession(s2.id) == [s2.id, s3.id]

    # Resolve chain starting at S3 (terminal active statement)
    assert kgk.resolve_supersession(s3.id) == [s3.id]


def test_supersession_cycle_detection(kgk, provenance):
    s1 = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="A"),
            relation=RelationCreate(label="rel"),
            object=EntityCreate(label="B"),
            provenance=provenance,
        )
    ).statement

    s2 = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="A"),
            relation=RelationCreate(label="rel"),
            object=EntityCreate(label="C"),
            provenance=provenance,
        )
    ).statement

    kgk.supersede(s1.id, s2)
    # Manually link S2 -> S1 to simulate accidental cycle
    stmt2 = kgk.store.get_statement(s2.id)
    kgk.store.update_statement(stmt2.model_copy(update={"superseded_by": s1.id}))

    with pytest.raises(ValueError, match="Cycle detected in supersession chain"):
        kgk.resolve_supersession(s1.id)
