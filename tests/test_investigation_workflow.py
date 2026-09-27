import json
import tempfile
import unittest
from pathlib import Path

from src.investigation_workflow import (
    accept_problem_decomposition,
    prepare_evidence_prompts,
    prepare_manual_problem_step,
    retrieve_for_run,
)
from src.openalex import OpenAlexClient


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

    def __call__(self, request, timeout=0):
        return FakeResponse(self.payloads.pop(0))


def decomposition_payload():
    return {
        "case_id": "manual-test",
        "title": "Manual test case",
        "problem_statement": "Investigate thermal limitations in stacked memory.",
        "semantic_query": "thermal limitations and reliability in stacked memory",
        "domain_terms": ["high bandwidth memory", "3D stacked DRAM", "stacked memory"],
        "problem_terms": ["thermal management", "heat accumulation", "thermal resistance"],
        "constraints": [
            {"id": "C1", "name": "Thermal performance", "search_terms": ["thermal resistance", "heat dissipation"]},
            {"id": "C2", "name": "Reliability", "search_terms": ["thermo-mechanical reliability", "thermal stress"]},
            {"id": "C3", "name": "Manufacturability", "search_terms": ["process integration", "manufacturing compatibility"]},
        ],
    }


def work_payload():
    return {
        "id": "https://openalex.org/W123",
        "title": "Example stacked-memory thermal paper",
        "doi": "https://doi.org/10.1234/test",
        "publication_year": 2025,
        "cited_by_count": 5,
        "relevance_score": 12.0,
        "abstract_inverted_index": {"Thermal": [0], "performance": [1], "improves": [2]},
        "open_access": {"is_oa": True},
        "best_oa_location": {"landing_page_url": "https://example.org"},
        "primary_location": {"source": {"display_name": "Example Journal"}},
        "authorships": [],
    }


class InvestigationWorkflowTests(unittest.TestCase):
    def test_prepare_and_accept_manual_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            prompt = prepare_manual_problem_step("HBM thermal problem", run_dir)
            self.assertTrue(prompt.exists())
            self.assertTrue((run_dir / "00_problem.txt").exists())

            response = run_dir / "response.json"
            response.write_text(json.dumps(decomposition_payload()), encoding="utf-8")
            case_path, query_path = accept_problem_decomposition(response, run_dir)
            self.assertTrue(case_path.exists())
            plan = json.loads(query_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(plan["keyword_queries"]), 5)

    def test_retrieve_and_prepare_evidence_prompts_with_fake_openalex(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            case_path = run_dir / "02_case.json"
            case_path.write_text(json.dumps(decomposition_payload()), encoding="utf-8")

            # query generator yields 9 keyword calls + 1 semantic call for this fixture.
            payloads = [{"results": [work_payload()]} for _ in range(10)]
            client = OpenAlexClient(opener=FakeOpener(payloads))
            papers = retrieve_for_run(case_path, run_dir, limit=10, client=client)
            self.assertTrue(papers.exists())
            rows = [line for line in papers.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)

            prompts = prepare_evidence_prompts(case_path, papers, run_dir)
            self.assertEqual(len(prompts), 1)
            text = prompts[0].read_text(encoding="utf-8")
            self.assertIn("Use ONLY the supplied source text", text)
            self.assertIn("Example stacked-memory thermal paper", text)


if __name__ == "__main__":
    unittest.main()
