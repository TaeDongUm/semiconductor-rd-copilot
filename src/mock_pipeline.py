from __future__ import annotations

from .evaluator import evaluate_case
from .models import Claim, Evidence, InvestigationCase


def build_sample_case() -> InvestigationCase:
    evidence = (
        Evidence(
            evidence_id="E1",
            paper_id="P1",
            claim="Stacked memory architectures introduce thermal-management constraints.",
            source_text="Mock evidence for pipeline validation only.",
            constraint="thermal",
            status="supported",
        ),
        Evidence(
            evidence_id="E2",
            paper_id="P2",
            claim="Manufacturing trade-offs require further validation.",
            source_text="Mock evidence for pipeline validation only.",
            constraint="manufacturability",
            status="unknown",
        ),
    )

    claims = (
        Claim(
            claim_id="C1",
            text="Thermal management is a primary investigation constraint.",
            claim_type="fact",
            evidence_ids=("E1",),
        ),
        Claim(
            claim_id="C2",
            text=(
                "Hypothesis: an approach that improves the thermal path should be evaluated "
                "together with manufacturability constraints."
            ),
            claim_type="hypothesis",
            evidence_ids=("E1", "E2"),
        ),
    )

    return InvestigationCase(
        case_id="HBM-MOCK-001",
        problem_statement=(
            "Investigate thermal-management approaches for increasingly stacked HBM while "
            "considering reliability, manufacturability, and cost."
        ),
        constraints=("thermal", "reliability", "manufacturability", "cost"),
        paper_ids=("P1", "P2"),
        evidence=evidence,
        claims=claims,
    )


def main() -> None:
    case = build_sample_case()
    result = evaluate_case(case)

    print("=== Semiconductor R&D Copilot / Mock Run ===")
    print(f"Case: {case.case_id}")
    print(f"Problem: {case.problem_statement}")
    print(f"Constraints: {', '.join(case.constraints)}")
    print("\nClaims:")
    for claim in case.claims:
        print(f"- [{claim.claim_type.upper()}] {claim.text}")

    print("\nEvaluation:")
    print(f"- schema_pass: {result.schema_pass}")
    print(f"- citation_validity: {result.citation_validity}")
    print(f"- unsupported_claim_count: {result.unsupported_claim_count}")
    print(f"- hypothesis_labeling: {result.hypothesis_labeling}")
    print(f"- unknown_preservation: {result.unknown_preservation}")
    print(f"- conflict_preservation: {result.conflict_preservation}")
    print(f"\nOverall: {'PASS' if result.passed else 'FAIL'}")


if __name__ == "__main__":
    main()
