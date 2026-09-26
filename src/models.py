from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ClaimType = Literal["fact", "inference", "hypothesis"]
EvidenceStatus = Literal["supported", "unsupported", "conflict", "unknown"]


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    paper_id: str
    claim: str
    source_text: str
    constraint: str
    status: EvidenceStatus = "supported"
    numeric_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str
    claim_type: ClaimType
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class InvestigationCase:
    case_id: str
    problem_statement: str
    constraints: tuple[str, ...]
    paper_ids: tuple[str, ...]
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)
    claims: tuple[Claim, ...] = field(default_factory=tuple)
