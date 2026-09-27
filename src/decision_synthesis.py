from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .evidence_extraction import EvidenceRecord, PaperExtraction, parse_extraction


@dataclass(frozen=True)
class MatrixCell:
    status: str
    evidence_ids: tuple[str, ...]
    paper_ids: tuple[str, ...]
    note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "evidence_ids": list(self.evidence_ids),
            "paper_ids": list(self.paper_ids),
            "note": self.note,
        }


@dataclass(frozen=True)
class ApproachSummary:
    approach: str
    aliases: tuple[str, ...]
    cells: dict[str, MatrixCell]

    def to_dict(self) -> dict[str, Any]:
        return {
            "approach": self.approach,
            "aliases": list(self.aliases),
            "constraints": {
                key: value.to_dict() for key, value in self.cells.items()
            },
        }


@dataclass(frozen=True)
class CandidateHypothesis:
    hypothesis_id: str
    text: str
    basis_evidence_ids: tuple[str, ...]
    unknown_constraint_ids: tuple[str, ...]
    validation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {
            "basis_evidence_ids": list(self.basis_evidence_ids),
            "unknown_constraint_ids": list(self.unknown_constraint_ids),
        }


@dataclass(frozen=True)
class DecisionSynthesis:
    case_id: str
    context_evidence: tuple[dict[str, Any], ...]
    approaches: tuple[ApproachSummary, ...]
    conflicts: tuple[dict[str, Any], ...]
    unknowns: tuple[dict[str, Any], ...]
    hypotheses: tuple[CandidateHypothesis, ...]
    next_validations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "context_evidence": list(self.context_evidence),
            "approaches": [item.to_dict() for item in self.approaches],
            "conflicts": list(self.conflicts),
            "unknowns": list(self.unknowns),
            "hypotheses": [item.to_dict() for item in self.hypotheses],
            "next_validations": list(self.next_validations),
        }


_STOPWORDS = {
    "and",
    "for",
    "of",
    "the",
    "with",
    "to",
    "a",
    "an",
    "process",
    "integration",
    "optimization",
    "structure",
}


def _tokens(text: str) -> set[str]:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return {token for token in normalized.split() if token and token not in _STOPWORDS}


