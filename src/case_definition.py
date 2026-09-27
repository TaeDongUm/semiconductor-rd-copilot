from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


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


def _non_empty_strings(values, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{field_name} must be a non-empty list")
    cleaned = tuple(str(value).strip() for value in values if str(value).strip())
    if not cleaned:
        raise ValueError(f"{field_name} must contain non-empty strings")
    return cleaned


def load_case(path: Path) -> EngineeringCase:
    payload = json.loads(path.read_text(encoding="utf-8"))

    required = ("case_id", "title", "problem_statement")
    for field in required:
        if not str(payload.get(field, "")).strip():
            raise ValueError(f"missing required field: {field}")

    constraints_raw = payload.get("constraints")
    if not isinstance(constraints_raw, list) or not constraints_raw:
        raise ValueError("constraints must be a non-empty list")

    constraints = []
    for item in constraints_raw:
        if not isinstance(item, dict):
            raise ValueError("each constraint must be an object")
        constraint_id = str(item.get("id", "")).strip()
        name = str(item.get("name", "")).strip()
        if not constraint_id or not name:
            raise ValueError("constraint id and name are required")
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
