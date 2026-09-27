import json
import unittest

from src.evidence_extraction import (
    EvidenceExtractionError,
    build_evidence_prompt,
    parse_extraction,
    validate_constraint_ids,
)


class EvidenceExtractionTests(unittest.TestCase):
    def setUp(self):
        self.case = {
            "case_id": "TEST",
            "problem_statement": "Investigate HBM thermal management.",
            "constraints": [
                {"id": "C1", "name": "Thermal performance"},
                {"id": "C3", "name": "Reliability"},
            ],
        }
        self.paper = {
            "candidate_id": "P01",
            "title": "Example paper",
            "doi": "10.0000/example",
        }

    def valid_payload(self):
        return {
            "paper_id": "P01",
            "paper_title": "Example paper",
            "doi": "10.0000/example",
            "problem_relevance": "Directly discusses thermal performance.",
            "approaches": ["hybrid bonding"],
            "evidence": [
                {
                    "evidence_id": "E-P01-01",
                    "paper_id": "P01",
                    "doi": "10.0000/example",
                    "source_scope": "abstract",
                    "source_locator": "abstract",
                    "approach": "hybrid bonding",
                    "kind": "finding",
                    "claim": "The reported approach improves thermal performance.",
                    "constraint_ids": ["C1"],
                    "support_level": "direct",
                    "polarity": "positive",
                    "metrics": [],
                    "notes": "",
                }
            ],
            "unresolved_questions": ["Long-term reliability is not established here."],
        }

    def test_prompt_forbids_outside_knowledge(self):
        prompt = build_evidence_prompt(
            case=self.case,
            paper=self.paper,
            source_text="Example source",
        )
        self.assertIn("Use ONLY the supplied source text", prompt)
        self.assertIn("C1: Thermal performance", prompt)
        self.assertIn("Return JSON only", prompt)

    def test_valid_extraction_parses(self):
        extraction = parse_extraction(self.valid_payload())
        self.assertEqual(extraction.paper_id, "P01")
        self.assertEqual(extraction.evidence[0].constraint_ids, ("C1",))

    def test_invalid_kind_fails(self):
        payload = self.valid_payload()
        payload["evidence"][0]["kind"] = "opinion"
        with self.assertRaises(EvidenceExtractionError):
            parse_extraction(json.dumps(payload))

    def test_invalid_constraint_is_detected(self):
        payload = self.valid_payload()
        payload["evidence"][0]["constraint_ids"] = ["C99"]
        extraction = parse_extraction(payload)
        self.assertEqual(validate_constraint_ids(extraction, ["C1", "C3"]), ["C99"])


class VerifiedSeedTests(unittest.TestCase):
    def test_verified_seed_is_parseable_and_uses_known_constraints(self):
        from pathlib import Path

        valid_ids = ["C1", "C2", "C3", "C4", "C5", "C6"]
        path = Path("data/evidence/hbm_thermal_verified_seed.jsonl")
        rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(rows), 7)
        for line in rows:
            extraction = parse_extraction(line)
            self.assertEqual(validate_constraint_ids(extraction, valid_ids), [])


if __name__ == "__main__":
    unittest.main()


def test_prompt_requires_constraint_coverage_check():
    from src.evidence_extraction import build_evidence_prompt
    prompt = build_evidence_prompt(
        case={"case_id":"T","problem_statement":"x","constraints":[{"id":"C1","name":"Thermal"}]},
        paper={"paper_id":"P1","title":"t","doi":"10.test/a"},
        source_text="thermal evidence",
    )
    assert "CONSTRAINT COVERAGE CHECK" in prompt
    assert "unsupported constraints must remain omitted/unknown" in prompt
