from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Literal

EvidenceKind = Literal["finding", "limitation", "tradeoff", "unknown"]
SupportLevel = Literal["direct", "indirect"]
Polarity = Literal["positive", "negative", "mixed", "neutral"]


@dataclass(frozen=True)
class Metric:
    name: str
    value: str
    unit: str | None = None
    comparison: str | None = None


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    paper_id: str
    doi: str
    source_scope: str
    source_locator: str
    approach: str
    kind: EvidenceKind
    claim: str
    constraint_ids: tuple[str, ...]
    support_level: SupportLevel
    polarity: Polarity
    metrics: tuple[Metric, ...] = ()
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["constraint_ids"] = list(self.constraint_ids)
        payload["metrics"] = [asdict(metric) for metric in self.metrics]
        return payload


@dataclass(frozen=True)
class PaperExtraction:
    paper_id: str
    paper_title: str
    doi: str
    problem_relevance: str
    approaches: tuple[str, ...]
    evidence: tuple[EvidenceRecord, ...]
    unresolved_questions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "paper_title": self.paper_title,
            "doi": self.doi,
            "problem_relevance": self.problem_relevance,
            "approaches": list(self.approaches),
            "evidence": [item.to_dict() for item in self.evidence],
            "unresolved_questions": list(self.unresolved_questions),
        }


class EvidenceExtractionError(ValueError):
    pass


def build_evidence_prompt(
    *,
    case: dict[str, Any],
    paper: dict[str, Any],
    source_text: str,
    source_scope: str = "abstract",
) -> str:
    constraints = case.get("constraints") or []
    constraint_lines = "\n".join(
        f'- {item["id"]}: {item["name"]}' for item in constraints
    )

    schema = {
        "paper_id": paper.get("paper_id") or paper.get("candidate_id") or "PXX",
        "paper_title": paper.get("title", ""),
        "doi": paper.get("doi", ""),
        "problem_relevance": "one-sentence relevance limited to supplied source",
        "approaches": ["approach name"],
        "evidence": [
            {
                "evidence_id": "E-<paper_id>-01",
                "paper_id": paper.get("paper_id") or paper.get("candidate_id") or "PXX",
                "doi": paper.get("doi", ""),
                "source_scope": source_scope,
                "source_locator": "abstract / section / page if known",
                "approach": "technology or method",
                "kind": "finding | limitation | tradeoff | unknown",
                "claim": "paraphrased claim supported by supplied source only",
                "constraint_ids": ["C1"],
                "support_level": "direct | indirect",
                "polarity": "positive | negative | mixed | neutral",
                "metrics": [
                    {
                        "name": "metric name",
                        "value": "value exactly supported by source",
                        "unit": "unit or null",
                        "comparison": "comparison baseline or null",
                    }
                ],
                "notes": "optional caveat",
            }
        ],
        "unresolved_questions": ["question that cannot be answered from supplied source"],
    }

    return f"""You are extracting evidence for a semiconductor R&D investigation.

RULES
1. Use ONLY the supplied source text. Do not use outside knowledge.
2. Do not turn correlation, simulation, or a limited experiment into a universal causal claim.
3. Do not invent numbers, materials, process conditions, reliability outcomes, or cost/yield effects.
4. If the source does not support a constraint, omit that constraint rather than guessing.
5. Distinguish findings from limitations/trade-offs. Use 'unknown' when the source cannot answer an important point.
6. Hypotheses are NOT requested here. This step only extracts evidence.
7. Keep claims concise and paraphrased. Do not copy long source passages.
8. Return JSON only, matching the schema exactly.

CASE
case_id: {case.get('case_id', '')}
problem: {case.get('problem_statement', '')}
constraints:
{constraint_lines}

PAPER
paper_id: {paper.get('paper_id') or paper.get('candidate_id') or ''}
title: {paper.get('title', '')}
doi: {paper.get('doi', '')}
source_scope: {source_scope}

SOURCE TEXT
---
{source_text.strip()}
---

OUTPUT SCHEMA
{json.dumps(schema, ensure_ascii=False, indent=2)}
"""


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EvidenceExtractionError(f"'{key}' must be a non-empty string")
    return value.strip()


