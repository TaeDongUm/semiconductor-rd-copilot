from pathlib import Path


def test_static_benchmark_page_contains_v1_and_v2_diagnostics():
    text = Path("demo/retrieval-benchmark.html").read_text(encoding="utf-8")
    assert "HBM Thermal Retrieval Benchmark V2" in text
    assert "V1 보존 결과" in text
    assert "Source Coverage" in text
    assert "Reciprocal Rank Fusion" in text
    assert "multi_query_rrf_v2" in text
    assert "hybrid_rrf_v2" in text
    assert "결과 JSON 저장" in text
    assert 'id="apiKey"' in text


def test_v1_baseline_is_preserved_as_immutable_history():
    text = Path("evals/retrieval/history/hbm_thermal_v1_user_run_2026-09-27.json").read_text(encoding="utf-8")
    assert '"benchmark_id": "HBM-THERMAL-RETRIEVAL-V1-USER-RUN"' in text
    assert '"recall_at_20": 0.2857142857142857' in text
    assert '"recall_at_20": 0.42857142857142855' in text


def test_v2_user_run_is_preserved_as_actual_history():
    text = Path("evals/retrieval/history/hbm_thermal_v2_user_run_2026-09-27.json").read_text(encoding="utf-8")
    assert '"benchmarkId": "HBM-THERMAL-RETRIEVAL-V2"' in text
    assert '"matched": 5' in text
    assert '"recall": 0.7142857142857143' in text
    assert '"matched": 6' in text
    assert '"recall": 0.8571428571428571' in text


def test_comparison_file_records_completed_v2_result():
    text = Path("evals/retrieval/hbm_thermal_v1_vs_v2.json").read_text(encoding="utf-8")
    assert '"status": "completed"' in text
    assert '"delta_pp": 42.85714285714286' in text
    assert '"name": "multi_query_rrf_v2"' in text
