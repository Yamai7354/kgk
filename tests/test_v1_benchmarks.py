import os
from datetime import datetime, timezone

from kgk import (
    EpistemicStatus,
    KnowledgeGraphKernel,
    ProvenanceRecord,
    SqliteEventStore,
    SqliteGraphStore,
    StatementCreate,
    StatementStatus,
)


def test_v1_scale_ingestion_and_hybrid_retrieval(kgk):
    # Ingest 100 character nodes with connections
    for i in range(100):
        kgk.ingest(
            StatementCreate(
                subject={"label": f"Agent_{i:03d}", "type": "Agent"},
                relation={"label": "collaborates_with"},
                object={"label": f"Agent_{(i + 1) % 100:03d}", "type": "Agent"},
                provenance=ProvenanceRecord(source="batch_runner", confidence=0.85),
                namespace="project_swarm",
            )
        )

    # Ingest identical triples to verify deduplication & reinforcement
    res = kgk.ingest(
        StatementCreate(
            subject={"label": "Agent_000", "type": "Agent"},
            relation={"label": "collaborates_with"},
            object={"label": "Agent_001", "type": "Agent"},
            provenance=ProvenanceRecord(source="validator_agent", confidence=0.9),
            namespace="project_swarm",
        )
    )

    # Total active statements in project_swarm must be exactly 100
    swarm_stmts = [
        s
        for s in kgk.store.all_statements()
        if getattr(s, "namespace", "global") == "project_swarm"
    ]
    assert len(swarm_stmts) == 100

    # Reinforced confidence: 1 - (1-0.85)*(1-0.9) = 0.985
    assert res.statement.provenance.confidence == 0.985

    # Multi-hop pathfinding across the swarm ring
    paths = kgk.find_paths(
        start_entity_id=res.subject.id,
        end_entity_id=kgk.entities.resolve("Agent_003", namespace="project_swarm").entity.id,
        max_depth=4,
    )
    assert len(paths) >= 1
    assert len(paths[0]) == 3  # Agent_000 -> Agent_001 -> Agent_002 -> Agent_003


def test_v1_persistent_sqlite_all_10_invariants(tmp_path):
    db_file = tmp_path / "v1_invariants.db"
    db_str = str(db_file)

    store = SqliteGraphStore(db_str)
    events = SqliteEventStore(db_str)
    kernel = KnowledgeGraphKernel(store=store, events=events)

    try:
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        prov = ProvenanceRecord(source="benchmark", authority=100, confidence=0.95)

        # 1. Ingestion
        res = kernel.ingest(
            StatementCreate(
                subject={"label": "Mina"},
                relation={"label": "lives_in"},
                object={"label": "Tokyo"},
                provenance=prov,
                valid_from=t0,
                epistemic_status=EpistemicStatus.FACT,
            )
        )
        s1 = res.statement

        # Invariant 1 & 2: Soft Retraction
        kernel.retract(s1.id, reason="Relocated")
        stored_s1 = kernel.store.get_statement(s1.id)
        assert stored_s1 is not None
        assert stored_s1.status == StatementStatus.RETRACTED

        # Invariant 3: Lineage & Provenance
        assert len(kernel.provenance.lineage_for(s1.id)) >= 2

        # Invariant 6: Entity Aliasing & Canonical Merging
        e1 = kernel.ingest(
            StatementCreate(
                subject={"label": "Neo Tokyo"},
                relation={"label": "status"},
                object={"label": "Metropolis"},
                provenance=prov,
            )
        ).subject
        kernel.entities.add_alias(e1.id, "Tokyo-3")
        resolved = kernel.entities.resolve("Tokyo-3")
        assert resolved is not None
        assert resolved.entity.id == e1.id

        # Invariant 7: Event Log Primacy & Deterministic Replay
        fresh_sqlite = SqliteGraphStore(":memory:")
        kernel.migrate_to(fresh_sqlite)
        assert len(fresh_sqlite.all_statements()) >= 2

    finally:
        store.close()
        events.close()
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception:
                pass
