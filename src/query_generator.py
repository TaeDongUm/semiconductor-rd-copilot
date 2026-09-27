from __future__ import annotations

from dataclasses import dataclass

from .case_definition import EngineeringCase


@dataclass(frozen=True)
class SearchQuery:
    strategy: str
    query: str
    constraint_id: str | None = None


@dataclass(frozen=True)
class QueryPlan:
    keyword_queries: tuple[SearchQuery, ...]
    semantic_query: str


def _unique_queries(queries: list[SearchQuery]) -> tuple[SearchQuery, ...]:
    seen: set[str] = set()
    unique: list[SearchQuery] = []
    for item in queries:
        normalized = " ".join(item.query.lower().split())
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(item)
    return tuple(unique)


def generate_query_plan(case: EngineeringCase, max_keyword_queries: int = 10) -> QueryPlan:
    """Build a bounded multi-query plan from the case definition.

    This stage is intentionally deterministic. In a later step an LLM may populate or
    refine domain/problem/constraint search terms, but retrieval never depends on one
    opaque generated query.
    """
    if max_keyword_queries < 2:
        raise ValueError("max_keyword_queries must be at least 2")

    primary_domain = case.domain_terms[0]
    primary_problem = case.problem_terms[0]
    queries: list[SearchQuery] = [
        SearchQuery("broad", f'"{primary_domain}" {primary_problem}'),
    ]

    if len(case.domain_terms) > 1:
        queries.append(
            SearchQuery("domain_alias", f'"{case.domain_terms[1]}" {primary_problem}')
        )

    for constraint in case.constraints:
        # Every added constraint automatically contributes one focused query.
        focus = constraint.search_terms[0]
        queries.append(
            SearchQuery(
                "constraint",
                f'"{primary_domain}" {primary_problem} "{focus}"',
                constraint.id,
            )
        )

    # One vocabulary-expansion query helps catch papers using alternative domain/problem terms.
    if len(case.domain_terms) > 2 and len(case.problem_terms) > 1:
        queries.append(
            SearchQuery(
                "vocabulary_expansion",
                f'"{case.domain_terms[2]}" "{case.problem_terms[1]}"',
            )
        )

    return QueryPlan(
        keyword_queries=_unique_queries(queries)[:max_keyword_queries],
        semantic_query=case.semantic_query,
    )
