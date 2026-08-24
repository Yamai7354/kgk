from models import EntityCreate, RelationCreate, StatementCreate


def test_pathfinding_and_shortest_path(kgk, provenance):
    # A -> B -> C -> D
    ea = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Alpha"),
            relation=RelationCreate(label="connects_to"),
            object=EntityCreate(label="Beta"),
            provenance=provenance,
        )
    ).subject

    eb = kgk.store.get_entity(kgk.store.statements_for_subject(ea.id)[0].object_id)

    ec = kgk.ingest(
        StatementCreate(
            subject=eb,
            relation=RelationCreate(label="connects_to"),
            object=EntityCreate(label="Gamma"),
            provenance=provenance,
        )
    ).object

    ed = kgk.ingest(
        StatementCreate(
            subject=ec,
            relation=RelationCreate(label="connects_to"),
            object=EntityCreate(label="Delta"),
            provenance=provenance,
        )
    ).object

    # Direct alternate path: A -> D (1 hop)
    kgk.ingest(
        StatementCreate(
            subject=ea,
            relation=RelationCreate(label="shortcut_to"),
            object=ed,
            provenance=provenance,
        )
    )

    # Find all paths A -> D
    all_paths = kgk.find_paths(ea.id, ed.id, max_depth=4)
    assert len(all_paths) == 2

    # Find shortest path A -> D (should be the 1-hop shortcut)
    shortest = kgk.shortest_path(ea.id, ed.id, max_depth=4)
    assert shortest is not None
    assert len(shortest) == 1
    assert shortest[0].relation.label == "shortcut_to"


def test_subgraph_formatting_markdown_mermaid_jsonld(kgk, provenance):
    res = kgk.ingest(
        StatementCreate(
            subject=EntityCreate(label="Mina"),
            relation=RelationCreate(label="lives_in"),
            object=EntityCreate(label="Tokyo"),
            provenance=provenance,
        )
    )

    # Markdown format
    md = kgk.format_neighborhood(res.subject.id, format_type="markdown")
    assert "- [Mina] --(lives_in)--> [Tokyo]" in md

    # Mermaid format
    mermaid = kgk.format_neighborhood(res.subject.id, format_type="mermaid")
    assert "graph LR" in mermaid
    assert "Mina" in mermaid
    assert "Tokyo" in mermaid

    # JSON-LD format
    json_ld = kgk.format_neighborhood(res.subject.id, format_type="json_ld")
    assert isinstance(json_ld, list)
    assert len(json_ld) == 1
    assert json_ld[0]["subject"]["label"] == "Mina"
    assert json_ld[0]["object"]["label"] == "Tokyo"
