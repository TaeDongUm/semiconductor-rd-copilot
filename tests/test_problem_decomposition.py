import json
import unittest

from src.problem_decomposition import (
    ProblemDecompositionError,
    build_problem_decomposition_prompt,
    parse_problem_decomposition,
)


class ProblemDecompositionTests(unittest.TestCase):
    def payload(self):
        return {
            "case_id": "example-case",
            "title": "Example semiconductor problem",
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

    def test_prompt_emphasizes_retrieval_vocabulary_and_json(self):
        prompt = build_problem_decomposition_prompt("HBM thermal problem")
        self.assertIn("vocabulary quality matters", prompt)
        self.assertIn("paper titles/abstracts", prompt)
        self.assertIn("Return JSON only", prompt)

    def test_valid_payload_becomes_engineering_case(self):
        case = parse_problem_decomposition(self.payload())
        self.assertEqual(case.case_id, "example-case")
        self.assertEqual(len(case.constraints), 3)
        self.assertEqual(case.constraints[0].search_terms[1], "heat dissipation")

    def test_constraint_requires_multiple_search_terms(self):
        payload = self.payload()
        payload["constraints"][0]["search_terms"] = ["thermal resistance"]
        with self.assertRaises(ProblemDecompositionError):
            parse_problem_decomposition(payload)

    def test_too_few_constraints_fails(self):
        payload = self.payload()
        payload["constraints"] = payload["constraints"][:2]
        with self.assertRaises(ProblemDecompositionError):
            parse_problem_decomposition(json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
