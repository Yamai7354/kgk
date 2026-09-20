import argparse
import json
import sys

from epistemic.models import EpistemicStatus
from kernel import KnowledgeGraphKernel
from models import EntityCreate, RelationCreate, StatementCreate
from namespaces import Namespace
from provenance.models import ProvenanceRecord


def get_kernel(db_path: str | None = None) -> KnowledgeGraphKernel:
    if db_path:
        return KnowledgeGraphKernel.persistent(db_path)
    return KnowledgeGraphKernel()


def handle_ingest(args: argparse.Namespace, kgk: KnowledgeGraphKernel) -> int:
    prov = ProvenanceRecord(
        source=args.source or "cli",
        confidence=args.confidence,
        authority=args.authority,
    )
    status = EpistemicStatus(args.status) if args.status else EpistemicStatus.FACT
    scope = kgk.scope(args.namespace, actor="cli")
    res = scope.ingest(
        StatementCreate(
            subject=EntityCreate(label=args.subject, namespace=args.namespace),
            relation=RelationCreate(label=args.relation, namespace=args.namespace),
            object=EntityCreate(label=args.object, namespace=args.namespace),
            provenance=prov,
            namespace=args.namespace,
            epistemic_status=status,
        )
    )
    print(f"[OK] Ingested Statement: {res.statement.id}")
    print(f"     Subject: {res.subject.label} ({res.subject.id})")
    print(f"     Relation: {res.relation.label} ({res.relation.id})")
    print(f"     Object: {res.object.label} ({res.object.id})")
    print(f"     Confidence: {res.statement.provenance.confidence}")
    return 0


def handle_retract(args: argparse.Namespace, kgk: KnowledgeGraphKernel) -> int:
    res = kgk.scope(args.namespace, actor="cli").retract(
        args.statement_id, reason=args.reason
    )
    if res.statement:
        print(f"[OK] Retracted Statement: {res.statement.id}")
        print(f"     Reason: {res.statement.retraction_reason}")
        return 0
    print(f"[ERROR] Statement {args.statement_id} not found.")
    return 1


def handle_search(args: argparse.Namespace, kgk: KnowledgeGraphKernel) -> int:
    vector = [float(x.strip()) for x in args.vector.split(",")] if args.vector else None
    results = kgk.scope(args.namespace, actor="cli").search_hybrid(
        query_text=args.query,
        query_vector=vector,
        top_k=args.top_k,
    )
    print(f"--- Search Results ({len(results)} matches) ---")
    for idx, r in enumerate(results, start=1):
        print(
            f"{idx}. [{r.entity.label}] (id={r.entity.id}, type={r.entity.type}) - score={r.score}"
        )
    return 0


def handle_path(args: argparse.Namespace, kgk: KnowledgeGraphKernel) -> int:
    paths = kgk.scope(args.namespace, actor="cli").find_paths(
        args.start, args.end, max_depth=args.max_depth
    )
    print(f"--- Found {len(paths)} paths from {args.start} to {args.end} ---")
    for idx, path in enumerate(paths, start=1):
        chain_str = " -> ".join(
            f"[{r.subject.label}] --({r.relation.label})--> [{r.object.label}]" for r in path
        )
        print(f"{idx}. {chain_str}")
    return 0


def handle_format(args: argparse.Namespace, kgk: KnowledgeGraphKernel) -> int:
    output = kgk.scope(args.namespace, actor="cli").format_neighborhood(
        args.entity, depth=args.depth, format_type=args.format, max_chars=args.max_chars
    )
    if isinstance(output, list):
        print(json.dumps(output, indent=2))
    else:
        print(output)
    return 0


def handle_namespace_register(args: argparse.Namespace, kgk: KnowledgeGraphKernel) -> int:
    namespace = kgk.register_namespace(
        Namespace(
            id=args.namespace_id,
            parent_id=args.parent,
            description=args.description,
            is_read_only=args.read_only,
        ),
        actor="cli",
    )
    print(f"[OK] Registered Namespace: {namespace.id}")
    print(f"     Parent: {namespace.parent_id or '(none)'}")
    return 0


