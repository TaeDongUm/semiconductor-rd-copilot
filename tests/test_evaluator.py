import unittest

from src.evaluator import evaluate_case
from src.models import Claim, Evidence, InvestigationCase


class EvaluatorTest(unittest.TestCase):
    def base_case(self, claims):
        return InvestigationCase(
            case_id="TEST-001",
            problem_statement="HBM thermal investigation",
            constraints=("thermal",),
            paper_ids=("P1",),
            evidence=(
                Evidence(
                    evidence_id="E1",
                    paper_id="P1",
                    claim="Supported evidence",
                    source_text="Mock source",
                    constraint="thermal",
                    status="supported",
                ),
            ),
            claims=claims,
        )

    def test_supported_fact_passes(self):
        case = self.base_case(
            (Claim("C1", "Supported fact", "fact", ("E1",)),)
        )
        result = evaluate_case(case)
        self.assertTrue(result.citation_validity)
        self.assertEqual(result.unsupported_claim_count, 0)

    def test_fact_without_evidence_fails(self):
        case = self.base_case((Claim("C1", "Unsupported fact", "fact", ()),))
        result = evaluate_case(case)
        self.assertEqual(result.unsupported_claim_count, 1)
        self.assertFalse(result.passed)

    def test_missing_evidence_id_fails_citation_validation(self):
        case = self.base_case(
            (Claim("C1", "Bad citation", "fact", ("E999",)),)
        )
        result = evaluate_case(case)
        self.assertFalse(result.citation_validity)

    def test_hypothesis_can_exist_without_confirmed_fact_status(self):
        case = self.base_case(
            (Claim("C1", "Hypothesis: test a combined approach", "hypothesis", ()),)
        )
        result = evaluate_case(case)
        self.assertEqual(result.unsupported_claim_count, 0)
        self.assertTrue(result.hypothesis_labeling)


if __name__ == "__main__":
    unittest.main()
