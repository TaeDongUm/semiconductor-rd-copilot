from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Callable, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class OpenAlexError(RuntimeError):
    """Raised when an OpenAlex request or response cannot be handled."""


@dataclass
class PaperRecord:
    openalex_id: str
    title: str
    doi: str | None
    publication_year: int | None
    cited_by_count: int
    relevance_score: float | None
    abstract: str | None
    is_oa: bool
    oa_url: str | None
    source_name: str | None
    authors: list[str]
    matched_queries: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    if not inverted_index:
        return None

    positioned_words: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for position in positions:
            positioned_words.append((position, word))

    if not positioned_words:
        return None

    positioned_words.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positioned_words)


def _normalize_doi(raw_doi: str | None) -> str | None:
    if not raw_doi:
        return None
    prefix = "https://doi.org/"
    return raw_doi[len(prefix):] if raw_doi.lower().startswith(prefix) else raw_doi


def normalize_work(work: dict, query: str) -> PaperRecord:
    open_access = work.get("open_access") or {}
    best_oa_location = work.get("best_oa_location") or {}
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}

    authors = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        display_name = author.get("display_name")
        if display_name:
            authors.append(display_name)

    return PaperRecord(
        openalex_id=work.get("id", ""),
        title=work.get("title") or "",
        doi=_normalize_doi(work.get("doi")),
        publication_year=work.get("publication_year"),
        cited_by_count=int(work.get("cited_by_count") or 0),
        relevance_score=work.get("relevance_score"),
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
        is_oa=bool(open_access.get("is_oa")),
        oa_url=best_oa_location.get("landing_page_url") or best_oa_location.get("pdf_url"),
        source_name=source.get("display_name"),
        authors=authors,
        matched_queries=[query],
    )


class OpenAlexClient:
    BASE_URL = "https://api.openalex.org/works"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: int = 20,
        opener: Callable = urlopen,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENALEX_API_KEY")
        self.timeout = timeout
        self.opener = opener

    def build_url(
        self,
        query: str,
        *,
        mode: str = "keyword",
        per_page: int = 10,
        open_access_only: bool = True,
        require_abstract: bool = True,
    ) -> str:
        if not 1 <= per_page <= 50:
            raise ValueError("per_page must be between 1 and 50")
        if mode not in {"keyword", "semantic"}:
            raise ValueError("mode must be 'keyword' or 'semantic'")

        search_key = "search.semantic" if mode == "semantic" else "search"
        filters: list[str] = []
        if require_abstract:
            filters.append("has_abstract:true")
        if open_access_only:
            filters.append("open_access.is_oa:true")

        params = {
            search_key: query,
            "per_page": per_page,
        }
        if mode == "keyword":
            params["sort"] = "relevance_score:desc"
        if filters:
            params["filter"] = ",".join(filters)
        if self.api_key:
            params["api_key"] = self.api_key

        return f"{self.BASE_URL}?{urlencode(params)}"

    def search(
        self,
        query: str,
        *,
        mode: str = "keyword",
        per_page: int = 10,
        open_access_only: bool = True,
    ) -> list[PaperRecord]:
        url = self.build_url(
            query,
            mode=mode,
            per_page=per_page,
            open_access_only=open_access_only,
        )
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "semiconductor-rd-copilot/0.1",
            },
        )

        try:
            with self.opener(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # network errors differ by runtime
            raise OpenAlexError(f"OpenAlex request failed: {exc}") from exc

        results = payload.get("results")
        if not isinstance(results, list):
            raise OpenAlexError("OpenAlex response does not contain a results list")

        return [normalize_work(work, query) for work in results]

    def search_many(
        self,
        queries: Iterable[str],
        *,
        mode: str = "keyword",
        per_query: int = 8,
        open_access_only: bool = True,
        limit: int = 20,
    ) -> list[PaperRecord]:
        merged: dict[str, PaperRecord] = {}

        for query in queries:
            for paper in self.search(
                query,
                mode=mode,
                per_page=per_query,
                open_access_only=open_access_only,
            ):
                key = paper.doi or paper.openalex_id
                if key not in merged:
                    merged[key] = paper
                    continue

                existing = merged[key]
                if query not in existing.matched_queries:
                    existing.matched_queries.append(query)
                if (paper.relevance_score or 0) > (existing.relevance_score or 0):
                    existing.relevance_score = paper.relevance_score

        ranked = sorted(
            merged.values(),
            key=lambda paper: (
                len(paper.matched_queries),
                paper.relevance_score or 0,
                paper.cited_by_count,
            ),
            reverse=True,
        )
        return ranked[:limit]
