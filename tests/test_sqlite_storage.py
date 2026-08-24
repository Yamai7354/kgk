import os

from events.models import EventType, KnowledgeEvent
from models import (
    Entity,
    EntityCreate,
    Relation,
    RelationCreate,
    Statement,
    StatementCreate,
    StatementStatus,
)
from provenance.models import ProvenanceRecord
from storage.sqlite.event_store import SqliteEventStore
from storage.sqlite.graph_store import SqliteGraphStore


def test_sqlite_graph_store_crud():
    store = SqliteGraphStore(":memory:")
    try:
        e1 = Entity(label="Mina", type="Person")
        e2 = Entity(label="Tokyo", type="Location")
        r1 = Relation(label="lives_in", type="binary")

        store.add_entity(e1)
        store.add_entity(e2)
        store.add_relation(r1)

        stmt = Statement(
            subject_id=e1.id,
            relation_id=r1.id,
            object_id=e2.id,
            provenance=ProvenanceRecord(source="test"),
        )
        store.add_statement(stmt)

        # Query back
        assert store.get_entity(e1.id) is not None
        assert store.get_relation(r1.id) is not None
        assert store.get_statement(stmt.id) is not None

        # Query by subject
        stmts = store.statements_for_subject(e1.id)
        assert len(stmts) == 1
        assert stmts[0].id == stmt.id

        # Update statement
        updated = stmt.model_copy(update={"status": StatementStatus.RETRACTED})
        store.update_statement(updated)
        assert store.get_statement(stmt.id).status == StatementStatus.RETRACTED
    finally:
        store.close()


def test_sqlite_event_store():
    event_store = SqliteEventStore(":memory:")
    try:
        ev = KnowledgeEvent(
            event_type=EventType.ASSERT,
            target_id="stmt-123",
            namespace="global",
            payload={"test": "data"},
        )
        event_store.append(ev)

        fetched = event_store.get(ev.event_id)
        assert fetched is not None
        assert fetched.event_id == ev.event_id
        assert fetched.payload == {"test": "data"}

        by_type = event_store.events_by_type(EventType.ASSERT)
        assert len(by_type) == 1
    finally:
        event_store.close()


def test_kernel_migration_to_sqlite(kgk, provenance, tmp_path):
    # Ingest data into default in-memory KGK
    kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="hobby"),
            object=EntityCreate(label="Guitar"),
            provenance=provenance,
        )
    )

    db_file = tmp_path / "migrated_kgk.db"
    sqlite_store = SqliteGraphStore(str(db_file))

    try:
        # Migrate in-memory kernel to sqlite
        kgk.migrate_to(sqlite_store)

        # Assert sqlite store has entities and statements
        assert len(sqlite_store.all_entities()) >= 2
        assert len(sqlite_store.all_statements()) == 1

        # Query through kernel facade
        results = kgk.query_scoped(subject_id=sqlite_store.all_entities()[0].id)
        assert len(results) >= 1
    finally:
        sqlite_store.close()
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception:
                pass