def _similarity(a: str, b: str) -> float:
    left = _tokens(a)
    right = _tokens(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def group_approaches(records: Iterable[EvidenceRecord], threshold: float = 0.34) -> list[tuple[str, list[EvidenceRecord], list[str]]]:
    groups: list[dict[str, Any]] = []
    for record in records:
        best_index = None
        best_score = 0.0
        for index, group in enumerate(groups):
            score = max(_similarity(record.approach, alias) for alias in group["aliases"])
            if score > best_score:
                best_score = score
                best_index = index
        if best_index is not None and best_score >= threshold:
            group = groups[best_index]
            group["records"].append(record)
            if record.approach not in group["aliases"]:
                group["aliases"].append(record.approach)
        else:
            groups.append(
                {
                    "canonical": record.approach,
                    "aliases": [record.approach],
                    "records": [record],
                }
            )

    output: list[tuple[str, list[EvidenceRecord], list[str]]] = []
    for group in groups:
        aliases = sorted(group["aliases"], key=lambda x: (len(x), x.lower()))
        canonical = aliases[0]
        output.append((canonical, group["records"], aliases))
    return sorted(output, key=lambda item: item[0].lower())


def _cell_status(records: list[EvidenceRecord]) -> tuple[str, str]:
    if not records:
        return "unknown", "No verified evidence is linked to this constraint."

    polarities = {record.polarity for record in records}
    kinds = {record.kind for record in records}
    direct_polarities = {
        record.polarity for record in records if record.support_level == "direct"
    }

    if "positive" in direct_polarities and "negative" in direct_polarities:
        return "conflict", "Direct verified evidence contains both positive and negative findings."
    if "tradeoff" in kinds or "mixed" in polarities:
        return "tradeoff", "Evidence indicates a trade-off or mixed effect."
    if "negative" in polarities and "positive" not in polarities:
        return "negative", "Verified evidence reports a downside or adverse effect."
    if "positive" in polarities and "negative" not in polarities:
        return "positive", "Verified evidence reports a benefit for this constraint."
    if "unknown" in kinds:
        return "unknown", "The source explicitly leaves this point unresolved."
    return "observed", "Verified evidence is relevant but does not support a directional conclusion."


def _constraint_map(case: dict[str, Any]) -> dict[str, str]:
    return {
        item["id"]: item["name"]
        for item in case.get("constraints", [])
        if isinstance(item, dict) and item.get("id") and item.get("name")
    }


def synthesize(case: dict[str, Any], extractions: Iterable[PaperExtraction]) -> DecisionSynthesis:
    extraction_list = list(extractions)
    records = [record for extraction in extraction_list for record in extraction.evidence]
    context_records = [record for record in records if record.role == "context"]
    approach_records = [record for record in records if record.role == "approach"]
    constraints = _constraint_map(case)

    context_evidence = tuple(
        {
            "evidence_id": record.evidence_id,
            "paper_id": record.paper_id,
            "claim": record.claim,
            "constraint_ids": list(record.constraint_ids),
        }
        for record in context_records
    )
    approaches: list[ApproachSummary] = []
    conflicts: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    hypotheses: list[CandidateHypothesis] = []
    next_validations: list[str] = []

    for approach, group_records, aliases in group_approaches(approach_records):
        cells: dict[str, MatrixCell] = {}
        positive_constraints: list[str] = []
        unknown_constraints: list[str] = []
        basis_evidence: list[str] = []

        for constraint_id, constraint_name in constraints.items():
            matched = [
                record for record in group_records if constraint_id in record.constraint_ids
            ]
            status, note = _cell_status(matched)
            evidence_ids = tuple(dict.fromkeys(record.evidence_id for record in matched))
            paper_ids = tuple(dict.fromkeys(record.paper_id for record in matched))
            cells[constraint_id] = MatrixCell(
                status=status,
                evidence_ids=evidence_ids,
                paper_ids=paper_ids,
                note=note,
            )

            if status == "positive":
                positive_constraints.append(constraint_id)
                basis_evidence.extend(evidence_ids)
            if status == "unknown":
                unknown_constraints.append(constraint_id)
                unknowns.append(
                    {
                        "approach": approach,
                        "constraint_id": constraint_id,
                        "constraint": constraint_name,
                        "reason": note,
                    }
                )
            if status == "conflict":
                conflicts.append(
                    {
                        "approach": approach,
                        "constraint_id": constraint_id,
                        "constraint": constraint_name,
                        "evidence_ids": list(evidence_ids),
                        "paper_ids": list(paper_ids),
                    }
                )

        approaches.append(
            ApproachSummary(
                approach=approach,
                aliases=tuple(aliases),
                cells=cells,
            )
        )

        # Generate only validation hypotheses: a verified benefit + unresolved constraints.
        if positive_constraints and unknown_constraints:
            benefit_names = ", ".join(constraints[item] for item in positive_constraints[:2])
            unknown_names = ", ".join(constraints[item] for item in unknown_constraints[:3])
            hypothesis_id = f"H{len(hypotheses) + 1:02d}"
            hypotheses.append(
                CandidateHypothesis(
                    hypothesis_id=hypothesis_id,
                    text=(
                        f"{approach} shows verified evidence of benefit for {benefit_names}, "
                        f"but its suitability for this case remains unverified for {unknown_names}."
                    ),
                    basis_evidence_ids=tuple(dict.fromkeys(basis_evidence)),
                    unknown_constraint_ids=tuple(unknown_constraints),
                    validation=(
                        f"Collect direct evidence or design a simulation/experiment that evaluates "
                        f"{approach} against {unknown_names} under the target HBM conditions."
                    ),
                )
            )

    for conflict in conflicts:
        next_validations.append(
            f"Resolve conflicting evidence for {conflict['approach']} × {conflict['constraint']} by comparing study conditions and evidence scope."
        )

    # Prefer validations that close gaps around approaches with demonstrated benefits.
    for hypothesis in hypotheses[:5]:
        next_validations.append(hypothesis.validation)

    # Preserve paper-level unresolved questions as investigation items.
    unresolved_seen: set[str] = set()
    for extraction in extraction_list:
        for question in extraction.unresolved_questions:
            cleaned = question.strip()
            if cleaned and cleaned not in unresolved_seen:
                unresolved_seen.add(cleaned)
                next_validations.append(cleaned)

    return DecisionSynthesis(
        case_id=str(case.get("case_id") or ""),
        context_evidence=context_evidence,
        approaches=tuple(approaches),
        conflicts=tuple(conflicts),
        unknowns=tuple(unknowns),
        hypotheses=tuple(hypotheses),
        next_validations=tuple(dict.fromkeys(next_validations)),
    )


def load_case(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_extractions(path: str | Path) -> list[PaperExtraction]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(parse_extraction(line))
    return rows


def write_json(result: DecisionSynthesis, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _status_mark(status: str) -> str:
    return {
        "positive": "+",
        "negative": "−",
        "tradeoff": "±",
        "conflict": "CONFLICT",
        "observed": "•",
        "unknown": "?",
    }.get(status, status)


def render_markdown(case: dict[str, Any], result: DecisionSynthesis) -> str:
    constraints = _constraint_map(case)
    lines: list[str] = [
        f"# Investigation Brief — {case.get('title', result.case_id)}",
        "",
        "## Problem",
        "",
        str(case.get("problem_statement") or ""),
        "",
        "## Verified Problem Context",
        "",
    ]
    if result.context_evidence:
        for item in result.context_evidence:
            lines.append(f"- [{item['paper_id']}] {item['claim']}")
    else:
        lines.append("- No background-only evidence is registered.")

    lines.extend(["", "## Approach × Constraint Matrix", ""])

    headers = ["Approach", *[f"{cid} {name}" for cid, name in constraints.items()]]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for approach in result.approaches:
        row = [approach.approach]
        for constraint_id in constraints:
            cell = approach.cells[constraint_id]
            refs = ",".join(cell.paper_ids)
            label = _status_mark(cell.status)
            row.append(f"{label}{f' ({refs})' if refs else ''}")
        lines.append("| " + " | ".join(row) + " |")

    lines.extend(["", "Legend: `+` benefit, `−` downside, `±` trade-off, `•` relevant evidence without direction, `?` unknown.", ""])

    lines.extend(["## Conflicting Evidence", ""])
    if result.conflicts:
        for item in result.conflicts:
            lines.append(
                f"- **{item['approach']} × {item['constraint']}** — papers: {', '.join(item['paper_ids'])}"
            )
    else:
        lines.append("- No direct positive-vs-negative conflict was detected in the verified seed evidence.")

    lines.extend(["", "## Key Unknowns", ""])
    prioritized_unknowns = result.unknowns[:12]
    if prioritized_unknowns:
        for item in prioritized_unknowns:
            lines.append(
                f"- **{item['approach']} × {item['constraint']}** — {item['reason']}"
            )
    else:
        lines.append("- No unknown cells were detected.")

    lines.extend(["", "## Candidate Hypotheses", ""])
    if result.hypotheses:
        for item in result.hypotheses:
            evidence = ", ".join(item.basis_evidence_ids) or "none"
            lines.append(f"### {item.hypothesis_id}")
            lines.append("")
            lines.append(f"- Hypothesis: {item.text}")
            lines.append(f"- Basis evidence: {evidence}")
            lines.append(f"- Next validation: {item.validation}")
            lines.append("")
    else:
        lines.append("- No evidence-constrained validation hypothesis could be generated.")

    lines.extend(["", "## Next Validation", ""])
    for item in result.next_validations[:15]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Interpretation Rule",
            "",
            "This brief does not identify a best technology or a proven root cause. It narrows the investigation space using verified evidence and preserves unresolved constraints for human review.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown(case: dict[str, Any], result: DecisionSynthesis, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(case, result), encoding="utf-8")
