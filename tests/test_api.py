from fastapi.testclient import TestClient

from api.app import create_app
from kernel import KnowledgeGraphKernel
from namespaces import Namespace

HEADERS = {"X-KGK-Namespace": "global", "X-KGK-Actor": "test-client"}


def test_health_endpoint():
    client = TestClient(create_app(KnowledgeGraphKernel()))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_via_api():
    client = TestClient(create_app(KnowledgeGraphKernel()))
    response = client.post(
        "/statements",
        headers=HEADERS,
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
        headers=HEADERS,
        json={
            "subject": {"label": "Alice", "type": "Person"},
            "relation_label": "knows",
            "object": {"label": "Bob", "type": "Person"},
            "provenance": {"source": "api-test"},
        },
    ).json()

    sub_id = ingest_res["subject_id"]

    # Test GET /entities
    entities_res = client.get("/entities", headers=HEADERS)
    assert entities_res.status_code == 200
    entities = entities_res.json()
    assert len(entities) >= 2
    assert any(e["id"] == sub_id for e in entities)

    # Test GET /entities/{entity_id}
    entity_res = client.get(f"/entities/{sub_id}", headers=HEADERS)
    assert entity_res.status_code == 200
    assert entity_res.json()["label"] == "Alice"


def test_statements_for_entity_direction_api():
    client = TestClient(create_app(KnowledgeGraphKernel()))
    ingest_res = client.post(
        "/statements",
        headers=HEADERS,
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
    res = client.get(
        f"/entities/{sub_id}/statements?direction=subject", headers=HEADERS
    )
    assert len(res.json()) == 1

    # Test object direction for subject
    res = client.get(
        f"/entities/{sub_id}/statements?direction=object", headers=HEADERS
    )
    assert len(res.json()) == 0

    # Test object direction for object
    res = client.get(
        f"/entities/{obj_id}/statements?direction=object", headers=HEADERS
    )
    assert len(res.json()) == 1

    # Test both directions
    res = client.get(f"/entities/{obj_id}/statements?direction=both", headers=HEADERS)
    assert len(res.json()) == 1

    # Test invalid direction
    res = client.get(
        f"/entities/{obj_id}/statements?direction=invalid", headers=HEADERS
    )
    assert res.status_code == 400


def test_merge_entities_api():
    client = TestClient(create_app(KnowledgeGraphKernel()))
    stmt1 = client.post(
        "/statements",
        headers=HEADERS,
        json={
            "subject": {"label": "Alice", "type": "Person"},
            "relation_label": "knows",
            "object": {"label": "Bob"},
            "provenance": {"source": "api-test"},
        },
    ).json()

    stmt2 = client.post(
        "/statements",
        headers=HEADERS,
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
        headers=HEADERS,
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
        headers=HEADERS,
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
        headers=HEADERS,
        json={"vector": [0.1, 0.5, -0.2], "model": "test-model"},
    )
    assert embedding_res.status_code == 200

    # Search embedding
    search_res = client.post(
        "/entities/search",
        headers=HEADERS,
        json={"vector": [0.11, 0.49, -0.21], "top_k": 2},
    )
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    assert results[0]["entity_id"] == sub_id
    assert results[0]["score"] > 0.99
    assert results[0]["entity"]["label"] == "DeepLearning"


def test_api_requires_and_enforces_namespace_capability():
    client = TestClient(create_app(KnowledgeGraphKernel()))

    assert client.get("/entities").status_code == 422

    for namespace in ("project:ape", "project:map"):
        response = client.post(
            "/namespaces",
            json={"id": namespace, "parent_id": "global"},
        )
        assert response.status_code == 200

    ape_headers = {"X-KGK-Namespace": "project:ape"}
    map_headers = {"X-KGK-Namespace": "project:map"}

    ape_statement = client.post(
        "/statements",
        headers=ape_headers,
        json={
            "subject": {"label": "Ape Agent"},
            "relation_label": "owns",
            "object": {"label": "Character Meaning"},
            "provenance": {"source": "api-test"},
        },
    )
    assert ape_statement.status_code == 200
    ape_statement_id = ape_statement.json()["statement_id"]

    assert client.get(f"/statements/{ape_statement_id}", headers=ape_headers).status_code == 200
    assert client.get(f"/statements/{ape_statement_id}", headers=map_headers).status_code == 404

    mismatch = client.post(
        "/statements",
        headers=ape_headers,
        json={
            "subject": {"label": "Wrong"},
            "relation_label": "crosses",
            "object": {"label": "Boundary"},
            "provenance": {"source": "api-test"},
            "namespace": "project:map",
        },
    )
    assert mismatch.status_code == 403


def test_api_host_authorizer_binds_actor_to_namespace():
    kernel = KnowledgeGraphKernel()
    kernel.register_namespace(Namespace(id="project:ape", parent_id="global"))
    kernel.register_namespace(Namespace(id="project:map", parent_id="global"))

    def authorize(actor: str, namespace: str, operation: str) -> bool:
        if operation == "register":
            return actor == "workspace-admin"
        return actor == "ape-runtime" and namespace == "project:ape"

    client = TestClient(create_app(kernel, authorize_namespace=authorize))

    allowed = client.get(
        "/entities",
        headers={"X-KGK-Namespace": "project:ape", "X-KGK-Actor": "ape-runtime"},
    )
    assert allowed.status_code == 200

    denied = client.get(
        "/entities",
        headers={"X-KGK-Namespace": "project:map", "X-KGK-Actor": "ape-runtime"},
    )
    assert denied.status_code == 403

    denied_registration = client.post(
        "/namespaces",
        headers={"X-KGK-Actor": "ape-runtime"},
        json={"id": "project:unauthorized", "parent_id": "global"},
    )
    assert denied_registration.status_code == 403
