import json
import tempfile
import unittest
from pathlib import Path

from src.openalex import PaperRecord
from src.retrieval_eval import evaluate_retrieval, load_accepted_golden_ids


def paper(doi: str, title: str = "paper") -> PaperRecord:
    return PaperRecord(
        openalex_id="https://openalex.org/W1",
        title=title,
        doi=doi,
        publication_year=2025,
        cited_by_count=0,
        relevance_score=1.0,
        abstract="abstract",
        is_oa=True,
        oa_url=None,
        source_name=None,
        authors=[],
        matched_queries=["q"],
    )


class RetrievalEvalTests(unittest.TestCase):
    def test_only_accepted_candidates_are_loaded(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        tmp.write(json.dumps({"doi": "10.1/a", "review_status": "accepted"}) + "\n")
        tmp.write(json.dumps({"doi": "10.1/b", "review_status": "candidate"}) + "\n")
        tmp.close()

        ids = load_accepted_golden_ids(Path(tmp.name))
        self.assertEqual(ids, {"doi:10.1/a"})

    def test_recall_at_k(self):
        golden = {"doi:10.1/a", "doi:10.1/b"}
        result = evaluate_retrieval([paper("10.1/a"), paper("10.1/x")], golden, k=2)
        self.assertEqual(result.matched_count, 1)
        self.assertEqual(result.recall_at_k, 0.5)

    def test_empty_golden_returns_no_recall(self):
        result = evaluate_retrieval([paper("10.1/a")], set(), k=1)
        self.assertIsNone(result.recall_at_k)


if __name__ == "__main__":
    unittest.main()
