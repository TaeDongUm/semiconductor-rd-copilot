from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


def _norm_doi(value: str) -> str:
    value = (value or "").strip().lower()
    value = value.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _constraint_pairs(items: Iterable[dict[str, Any]]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for paper in items:
        doi = _norm_doi(str(paper.get("doi") or ""))
        for evidence in paper.get("evidence") or []:
            for constraint_id in evidence.get("constraint_ids") or []:
                pairs.add((doi, str(constraint_id)))
    return pairs


def _metric_keys(items: Iterable[dict[str, Any]]) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    for paper in items:
        doi = _norm_doi(str(paper.get("doi") or ""))
        for evidence in paper.get("evidence") or []:
            for metric in evidence.get("metrics") or []:
                name = re.sub(r"\s+", " ", str(metric.get("name") or "").strip().lower())
                value = re.sub(r"\s+", "", str(metric.get("value") or "").strip().lower())
                keys.add((doi, name, value))
    return keys


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


@dataclass(frozen=True)
class OutputEvaluation:
    case_id: str
    evaluated_papers: int
    golden_papers_in_case: int
    citation_validity: float
    constraint_precision: float
    constraint_recall: float
    constraint_f1: float
    unsupported_constraint_mappings: int
    missed_constraint_mappings: int
    numeric_precision: float
    numeric_recall: float
    hypothesis_traceability: float
    deterministic_gate: str
    missed_pairs: tuple[tuple[str, str], ...]
    extra_pairs: tuple[tuple[str, str], ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["missed_pairs"] = [list(item) for item in self.missed_pairs]
        data["extra_pairs"] = [list(item) for item in self.extra_pairs]
        return data


def evaluate_output(
    *,
    golden: list[dict[str, Any]],
    actual: list[dict[str, Any]],
    decision: dict[str, Any],
    case_id: str = "HBM-THERMAL-001",
) -> OutputEvaluation:
    golden_by_doi = {_norm_doi(item["doi"]): item for item in golden}
    actual_dois = {_norm_doi(item.get("doi", "")) for item in actual}
    overlapping_dois = actual_dois & set(golden_by_doi)

    golden_overlap = [golden_by_doi[doi] for doi in overlapping_dois]

    citation_validity = (
        sum(1 for item in actual if _norm_doi(item.get("doi", "")) in golden_by_doi) / len(actual)
        if actual
        else 0.0
    )

    gold_pairs = _constraint_pairs(golden_overlap)
    actual_pairs = _constraint_pairs(actual)
    shared_pairs = gold_pairs & actual_pairs
    extra_pairs = actual_pairs - gold_pairs
    missed_pairs = gold_pairs - actual_pairs

    constraint_precision = len(shared_pairs) / len(actual_pairs) if actual_pairs else 0.0
    constraint_recall = len(shared_pairs) / len(gold_pairs) if gold_pairs else 0.0
    constraint_f1 = _f1(constraint_precision, constraint_recall)

    gold_metrics = _metric_keys(golden_overlap)
    actual_metrics = _metric_keys(actual)
    shared_metrics = gold_metrics & actual_metrics
    numeric_precision = len(shared_metrics) / len(actual_metrics) if actual_metrics else (1.0 if not gold_metrics else 0.0)
    numeric_recall = len(shared_metrics) / len(gold_metrics) if gold_metrics else 1.0

    evidence_ids = {
        evidence.get("evidence_id")
        for paper in actual
        for evidence in paper.get("evidence") or []
        if evidence.get("evidence_id")
    }
    hypotheses = decision.get("hypotheses") or []
    traceable = 0
    for hypothesis in hypotheses:
        basis = set(hypothesis.get("basis_evidence_ids") or [])
        unknowns = set(hypothesis.get("unknown_constraint_ids") or [])
        text = str(hypothesis.get("text") or "").lower()
        validation = str(hypothesis.get("validation") or "").strip()
        if basis and basis.issubset(evidence_ids) and unknowns and "unverified" in text and validation:
            traceable += 1
    hypothesis_traceability = traceable / len(hypotheses) if hypotheses else 1.0

    # Conservative MVP gate: don't reward only high precision while missing too much supported evidence.
    passed = all(
        (
            citation_validity == 1.0,
            constraint_precision >= 0.95,
            constraint_recall >= 0.80,
            numeric_precision == 1.0,
            numeric_recall == 1.0,
            hypothesis_traceability == 1.0,
        )
    )

    notes = (
        "Evaluation is conditional on papers already retrieved; retrieval recall is measured separately.",
        "Constraint mapping is scored as DOI × constraint_id atomic pairs against human-reviewed Golden Evidence.",
        "This deterministic harness does not prove free-text semantic equivalence; it checks citations, coverage, metrics, and hypothesis traceability.",
    )

    return OutputEvaluation(
        case_id=case_id,
        evaluated_papers=len(actual),
        golden_papers_in_case=len(golden),
        citation_validity=citation_validity,
        constraint_precision=constraint_precision,
        constraint_recall=constraint_recall,
        constraint_f1=constraint_f1,
        unsupported_constraint_mappings=len(extra_pairs),
        missed_constraint_mappings=len(missed_pairs),
        numeric_precision=numeric_precision,
        numeric_recall=numeric_recall,
        hypothesis_traceability=hypothesis_traceability,
        deterministic_gate="PASS" if passed else "FAIL",
        missed_pairs=tuple(sorted(missed_pairs)),
        extra_pairs=tuple(sorted(extra_pairs)),
        notes=notes,
    )


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(result: OutputEvaluation, *, version: str = "V1") -> str:
    missed = "\n".join(f"- `{doi}` → `{constraint}`" for doi, constraint in result.missed_pairs) or "- 없음"
    extra = "\n".join(f"- `{doi}` → `{constraint}`" for doi, constraint in result.extra_pairs) or "- 없음"
    if result.deterministic_gate == "PASS":
        interpretation = (
            "- 현재 출력은 deterministic quality gate를 통과했습니다. "
            "근거 없는 constraint를 추가하지 않는 precision을 유지하면서 Golden Evidence coverage를 확보했습니다.\n"
            "- 남은 miss가 있다면 source wording과 Golden label을 사람이 다시 확인합니다. "
            "점수를 높이기 위해 근거 없는 constraint를 강제로 채우지 않습니다."
        )
        next_step = (
            "현재 Prompt를 기준선으로 고정하고, 실제 End-to-End Run에서 동일 평가를 재사용합니다. "
            "Golden label이 source보다 강한 해석을 포함하는지도 별도로 점검합니다."
        )
    else:
        interpretation = (
            "- 현재 출력은 **근거 없는 constraint를 추가하지 않는 precision은 높지만, "
            "source가 지원하는 constraint 일부를 놓쳐 recall이 부족**합니다.\n"
            "- 누락 유형을 분석한 뒤 source가 명시적으로 지원하는 constraint만 coverage check에서 복구합니다."
        )
        next_step = (
            "Evidence Extraction Prompt의 `Constraint Coverage Check`를 적용해, source가 명시적으로 지원하는 "
            "constraint가 누락되지 않았는지 출력 직전에 한 번 더 확인합니다. 단, 근거가 없는 constraint를 "
            "채우도록 강제하지 않습니다."
        )

    return f"""# AI Output Evaluation {version}\n\n## 결과\n\n| Metric | Result |\n| --- | ---: |\n| Evaluated retrieved papers | {result.evaluated_papers} |\n| Citation validity | {_pct(result.citation_validity)} |\n| Constraint mapping precision | {_pct(result.constraint_precision)} |\n| Constraint mapping recall | {_pct(result.constraint_recall)} |\n| Constraint mapping F1 | {_pct(result.constraint_f1)} |\n| Unsupported constraint mappings | {result.unsupported_constraint_mappings} |\n| Missed constraint mappings | {result.missed_constraint_mappings} |\n| Numeric precision | {_pct(result.numeric_precision)} |\n| Numeric recall | {_pct(result.numeric_recall)} |\n| Hypothesis traceability | {_pct(result.hypothesis_traceability)} |\n| Deterministic quality gate | **{result.deterministic_gate}** |\n\n## 놓친 Golden Constraint Mapping\n\n{missed}\n\n## 근거 없이 추가된 Mapping\n\n{extra}\n\n## 해석\n\n{interpretation}\n- 이 평가는 Retrieval 이후 단계만 측정합니다. 논문 검색 Recall은 별도 Retrieval Benchmark에서 관리합니다.\n- 자유문장 의미가 원문과 완전히 동일한지까지 자동 판정하는 평가는 아닙니다. 현재 단계에서는 사람이 검토한 Golden Evidence의 DOI·constraint·numeric metric과 output traceability를 deterministic하게 비교합니다.\n\n## 다음 단계\n\n{next_step}\n"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate AI evidence output against Golden Evidence")
    parser.add_argument("--golden", default="data/evidence/hbm_thermal_verified_seed.jsonl")
    parser.add_argument("--actual", default="runs/hbm_thermal_live_demo_2026-09-27/06_evidence.jsonl")
    parser.add_argument("--decision", default="runs/hbm_thermal_live_demo_2026-09-27/07_decision.json")
    parser.add_argument("--json-out", default="evals/output/history/hbm_thermal_output_v1_2026-09-27.json")
    parser.add_argument("--report-out", default="reports/output_evaluation_v1.md")
    parser.add_argument("--version", default="V1")
    args = parser.parse_args()

    golden = _load_jsonl(Path(args.golden))
    actual = _load_jsonl(Path(args.actual))
    decision = json.loads(Path(args.decision).read_text(encoding="utf-8"))
    result = evaluate_output(golden=golden, actual=actual, decision=decision)

    json_out = Path(args.json_out)
    report_out = Path(args.report_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_out.write_text(render_markdown(result, version=args.version), encoding="utf-8")

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
