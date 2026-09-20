import pytest

from models import Entity, EntityCreate, RelationCreate, StatementCreate
from namespaces import NamespaceAccessError
from namespaces.models import Namespace


def test_namespace_hierarchy_and_read_scope(kgk):
    # Register hierarchy: global -> user:randy -> project:mina
    kgk.namespaces.register(Namespace(id="user:randy", parent_id="global"))
    kgk.namespaces.register(Namespace(id="project:mina", parent_id="user:randy"))

    # Resolve read scope for project:mina
    scope = kgk.namespaces.resolve_read_scope("project:mina")
    assert "project:mina" in scope
    assert "user:randy" in scope
    assert "global" in scope


def test_scoped_queries_isolate_namespaces(kgk, provenance):
    kgk.namespaces.register(Namespace(id="project:mina", parent_id="global"))
    kgk.namespaces.register(Namespace(id="project:jade", parent_id="global"))

    # Ingest in project:mina
    mina_stmt = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina", namespace="project:mina"),
            relation=RelationCreate(label="hobby"),
            object=EntityCreate(label="Singing", namespace="project:mina"),
            provenance=provenance,
            namespace="project:mina",
        )
    )

    # Ingest in project:jade
    kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Jade", namespace="project:jade"),
            relation=RelationCreate(label="hobby"),
            object=EntityCreate(label="Gaming", namespace="project:jade"),
            provenance=provenance,
            namespace="project:jade",
        )
    )

    # Query scoped to project:mina
    mina_results = kgk.query_scoped(subject_id=mina_stmt.subject.id, namespaces=["project:mina"])
    assert len(mina_results) == 1
    assert mina_results[0].statement.id == mina_stmt.statement.id

    # Query Mina entity with scope project:jade (should find nothing)
    jade_results = kgk.query_scoped(subject_id=mina_stmt.subject.id, namespaces=["project:jade"])
    assert len(jade_results) == 0


def test_unregistered_namespace_is_rejected(kgk, provenance):
    with pytest.raises(KeyError, match="Namespace not registered"):
        kgk.ingest(
            StatementCreate(
                subject=EntityCreate(label="Unknown", namespace="project:unknown"),
                relation=RelationCreate(label="owns", namespace="project:unknown"),
                object=EntityCreate(label="Knowledge", namespace="project:unknown"),
                provenance=provenance,
                namespace="project:unknown",
            )
        )


def test_existing_entity_id_cannot_be_smuggled_across_namespaces(kgk, provenance):
    kgk.register_namespace(Namespace(id="project:ape", parent_id="global"))
    kgk.register_namespace(Namespace(id="project:map", parent_id="global"))
    ape = kgk.scope("project:ape").ingest(
        StatementCreate(
            subject=EntityCreate(label="APE", namespace="project:ape"),
            relation=RelationCreate(label="owns", namespace="project:ape"),
            object=EntityCreate(label="Meaning", namespace="project:ape"),
            provenance=provenance,
            namespace="project:ape",
        )
    )

    forged = Entity(
        id=ape.subject.id,
        label=ape.subject.label,
        namespace="project:map",
    )
    with pytest.raises(PermissionError, match="across namespace boundaries"):
        kgk.scope("project:map").ingest(
            StatementCreate(
                subject=forged,
                relation=RelationCreate(label="claims", namespace="project:map"),
                object=EntityCreate(label="Reality", namespace="project:map"),
                provenance=provenance,
                namespace="project:map",
            )
        )


def test_read_only_namespace_rejects_scoped_writes(kgk, provenance):
    kgk.register_namespace(
        Namespace(id="published:reference", parent_id="global", is_read_only=True)
    )
    with pytest.raises(NamespaceAccessError, match="read-only"):
        kgk.scope("published:reference").ingest(
            StatementCreate(
                subject=EntityCreate(label="Public", namespace="published:reference"),
                relation=RelationCreate(label="is", namespace="published:reference"),
                object=EntityCreate(label="Immutable", namespace="published:reference"),
                provenance=provenance,
                namespace="published:reference",
            )
        )
