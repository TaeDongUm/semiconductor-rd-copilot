from __future__ import annotations

import json
from pathlib import Path

from src.openalex import PaperRecord
from src.retrieval_benchmark import reciprocal_rank_fusion, run_benchmark, to_markdown


def paper(doi: str, title: str, query: str = "q", abstract: str | None = "abstract") -> PaperRecord:
    return PaperRecord(
        openalex_id=f"https://openalex.org/{doi.replace('/', '')}",
        title=title,
        doi=doi,
        publication_year=2025,
        cited_by_count=10,
        relevance_score=0.9,
        abstract=abstract,
        is_oa=False,
        oa_url=None,
        source_name="Journal",
        authors=["Author"],
        matched_queries=[query],
    )


class FakeClient:
    def __init__(self) -> None:
        self.calls = []
        self.coverage = {
            "10.1/a": paper("10.1/a", "A"),
            "10.1/b": paper("10.1/b", "B", abstract=None),
            # 10.1/c intentionally absent from OpenAlex source coverage
        }

    def get_work_by_doi(self, doi):
        self.calls.append(("lookup", doi))
        return self.coverage.get(doi.lower())

    def search(self, query, *, mode="keyword", per_page=10, open_access_only=True):
        self.calls.append(("search", mode, query, open_access_only, per_page))
        if mode == "semantic":
            return [paper("10.1/a", "A", query)]
        if query == '"high bandwidth memory" "thermal management"':
            return [paper("10.1/a", "A", query)]
        if "C2 term" in query:
            return [paper("10.1/b", "B", query), paper("10.9/x", "X", query)]
        return [paper("10.1/a", "A", query), paper("10.9/x", "X", query)]


def test_rrf_rewards_repeated_high_rank_results():
    a1 = paper("10.1/a", "A", "q1")
    b1 = paper("10.1/b", "B", "q1")
    b2 = paper("10.1/b", "B", "q2")
    c2 = paper("10.1/c", "C", "q2")
    fused, scores = reciprocal_rank_fusion([[a1, b1], [b2, c2]], limit=3, rrf_k=60)
    assert fused[0].doi == "10.1/b"
    assert scores["doi:10.1/b"] > scores["doi:10.1/a"]


def test_benchmark_separates_source_coverage_from_retrieval_miss(tmp_path: Path):
    case = {
        "case_id": "T-1",
        "title": "Test",
        "problem_statement": "problem",
        "domain_terms": ["high bandwidth memory", "HBM"],
        "problem_terms": ["thermal management", "thermal resistance"],
        "constraints": [
            {"id": "C1", "name": "Thermal", "search_terms": ["resistance", "hotspot"]},
            {"id": "C2", "name": "Integration", "search_terms": ["C2 term", "interconnect"]},
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
        ) + "\n",
        encoding="utf-8",
    )

    client = FakeClient()
    report = run_benchmark(
        case_path=case_path,
        golden_path=golden_path,
        k=3,
        per_query=3,
        max_keyword_queries=4,
        client=client,
    )

    by_name = {result.strategy: result for result in report.results}
    assert set(by_name) == {
        "single_keyword_v1_baseline",
        "multi_query_rrf_v2",
        "semantic",
        "hybrid_rrf_v2",
    }
    assert len(report.source_coverage) == 3
    assert sum(1 for x in report.source_coverage if x.indexed) == 2
    assert by_name["multi_query_rrf_v2"].matched_count == 2
    assert by_name["multi_query_rrf_v2"].recall_at_k == 2 / 3
    assert by_name["multi_query_rrf_v2"].conditional_recall_at_k == 1.0
    assert by_name["multi_query_rrf_v2"].source_unavailable_golden_ids == ("doi:10.1/c",)
    assert by_name["multi_query_rrf_v2"].retrieval_miss_golden_ids == ()
    assert all(call[3] is False for call in client.calls if call[0] == "search")

    markdown = to_markdown(report)
    assert "Source coverage" in markdown
    assert "indexed only" in markdown
