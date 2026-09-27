from __future__ import annotations

import json
from pathlib import Path

from src.openalex import PaperRecord
from src.retrieval_benchmark import run_benchmark, to_markdown


def paper(doi: str, title: str, query: str = "q") -> PaperRecord:
    return PaperRecord(
        openalex_id=f"https://openalex.org/{doi}",
        title=title,
        doi=doi,
        publication_year=2025,
        cited_by_count=10,
        relevance_score=0.9,
        abstract="abstract",
        is_oa=False,
        oa_url=None,
        source_name="Journal",
        authors=["Author"],
        matched_queries=[query],
    )


class FakeClient:
    def __init__(self) -> None:
        self.calls = []

    def search(self, query, *, mode="keyword", per_page=10, open_access_only=True):
        self.calls.append(("search", mode, query, open_access_only))
        if mode == "semantic":
            return [
                paper("10.1/a", "A", query),
                paper("10.1/c", "C", query),
            ]
        return [paper("10.1/a", "A", query)]

    def search_many(self, queries, *, mode="keyword", per_query=8, open_access_only=True, limit=20):
        self.calls.append(("search_many", mode, tuple(queries), open_access_only))
        return [
            paper("10.1/a", "A", queries[0]),
            paper("10.1/b", "B", queries[1] if len(queries) > 1 else queries[0]),
        ]


def test_benchmark_compares_four_strategies_and_disables_oa_filter(tmp_path: Path):
    case = {
        "case_id": "T-1",
        "title": "Test",
        "problem_statement": "problem",
        "domain_terms": ["HBM", "stacked DRAM"],
        "problem_terms": ["thermal", "heat"],
        "constraints": [
            {"id": "C1", "name": "Thermal", "search_terms": ["resistance", "hotspot"]}
        ],
        "semantic_query": "semantic problem",
    }
    case_path = tmp_path / "case.json"
    case_path.write_text(json.dumps(case), encoding="utf-8")

    golden_path = tmp_path / "golden.jsonl"
    golden_path.write_text(
        "\n".join(
            [
                json.dumps({"doi": "10.1/a", "review_status": "accepted"}),
                json.dumps({"doi": "10.1/b", "review_status": "accepted"}),
                json.dumps({"doi": "10.1/c", "review_status": "accepted"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    client = FakeClient()
    report = run_benchmark(
        case_path=case_path,
        golden_path=golden_path,
        k=3,
        per_query=3,
        max_keyword_queries=3,
        client=client,
    )

    by_name = {result.strategy: result for result in report.results}
    assert set(by_name) == {
        "single_keyword",
        "multi_query_keyword",
        "semantic",
        "hybrid",
    }
    assert by_name["single_keyword"].recall_at_k == 1 / 3
    assert by_name["multi_query_keyword"].recall_at_k == 2 / 3
    assert by_name["semantic"].recall_at_k == 2 / 3
    assert by_name["hybrid"].recall_at_k == 1.0
    assert all(call[-1] is False for call in client.calls)

    markdown = to_markdown(report)
    assert "single_keyword" in markdown
    assert "100.0%" in markdown
