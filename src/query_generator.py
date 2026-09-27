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


def generate_query_plan(case: EngineeringCase, max_keyword_queries: int = 12) -> QueryPlan:
    """Build a bounded multi-query plan from a reviewable Engineering Case.

    A decomposition model may propose vocabulary, but retrieval does not depend on one opaque
    generated query. Each constraint contributes at least one focused query and, when room is
    available, a vocabulary-expansion query using an alternative literature term.
    """
    if max_keyword_queries < 2:
        raise ValueError("max_keyword_queries must be at least 2")

    primary_domain = case.domain_terms[0]
    primary_problem = case.problem_terms[0]
    queries: list[SearchQuery] = [
        SearchQuery("broad", f'"{primary_domain}" "{primary_problem}"'),
    ]

    if len(case.domain_terms) > 1:
        queries.append(
            SearchQuery("domain_alias", f'"{case.domain_terms[1]}" "{primary_problem}"')
        )

    # First pass: every constraint must be represented.
    for constraint in case.constraints:
        focus = constraint.search_terms[0]
        queries.append(
            SearchQuery(
                "constraint",
                f'"{primary_domain}" "{primary_problem}" "{focus}"',
                constraint.id,
            )
        )

    # Second pass: use alternative literature vocabulary when the query budget allows it.
    for constraint in case.constraints:
        if len(queries) >= max_keyword_queries:
            break
        if len(constraint.search_terms) < 2:
            continue
        alias = constraint.search_terms[1]
        domain = case.domain_terms[1] if len(case.domain_terms) > 1 else primary_domain
        problem = case.problem_terms[1] if len(case.problem_terms) > 1 else primary_problem
        queries.append(
            SearchQuery(
                "constraint_alias",
                f'"{domain}" "{problem}" "{alias}"',
                constraint.id,
            )
        )

    # One broad vocabulary-expansion query catches terminology drift across subfields.
    if len(queries) < max_keyword_queries and len(case.domain_terms) > 2 and len(case.problem_terms) > 1:
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
