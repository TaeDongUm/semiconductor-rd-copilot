from __future__ import annotations

import argparse

from .decision_synthesis import (
    load_case,
    load_extractions,
    synthesize,
    write_json,
    write_markdown,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an evidence-constrained investigation brief.")
    parser.add_argument("--case", default="data/cases/hbm_thermal.json")
    parser.add_argument(
        "--evidence",
        default="data/evidence/hbm_thermal_verified_seed.jsonl",
    )
    parser.add_argument(
        "--json-output",
        default="data/decision/hbm_thermal_decision.json",
    )
    parser.add_argument(
        "--report-output",
        default="reports/hbm_thermal_investigation_brief.md",
    )
    args = parser.parse_args()

    case = load_case(args.case)
    extractions = load_extractions(args.evidence)
    result = synthesize(case, extractions)
    write_json(result, args.json_output)
    write_markdown(case, result, args.report_output)

    print(f"case: {result.case_id}")
    print(f"approaches: {len(result.approaches)}")
    print(f"conflicts: {len(result.conflicts)}")
    print(f"unknowns: {len(result.unknowns)}")
    print(f"hypotheses: {len(result.hypotheses)}")
    print(f"json: {args.json_output}")
    print(f"report: {args.report_output}")


if __name__ == "__main__":
    main()
