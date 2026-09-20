import pytest

from kernel import KnowledgeGraphKernel
from models import EntityCreate, RelationCreate, StatementCreate
from namespaces import Namespace, NamespaceAccessError
from provenance import ProvenanceRecord


def _statement(subject: str, relation: str, object_: str, namespace: str) -> StatementCreate:
    return StatementCreate(
        subject=EntityCreate(label=subject, namespace=namespace),
        relation=RelationCreate(label=relation, namespace=namespace),
        object=EntityCreate(label=object_, namespace=namespace),
        provenance=ProvenanceRecord(source="persistent-namespace-test"),
        namespace=namespace,
    )


def test_namespaces_and_knowledge_survive_restart_with_isolation(tmp_path):
    db_path = str(tmp_path / "shared-kgk.db")

    first = KnowledgeGraphKernel.persistent(db_path)
    first.register_namespace(Namespace(id="project:ape", parent_id="global"))
    first.register_namespace(Namespace(id="project:map", parent_id="global"))

    global_result = first.scope("global").ingest(
        _statement("Infrastructure", "uses", "KGK", "global")
    )
    ape_result = first.scope("project:ape").ingest(
        _statement("APE", "owns", "Character Meaning", "project:ape")
    )
    map_result = first.scope("project:map").ingest(
        _statement("MAP", "owns", "Observable Reality", "project:map")
    )
    first.close()

    reopened = KnowledgeGraphKernel.persistent(db_path)
    try:
        assert reopened.namespaces.get("project:ape") is not None
        assert reopened.namespaces.get("project:map") is not None

        ape_scope = reopened.scope("project:ape")
        map_scope = reopened.scope("project:map")

        assert ape_scope.get_statement(ape_result.statement.id) is not None
        assert ape_scope.get_statement(global_result.statement.id) is not None
        assert map_scope.get_statement(map_result.statement.id) is not None
        assert map_scope.get_statement(global_result.statement.id) is not None

        with pytest.raises(NamespaceAccessError):
            ape_scope.get_statement(map_result.statement.id)
        with pytest.raises(NamespaceAccessError):
            map_scope.get_statement(ape_result.statement.id)
        with pytest.raises(NamespaceAccessError):
            ape_scope.retract(map_result.statement.id, "not owned")

        assert [result.entity.label for result in ape_scope.search_hybrid(query_text="APE")]
        assert map_scope.search_hybrid(query_text="APE") == []
    finally:
        reopened.close()
