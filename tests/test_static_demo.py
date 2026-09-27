import unittest
from pathlib import Path

from src.export_static_demo import render_static_demo
from src.ui_data import (
    find_default_demo_run,
    load_demo_bundle,
    load_output_evaluation_comparison,
    load_retrieval_evaluation,
)

ROOT = Path(__file__).resolve().parents[1]


class StaticDemoTest(unittest.TestCase):
    def test_static_demo_contains_verified_results(self):
        bundle = load_demo_bundle(find_default_demo_run(ROOT))
        page = render_static_demo(bundle)
        self.assertIn("Semiconductor R&D Copilot", page)
        self.assertIn("HBM 적층 수 증가", page)
        self.assertIn("ECS-TTL embedded cooling", page)
        self.assertIn("Unknowns", page)
        self.assertIn("5", page)
        self.assertIn("AI Output Evaluation", page)
        self.assertIn("94.7%", page)
        self.assertIn("Overall Gate", page)

    def test_static_demo_contains_retrieval_v1_v2_evidence(self):
        bundle = load_demo_bundle(find_default_demo_run(ROOT))
        retrieval = load_retrieval_evaluation(ROOT)
        page = render_static_demo(bundle, retrieval)
        self.assertIn("Retrieval Evaluation · V1 → V2", page)
        self.assertIn("28.6%", page)
        self.assertIn("71.4%", page)
        self.assertIn("85.7%", page)

    def test_static_demo_contains_output_v1_v2_evidence(self):
        bundle = load_demo_bundle(find_default_demo_run(ROOT))
        comparison = load_output_evaluation_comparison(ROOT)
        page = render_static_demo(bundle, output_comparison=comparison)
        self.assertIn("AI Output Evaluation · V1 → V2", page)
        self.assertIn("77.8%", page)
        self.assertIn("94.4%", page)
        self.assertIn("FAIL", page)
        self.assertIn("PASS", page)


if __name__ == "__main__":
    unittest.main()
