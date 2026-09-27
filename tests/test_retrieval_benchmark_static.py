from pathlib import Path


def test_static_benchmark_page_contains_real_golden_and_strategies():
    text = Path("demo/retrieval-benchmark.html").read_text(encoding="utf-8")
    assert "HBM Thermal Retrieval Benchmark" in text
    assert "10.3390/electronics14132682" in text
    assert "multi_query_keyword" in text
    assert "search.semantic" in text
    assert "Recall@20" in text
    assert 'id="apiKey"' in text
    assert "retryAfter" in text


def test_benchmark_status_does_not_claim_unexecuted_results():
    text = Path("evals/retrieval/hbm_thermal_v1_status.json").read_text(encoding="utf-8")
    assert '"executed_in_build_environment": false' in text
    assert "Do not report Recall values" in text
