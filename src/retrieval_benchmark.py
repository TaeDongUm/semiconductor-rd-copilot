from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .case_definition import load_case
from .openalex import OpenAlexClient, OpenAlexError, PaperRecord
from .query_generator import generate_query_plan
from .retrieval_eval import load_accepted_golden_ids


DEFAULT_CASE = Path("data/cases/hbm_thermal.json")
DEFAULT_GOLDEN = Path("evals/golden/hbm_thermal/v1/golden.jsonl")
DEFAULT_OUTPUT = Path("evals/retrieval/hbm_thermal_v2_benchmark.json")
DEFAULT_COVERAGE = Path("evals/retrieval/hbm_thermal_v2_source_coverage.json")


@dataclass(frozen=True)
class GoldenCoverage:
    golden_id: str
    doi: str
    indexed: bool
    has_abstract: bool
    openalex_id: str | None
    title: str | None


@dataclass(frozen=True)
class StrategyResult:
    strategy: str
    k: int
    golden_count: int
    source_covered_golden_count: int
    retrieved_count: int
    matched_count: int
    recall_at_k: float | None
    conditional_recall_at_k: float | None
    matched_golden_ids: tuple[str, ...]
    missing_golden_ids: tuple[str, ...]
    source_unavailable_golden_ids: tuple[str, ...]
    retrieval_miss_golden_ids: tuple[str, ...]
    retrieved: tuple[dict, ...]


@dataclass(frozen=True)
class BenchmarkReport:
    benchmark_id: str
    case_id: str
    golden_file: str
    access_policy: str
    fusion_policy: str
    source_coverage: tuple[GoldenCoverage, ...]
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


def _compact_paper(paper: PaperRecord, rank: int, fusion_score: float | None = None) -> dict:
    result = {
        "rank": rank,
        "title": paper.title,
        "doi": paper.doi,
        "publication_year": paper.publication_year,
        "cited_by_count": paper.cited_by_count,
        "matched_query_count": len(paper.matched_queries),
        "matched_queries": paper.matched_queries,
    }
    if fusion_score is not None:
        result["fusion_score"] = round(fusion_score, 8)
    return result


def _load_golden_entries(path: Path) -> list[dict]:
    entries=[]
    with path.open(encoding="utf-8") as f:
        for raw in f:
            raw=raw.strip()
            if not raw:
                continue
            item=json.loads(raw)
            if item.get("review_status") == "accepted" and item.get("doi"):
                entries.append(item)
    return entries


def diagnose_source_coverage(client: OpenAlexClient, golden_path: Path) -> tuple[GoldenCoverage, ...]:
    rows=[]
    for item in _load_golden_entries(golden_path):
        doi=_normalize_doi(item.get("doi")) or ""
        golden_id=f"doi:{doi}"
        work=client.get_work_by_doi(doi)
        rows.append(
            GoldenCoverage(
                golden_id=golden_id,
                doi=doi,
                indexed=work is not None,
                has_abstract=bool(work.abstract) if work else False,
                openalex_id=work.openalex_id if work else None,
                title=work.title if work else None,
            )
        )
    return tuple(rows)


def reciprocal_rank_fusion(
    rankings: list[list[PaperRecord]],
    *,
    limit: int,
    rrf_k: int = 60,
) -> tuple[list[PaperRecord], dict[str, float]]:
    """Fuse independently ranked result lists using reciprocal-rank fusion.

    RRF depends only on rank positions, avoiding incomparable relevance-score scales between
    keyword and semantic search. Repeated appearance across queries increases a paper's score.
    """
    if limit < 1:
        return [], {}
    scores: dict[str, float] = {}
    papers: dict[str, PaperRecord] = {}
    for ranking in rankings:
        for rank, paper in enumerate(ranking, start=1):
            key=_paper_identity(paper)
            scores[key]=scores.get(key, 0.0) + 1.0 / (rrf_k + rank)
            if key not in papers:
                papers[key]=paper
            else:
                existing=papers[key]
                for q in paper.matched_queries:
                    if q not in existing.matched_queries:
                        existing.matched_queries.append(q)
    ordered=sorted(scores, key=lambda key: (scores[key], papers[key].cited_by_count), reverse=True)
    selected=[papers[key] for key in ordered[:limit]]
    return selected, {key:scores[key] for key in ordered[:limit]}


def _strategy_result(
    strategy: str,
    papers: list[PaperRecord],
    golden_ids: set[str],
    source_covered_ids: set[str],
    *,
    k: int,
    fusion_scores: dict[str, float] | None = None,
) -> StrategyResult:
    top_k=papers[:k]
    retrieved_ids={_paper_identity(paper) for paper in top_k}
    matched=tuple(sorted(golden_ids & retrieved_ids))
    missing=tuple(sorted(golden_ids - retrieved_ids))
    source_unavailable=tuple(sorted(golden_ids - source_covered_ids))
    retrieval_miss=tuple(sorted((golden_ids & source_covered_ids) - retrieved_ids))
    recall=(len(matched)/len(golden_ids)) if golden_ids else None
    conditional=(len(set(matched)&source_covered_ids)/len(source_covered_ids)) if source_covered_ids else None
    return StrategyResult(
        strategy=strategy,
        k=k,
        golden_count=len(golden_ids),
        source_covered_golden_count=len(source_covered_ids),
        retrieved_count=len(top_k),
        matched_count=len(matched),
        recall_at_k=recall,
        conditional_recall_at_k=conditional,
        matched_golden_ids=matched,
        missing_golden_ids=missing,
        source_unavailable_golden_ids=source_unavailable,
        retrieval_miss_golden_ids=retrieval_miss,
        retrieved=tuple(
            _compact_paper(
                p,
                i,
                (fusion_scores or {}).get(_paper_identity(p)),
            )
            for i,p in enumerate(top_k, start=1)
        ),
    )


