import json
import tempfile
import unittest
from pathlib import Path

from src.evidence_collection import (
    build_expected_papers,
    collect_evidence_responses,
    write_evidence_jsonl,
)


class EvidenceCollectionTests(unittest.TestCase):
    def setUp(self):
        self.case = {
            "case_id": "CASE-1",
            "constraints": [
                {"id": "C1", "name": "Thermal performance"},
                {"id": "C2", "name": "Reliability"},
            ],
        }

    def payload(self, paper_id="R01", doi="10.1000/a", evidence_id="E-R01-01"):
        return {
            "paper_id": paper_id,
            "paper_title": "Paper A",
            "doi": doi,
            "problem_relevance": "Relevant",
            "approaches": ["hybrid bonding"],
            "evidence": [
                {
                    "evidence_id": evidence_id,
                    "paper_id": paper_id,
                    "doi": doi,
                    "source_scope": "abstract",
                    "source_locator": "abstract",
                    "approach": "hybrid bonding",
                    "role": "approach",
                    "kind": "finding",
                    "claim": "A supported finding.",
                    "constraint_ids": ["C1"],
                    "support_level": "direct",
                    "polarity": "positive",
                    "metrics": [],
                    "notes": "",
                }
            ],
            "unresolved_questions": ["Reliability remains unknown."],
        }

    def test_valid_response_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            response_dir = Path(tmp)
            (response_dir / "R01.json").write_text(
                json.dumps(self.payload()), encoding="utf-8"
            )
            result = collect_evidence_responses(
                response_dir=response_dir,
                case=self.case,
                expected_papers={"R01": {"title": "Paper A", "doi": "https://doi.org/10.1000/a"}},
            )
            self.assertEqual(len(result.accepted), 1)
            self.assertEqual(result.error_count, 0)

    def test_markdown_json_fence_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            response_dir = Path(tmp)
            text = "```json\n" + json.dumps(self.payload()) + "\n```\n"
            (response_dir / "R01.json").write_text(text, encoding="utf-8")
            result = collect_evidence_responses(
                response_dir=response_dir,
                case=self.case,
                expected_papers={"R01": {"title": "Paper A", "doi": "10.1000/a"}},
            )
            self.assertEqual(len(result.accepted), 1)

    def test_unknown_constraint_rejects_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            response_dir = Path(tmp)
            payload = self.payload()
            payload["evidence"][0]["constraint_ids"] = ["C99"]
            (response_dir / "R01.json").write_text(json.dumps(payload), encoding="utf-8")
            result = collect_evidence_responses(
                response_dir=response_dir,
                case=self.case,
                expected_papers={"R01": {"title": "Paper A", "doi": "10.1000/a"}},
            )
            self.assertEqual(len(result.accepted), 0)
            self.assertIn("unknown_constraint", [issue.code for issue in result.issues])

    def test_doi_mismatch_rejects_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            response_dir = Path(tmp)
            (response_dir / "R01.json").write_text(json.dumps(self.payload()), encoding="utf-8")
            result = collect_evidence_responses(
                response_dir=response_dir,
                case=self.case,
                expected_papers={"R01": {"title": "Paper A", "doi": "10.1000/different"}},
            )
            self.assertEqual(len(result.accepted), 0)
            self.assertIn("doi_mismatch", [issue.code for issue in result.issues])

    def test_duplicate_evidence_id_across_files_rejects_later_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            response_dir = Path(tmp)
            (response_dir / "R01.json").write_text(json.dumps(self.payload()), encoding="utf-8")
            second = self.payload("R02", "10.1000/b", "E-R01-01")
            (response_dir / "R02.json").write_text(json.dumps(second), encoding="utf-8")
            result = collect_evidence_responses(
                response_dir=response_dir,
                case=self.case,
                expected_papers={
                    "R01": {"title": "Paper A", "doi": "10.1000/a"},
                    "R02": {"title": "Paper B", "doi": "10.1000/b"},
                },
            )
            self.assertEqual(len(result.accepted), 1)
            self.assertIn("duplicate_evidence_id", [issue.code for issue in result.issues])

    def test_write_accepted_evidence_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            response_dir = Path(tmp) / "responses"
            response_dir.mkdir()
            (response_dir / "R01.json").write_text(json.dumps(self.payload()), encoding="utf-8")
            result = collect_evidence_responses(
                response_dir=response_dir,
                case=self.case,
                expected_papers={"R01": {"title": "Paper A", "doi": "10.1000/a"}},
            )
            output = Path(tmp) / "evidence.jsonl"
            write_evidence_jsonl(result.accepted, output)
            row = json.loads(output.read_text(encoding="utf-8").strip())
            self.assertEqual(row["paper_id"], "R01")

    def test_build_expected_papers_uses_same_r_ids_as_prompt_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "papers.jsonl"
            rows = [
                {"title": "No abstract", "doi": "10.0/skip", "abstract": ""},
                {"title": "Paper", "doi": "10.0/two", "abstract": "text"},
            ]
            path.write_text("\n".join(json.dumps(x) for x in rows) + "\n", encoding="utf-8")
            expected = build_expected_papers(path)
            self.assertNotIn("R01", expected)
            self.assertEqual(expected["R02"]["doi"], "10.0/two")


if __name__ == "__main__":
    unittest.main()
