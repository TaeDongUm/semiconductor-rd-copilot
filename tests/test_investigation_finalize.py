import json
import tempfile
import unittest
from pathlib import Path

from src.investigation_workflow import finalize_manual_evidence


class InvestigationFinalizeTests(unittest.TestCase):
    def payload(self):
        return {
            "paper_id": "R01",
            "paper_title": "HBM Paper",
            "doi": "10.1000/hbm",
            "problem_relevance": "Relevant to HBM thermal performance.",
            "approaches": ["hybrid bonding"],
            "evidence": [
                {
                    "evidence_id": "E-R01-01",
                    "paper_id": "R01",
                    "doi": "10.1000/hbm",
                    "source_scope": "abstract",
                    "source_locator": "abstract",
                    "approach": "hybrid bonding",
                    "role": "approach",
                    "kind": "finding",
                    "claim": "Thermal performance improves under the reported setup.",
                    "constraint_ids": ["C1"],
                    "support_level": "direct",
                    "polarity": "positive",
                    "metrics": [],
                    "notes": "",
                }
            ],
            "unresolved_questions": ["Manufacturability remains unverified."],
        }

    def test_finalize_builds_evidence_decision_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = {
                "case_id": "CASE-1",
                "title": "Test Case",
                "problem_statement": "Investigate HBM thermal management.",
                "constraints": [
                    {"id": "C1", "name": "Thermal performance"},
                    {"id": "C2", "name": "Manufacturability"},
                ],
            }
            case_path = root / "02_case.json"
            case_path.write_text(json.dumps(case), encoding="utf-8")

            papers_path = root / "04_papers.jsonl"
            papers_path.write_text(
                json.dumps(
                    {
                        "title": "HBM Paper",
                        "doi": "10.1000/hbm",
                        "abstract": "Abstract text",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            responses = root / "06_evidence_responses"
            responses.mkdir()
            (responses / "R01.json").write_text(
                json.dumps(self.payload()), encoding="utf-8"
            )

            outputs = finalize_manual_evidence(case_path, papers_path, responses, root)

            self.assertEqual(outputs["accepted_count"], 1)
            self.assertTrue((root / "06_evidence.jsonl").exists())
            self.assertTrue((root / "06_evidence_validation.json").exists())
            self.assertTrue((root / "07_decision.json").exists())
            self.assertTrue((root / "08_investigation_brief.md").exists())
            report = (root / "08_investigation_brief.md").read_text(encoding="utf-8")
            self.assertIn("hybrid bonding", report)
            self.assertIn("Candidate Hypotheses", report)


if __name__ == "__main__":
    unittest.main()