def handle_replay(args: argparse.Namespace, kgk: KnowledgeGraphKernel) -> int:
    replayed_store = kgk.replay()
    print("[OK] Replay Completed Successfully.")
    print(f"     Active Entities: {len(replayed_store.all_entities())}")
    print(f"     Active Relations: {len(replayed_store.all_relations())}")
    print(f"     Active Statements: {len(replayed_store.all_statements())}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kgk",
        description="Knowledge Graph Kernel (KGK) CLI Management Utility",
    )
    parser.add_argument("--db", type=str, default=None, help="Path to SQLite database file")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Ingest
    p_ingest = subparsers.add_parser("ingest", help="Ingest a statement")
    p_ingest.add_argument("--subject", "-s", required=True, help="Subject entity label")
    p_ingest.add_argument("--relation", "-r", required=True, help="Relation label")
    p_ingest.add_argument("--object", "-o", required=True, help="Object entity label")
    p_ingest.add_argument("--namespace", "-n", default="global", help="Namespace")
    p_ingest.add_argument(
        "--confidence", "-c", type=float, default=0.9, help="Confidence (0.0 - 1.0)"
    )
    p_ingest.add_argument("--authority", "-a", type=int, default=50, help="Authority score")
    p_ingest.add_argument(
        "--status",
        choices=["fact", "hypothesis", "belief"],
        default="fact",
        help="Epistemic status",
    )
    p_ingest.add_argument("--source", default="cli", help="Source annotation")

    # Retract
    p_retract = subparsers.add_parser("retract", help="Retract a statement")
    p_retract.add_argument("statement_id", help="ID of statement to retract")
    p_retract.add_argument("--reason", "-m", required=True, help="Reason for retraction")
    p_retract.add_argument("--namespace", "-n", default="global", help="Namespace")

    # Search
    p_search = subparsers.add_parser("search", help="Hybrid search entities")
    p_search.add_argument("--query", "-q", default=None, help="Text search query")
    p_search.add_argument("--vector", "-v", default=None, help="Comma-separated vector floats")
    p_search.add_argument("--top-k", "-k", type=int, default=10, help="Max results")
    p_search.add_argument("--namespace", "-n", default="global", help="Namespace capability")

    # Path
    p_path = subparsers.add_parser("path", help="Find relation paths between entities")
    p_path.add_argument("--start", required=True, help="Start entity ID")
    p_path.add_argument("--end", required=True, help="End entity ID")
    p_path.add_argument("--max-depth", type=int, default=3, help="Max path hops")
    p_path.add_argument("--namespace", "-n", default="global", help="Namespace capability")

    # Format
    p_format = subparsers.add_parser("format", help="Format subgraph for prompt context")
    p_format.add_argument("entity", help="Center entity ID")
    p_format.add_argument("--depth", type=int, default=1, help="Neighborhood hop depth")
    p_format.add_argument(
        "--format",
        choices=["markdown", "mermaid", "json_ld"],
        default="markdown",
        help="Output format",
    )
    p_format.add_argument("--max-chars", type=int, default=4000, help="Max output characters")
    p_format.add_argument("--namespace", "-n", default="global", help="Namespace capability")

    # Namespace registration
    p_namespace = subparsers.add_parser("namespace", help="Register a durable namespace")
    p_namespace.add_argument("namespace_id", help="Namespace id, such as project:ape")
    p_namespace.add_argument("--parent", default="global", help="Parent namespace")
    p_namespace.add_argument("--description", default=None, help="Namespace description")
    p_namespace.add_argument("--read-only", action="store_true", help="Reject scoped writes")

    # Replay
    subparsers.add_parser("replay", help="Replay event log to rebuild graph store")

    parsed = parser.parse_args(argv)
    if not parsed.command:
        parser.print_help()
        return 0

    kgk = get_kernel(parsed.db)
    try:
        if parsed.command == "ingest":
            return handle_ingest(parsed, kgk)
        elif parsed.command == "retract":
            return handle_retract(parsed, kgk)
        elif parsed.command == "search":
            return handle_search(parsed, kgk)
        elif parsed.command == "path":
            return handle_path(parsed, kgk)
        elif parsed.command == "format":
            return handle_format(parsed, kgk)
        elif parsed.command == "replay":
            return handle_replay(parsed, kgk)
        elif parsed.command == "namespace":
            return handle_namespace_register(parsed, kgk)

        return 0
    finally:
        kgk.close()


if __name__ == "__main__":
    sys.exit(main())
