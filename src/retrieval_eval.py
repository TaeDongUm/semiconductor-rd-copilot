from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .openalex import PaperRecord


@dataclass(frozen=True)
class RetrievalEvaluation:
    golden_count: int
    retrieved_count: int
    matched_count: int
    recall_at_k: float | None


def _normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().lower()
    prefix = "https://doi.org/"
    if cleaned.startswith(prefix):
        cleaned = cleaned[len(prefix):]
    return cleaned or None


def load_accepted_golden_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    with path.open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("review_status") != "accepted":
                continue
            doi = _normalize_doi(item.get("doi"))
            openalex_id = str(item.get("openalex_id") or "").strip().lower()
            if doi:
                ids.add(f"doi:{doi}")
            elif openalex_id:
                ids.add(f"openalex:{openalex_id}")
    return ids


def _paper_identity(paper: PaperRecord) -> str:
    doi = _normalize_doi(paper.doi)
    if doi:
        return f"doi:{doi}"
    return f"openalex:{paper.openalex_id.strip().lower()}"


def evaluate_retrieval(
    papers: Iterable[PaperRecord], golden_ids: set[str], *, k: int = 20
) -> RetrievalEvaluation:
    top_k = list(papers)[:k]
    retrieved_ids = {_paper_identity(paper) for paper in top_k}
    matches = golden_ids & retrieved_ids
    recall = None if not golden_ids else len(matches) / len(golden_ids)
    return RetrievalEvaluation(
        golden_count=len(golden_ids),
        retrieved_count=len(top_k),
        matched_count=len(matches),
        recall_at_k=recall,
    )
