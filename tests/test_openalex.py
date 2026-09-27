import json
import unittest
from urllib.parse import parse_qs, urlparse

from src.openalex import OpenAlexClient, normalize_work, reconstruct_abstract


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeOpener:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def __call__(self, request, timeout=0):
        self.calls.append((request.full_url, timeout))
        return FakeResponse(self.payloads.pop(0))


def sample_work(title="HBM Thermal Study", doi="https://doi.org/10.1234/example"):
    return {
        "id": "https://openalex.org/W123",
        "title": title,
        "doi": doi,
        "publication_year": 2025,
        "cited_by_count": 10,
        "relevance_score": 42.5,
        "abstract_inverted_index": {
            "HBM": [0],
            "thermal": [1],
            "management": [2],
        },
        "open_access": {"is_oa": True},
        "best_oa_location": {"landing_page_url": "https://example.org/paper"},
        "primary_location": {"source": {"display_name": "Example Journal"}},
        "authorships": [
            {"author": {"display_name": "Alice Kim"}},
            {"author": {"display_name": "Bob Lee"}},
        ],
    }


class OpenAlexTests(unittest.TestCase):
    def test_reconstruct_abstract_orders_words_by_position(self):
        inverted = {"thermal": [1], "HBM": [0], "problem": [2]}
        self.assertEqual(reconstruct_abstract(inverted), "HBM thermal problem")

    def test_build_url_contains_search_filters_and_api_key(self):
        client = OpenAlexClient(api_key="test-key")
        url = client.build_url("HBM thermal management", per_page=7)
        params = parse_qs(urlparse(url).query)

        self.assertEqual(params["search"], ["HBM thermal management"])
        self.assertEqual(params["per_page"], ["7"])
        self.assertEqual(params["api_key"], ["test-key"])
        self.assertIn("has_abstract:true", params["filter"][0])
        self.assertIn("open_access.is_oa:true", params["filter"][0])

    def test_normalize_work_reconstructs_metadata(self):
        paper = normalize_work(sample_work(), "query one")

        self.assertEqual(paper.doi, "10.1234/example")
        self.assertEqual(paper.abstract, "HBM thermal management")
        self.assertEqual(paper.authors, ["Alice Kim", "Bob Lee"])
        self.assertTrue(paper.is_oa)
        self.assertEqual(paper.matched_queries, ["query one"])

    def test_search_many_deduplicates_same_doi_and_tracks_queries(self):
        opener = FakeOpener([
            {"results": [sample_work()]},
            {"results": [sample_work()]},
        ])
        client = OpenAlexClient(opener=opener)

        papers = client.search_many(["query one", "query two"], per_query=3, limit=10)

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].matched_queries, ["query one", "query two"])
        self.assertEqual(len(opener.calls), 2)

    def test_semantic_mode_uses_semantic_search_parameter(self):
        client = OpenAlexClient()
        url = client.build_url("long engineering problem", mode="semantic")
        params = parse_qs(urlparse(url).query)

        self.assertIn("search.semantic", params)
        self.assertNotIn("search", params)
        self.assertNotIn("sort", params)


if __name__ == "__main__":
    unittest.main()
