from __future__ import annotations

import argparse
import json
from pathlib import Path

from .case_definition import load_case
from .openalex import OpenAlexClient, OpenAlexError, PaperRecord
from .query_generator import QueryPlan, generate_query_plan
from .retrieval_eval import evaluate_retrieval, load_accepted_golden_ids


DEFAULT_CASE_FILE = Path("data/cases/hbm_thermal.json")
DEFAULT_OUTPUT_FILE = Path("data/openalex_case_results.jsonl")
DEFAULT_GOLDEN_FILE = Path("evals/golden/hbm_thermal/v1/candidates.jsonl")


def _merge_papers(groups: list[list[PaperRecord]], limit: int) -> list[PaperRecord]:
    merged: dict[str, PaperRecord] = {}
    for papers in groups:
        for paper in papers:
            key = paper.doi or paper.openalex_id
            if key not in merged:
                merged[key] = paper
                continue
            existing = merged[key]
            for query in paper.matched_queries:
                if query not in existing.matched_queries:
                    existing.matched_queries.append(query)
            if (paper.relevance_score or 0) > (existing.relevance_score or 0):
                existing.relevance_score = paper.relevance_score

    ranked = sorted(
        merged.values(),
        key=lambda paper: (
            len(paper.matched_queries),
            paper.relevance_score or 0,
            paper.cited_by_count,
        ),
        reverse=True,
    )
    return ranked[:limit]


def write_jsonl(records: list[PaperRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")


def query_plan_to_dict(plan: QueryPlan) -> dict:
    return {
        "keyword_queries": [
            {
                "strategy": item.strategy,
                "constraint_id": item.constraint_id,
                "query": item.query,
            }
            for item in plan.keyword_queries
        ],
        "semantic_query": plan.semantic_query,
    }


def print_query_plan(plan: QueryPlan) -> None:
    print("Query Plan")
    for index, item in enumerate(plan.keyword_queries, start=1):
        suffix = f" / {item.constraint_id}" if item.constraint_id else ""
        print(f"  K{index:02d} [{item.strategy}{suffix}] {item.query}")
    print(f"  S01 [semantic] {plan.semantic_query}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve papers for an engineering case")
    parser.add_argument("--case", type=Path, default=DEFAULT_CASE_FILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_FILE)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN_FILE)
    parser.add_argument("--mode", choices=["keyword", "semantic", "hybrid"], default="hybrid")
    parser.add_argument("--per-query", type=int, default=6)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--max-keyword-queries", type=int, default=10)
    parser.add_argument("--include-closed-access", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated query plan without calling OpenAlex.",
    )
    parser.add_argument(
        "--save-query-plan",
        type=Path,
        help="Optionally save the generated query plan as JSON before retrieval.",
    )
    args = parser.parse_args()

    case = load_case(args.case)
    plan = generate_query_plan(case, max_keyword_queries=args.max_keyword_queries)
    print(f"case: {case.case_id} / {case.title}")
    print_query_plan(plan)

    if args.save_query_plan:
        args.save_query_plan.parent.mkdir(parents=True, exist_ok=True)
        args.save_query_plan.write_text(
            json.dumps(query_plan_to_dict(plan), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"saved query plan to {args.save_query_plan}")

    if args.dry_run:
        print("dry-run: OpenAlex was not called")
        return

    client = OpenAlexClient()
    groups: list[list[PaperRecord]] = []

    try:
        if args.mode in {"keyword", "hybrid"}:
            keyword_queries = [item.query for item in plan.keyword_queries]
            groups.append(
                client.search_many(
                    keyword_queries,
                    mode="keyword",
                    per_query=args.per_query,
                    open_access_only=not args.include_closed_access,
                    limit=args.limit,
                )
            )
        if args.mode in {"semantic", "hybrid"}:
            groups.append(
                client.search(
                    plan.semantic_query,
                    mode="semantic",
                    per_page=min(args.limit, 50),
                    open_access_only=not args.include_closed_access,
                )
            )
    except OpenAlexError as exc:
        raise SystemExit(str(exc)) from exc

    papers = _merge_papers(groups, args.limit)
    write_jsonl(papers, args.output)
    print(f"saved {len(papers)} papers to {args.output}")

    if args.golden.exists():
        golden_ids = load_accepted_golden_ids(args.golden)
        evaluation = evaluate_retrieval(papers, golden_ids, k=args.limit)
        if evaluation.recall_at_k is None:
            print("Recall@K: N/A (Golden Corpus has no accepted papers yet)")
        else:
            print(
                f"Recall@{args.limit}: {evaluation.matched_count}/{evaluation.golden_count} "
                f"= {evaluation.recall_at_k:.1%}"
            )

    for index, paper in enumerate(papers[:10], start=1):
        print(f"{index:02d}. {paper.title} ({paper.publication_year})")
        print(f"    DOI: {paper.doi or '-'}")
        print(f"    matched queries: {len(paper.matched_queries)}")


if __name__ == "__main__":
    main()
