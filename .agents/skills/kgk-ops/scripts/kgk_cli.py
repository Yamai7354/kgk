#!/usr/bin/env python3
"""CLI helper to interact with the Knowledge Graph Kernel API server."""

import argparse
import json
import sys
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8000"


def _request(path: str, method: str = "GET", data: dict = None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}

    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        print(f"HTTP Error {exc.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Error connecting to server at {BASE_URL}: {exc.reason}", file=sys.stderr)
        print(
            "Ensure the FastAPI server is running with 'uv run uvicorn api.app:app --reload'",
            file=sys.stderr,
        )
        sys.exit(1)


def cmd_health(args):
    res = _request("/health")
    print(json.dumps(res, indent=2))


def cmd_ingest(args):
    payload = {
        "subject": {"label": args.subject_label, "type": args.subject_type},
        "relation_label": args.relation_label,
        "relation_type": args.relation_type,
        "object": {"label": args.object_label, "type": args.object_type},
        "provenance": {"source": args.source, "confidence": args.confidence},
    }
    res = _request("/statements", method="POST", data=payload)
    print("Statement Ingested Successfully!")
    print(json.dumps(res, indent=2))


def cmd_query(args):
    path = f"/entities/{args.entity_id}/statements?direction={args.direction}"
    res = _request(path)
    print(json.dumps(res, indent=2))


def cmd_neighborhood(args):
    path = f"/entities/{args.entity_id}/neighborhood?depth={args.depth}"
    res = _request(path)
    print(json.dumps(res, indent=2))


def cmd_retract(args):
    payload = {"reason": args.reason}
    path = f"/statements/{args.statement_id}/retract"
    res = _request(path, method="POST", data=payload)
    print("Statement Retracted Successfully!")
    print(json.dumps(res, indent=2))


def cmd_merge(args):
    payload = {"duplicate_ids": args.duplicate_ids}
    path = f"/entities/{args.canonical_id}/merge"
    res = _request(path, method="POST", data=payload)
    print("Entities Merged Successfully!")
    print(json.dumps(res, indent=2))


def cmd_embed(args):
    try:
        vector = [float(x) for x in args.vector.split(",")]
    except ValueError:
        print("Error: vector must be a comma-separated list of floats.", file=sys.stderr)
        sys.exit(1)

    payload = {"vector": vector, "model": args.model}
    path = f"/entities/{args.entity_id}/embeddings"
    res = _request(path, method="POST", data=payload)
    print("Embedding Upserted Successfully!")
    print(json.dumps(res, indent=2))


def cmd_search(args):
    try:
        vector = [float(x) for x in args.vector.split(",")]
    except ValueError:
        print("Error: vector must be a comma-separated list of floats.", file=sys.stderr)
        sys.exit(1)

    payload = {"vector": vector, "top_k": args.top_k}
    path = "/entities/search"
    res = _request(path, method="POST", data=payload)
    print("Similarity Search Results:")
    print(json.dumps(res, indent=2))


def main():
    parser = argparse.ArgumentParser(description="KGK Database CLI Helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Health command
    subparsers.add_parser("health", help="Check server health")

    # Ingest command
    p_ingest = subparsers.add_parser("ingest", help="Ingest a new statement")
    p_ingest.add_argument("--subject-label", required=True, help="Label of subject entity")
    p_ingest.add_argument("--subject-type", default="Thing", help="Type of subject entity")
    p_ingest.add_argument("--relation-label", required=True, help="Label of relation")
    p_ingest.add_argument("--relation-type", default="Relation", help="Type of relation")
    p_ingest.add_argument("--object-label", required=True, help="Label of object entity")
    p_ingest.add_argument("--object-type", default="Thing", help="Type of object entity")
    p_ingest.add_argument("--source", required=True, help="Source of statement provenance")
    p_ingest.add_argument(
        "--confidence", type=float, default=1.0, help="Confidence value (0.0 to 1.0)"
    )

    # Query command
    p_query = subparsers.add_parser("query", help="Retrieve statements for an entity")
    p_query.add_argument("entity_id", help="ID of entity to query")
    p_query.add_argument(
        "--direction",
        choices=["subject", "object", "both"],
        default="both",
        help="Statement direction",
    )

    # Neighborhood command
    p_neigh = subparsers.add_parser(
        "neighborhood", help="Retrieve neighborhood subgraph around an entity"
    )
    p_neigh.add_argument("entity_id", help="ID of root entity")
    p_neigh.add_argument("--depth", type=int, default=1, help="Traversal depth limit")

    # Retract command
    p_retract = subparsers.add_parser("retract", help="Retract a statement")
    p_retract.add_argument("statement_id", help="ID of statement to retract")
    p_retract.add_argument("--reason", required=True, help="Reason for retraction")

    # Merge command
    p_merge = subparsers.add_parser("merge", help="Merge duplicate entities")
    p_merge.add_argument("canonical_id", help="ID of canonical entity")
    p_merge.add_argument("duplicate_ids", nargs="+", help="IDs of duplicate entities to merge")

    # Embed command
    p_embed = subparsers.add_parser("embed", help="Upsert entity vector embedding")
    p_embed.add_argument("entity_id", help="ID of entity")
    p_embed.add_argument(
        "--vector", required=True, help="Comma-separated floats (e.g. 0.15,0.4,-0.1)"
    )
    p_embed.add_argument("--model", default="default", help="Embedding model name")

    # Search command
    p_search = subparsers.add_parser("search", help="Semantic similarity search")
    p_search.add_argument(
        "--vector", required=True, help="Comma-separated query vector (e.g. 0.15,0.4,-0.1)"
    )
    p_search.add_argument("--top-k", type=int, default=10, help="Limit number of results")

    args = parser.parse_args()

    cmds = {
        "health": cmd_health,
        "ingest": cmd_ingest,
        "query": cmd_query,
        "neighborhood": cmd_neighborhood,
        "retract": cmd_retract,
        "merge": cmd_merge,
        "embed": cmd_embed,
        "search": cmd_search,
    }

    cmds[args.command](args)


if __name__ == "__main__":
    main()
