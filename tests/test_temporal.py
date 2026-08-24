import time
from datetime import datetime, timezone

from models import EntityCreate, RelationCreate, StatementCreate


def test_as_of_real_world_validity_window(kgk, provenance):
    t_2020 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    t_2022 = datetime(2022, 1, 1, tzinfo=timezone.utc)

    # Mina lived in Tokyo from 2020 to 2022
    s_tokyo = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="lives_in"),
            object=EntityCreate(label="Tokyo"),
            valid_from=t_2020,
            valid_until=t_2022,
            provenance=provenance,
        )
    )

    # Mina lived in Omaha from 2022 onwards
    kgk.ingest(
        StatementCreate(
            subject=s_tokyo.subject,
            relation=RelationCreate(label="lives_in"),
            object=EntityCreate(label="Omaha"),
            valid_from=t_2022,
            provenance=provenance,
        )
    )

    # Query as of 2021 (should find Tokyo, not Omaha)
    res_2021 = kgk.as_of(datetime(2021, 6, 1, tzinfo=timezone.utc), subject_id=s_tokyo.subject.id)
    assert len(res_2021) == 1
    assert res_2021[0].object.label == "Tokyo"

    # Query as of 2023 (should find Omaha, not Tokyo)
    res_2023 = kgk.as_of(datetime(2023, 6, 1, tzinfo=timezone.utc), subject_id=s_tokyo.subject.id)
    assert len(res_2023) == 1
    assert res_2023[0].object.label == "Omaha"


def test_as_known_at_point_in_time_system_state(kgk, provenance):
    # Ingest S1
    s1 = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Alice"),
            relation=RelationCreate(label="status"),
            object=EntityCreate(label="Employed"),
            provenance=provenance,
        )
    )
    time.sleep(0.01)
    t_after_s1 = datetime.now(timezone.utc)
    time.sleep(0.01)

    # Retract S1
    kgk.retract(s1.statement.id, reason="Terminated")
    time.sleep(0.01)
    t_after_retract = datetime.now(timezone.utc)

    # Reconstruct state at t_after_s1 (before retraction)
    store_past = kgk.as_known_at(t_after_s1)
    past_stmt = store_past.get_statement(s1.statement.id)
    assert past_stmt is not None
    assert past_stmt.is_active

    # Reconstruct state at t_after_retract (after retraction)
    store_present = kgk.as_known_at(t_after_retract)
    present_stmt = store_present.get_statement(s1.statement.id)
    assert present_stmt is not None
    assert not present_stmt.is_active
