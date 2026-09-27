from __future__ import annotations

import argparse
import json
from pathlib import Path

from .openalex import OpenAlexClient, OpenAlexError


DEFAULT_QUERY_FILE = Path("data/hbm_thermal_queries.json")
DEFAULT_OUTPUT_FILE = Path("data/openalex_hbm_results.jsonl")


def load_queries(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    queries = payload.get("queries")
    if not isinstance(queries, list) or not queries:
        raise ValueError("query file must contain a non-empty 'queries' list")
    return [str(query) for query in queries]


def write_jsonl(records, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve HBM thermal papers from OpenAlex")
    parser.add_argument("--query-file", type=Path, default=DEFAULT_QUERY_FILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_FILE)
    parser.add_argument("--mode", choices=["keyword", "semantic"], default="keyword")
    parser.add_argument("--per-query", type=int, default=8)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--include-closed-access",
        action="store_true",
        help="Do not restrict retrieval to open-access works.",
    )
    args = parser.parse_args()

    queries = load_queries(args.query_file)
    client = OpenAlexClient()

    try:
        papers = client.search_many(
            queries,
            mode=args.mode,
            per_query=args.per_query,
            open_access_only=not args.include_closed_access,
            limit=args.limit,
        )
    except OpenAlexError as exc:
        raise SystemExit(str(exc)) from exc

    write_jsonl(papers, args.output)
    print(f"saved {len(papers)} papers to {args.output}")
    for index, paper in enumerate(papers[:10], start=1):
        print(f"{index:02d}. {paper.title} ({paper.publication_year})")
        print(f"    DOI: {paper.doi or '-'}")
        print(f"    matched queries: {len(paper.matched_queries)}")


if __name__ == "__main__":
    main()
