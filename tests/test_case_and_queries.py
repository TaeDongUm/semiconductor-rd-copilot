import json
import tempfile
import unittest
from pathlib import Path

from src.case_definition import load_case
from src.query_generator import generate_query_plan


class CaseAndQueryTests(unittest.TestCase):
    def write_case(self, payload):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(payload, tmp, ensure_ascii=False)
        tmp.close()
        return Path(tmp.name)

    def base_payload(self):
        return {
            "case_id": "TEST-CASE",
            "title": "Test Case",
            "problem_statement": "Investigate a semiconductor thermal problem.",
            "domain_terms": ["high bandwidth memory", "HBM", "3D stacked DRAM"],
            "problem_terms": ["thermal management", "thermal resistance"],
            "constraints": [
                {
                    "id": "C1",
                    "name": "Thermal",
                    "search_terms": ["thermal resistance", "hotspot"]
                }
            ]
        }

    def test_load_case_parses_constraints(self):
        path = self.write_case(self.base_payload())
        case = load_case(path)
        self.assertEqual(case.case_id, "TEST-CASE")
        self.assertEqual(case.constraints[0].id, "C1")
        self.assertEqual(case.constraints[0].search_terms[0], "thermal resistance")

    def test_new_constraint_automatically_adds_focused_query(self):
        payload = self.base_payload()
        payload["constraints"].append(
            {
                "id": "C7",
                "name": "Power",
                "search_terms": ["power consumption", "energy efficiency"]
            }
        )
        case = load_case(self.write_case(payload))
        plan = generate_query_plan(case)

        c7_queries = [q for q in plan.keyword_queries if q.constraint_id == "C7"]
        self.assertGreaterEqual(len(c7_queries), 1)
        self.assertTrue(any("power consumption" in q.query for q in c7_queries))

    def test_semantic_query_uses_problem_statement(self):
        case = load_case(self.write_case(self.base_payload()))
        plan = generate_query_plan(case)
        self.assertEqual(plan.semantic_query, case.semantic_query)


if __name__ == "__main__":
    unittest.main()


def test_query_plan_uses_boolean_concept_families_without_golden_title_leakage():
    payload = CaseAndQueryTests().base_payload()
    payload["constraints"].append({"id": "C2", "name": "Reliability", "search_terms": ["CTE mismatch", "warpage"]})
    path = CaseAndQueryTests().write_case(payload)
    plan = generate_query_plan(load_case(path), max_keyword_queries=6)
    text = "\n".join(q.query for q in plan.keyword_queries)
    assert " OR " in text
    assert " AND " in text
    assert "CTE mismatch" in text
    assert "plugged sidewall" not in text.lower()
