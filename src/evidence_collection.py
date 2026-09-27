from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .evidence_extraction import (
    EvidenceExtractionError,
    PaperExtraction,
    parse_extraction,
    validate_constraint_ids,
)


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    file: str = ""
    paper_id: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "file": self.file,
            "paper_id": self.paper_id,
        }


@dataclass(frozen=True)
class EvidenceCollectionResult:
    accepted: tuple[PaperExtraction, ...]
    rejected_files: tuple[str, ...]
    issues: tuple[ValidationIssue, ...]

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_count": len(self.accepted),
            "rejected_count": len(self.rejected_files),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "accepted_paper_ids": [item.paper_id for item in self.accepted],
            "rejected_files": list(self.rejected_files),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _normalize_doi(value: str) -> str:
    text = (value or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    return text.strip().rstrip("/")


def _read_json_response(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().lower() in {"```", "```json"}:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def build_expected_papers(papers_path: str | Path) -> dict[str, dict[str, str]]:
    rows = [
        json.loads(line)
        for line in Path(papers_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    expected: dict[str, dict[str, str]] = {}
    for index, paper in enumerate(rows, start=1):
        if not str(paper.get("abstract") or "").strip():
            continue
        paper_id = f"R{index:02d}"
        expected[paper_id] = {
            "title": str(paper.get("title") or "").strip(),
            "doi": str(paper.get("doi") or paper.get("openalex_id") or "").strip(),
        }
    return expected


def _validate_extraction(
    extraction: PaperExtraction,
    *,
    filename: str,
    valid_constraint_ids: Iterable[str],
    expected_paper: dict[str, str] | None,
    seen_evidence_ids: set[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    paper_id = extraction.paper_id

    stem = Path(filename).stem
    if stem and stem != paper_id:
        issues.append(
            ValidationIssue(
                "error",
                "paper_id_filename_mismatch",
                f"filename '{stem}' does not match payload paper_id '{paper_id}'",
                filename,
                paper_id,
            )
        )

    if expected_paper is not None:
        expected_doi = _normalize_doi(expected_paper.get("doi", ""))
        actual_doi = _normalize_doi(extraction.doi)
        if expected_doi and actual_doi and expected_doi != actual_doi:
            issues.append(
                ValidationIssue(
                    "error",
                    "doi_mismatch",
                    f"payload DOI '{extraction.doi}' does not match retrieved paper DOI '{expected_paper.get('doi', '')}'",
                    filename,
                    paper_id,
                )
            )

    invalid_constraints = validate_constraint_ids(extraction, valid_constraint_ids)
    if invalid_constraints:
        issues.append(
            ValidationIssue(
                "error",
                "unknown_constraint",
                f"unknown constraint ids: {', '.join(invalid_constraints)}",
                filename,
                paper_id,
            )
        )

    approach_names = {item.strip().lower() for item in extraction.approaches if item.strip()}
    for evidence in extraction.evidence:
        if evidence.paper_id != paper_id:
            issues.append(
                ValidationIssue(
                    "error",
                    "nested_paper_id_mismatch",
                    f"evidence {evidence.evidence_id} references paper_id '{evidence.paper_id}' instead of '{paper_id}'",
                    filename,
                    paper_id,
                )
            )
        if _normalize_doi(evidence.doi) != _normalize_doi(extraction.doi):
            issues.append(
                ValidationIssue(
                    "error",
                    "nested_doi_mismatch",
                    f"evidence {evidence.evidence_id} DOI differs from extraction DOI",
                    filename,
                    paper_id,
                )
            )
        if evidence.evidence_id in seen_evidence_ids:
            issues.append(
                ValidationIssue(
                    "error",
                    "duplicate_evidence_id",
                    f"duplicate evidence_id '{evidence.evidence_id}'",
                    filename,
                    paper_id,
                )
            )
        if evidence.role == "approach" and evidence.approach.strip().lower() not in approach_names:
            issues.append(
                ValidationIssue(
                    "warning",
                    "approach_not_listed",
                    f"evidence approach '{evidence.approach}' is not listed in top-level approaches",
                    filename,
                    paper_id,
                )
            )

    return issues


def collect_evidence_responses(
    *,
    response_dir: str | Path,
    case: dict[str, Any],
    expected_papers: dict[str, dict[str, str]] | None = None,
) -> EvidenceCollectionResult:
    response_path = Path(response_dir)
    valid_constraint_ids = [
        str(item.get("id"))
        for item in case.get("constraints", [])
        if isinstance(item, dict) and item.get("id")
    ]
    expected_papers = expected_papers or {}

    accepted: list[PaperExtraction] = []
    rejected: list[str] = []
    issues: list[ValidationIssue] = []
    seen_evidence_ids: set[str] = set()

    files = sorted(path for path in response_path.glob("*.json") if path.is_file())
    for path in files:
        try:
            extraction = parse_extraction(_read_json_response(path))
        except (EvidenceExtractionError, OSError) as exc:
            rejected.append(path.name)
            issues.append(
                ValidationIssue(
                    "error",
                    "invalid_response",
                    str(exc),
                    path.name,
                    "",
                )
            )
            continue

        expected = expected_papers.get(extraction.paper_id)
        if expected_papers and expected is None:
            current_issues = [
                ValidationIssue(
                    "error",
                    "unexpected_paper",
                    f"paper_id '{extraction.paper_id}' is not present in the retrieved-paper manifest",
                    path.name,
                    extraction.paper_id,
                )
            ]
        else:
            current_issues = _validate_extraction(
                extraction,
                filename=path.name,
                valid_constraint_ids=valid_constraint_ids,
                expected_paper=expected,
                seen_evidence_ids=seen_evidence_ids,
            )

        issues.extend(current_issues)
        has_error = any(issue.severity == "error" for issue in current_issues)
        if has_error:
            rejected.append(path.name)
            continue

        accepted.append(extraction)
        seen_evidence_ids.update(item.evidence_id for item in extraction.evidence)

    if expected_papers:
        accepted_ids = {item.paper_id for item in accepted}
        rejected_ids = {issue.paper_id for issue in issues if issue.paper_id}
        for paper_id in expected_papers:
            if paper_id not in accepted_ids and paper_id not in rejected_ids:
                issues.append(
                    ValidationIssue(
                        "warning",
                        "missing_response",
                        f"no evidence response was supplied for '{paper_id}'",
                        "",
                        paper_id,
                    )
                )

    return EvidenceCollectionResult(
        accepted=tuple(accepted),
        rejected_files=tuple(dict.fromkeys(rejected)),
        issues=tuple(issues),
    )


def write_evidence_jsonl(extractions: Iterable[PaperExtraction], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(item.to_dict(), ensure_ascii=False) for item in extractions]
    output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def write_validation_report(result: EvidenceCollectionResult, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