def parse_extraction(payload: str | dict[str, Any]) -> PaperExtraction:
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise EvidenceExtractionError(f"invalid JSON: {exc}") from exc
    else:
        data = payload

    if not isinstance(data, dict):
        raise EvidenceExtractionError("extraction payload must be an object")

    paper_id = _require_string(data, "paper_id")
    paper_title = _require_string(data, "paper_title")
    doi = _require_string(data, "doi")
    problem_relevance = _require_string(data, "problem_relevance")

    approaches_raw = data.get("approaches") or []
    if not isinstance(approaches_raw, list) or not all(isinstance(x, str) for x in approaches_raw):
        raise EvidenceExtractionError("'approaches' must be a list of strings")

    evidence_raw = data.get("evidence") or []
    if not isinstance(evidence_raw, list):
        raise EvidenceExtractionError("'evidence' must be a list")

    allowed_kind = {"finding", "limitation", "tradeoff", "unknown"}
    allowed_support = {"direct", "indirect"}
    allowed_polarity = {"positive", "negative", "mixed", "neutral"}
    evidence: list[EvidenceRecord] = []

    for index, raw in enumerate(evidence_raw):
        if not isinstance(raw, dict):
            raise EvidenceExtractionError(f"evidence[{index}] must be an object")

        kind = _require_string(raw, "kind")
        support_level = _require_string(raw, "support_level")
        polarity = _require_string(raw, "polarity")
        if kind not in allowed_kind:
            raise EvidenceExtractionError(f"invalid kind: {kind}")
        if support_level not in allowed_support:
            raise EvidenceExtractionError(f"invalid support_level: {support_level}")
        if polarity not in allowed_polarity:
            raise EvidenceExtractionError(f"invalid polarity: {polarity}")

        constraints = raw.get("constraint_ids") or []
        if not isinstance(constraints, list) or not all(isinstance(x, str) for x in constraints):
            raise EvidenceExtractionError("constraint_ids must be a list of strings")

        metrics_raw = raw.get("metrics") or []
        if not isinstance(metrics_raw, list):
            raise EvidenceExtractionError("metrics must be a list")
        metrics: list[Metric] = []
        for metric in metrics_raw:
            if not isinstance(metric, dict):
                raise EvidenceExtractionError("metric must be an object")
            metrics.append(
                Metric(
                    name=_require_string(metric, "name"),
                    value=_require_string(metric, "value"),
                    unit=metric.get("unit"),
                    comparison=metric.get("comparison"),
                )
            )

        evidence.append(
            EvidenceRecord(
                evidence_id=_require_string(raw, "evidence_id"),
                paper_id=_require_string(raw, "paper_id"),
                doi=_require_string(raw, "doi"),
                source_scope=_require_string(raw, "source_scope"),
                source_locator=_require_string(raw, "source_locator"),
                approach=_require_string(raw, "approach"),
                kind=kind,  # type: ignore[arg-type]
                claim=_require_string(raw, "claim"),
                constraint_ids=tuple(constraints),
                support_level=support_level,  # type: ignore[arg-type]
                polarity=polarity,  # type: ignore[arg-type]
                metrics=tuple(metrics),
                notes=str(raw.get("notes") or ""),
            )
        )

    unresolved = data.get("unresolved_questions") or []
    if not isinstance(unresolved, list) or not all(isinstance(x, str) for x in unresolved):
        raise EvidenceExtractionError("unresolved_questions must be a list of strings")

    return PaperExtraction(
        paper_id=paper_id,
        paper_title=paper_title,
        doi=doi,
        problem_relevance=problem_relevance,
        approaches=tuple(approaches_raw),
        evidence=tuple(evidence),
        unresolved_questions=tuple(unresolved),
    )


def validate_constraint_ids(extraction: PaperExtraction, valid_ids: Iterable[str]) -> list[str]:
    valid = set(valid_ids)
    invalid: list[str] = []
    for item in extraction.evidence:
        for constraint_id in item.constraint_ids:
            if constraint_id not in valid and constraint_id not in invalid:
                invalid.append(constraint_id)
    return invalid
