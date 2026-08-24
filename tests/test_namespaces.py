from models import EntityCreate, RelationCreate, StatementCreate
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
