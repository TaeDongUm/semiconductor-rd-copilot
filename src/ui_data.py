from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STATUS_SYMBOLS = {
    "positive": "+",
    "negative": "−",
    "tradeoff": "±",
    "observed": "•",
    "unknown": "?",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_demo_bundle(run_dir: Path) -> dict[str, Any]:
    required = {
        "case": run_dir / "02_case.json",
        "papers": run_dir / "04_papers.jsonl",
        "provenance": run_dir / "04_retrieval_provenance.json",
        "evidence": run_dir / "06_evidence.jsonl",
        "validation": run_dir / "06_evidence_validation.json",
        "decision": run_dir / "07_decision.json",
        "brief": run_dir / "08_investigation_brief.md",
    }
    missing = [str(path) for key, path in required.items() if not path.exists() and key != "brief"]
    if missing:
        raise FileNotFoundError("missing demo artifacts: " + ", ".join(missing))

    output_eval_path = run_dir / "09_output_evaluation.json"
    e2e_eval_path = run_dir / "10_end_to_end_evaluation.json"

    return {
        "run_dir": run_dir,
        "case": load_json(required["case"]),
        "papers": load_jsonl(required["papers"]),
        "provenance": load_json(required["provenance"]),
        "evidence": load_jsonl(required["evidence"]),
        "validation": load_json(required["validation"]),
        "decision": load_json(required["decision"]),
        "brief": required["brief"].read_text(encoding="utf-8") if required["brief"].exists() else "",
        "output_evaluation": load_json(output_eval_path) if output_eval_path.exists() else None,
        "end_to_end_evaluation": load_json(e2e_eval_path) if e2e_eval_path.exists() else None,
    }


def build_matrix_rows(case: dict[str, Any], decision: dict[str, Any]) -> list[dict[str, str]]:
    constraints = case.get("constraints", [])
    rows: list[dict[str, str]] = []
    for approach in decision.get("approaches", []):
        row: dict[str, str] = {"Approach": str(approach.get("approach", ""))}
        constraint_map = approach.get("constraints", {})
        for constraint in constraints:
            cid = str(constraint.get("id", ""))
            name = str(constraint.get("name", cid))
            cell = constraint_map.get(cid, {})
            symbol = STATUS_SYMBOLS.get(str(cell.get("status", "unknown")), "?")
            paper_ids = cell.get("paper_ids") or []
            row[f"{cid} {name}"] = f"{symbol} ({','.join(paper_ids)})" if paper_ids else symbol
        rows.append(row)
    return rows


def flatten_evidence(evidence_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for doc in evidence_docs:
        paper_id = doc.get("paper_id")
        paper_title = doc.get("paper_title")
        for item in doc.get("evidence", []):
            rows.append(
                {
                    "evidence_id": item.get("evidence_id"),
                    "paper_id": paper_id,
                    "paper_title": paper_title,
                    "approach": item.get("approach"),
                    "kind": item.get("kind"),
                    "polarity": item.get("polarity"),
                    "constraint_ids": item.get("constraint_ids", []),
                    "claim": item.get("claim"),
                    "metrics": item.get("metrics", []),
                    "notes": item.get("notes"),
                }
            )
    return rows


def demo_metrics(bundle: dict[str, Any]) -> dict[str, int]:
    validation = bundle["validation"]
    decision = bundle["decision"]
    return {
        "papers": len(bundle["papers"]),
        "accepted_evidence_responses": int(validation.get("accepted_count", 0)),
        "validation_errors": int(validation.get("error_count", 0)),
        "approaches": len(decision.get("approaches", [])),
        "unknowns": len(decision.get("unknowns", [])),
        "hypotheses": len(decision.get("hypotheses", [])),
    }


def find_default_demo_run(project_root: Path) -> Path:
    final_run = project_root / "runs" / "hbm_thermal_e2e_final_2026-09-27"
    if final_run.exists():
        return final_run
    preferred = project_root / "runs" / "hbm_thermal_live_demo_2026-09-27"
    if preferred.exists():
        return preferred
    candidates = sorted((project_root / "runs").glob("*live_demo*")) if (project_root / "runs").exists() else []
    if not candidates:
        raise FileNotFoundError("no verified demo run found")
    return candidates[-1]

def load_retrieval_evaluation(project_root: Path) -> dict[str, Any]:
    comparison_path = project_root / "evals" / "retrieval" / "hbm_thermal_v1_vs_v2.json"
    v2_path = project_root / "evals" / "retrieval" / "history" / "hbm_thermal_v2_user_run_2026-09-27.json"
    if not comparison_path.exists() or not v2_path.exists():
        raise FileNotFoundError("retrieval evaluation artifacts are missing")
    return {
        "comparison": load_json(comparison_path),
        "v2": load_json(v2_path),
    }


def retrieval_comparison_rows(evaluation: dict[str, Any]) -> list[dict[str, str]]:
    comparison = evaluation["comparison"]
    labels = {
        "single_keyword": "Single keyword",
        "multi_query": "Multi-query + RRF",
        "semantic": "Semantic",
        "hybrid": "Hybrid + RRF",
    }
    rows: list[dict[str, str]] = []
    for key, label in labels.items():
        item = comparison.get("recall_at_20", {}).get(key, {})
        rows.append(
            {
                "Strategy": label,
                "V1 Recall@20": f"{float(item.get('v1', 0)) * 100:.1f}%",
                "V2 Recall@20": f"{float(item.get('v2', 0)) * 100:.1f}%",
                "Delta": f"{float(item.get('delta_pp', 0)):+.1f}%p",
            }
        )
    return rows


def retrieval_summary_metrics(evaluation: dict[str, Any]) -> dict[str, str]:
    comparison = evaluation["comparison"]
    source = comparison.get("source_coverage", {})
    best = comparison.get("best_observed_strategy", {})
    multi = comparison.get("recall_at_20", {}).get("multi_query", {})
    return {
        "source_coverage": f"{source.get('indexed', 0)}/{source.get('golden', 0)}",
        "with_abstract": f"{source.get('with_abstract', 0)}/{source.get('golden', 0)}",
        "multi_v1": f"{float(multi.get('v1', 0)) * 100:.1f}%",
        "multi_v2": f"{float(multi.get('v2', 0)) * 100:.1f}%",
        "multi_delta": f"{float(multi.get('delta_pp', 0)):+.1f}%p",
        "best_at_50": f"{float(best.get('recall_at_50', 0)) * 100:.1f}%",
    }



def load_output_evaluation_comparison(project_root: Path) -> dict[str, Any]:
    path = project_root / "evals" / "output" / "hbm_thermal_output_v1_vs_v2.json"
    if not path.exists():
        raise FileNotFoundError("output evaluation comparison artifact is missing")
    return load_json(path)


def output_comparison_rows(comparison: dict[str, Any]) -> list[dict[str, str]]:
    labels = {
        "citation_validity": "Citation validity",
        "constraint_precision": "Constraint precision",
        "constraint_recall": "Constraint recall",
        "constraint_f1": "Constraint F1",
        "numeric_precision": "Numeric precision",
        "numeric_recall": "Numeric recall",
        "hypothesis_traceability": "Hypothesis traceability",
    }
    rows: list[dict[str, str]] = []
    metrics = comparison.get("metrics", {})
    for key, label in labels.items():
        item = metrics.get(key, {})
        rows.append({
            "Metric": label,
            "V1": f"{float(item.get('v1', 0))*100:.1f}%",
            "V2": f"{float(item.get('v2', 0))*100:.1f}%",
            "Delta": f"{float(item.get('delta_pp', 0)):+.1f}%p",
        })
    return rows
