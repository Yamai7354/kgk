from embeddings.store import EmbeddingRecord
from models import EntityCreate, RelationCreate, StatementCreate


def test_hybrid_lexical_and_vector_search(kgk, provenance):
    # Ingest entities
    e_mina = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(
                label="Mina Park", properties={"bio": "Lead protagonist and singer"}
            ),
            relation=RelationCreate(label="role"),
            object=EntityCreate(label="Captain"),
            provenance=provenance,
        )
    ).subject

    e_jade = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(
                label="Jade Rivera", properties={"bio": "Chief engineer and hacker"}
            ),
            relation=RelationCreate(label="role"),
            object=EntityCreate(label="Engineer"),
            provenance=provenance,
        )
    ).subject

    # Add embeddings: Mina=[1.0, 0.0], Jade=[0.0, 1.0]
    kgk.embeddings.upsert(EmbeddingRecord(entity_id=e_mina.id, vector=[1.0, 0.0]))
    kgk.embeddings.upsert(EmbeddingRecord(entity_id=e_jade.id, vector=[0.0, 1.0]))

    # Pure lexical search for "Jade"
    results_lexical = kgk.search_hybrid(query_text="Jade", top_k=2)
    assert len(results_lexical) >= 1
    assert results_lexical[0].entity.id == e_jade.id

    # Pure vector search for [1.0, 0.0] (Mina)
    results_vector = kgk.search_hybrid(query_vector=[1.0, 0.0], top_k=2)
    assert len(results_vector) >= 1
    assert results_vector[0].entity.id == e_mina.id

    # Fused hybrid search
    results_fused = kgk.search_hybrid(query_text="Mina", query_vector=[1.0, 0.0], top_k=2)
    assert results_fused[0].entity.id == e_mina.id
    assert results_fused[0].lexical_rank is not None
    assert results_fused[0].vector_rank is not None
