import pytest

from models import EntityCreate, RelationCreate, StatementCreate


def test_entity_aliasing_and_resolution(kgk, provenance):
    # Ingest Mina
    mina = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="role"),
            object=EntityCreate(label="Lead"),
            provenance=provenance,
        )
    ).subject

    # Alias Mina Park -> Mina
    kgk.entities.alias(mina.id, "Mina Park")

    # Resolve by alias
    res = kgk.entities.resolve("Mina Park")
    assert res is not None
    assert res.entity.id == mina.id
    assert res.match_type == "alias"

    # Ingesting with alias "Mina Park" automatically reuses canonical Mina entity
    ingest_res = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina Park"),
            relation=RelationCreate(label="skill"),
            object=EntityCreate(label="Piano"),
            provenance=provenance,
        )
    )
    assert ingest_res.subject.id == mina.id


def test_multi_hop_entity_merge_resolution(kgk, provenance):
    # Entities A, B, C
    ea = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Node A"),
            relation=RelationCreate(label="link"),
            object=EntityCreate(label="X"),
            provenance=provenance,
        )
    ).subject

    eb = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Node B"),
            relation=RelationCreate(label="link"),
            object=EntityCreate(label="Y"),
            provenance=provenance,
        )
    ).subject

    ec = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Node C"),
            relation=RelationCreate(label="link"),
            object=EntityCreate(label="Z"),
            provenance=provenance,
        )
    ).subject

    # Merge A -> B, then B -> C
    kgk.entities.merge(eb.id, [ea.id])
    kgk.entities.merge(ec.id, [eb.id])

    # Resolving A should resolve directly to C
    res_a = kgk.entities.resolve(ea.id)
    assert res_a is not None
    assert res_a.entity.id == ec.id
    assert res_a.match_type == "canonical_merge"

    # Resolving B should resolve directly to C
    res_b = kgk.entities.resolve(eb.id)
    assert res_b is not None
    assert res_b.entity.id == ec.id


def test_entity_merge_cycle_rejection(kgk, provenance):
    ea = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Alpha"),
            relation=RelationCreate(label="link"),
            object=EntityCreate(label="1"),
            provenance=provenance,
        )
    ).subject

    eb = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Beta"),
            relation=RelationCreate(label="link"),
            object=EntityCreate(label="2"),
            provenance=provenance,
        )
    ).subject

    # Merge Beta -> Alpha
    kgk.entities.merge(ea.id, [eb.id])

    # Attempt merging Alpha -> Beta (must be rejected)
    with pytest.raises(ValueError, match="Cycle detected|already merged"):
        kgk.entities.merge(eb.id, [ea.id])
