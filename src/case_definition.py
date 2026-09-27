from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ConstraintDefinition:
    id: str
    name: str
    search_terms: tuple[str, ...]


@dataclass(frozen=True)
class EngineeringCase:
    case_id: str
    title: str
    problem_statement: str
    semantic_query: str
    domain_terms: tuple[str, ...]
    problem_terms: tuple[str, ...]
    constraints: tuple[ConstraintDefinition, ...]


def _non_empty_strings(values: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{field_name} must be a non-empty list")
    cleaned = tuple(str(value).strip() for value in values if str(value).strip())
    if not cleaned:
        raise ValueError(f"{field_name} must contain non-empty strings")
    return cleaned


def case_from_payload(payload: dict[str, Any]) -> EngineeringCase:
    if not isinstance(payload, dict):
        raise ValueError("case payload must be an object")

    required = ("case_id", "title", "problem_statement")
    for field in required:
        if not str(payload.get(field, "")).strip():
            raise ValueError(f"missing required field: {field}")

    constraints_raw = payload.get("constraints")
    if not isinstance(constraints_raw, list) or not constraints_raw:
        raise ValueError("constraints must be a non-empty list")

    constraints: list[ConstraintDefinition] = []
    seen_ids: set[str] = set()
    for item in constraints_raw:
        if not isinstance(item, dict):
            raise ValueError("each constraint must be an object")
        constraint_id = str(item.get("id", "")).strip()
        name = str(item.get("name", "")).strip()
        if not constraint_id or not name:
            raise ValueError("constraint id and name are required")
        if constraint_id in seen_ids:
            raise ValueError(f"duplicate constraint id: {constraint_id}")
        seen_ids.add(constraint_id)
        constraints.append(
            ConstraintDefinition(
                id=constraint_id,
                name=name,
                search_terms=_non_empty_strings(
                    item.get("search_terms"), f"constraints[{constraint_id}].search_terms"
                ),
            )
        )

    return EngineeringCase(
        case_id=str(payload["case_id"]).strip(),
        title=str(payload["title"]).strip(),
        problem_statement=str(payload["problem_statement"]).strip(),
        semantic_query=str(payload.get("semantic_query") or payload["problem_statement"]).strip(),
        domain_terms=_non_empty_strings(payload.get("domain_terms"), "domain_terms"),
        problem_terms=_non_empty_strings(payload.get("problem_terms"), "problem_terms"),
        constraints=tuple(constraints),
    )


def case_to_dict(case: EngineeringCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "title": case.title,
        "problem_statement": case.problem_statement,
        "semantic_query": case.semantic_query,
        "domain_terms": list(case.domain_terms),
        "problem_terms": list(case.problem_terms),
        "constraints": [
            {
                "id": item.id,
                "name": item.name,
                "search_terms": list(item.search_terms),
            }
            for item in case.constraints
        ],
    }


def load_case(path: Path) -> EngineeringCase:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return case_from_payload(payload)


def write_case(case: EngineeringCase, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(case_to_dict(case), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
