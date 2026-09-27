from __future__ import annotations

import json
import re
from typing import Any

from .case_definition import EngineeringCase, case_from_payload


class ProblemDecompositionError(ValueError):
    pass


def _slug(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return normalized[:48] or "engineering-case"


def build_problem_decomposition_prompt(problem_statement: str) -> str:
    problem = problem_statement.strip()
    if not problem:
        raise ValueError("problem_statement must not be empty")

    schema = {
        "case_id": "short-kebab-case-id",
        "title": "short English title",
        "problem_statement": "preserve the user's engineering problem without inventing facts",
        "semantic_query": "one natural-language search query describing the full technical problem",
        "domain_terms": ["canonical domain term", "important alias", "alternative technical name"],
        "problem_terms": ["primary problem term", "technical synonym", "related failure/limitation term"],
        "constraints": [
            {
                "id": "C1",
                "name": "engineering constraint",
                "search_terms": [
                    "canonical literature term",
                    "technical synonym",
                    "alternative expression used by papers",
                ],
            }
        ],
    }

    return f"""You are structuring a semiconductor engineering problem for literature retrieval.

GOAL
Convert the user's problem into a reviewable Engineering Case. The output will be used to generate multiple OpenAlex queries, so vocabulary quality matters.

RULES
1. Preserve the user's problem. Do not claim a physical cause, process condition, material property, or business effect that the user did not provide.
2. Constraints must be dimensions that should be checked when comparing technical approaches, not proposed solutions.
3. Create 3-7 constraints. Use concise engineering names.
4. For domain_terms, problem_terms, and each constraint.search_terms, include literature vocabulary and meaningful aliases rather than simple word repetition.
5. Prefer terms likely to appear in paper titles/abstracts. Include abbreviations and expanded forms when useful.
6. Do not create a constraint only because it sounds generally important. If its relevance is uncertain, omit it; the user can add it later.
7. semantic_query should be a full natural-language description for semantic retrieval, not a Boolean query.
8. Return JSON only. No markdown fences or explanation.

USER PROBLEM
---
{problem}
---

OUTPUT SCHEMA
{json.dumps(schema, ensure_ascii=False, indent=2)}
"""


def parse_problem_decomposition(payload: str | dict[str, Any]) -> EngineeringCase:
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ProblemDecompositionError(f"invalid JSON: {exc}") from exc
    else:
        data = payload

    if not isinstance(data, dict):
        raise ProblemDecompositionError("problem decomposition must be an object")

    if not str(data.get("case_id") or "").strip():
        title = str(data.get("title") or data.get("problem_statement") or "engineering-case")
        data = dict(data)
        data["case_id"] = _slug(title)

    try:
        case = case_from_payload(data)
    except ValueError as exc:
        raise ProblemDecompositionError(str(exc)) from exc

    if not 3 <= len(case.constraints) <= 7:
        raise ProblemDecompositionError("constraints must contain between 3 and 7 items")

    for constraint in case.constraints:
        if len(constraint.search_terms) < 2:
            raise ProblemDecompositionError(
                f"constraint {constraint.id} should include at least two search_terms"
            )

    return case
