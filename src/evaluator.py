from __future__ import annotations

from dataclasses import dataclass

from .models import InvestigationCase


@dataclass(frozen=True)
class EvaluationResult:
    schema_pass: bool
    citation_validity: bool
    unsupported_claim_count: int
    hypothesis_labeling: bool
    unknown_preservation: bool
    conflict_preservation: bool

    @property
    def passed(self) -> bool:
        return all(
            (
                self.schema_pass,
                self.citation_validity,
                self.unsupported_claim_count == 0,
                self.hypothesis_labeling,
                self.unknown_preservation,
                self.conflict_preservation,
            )
        )


def evaluate_case(case: InvestigationCase) -> EvaluationResult:
    evidence_by_id = {item.evidence_id: item for item in case.evidence}

    schema_pass = bool(
        case.case_id
        and case.problem_statement.strip()
        and case.constraints
        and case.paper_ids
    )

    referenced_ids = {
        evidence_id
        for claim in case.claims
        for evidence_id in claim.evidence_ids
    }
    citation_validity = referenced_ids.issubset(evidence_by_id.keys())

    unsupported_claim_count = 0
    for claim in case.claims:
        if claim.claim_type == "hypothesis":
            continue
        if not claim.evidence_ids:
            unsupported_claim_count += 1
            continue
        referenced = [
            evidence_by_id[eid]
            for eid in claim.evidence_ids
            if eid in evidence_by_id
        ]
        if not referenced or all(item.status == "unsupported" for item in referenced):
            unsupported_claim_count += 1

    hypothesis_labeling = all(
        not (
            "hypothesis" in claim.text.lower()
            and claim.claim_type != "hypothesis"
        )
        for claim in case.claims
    )

    unknown_exists = any(item.status == "unknown" for item in case.evidence)
    unknown_preservation = unknown_exists or all(
        "unknown" not in claim.text.lower() for claim in case.claims
    )

    conflict_exists = any(item.status == "conflict" for item in case.evidence)
    conflict_preservation = conflict_exists or all(
        "conflict" not in claim.text.lower() for claim in case.claims
    )

    return EvaluationResult(
        schema_pass=schema_pass,
        citation_validity=citation_validity,
        unsupported_claim_count=unsupported_claim_count,
        hypothesis_labeling=hypothesis_labeling,
        unknown_preservation=unknown_preservation,
        conflict_preservation=conflict_preservation,
    )
