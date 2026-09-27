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


def _quoted(term: str) -> str:
    cleaned = " ".join(term.strip().split())
    if not cleaned:
        raise ValueError("search term must not be empty")
    # Keep multi-word engineering concepts intact; single tokens do not need quotes.
    return f'"{cleaned}"' if " " in cleaned else cleaned


def _or_group(terms: list[str], limit: int) -> str:
    selected=[]
    seen=set()
    for term in terms:
        norm=" ".join(term.lower().split())
        if not norm or norm in seen:
            continue
        seen.add(norm)
        selected.append(_quoted(term))
        if len(selected)>=limit:
            break
    if not selected:
        raise ValueError("at least one search term is required")
    return f"({' OR '.join(selected)})" if len(selected)>1 else selected[0]


def generate_query_plan(case: EngineeringCase, max_keyword_queries: int = 12) -> QueryPlan:
    """Build a bounded, reviewable multi-query plan from an Engineering Case.

    V2 deliberately avoids requiring one exact problem phrase in every query.  The broad query
    combines domain aliases and problem vocabulary, while each constraint receives its own
    concept-family query.  This improves recall without inserting titles or terms learned from
    the Golden Corpus.
    """
    if max_keyword_queries < 2:
        raise ValueError("max_keyword_queries must be at least 2")

    domain_group = _or_group(case.domain_terms, limit=3)
    problem_group = _or_group(case.problem_terms, limit=4)
    queries: list[SearchQuery] = [
        SearchQuery("broad_boolean", f"{domain_group} AND {problem_group}"),
    ]

    # Each engineering constraint gets a query independent of the primary problem wording.
    # This catches relevant approaches whose titles/abstracts use different thermal vocabulary.
    for constraint in case.constraints:
        constraint_group = _or_group(constraint.search_terms, limit=4)
        queries.append(
            SearchQuery(
                "constraint_family",
                f"{domain_group} AND {constraint_group}",
                constraint.id,
            )
        )
        if len(queries) >= max_keyword_queries:
            break

    # If budget remains, add domain/problem pair queries.  These are generic aliases from the
    # case definition, not paper-title-derived keywords, so the benchmark remains non-leaky.
    for domain in case.domain_terms[1:]:
        if len(queries) >= max_keyword_queries:
            break
        for problem in case.problem_terms[1:]:
            if len(queries) >= max_keyword_queries:
                break
            queries.append(
                SearchQuery("alias_pair", f"{_quoted(domain)} AND {_quoted(problem)}")
            )

    return QueryPlan(
        keyword_queries=_unique_queries(queries)[:max_keyword_queries],
        semantic_query=case.semantic_query,
    )
