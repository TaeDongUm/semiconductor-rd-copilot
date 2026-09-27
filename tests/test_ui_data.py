import unittest
from pathlib import Path

from src.ui_data import build_matrix_rows, demo_metrics, find_default_demo_run, load_demo_bundle


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


if __name__ == "__main__":
    unittest.main()
