from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .case_definition import load_case
from .openalex import OpenAlexClient, OpenAlexError, PaperRecord
from .query_generator import generate_query_plan
from .retrieval_eval import evaluate_retrieval, load_accepted_golden_ids
from .retrieve_case import _merge_papers


DEFAULT_CASE = Path("data/cases/hbm_thermal.json")
DEFAULT_GOLDEN = Path("evals/golden/hbm_thermal/v1/golden.jsonl")
DEFAULT_OUTPUT = Path("evals/retrieval/hbm_thermal_v1_benchmark.json")


@dataclass(frozen=True)
class StrategyResult:
    strategy: str
    k: int
    golden_count: int
    retrieved_count: int
    matched_count: int
    recall_at_k: float | None
    matched_golden_ids: tuple[str, ...]
    missing_golden_ids: tuple[str, ...]
    retrieved: tuple[dict, ...]


@dataclass(frozen=True)
class BenchmarkReport:
    benchmark_id: str
    case_id: str
    golden_file: str
    access_policy: str
    results: tuple[StrategyResult, ...]


def _normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().lower()
    prefix = "https://doi.org/"
    if cleaned.startswith(prefix):
        cleaned = cleaned[len(prefix):]
    return cleaned or None


def _paper_identity(paper: PaperRecord) -> str:
    doi = _normalize_doi(paper.doi)
    if doi:
        return f"doi:{doi}"
    return f"openalex:{paper.openalex_id.strip().lower()}"


def _compact_paper(paper: PaperRecord, rank: int) -> dict:
    return {
        "rank": rank,
        "title": paper.title,
        "doi": paper.doi,
        "publication_year": paper.publication_year,
        "cited_by_count": paper.cited_by_count,
        "matched_query_count": len(paper.matched_queries),
        "matched_queries": paper.matched_queries,
    }


def _strategy_result(
    strategy: str,
    papers: list[PaperRecord],
    golden_ids: set[str],
    *,
    k: int,
) -> StrategyResult:
    evaluation = evaluate_retrieval(papers, golden_ids, k=k)
    top_k = papers[:k]
    retrieved_ids = {_paper_identity(paper) for paper in top_k}
    matched = tuple(sorted(golden_ids & retrieved_ids))
    missing = tuple(sorted(golden_ids - retrieved_ids))
    return StrategyResult(
        strategy=strategy,
        k=k,
        golden_count=evaluation.golden_count,
        retrieved_count=evaluation.retrieved_count,
        matched_count=evaluation.matched_count,
        recall_at_k=evaluation.recall_at_k,
        matched_golden_ids=matched,
        missing_golden_ids=missing,
        retrieved=tuple(_compact_paper(p, i) for i, p in enumerate(top_k, start=1)),
    )


def run_benchmark(
    *,
    case_path: Path = DEFAULT_CASE,
    golden_path: Path = DEFAULT_GOLDEN,
    k: int = 20,
    per_query: int = 8,
    max_keyword_queries: int = 10,
    client: OpenAlexClient | None = None,
) -> BenchmarkReport:
    """Compare retrieval strategies against a fixed Golden Corpus.

    Benchmark retrieval intentionally searches both OA and closed-access metadata.
    Access restrictions are an evidence-acquisition concern, not a retrieval-quality metric.
    """
    if k < 1 or k > 50:
        raise ValueError("k must be between 1 and 50")

    case = load_case(case_path)
    golden_ids = load_accepted_golden_ids(golden_path)
    if not golden_ids:
        raise ValueError("Golden Corpus contains no accepted papers")

    plan = generate_query_plan(case, max_keyword_queries=max_keyword_queries)
    client = client or OpenAlexClient()

    # A. One broad keyword query: intentionally simple baseline.
    baseline_query = plan.keyword_queries[0].query
    baseline = client.search(
        baseline_query,
        mode="keyword",
        per_page=k,
        open_access_only=False,
    )

    # B. Multi-query keyword retrieval.
    multi_keyword = client.search_many(
        [item.query for item in plan.keyword_queries],
        mode="keyword",
        per_query=per_query,
        open_access_only=False,
        limit=k,
    )

    # C. Semantic retrieval using the engineering problem statement.
    semantic = client.search(
        plan.semantic_query,
        mode="semantic",
        per_page=k,
        open_access_only=False,
    )

    # D. Hybrid: multi-query keyword + semantic, same merge/ranking policy used by the app.
    hybrid = _merge_papers([multi_keyword, semantic], k)

    return BenchmarkReport(
        benchmark_id="HBM-THERMAL-RETRIEVAL-V1",
        case_id=case.case_id,
        golden_file=str(golden_path),
        access_policy="all_metadata_no_oa_filter",
        results=(
            _strategy_result("single_keyword", baseline, golden_ids, k=k),
            _strategy_result("multi_query_keyword", multi_keyword, golden_ids, k=k),
            _strategy_result("semantic", semantic, golden_ids, k=k),
            _strategy_result("hybrid", hybrid, golden_ids, k=k),
        ),
    )


def write_report(report: BenchmarkReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def to_markdown(report: BenchmarkReport) -> str:
    lines = [
        "# Retrieval Benchmark",
        "",
        f"- Benchmark: `{report.benchmark_id}`",
        f"- Case: `{report.case_id}`",
        f"- Access policy: `{report.access_policy}`",
        "",
        "| Strategy | Matched | Golden | Recall@K |",
        "|---|---:|---:|---:|",
    ]
    for item in report.results:
        recall = "N/A" if item.recall_at_k is None else f"{item.recall_at_k:.1%}"
        lines.append(
            f"| {item.strategy} | {item.matched_count} | {item.golden_count} | {recall} |"
        )
    lines.extend(["", "## Missing Golden Papers", ""])
    for item in report.results:
        missing = ", ".join(item.missing_golden_ids) if item.missing_golden_ids else "None"
        lines.append(f"- **{item.strategy}**: {missing}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark OpenAlex retrieval strategies")
    parser.add_argument("--case", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--k", type=int, default=20)
    parser.add_argument("--per-query", type=int, default=8)
    parser.add_argument("--max-keyword-queries", type=int, default=10)
    args = parser.parse_args()

    try:
        report = run_benchmark(
            case_path=args.case,
            golden_path=args.golden,
            k=args.k,
            per_query=args.per_query,
            max_keyword_queries=args.max_keyword_queries,
        )
    except OpenAlexError as exc:
        raise SystemExit(str(exc)) from exc

    write_report(report, args.output)
    print(f"saved benchmark JSON to {args.output}")
    print(to_markdown(report))

    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(to_markdown(report), encoding="utf-8")
        print(f"saved benchmark Markdown to {args.markdown}")


if __name__ == "__main__":
    main()
