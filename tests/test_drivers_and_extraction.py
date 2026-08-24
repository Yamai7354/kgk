import json

from drivers.extractors import (
    KeyValueExtractor,
    PatternExtractor,
    StructuredJsonExtractor,
)
from drivers.models import Document


def test_key_value_extractor(kgk):
    doc_text = """
    # Character Profile
    role: Lead Singer
    hometown: Neo-Tokyo
    affiliation: Cyber Band
    """
    doc = Document(
        text=doc_text,
        source_uri="file:///characters/mina.txt",
        metadata={"subject": "Mina Park"},
    )
    extractor = KeyValueExtractor()
    results = kgk.ingest_document(doc, extractor)

    assert len(results) == 3
    # Check subjects and relations
    rel_labels = {r.relation.label for r in results}
    assert rel_labels == {"role", "hometown", "affiliation"}

    # Check span provenance
    for r in results:
        assert r.statement.provenance.source_uri == "file:///characters/mina.txt"
        assert "span" in r.statement.provenance.metadata


def test_structured_json_extractor(kgk):
    card = {
        "name": "Jade Rivera",
        "type": "Person",
        "skills": ["Hacking", "Robotics"],
        "status": "Active",
    }
    doc = Document(
        text=json.dumps(card),
        source_type="character_card",
        metadata={"author": "System"},
    )
    extractor = StructuredJsonExtractor()
    results = kgk.ingest_document(doc, extractor)

    assert len(results) == 3  # 2 skills + 1 status
    skill_stmts = [r for r in results if r.relation.label == "skills"]
    assert len(skill_stmts) == 2
    assert {s.object.label for s in skill_stmts} == {"Hacking", "Robotics"}


def test_pattern_extractor(kgk):
    text = "Mina Park lives in Neo Tokyo. Jade Rivera works at Tech Corp."
    doc = Document(text=text, source_type="news_article")
    extractor = PatternExtractor()
    results = kgk.ingest_document(doc, extractor)

    assert len(results) == 2
    res1 = results[0]
    assert res1.subject.label == "Mina Park"
    assert res1.relation.label == "lives_in"
    assert res1.object.label == "Neo Tokyo"
