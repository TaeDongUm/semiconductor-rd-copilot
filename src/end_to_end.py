from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def _norm_doi(value: str) -> str:
    text = (value or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.startswith(prefix):
            text = text[len(prefix):]
    return text.rstrip("/")


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def retrieval_result_at_k(
    benchmark: dict[str, Any], strategy: str = "multi_query_rrf_v2", k: int = 20
) -> dict[str, Any]:
    rows = benchmark.get("results", {}).get(strategy, [])
    for row in rows:
        if int(row.get("k", -1)) == k:
            return row
    raise ValueError(f"retrieval result not found: strategy={strategy}, k={k}")


def matched_golden_dois(
    benchmark: dict[str, Any], strategy: str = "multi_query_rrf_v2", k: int = 20
) -> set[str]:
    coverage = {
        _norm_doi(item.get("doi", ""))
        for item in benchmark.get("sourceCoverage", [])
        if item.get("indexed") and item.get("doi")
    }
    result = retrieval_result_at_k(benchmark, strategy=strategy, k=k)
    missing = {_norm_doi(item) for item in result.get("missing", [])}
    return coverage - missing


@dataclass(frozen=True)
class EndToEndEvaluation:
    case_id: str
    execution_mode: str
    source_coverage: str
    retrieval_strategy: str
    retrieval_k: int
    retrieval_matched: int
    retrieval_golden: int
    retrieval_recall: float
    downstream_papers: int
    downstream_all_from_retrieval: bool
    evidence_accepted: int
    evidence_rejected: int
    evidence_errors: int
    output_gate: str
    output_constraint_precision: float
    output_constraint_recall: float
    output_constraint_f1: float
    hypothesis_traceability: float
    final_brief_exists: bool
    overall_gate: str
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["limitations"] = list(self.limitations)
        return payload


def evaluate_end_to_end(
    *,
    benchmark: dict[str, Any],
    papers: list[dict[str, Any]],
    evidence_validation: dict[str, Any],
    output_evaluation: dict[str, Any],
    brief_path: Path,
    strategy: str = "multi_query_rrf_v2",
    k: int = 20,
    execution_mode: str = "browser-openalex + manual-chatgpt",
) -> EndToEndEvaluation:
    retrieval = retrieval_result_at_k(benchmark, strategy=strategy, k=k)
    retrieved_dois = matched_golden_dois(benchmark, strategy=strategy, k=k)
    paper_dois = {_norm_doi(item.get("doi", "")) for item in papers if item.get("doi")}

    source = benchmark.get("sourceCoverage", [])
    indexed = sum(1 for item in source if item.get("indexed"))
    total_source = len(source)

    output_gate = str(output_evaluation.get("deterministic_gate") or "FAIL")
    evidence_errors = int(evidence_validation.get("error_count", 0))
    evidence_rejected = int(evidence_validation.get("rejected_count", 0))
    all_from_retrieval = bool(paper_dois) and paper_dois.issubset(retrieved_dois)
    final_brief_exists = brief_path.exists() and bool(brief_path.read_text(encoding="utf-8").strip())

    passed = all(
        (
            total_source > 0 and indexed == total_source,
            float(retrieval.get("recall", 0.0)) >= 0.70,
            all_from_retrieval,
            evidence_errors == 0,
            evidence_rejected == 0,
            output_gate == "PASS",
            final_brief_exists,
        )
    )

    limitations = (
        "Golden retrieval corpus contains 7 manually reviewed papers, so each paper changes recall by 14.3 percentage points.",
        "The downstream evidence set uses only Golden papers recovered by the V2 Top-20 benchmark; this validates the pipeline but is not a broad production retrieval study.",
        "LLM evidence extraction was performed in manual ChatGPT mode rather than a production API call.",
        "Deterministic output evaluation checks citation/constraint/numeric traceability, not full free-text semantic correctness.",
    )

    return EndToEndEvaluation(
        case_id=str(benchmark.get("caseId") or output_evaluation.get("case_id") or ""),
        execution_mode=execution_mode,
        source_coverage=f"{indexed}/{total_source}",
        retrieval_strategy=strategy,
        retrieval_k=k,
        retrieval_matched=int(retrieval.get("matched", 0)),
        retrieval_golden=int(retrieval.get("coveredCount", total_source)),
        retrieval_recall=float(retrieval.get("recall", 0.0)),
        downstream_papers=len(papers),
        downstream_all_from_retrieval=all_from_retrieval,
        evidence_accepted=int(evidence_validation.get("accepted_count", 0)),
        evidence_rejected=evidence_rejected,
        evidence_errors=evidence_errors,
        output_gate=output_gate,
        output_constraint_precision=float(output_evaluation.get("constraint_precision", 0.0)),
        output_constraint_recall=float(output_evaluation.get("constraint_recall", 0.0)),
        output_constraint_f1=float(output_evaluation.get("constraint_f1", 0.0)),
        hypothesis_traceability=float(output_evaluation.get("hypothesis_traceability", 0.0)),
        final_brief_exists=final_brief_exists,
        overall_gate="PASS" if passed else "FAIL",
        limitations=limitations,
    )


def render_markdown(result: EndToEndEvaluation) -> str:
    pct = lambda value: f"{value * 100:.1f}%"
    limits = "\n".join(f"- {item}" for item in result.limitations)
    return f"""# End-to-End Evaluation\n\n## Run result\n\n| Stage | Result |\n| --- | ---: |\n| Source coverage | {result.source_coverage} |\n| Retrieval | {result.retrieval_matched}/{result.retrieval_golden} @ {result.retrieval_k} ({pct(result.retrieval_recall)}) |\n| Downstream papers | {result.downstream_papers} |\n| All downstream papers recovered by retrieval | {str(result.downstream_all_from_retrieval).upper()} |\n| Evidence accepted / rejected | {result.evidence_accepted} / {result.evidence_rejected} |\n| Evidence validation errors | {result.evidence_errors} |\n| Constraint precision | {pct(result.output_constraint_precision)} |\n| Constraint recall | {pct(result.output_constraint_recall)} |\n| Constraint F1 | {pct(result.output_constraint_f1)} |\n| Hypothesis traceability | {pct(result.hypothesis_traceability)} |\n| Output quality gate | **{result.output_gate}** |\n| Final brief generated | {str(result.final_brief_exists).upper()} |\n| Overall gate | **{result.overall_gate}** |\n\n## Execution mode\n\n`{result.execution_mode}`\n\n## Limitations\n\n{limits}\n"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a complete semiconductor investigation run")
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--papers", required=True)
    parser.add_argument("--evidence-validation", required=True)
    parser.add_argument("--output-evaluation", required=True)
    parser.add_argument("--brief", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--report-out", required=True)
    parser.add_argument("--strategy", default="multi_query_rrf_v2")
    parser.add_argument("--k", type=int, default=20)
    args = parser.parse_args()

    result = evaluate_end_to_end(
        benchmark=_read_json(args.benchmark),
        papers=_read_jsonl(args.papers),
        evidence_validation=_read_json(args.evidence_validation),
        output_evaluation=_read_json(args.output_evaluation),
        brief_path=Path(args.brief),
        strategy=args.strategy,
        k=args.k,
    )

    json_out = Path(args.json_out)
    report_out = Path(args.report_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_out.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