def run_benchmark(
    *,
    case_path: Path = DEFAULT_CASE,
    golden_path: Path = DEFAULT_GOLDEN,
    k: int = 20,
    per_query: int = 20,
    max_keyword_queries: int = 10,
    client: OpenAlexClient | None = None,
) -> BenchmarkReport:
    if k < 1 or k > 50:
        raise ValueError("k must be between 1 and 50")
    if per_query < 1 or per_query > 50:
        raise ValueError("per_query must be between 1 and 50")

    case=load_case(case_path)
    golden_ids=load_accepted_golden_ids(golden_path)
    if not golden_ids:
        raise ValueError("Golden Corpus contains no accepted papers")
    client=client or OpenAlexClient()
    plan=generate_query_plan(case, max_keyword_queries=max_keyword_queries)

    coverage=diagnose_source_coverage(client, golden_path)
    source_covered_ids={row.golden_id for row in coverage if row.indexed}

    # Keep the v1 single-query baseline unchanged for an honest before/after comparison.
    baseline_query='"high bandwidth memory" "thermal management"'
    baseline=client.search(baseline_query, mode="keyword", per_page=k, open_access_only=False)

    keyword_rankings=[]
    for item in plan.keyword_queries:
        keyword_rankings.append(
            client.search(item.query, mode="keyword", per_page=per_query, open_access_only=False)
        )
    multi_keyword, multi_scores=reciprocal_rank_fusion(keyword_rankings, limit=k)

    semantic=client.search(plan.semantic_query, mode="semantic", per_page=k, open_access_only=False)
    hybrid, hybrid_scores=reciprocal_rank_fusion(keyword_rankings + [semantic], limit=k)

    return BenchmarkReport(
        benchmark_id="HBM-THERMAL-RETRIEVAL-V2",
        case_id=case.case_id,
        golden_file=str(golden_path),
        access_policy="all_metadata_no_oa_filter",
        fusion_policy="RRF(k=60), concept-family boolean keyword queries + semantic ranking",
        source_coverage=coverage,
        results=(
            _strategy_result("single_keyword_v1_baseline", baseline, golden_ids, source_covered_ids, k=k),
            _strategy_result("multi_query_rrf_v2", multi_keyword, golden_ids, source_covered_ids, k=k, fusion_scores=multi_scores),
            _strategy_result("semantic", semantic, golden_ids, source_covered_ids, k=k),
            _strategy_result("hybrid_rrf_v2", hybrid, golden_ids, source_covered_ids, k=k, fusion_scores=hybrid_scores),
        ),
    )


def write_report(report: BenchmarkReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def to_markdown(report: BenchmarkReport) -> str:
    indexed=sum(1 for row in report.source_coverage if row.indexed)
    abstracted=sum(1 for row in report.source_coverage if row.indexed and row.has_abstract)
    lines=[
        "# Retrieval Benchmark V2",
        "",
        f"- Benchmark: `{report.benchmark_id}`",
        f"- Case: `{report.case_id}`",
        f"- Source coverage: **{indexed}/{len(report.source_coverage)}** indexed; **{abstracted}/{len(report.source_coverage)}** with abstract",
        f"- Fusion: `{report.fusion_policy}`",
        "",
        "| Strategy | Matched | Golden | Recall@K | Recall@K (indexed only) |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in report.results:
        recall="N/A" if item.recall_at_k is None else f"{item.recall_at_k:.1%}"
        conditional="N/A" if item.conditional_recall_at_k is None else f"{item.conditional_recall_at_k:.1%}"
        lines.append(f"| {item.strategy} | {item.matched_count} | {item.golden_count} | {recall} | {conditional} |")
    lines.extend(["", "## Missing diagnosis", ""])
    for item in report.results:
        unavailable=", ".join(item.source_unavailable_golden_ids) or "None"
        misses=", ".join(item.retrieval_miss_golden_ids) or "None"
        lines.append(f"- **{item.strategy}** source-unavailable: {unavailable}")
        lines.append(f"- **{item.strategy}** retrieval/ranking miss: {misses}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser=argparse.ArgumentParser(description="Benchmark OpenAlex retrieval strategies with source-coverage diagnostics")
    parser.add_argument("--case", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--k", type=int, default=20)
    parser.add_argument("--per-query", type=int, default=20)
    parser.add_argument("--max-keyword-queries", type=int, default=10)
    args=parser.parse_args()
    try:
        report=run_benchmark(case_path=args.case, golden_path=args.golden, k=args.k, per_query=args.per_query, max_keyword_queries=args.max_keyword_queries)
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
