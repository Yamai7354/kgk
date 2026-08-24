from models import EntityCreate, RelationCreate, StatementCreate
from provenance import ProvenanceRecord


def test_ingest_and_retrieve(kgk, provenance):
    result = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Alice", type="Person"),
            relation=RelationCreate(label="knows"),
            object=EntityCreate(label="Bob", type="Person"),
            provenance=provenance,
        )
    )

    matches = kgk.retrieve.by_subject(result.subject.id)
    assert len(matches) == 1
    assert matches[0].statement.id == result.statement.id
    assert matches[0].object is not None
    assert matches[0].object.label == "Bob"


def test_retract_statement(kgk, provenance):
    result = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Alice"),
            relation=RelationCreate(label="knows"),
            object=EntityCreate(label="Bob"),
            provenance=provenance,
        )
    )

    kgk.retract(result.statement.id, "incorrect extraction")
    assert kgk.retrieve.by_subject(result.subject.id) == []

    lineage = kgk.provenance.lineage_for(result.statement.id)
    assert any(e.event_type == "retracted" for e in lineage)


def test_merge_entities_rewires_statements(kgk, provenance):
    alice_a = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Alice"),
            relation=RelationCreate(label="knows"),
            object=EntityCreate(label="Bob"),
            provenance=provenance,
        )
    )
    alice_dup = EntityCreate(label="alice", type="Person")
    dup_result = kgk.ingest(
        StatementCreate(
            subject=alice_dup,
            relation=RelationCreate(label="works_at"),
            object=EntityCreate(label="Acme"),
            provenance=provenance,
        )
    )

    merge = kgk.merge_entities(alice_a.subject.id, [dup_result.subject.id])
    assert dup_result.subject.id in merge.merged_ids

    canonical_statements = kgk.retrieve.by_subject(alice_a.subject.id)
    labels = {r.relation.label for r in canonical_statements if r.relation}
    assert "knows" in labels
    assert "works_at" in labels


def test_neighborhood_traversal(kgk, provenance):
    a = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="A"),
            relation=RelationCreate(label="link"),
            object=EntityCreate(label="B"),
            provenance=provenance,
        )
    )
    kgk.ingest(
        StatementCreate(
            subject=a.object,
            relation=RelationCreate(label="link"),
            object=EntityCreate(label="C"),
            provenance=provenance,
        )
    )

    subgraph = kgk.retrieve.neighborhood(a.subject.id, depth=2)
    assert len(subgraph.statements) >= 2


def test_merge_entities_rewires_self_loops(kgk, provenance):
    # Create duplicate entity
    dup = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Dup"),
            relation=RelationCreate(label="knows"),
            object=EntityCreate(label="Other"),
            provenance=provenance,
        )
    ).subject

    # Create a self-loop statement (e.g. Dup interacts with itself)
    self_loop = kgk.ingest(
        StatementCreate(
            subject=dup,
            relation=RelationCreate(label="self_talks"),
            object=dup,
            provenance=provenance,
        )
    )

    canonical = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Canonical"),
            relation=RelationCreate(label="knows"),
            object=EntityCreate(label="Other2"),
            provenance=provenance,
        )
    ).subject

    # Merge duplicate into canonical
    kgk.merge_entities(canonical.id, [dup.id])

    # Retrieve rewired statement
    retrieved = kgk.retrieve.get_statement(self_loop.statement.id)
    assert retrieved is not None
    assert retrieved.statement.subject_id == canonical.id
    assert retrieved.statement.object_id == canonical.id


def test_supersede_records_provenance(kgk, provenance):
    original = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Alice"),
            relation=RelationCreate(label="location"),
            object=EntityCreate(label="Paris"),
            provenance=provenance,
        )
    ).statement

    new_stmt = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Alice"),
            relation=RelationCreate(label="location"),
            object=EntityCreate(label="London"),
            provenance=provenance,
        )
    ).statement

    kgk.retraction.supersede(original.id, new_stmt, reason="moved")

    # Verify statement status
    old_stmt = kgk.retrieve._store.get_statement(original.id)
    assert old_stmt.status.value == "superseded"
    assert old_stmt.superseded_by == new_stmt.id

    # Verify lineage has supersede event
    lineage = kgk.provenance.lineage_for(original.id)
    assert any(
        e.event_type == "superseded" and e.record.metadata.get("reason") == "moved" for e in lineage
    )


def test_embeddings_store_operations(kgk):
    from embeddings.store import EmbeddingRecord

    # Create entity
    entity = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="DeepMind"),
            relation=RelationCreate(label="is_a"),
            object=EntityCreate(label="Company"),
            provenance=ProvenanceRecord(source="test"),
        )
    ).subject

    # Add embedding
    record = EmbeddingRecord(entity_id=entity.id, vector=[0.1, 0.2, 0.9])
    kgk.embeddings.upsert(record)

    # Fetch embedding
    fetched = kgk.embeddings.get(entity.id)
    assert fetched is not None
    assert fetched.vector == [0.1, 0.2, 0.9]

    # Search similarity
    search_results = kgk.embeddings.search([0.1, 0.2, 0.85], top_k=1)
    assert len(search_results) == 1
    assert search_results[0].entity_id == entity.id
    assert search_results[0].score > 0.99
