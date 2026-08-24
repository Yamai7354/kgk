from fastapi.testclient import TestClient

from api.app import create_app
from kernel import KnowledgeGraphKernel


def test_health_endpoint():
    client = TestClient(create_app(KnowledgeGraphKernel()))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_via_api():
    client = TestClient(create_app(KnowledgeGraphKernel()))
    response = client.post(
        "/statements",
        json={
            "subject": {"label": "Alice", "type": "Person"},
            "relation_label": "knows",
            "object": {"label": "Bob", "type": "Person"},
            "provenance": {"source": "api-test", "confidence": 0.8},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "statement_id" in body


def test_get_entities_and_entity_by_id_api():
    client = TestClient(create_app(KnowledgeGraphKernel()))
    # Ingest a statement first
    ingest_res = client.post(
        "/statements",
        json={
            "subject": {"label": "Alice", "type": "Person"},
            "relation_label": "knows",
            "object": {"label": "Bob", "type": "Person"},
            "provenance": {"source": "api-test"},
        },
    ).json()

    sub_id = ingest_res["subject_id"]

    # Test GET /entities
    entities_res = client.get("/entities")
    assert entities_res.status_code == 200
    entities = entities_res.json()
    assert len(entities) >= 2
    assert any(e["id"] == sub_id for e in entities)

    # Test GET /entities/{entity_id}
    entity_res = client.get(f"/entities/{sub_id}")
    assert entity_res.status_code == 200
    assert entity_res.json()["label"] == "Alice"


def test_statements_for_entity_direction_api():
    client = TestClient(create_app(KnowledgeGraphKernel()))
    ingest_res = client.post(
        "/statements",
        json={
            "subject": {"label": "Alice", "type": "Person"},
            "relation_label": "knows",
            "object": {"label": "Bob", "type": "Person"},
            "provenance": {"source": "api-test"},
        },
    ).json()

    sub_id = ingest_res["subject_id"]
    obj_id = ingest_res["object_id"]

    # Test subject direction
    res = client.get(f"/entities/{sub_id}/statements?direction=subject")
    assert len(res.json()) == 1

    # Test object direction for subject
    res = client.get(f"/entities/{sub_id}/statements?direction=object")
    assert len(res.json()) == 0

    # Test object direction for object
    res = client.get(f"/entities/{obj_id}/statements?direction=object")
    assert len(res.json()) == 1

    # Test both directions
    res = client.get(f"/entities/{obj_id}/statements?direction=both")
    assert len(res.json()) == 1

    # Test invalid direction
    res = client.get(f"/entities/{obj_id}/statements?direction=invalid")
    assert res.status_code == 400


def test_merge_entities_api():
    client = TestClient(create_app(KnowledgeGraphKernel()))
    stmt1 = client.post(
        "/statements",
        json={
            "subject": {"label": "Alice", "type": "Person"},
            "relation_label": "knows",
            "object": {"label": "Bob"},
            "provenance": {"source": "api-test"},
        },
    ).json()

    stmt2 = client.post(
        "/statements",
        json={
            "subject": {"label": "alice", "type": "Person"},
            "relation_label": "works_at",
            "object": {"label": "Acme"},
            "provenance": {"source": "api-test"},
        },
    ).json()

    canonical_id = stmt1["subject_id"]
    dup_id = stmt2["subject_id"]

    # Merge via API
    merge_res = client.post(
        f"/entities/{canonical_id}/merge",
        json={"duplicate_ids": [dup_id]},
    )
    assert merge_res.status_code == 200
    body = merge_res.json()
    assert body["canonical_id"] == canonical_id
    assert dup_id in body["merged_ids"]
    assert body["rewired_statements_count"] == 1


def test_entity_embeddings_and_search_api():
    client = TestClient(create_app(KnowledgeGraphKernel()))
    stmt = client.post(
        "/statements",
        json={
            "subject": {"label": "DeepLearning", "type": "Field"},
            "relation_label": "part_of",
            "object": {"label": "AI"},
            "provenance": {"source": "api-test"},
        },
    ).json()

    sub_id = stmt["subject_id"]

    # Upsert embedding
    embedding_res = client.post(
        f"/entities/{sub_id}/embeddings",
        json={"vector": [0.1, 0.5, -0.2], "model": "test-model"},
    )
    assert embedding_res.status_code == 200

    # Search embedding
    search_res = client.post(
        "/entities/search",
        json={"vector": [0.11, 0.49, -0.21], "top_k": 2},
    )
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    assert results[0]["entity_id"] == sub_id
    assert results[0]["score"] > 0.99
    assert results[0]["entity"]["label"] == "DeepLearning"
