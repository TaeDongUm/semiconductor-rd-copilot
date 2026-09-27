import unittest

from src.decision_synthesis import group_approaches, synthesize
from src.evidence_extraction import EvidenceRecord, PaperExtraction


class DecisionSynthesisTests(unittest.TestCase):
    def setUp(self):
        self.case = {
            "case_id": "CASE-1",
            "constraints": [
                {"id": "C1", "name": "Thermal"},
                {"id": "C2", "name": "Reliability"},
                {"id": "C3", "name": "Cost"},
            ],
        }

    def record(self, evidence_id, approach, constraint, polarity, kind="finding", paper_id="P1", role="approach"):
        return EvidenceRecord(
            evidence_id=evidence_id,
            paper_id=paper_id,
            doi="10.0000/example",
            source_scope="abstract",
            source_locator="abstract",
            approach=approach,
            kind=kind,
            claim="claim",
            constraint_ids=(constraint,),
            support_level="direct",
            polarity=polarity,
            role=role,
        )

    def extraction(self, *records):
        return PaperExtraction(
            paper_id="P1",
            paper_title="Paper",
            doi="10.0000/example",
            problem_relevance="Relevant",
            approaches=tuple({record.approach for record in records}),
            evidence=tuple(records),
            unresolved_questions=("What is the manufacturing cost?",),
        )

    def test_similar_hybrid_bonding_names_are_grouped(self):
        records = [
            self.record("E1", "hybrid bonding", "C1", "positive"),
            self.record("E2", "chip-to-wafer hybrid bonding", "C2", "negative"),
        ]
        groups = group_approaches(records)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0][1]), 2)

    def test_missing_constraint_becomes_unknown(self):
        extraction = self.extraction(
            self.record("E1", "hybrid bonding", "C1", "positive")
        )
        result = synthesize(self.case, [extraction])
        row = result.approaches[0]
        self.assertEqual(row.cells["C1"].status, "positive")
        self.assertEqual(row.cells["C3"].status, "unknown")

    def test_direct_positive_and_negative_becomes_conflict(self):
        extraction = self.extraction(
            self.record("E1", "hybrid bonding", "C2", "positive", paper_id="P1"),
            self.record("E2", "chip-to-wafer hybrid bonding", "C2", "negative", paper_id="P2"),
        )
        result = synthesize(self.case, [extraction])
        self.assertEqual(result.approaches[0].cells["C2"].status, "conflict")
        self.assertEqual(len(result.conflicts), 1)

    def test_tradeoff_is_not_promoted_to_positive(self):
        extraction = self.extraction(
            self.record("E1", "embedded cooling", "C1", "mixed", kind="tradeoff")
        )
        result = synthesize(self.case, [extraction])
        self.assertEqual(result.approaches[0].cells["C1"].status, "tradeoff")

    def test_hypothesis_requires_benefit_and_unknown(self):
        extraction = self.extraction(
            self.record("E1", "embedded cooling", "C1", "positive")
        )
        result = synthesize(self.case, [extraction])
        self.assertEqual(len(result.hypotheses), 1)
        self.assertIn("remains unverified", result.hypotheses[0].text)
        self.assertIn("E1", result.hypotheses[0].basis_evidence_ids)

    def test_paper_unresolved_question_is_preserved(self):
        extraction = self.extraction(
            self.record("E1", "embedded cooling", "C1", "positive")
        )
        result = synthesize(self.case, [extraction])
        self.assertIn("What is the manufacturing cost?", result.next_validations)

    def test_context_evidence_is_preserved_but_excluded_from_matrix(self):
        extraction = self.extraction(
            self.record("E0", "problem context", "C1", "negative", role="context"),
            self.record("E1", "hybrid bonding", "C1", "positive"),
        )
        result = synthesize(self.case, [extraction])
        self.assertEqual(len(result.context_evidence), 1)
        self.assertEqual(len(result.approaches), 1)
        self.assertEqual(result.approaches[0].approach, "hybrid bonding")


if __name__ == "__main__":
    unittest.main()
