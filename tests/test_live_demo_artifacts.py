import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "hbm_thermal_live_demo_2026-09-27"


class LiveDemoArtifactTests(unittest.TestCase):
    def test_real_paper_demo_is_internally_consistent(self):
        summary = json.loads((RUN / "09_run_summary.json").read_text(encoding="utf-8"))
        validation = json.loads((RUN / "06_evidence_validation.json").read_text(encoding="utf-8"))
        decision = json.loads((RUN / "07_decision.json").read_text(encoding="utf-8"))

        self.assertEqual(summary["real_papers"], 5)
        self.assertEqual(validation["accepted_count"], 5)
        self.assertEqual(validation["error_count"], 0)
        self.assertGreaterEqual(len(decision["approaches"]), 3)
        self.assertGreaterEqual(len(decision["unknowns"]), 1)
        self.assertTrue((RUN / "08_investigation_brief.md").read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    unittest.main()
