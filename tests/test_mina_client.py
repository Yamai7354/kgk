from clients.mina import MinaCanonClient
from models.statement import StatementStatus


def test_mina_canon_authority_overrides_rumor():
    client = MinaCanonClient()

    # 1. Record a rumor (authority=20, HYPOTHESIS)
    client.record_rumor("Mina", "birthplace", "Mars Colony")

    # Verify rumor is active initially
    profile_initial = client.get_character_profile("Mina")
    assert "birthplace" in profile_initial["rumors"]
    assert profile_initial["rumors"]["birthplace"] == ["Mars Colony"]

    # 2. Creator asserts immutable canon truth (authority=100, FACT)
    client.assert_canon("Mina", "birthplace", "Neo-Tokyo")

    # Conflict on functional relation 'birthplace' must automatically resolve in favor of canon
    profile_resolved = client.get_character_profile("Mina")
    assert profile_resolved["canon_facts"]["birthplace"] == ["Neo-Tokyo"]

    # Mars Colony rumor was retracted/superseded by the canon assertion
    all_stmts = client.kernel.store.all_statements()
    mars_stmts = [
        s
        for s in all_stmts
        if s.relation_id == client.kernel.store.all_relations()[0].id
        and client.kernel.store.get_entity(s.object_id).label == "Mars Colony"
    ]
    assert len(mars_stmts) == 1
    assert mars_stmts[0].status == StatementStatus.RETRACTED


def test_mina_prompt_context_generation():
    client = MinaCanonClient()
    client.assert_canon("Mina Park", "role", "Captain")
    client.assert_canon("Mina Park", "trait", "Fearless")
    client.record_observation("Mina Park", "mood", "Optimistic")
    client.record_rumor("Mina Park", "secret", "Rogue AI Sympathizer")

    # Strict canon context (FACT + BELIEF, excluding HYPOTHESIS)
    prompt_context = client.build_llm_prompt_context(
        "Mina Park", max_chars=1000, include_rumors=False
    )
    assert "Character Canon: Mina Park" in prompt_context
    assert "Captain" in prompt_context
    assert "Fearless" in prompt_context
    assert "Optimistic" in prompt_context
    assert "Rogue AI Sympathizer" not in prompt_context

    # Context with rumors enabled
    prompt_context_with_rumors = client.build_llm_prompt_context(
        "Mina Park", max_chars=1000, include_rumors=True
    )
    assert "Rogue AI Sympathizer" in prompt_context_with_rumors
