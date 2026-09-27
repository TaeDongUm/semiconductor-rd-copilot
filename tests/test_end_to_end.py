import json
from pathlib import Path

from src.end_to_end import evaluate_end_to_end, matched_golden_dois


def _benchmark():
    return {
        "caseId": "CASE-1",
        "sourceCoverage": [
            {"doi": "10/a", "indexed": True},
            {"doi": "10/b", "indexed": True},
        ],
        "results": {
            "multi_query_rrf_v2": [
                {"k": 20, "matched": 1, "coveredCount": 2, "recall": 0.5, "missing": ["doi:10/b"]}
            ]
        },
    }


def test_matched_golden_dois_derives_hits_from_missing():
    assert matched_golden_dois(_benchmark()) == {"10/a"}


def test_end_to_end_fails_when_retrieval_below_gate(tmp_path: Path):
    brief = tmp_path / "brief.md"
    brief.write_text("ok", encoding="utf-8")
    result = evaluate_end_to_end(
        benchmark=_benchmark(),
        papers=[{"doi": "10/a"}],
        evidence_validation={"accepted_count": 1, "rejected_count": 0, "error_count": 0},
        output_evaluation={
            "case_id": "CASE-1",
            "deterministic_gate": "PASS",
            "constraint_precision": 1.0,
            "constraint_recall": 1.0,
            "constraint_f1": 1.0,
            "hypothesis_traceability": 1.0,
        },
        brief_path=brief,
    )
    assert result.overall_gate == "FAIL"


def test_project_final_e2e_artifacts_are_consistent():
    root = Path(__file__).resolve().parents[1]
    run = root / "runs" / "hbm_thermal_e2e_final_2026-09-27"
    if not run.exists():
        return
    result = evaluate_end_to_end(
        benchmark=json.loads((run / "04_retrieval_benchmark.json").read_text(encoding="utf-8")),
        papers=[json.loads(line) for line in (run / "04_papers.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()],
        evidence_validation=json.loads((run / "06_evidence_validation.json").read_text(encoding="utf-8")),
        output_evaluation=json.loads((run / "09_output_evaluation.json").read_text(encoding="utf-8")),
        brief_path=run / "08_investigation_brief.md",
    )
    assert result.overall_gate == "PASS"
    assert result.downstream_all_from_retrieval is True
