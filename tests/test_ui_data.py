import unittest
from pathlib import Path

from src.ui_data import (
    build_matrix_rows,
    demo_metrics,
    find_default_demo_run,
    load_demo_bundle,
    load_retrieval_evaluation,
    retrieval_comparison_rows,
    retrieval_summary_metrics,
)


ROOT = Path(__file__).resolve().parents[1]


class UiDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_dir = find_default_demo_run(ROOT)
        cls.bundle = load_demo_bundle(cls.run_dir)

    def test_verified_demo_bundle_loads(self):
        self.assertEqual(self.bundle["case"]["case_id"], "HBM-THERMAL-001")
        self.assertEqual(len(self.bundle["papers"]), 5)

    def test_demo_metrics_match_live_run(self):
        metrics = demo_metrics(self.bundle)
        self.assertEqual(metrics["papers"], 5)
        self.assertEqual(metrics["accepted_evidence_responses"], 5)
        self.assertEqual(metrics["validation_errors"], 0)
        self.assertEqual(metrics["approaches"], 4)
        self.assertEqual(metrics["unknowns"], 13)
        self.assertEqual(metrics["hypotheses"], 2)

    def test_matrix_keeps_unknowns_visible(self):
        rows = build_matrix_rows(self.bundle["case"], self.bundle["decision"])
        plugged = next(row for row in rows if row["Approach"] == "plugged sidewall")
        self.assertEqual(plugged["C4 Manufacturability"], "?")
        self.assertTrue(plugged["C1 Thermal performance"].startswith("+"))

    def test_retrieval_evaluation_loads_actual_user_run(self):
        evaluation = load_retrieval_evaluation(ROOT)
        summary = retrieval_summary_metrics(evaluation)
        self.assertEqual(summary["source_coverage"], "7/7")
        self.assertEqual(summary["multi_v1"], "28.6%")
        self.assertEqual(summary["multi_v2"], "71.4%")
        self.assertEqual(summary["multi_delta"], "+42.9%p")
        self.assertEqual(summary["best_at_50"], "85.7%")

    def test_retrieval_comparison_rows_keep_semantic_failure_visible(self):
        evaluation = load_retrieval_evaluation(ROOT)
        rows = retrieval_comparison_rows(evaluation)
        semantic = next(row for row in rows if row["Strategy"] == "Semantic")
        multi = next(row for row in rows if row["Strategy"] == "Multi-query + RRF")
        self.assertEqual(semantic["V2 Recall@20"], "14.3%")
        self.assertEqual(multi["V2 Recall@20"], "71.4%")


if __name__ == "__main__":
    unittest.main()
