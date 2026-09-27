import json
from pathlib import Path

from src.output_evaluation import evaluate_output


def _jsonl(path: str):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def test_live_output_v1_detects_high_precision_but_missing_constraint_coverage():
    golden = _jsonl('data/evidence/hbm_thermal_verified_seed.jsonl')
    actual = _jsonl('runs/hbm_thermal_live_demo_2026-09-27/06_evidence.jsonl')
    decision = json.loads(Path('runs/hbm_thermal_live_demo_2026-09-27/07_decision.json').read_text())

    result = evaluate_output(golden=golden, actual=actual, decision=decision)

    assert result.citation_validity == 1.0
    assert result.constraint_precision == 1.0
    assert round(result.constraint_recall, 4) == 0.7778
    assert result.unsupported_constraint_mappings == 0
    assert result.missed_constraint_mappings == 4
    assert result.numeric_precision == 1.0
    assert result.numeric_recall == 1.0
    assert result.hypothesis_traceability == 1.0
    assert result.deterministic_gate == 'FAIL'


def test_output_evaluator_catches_unsupported_constraint_mapping():
    golden = [{
        'doi': '10.test/a',
        'evidence': [{'constraint_ids': ['C1'], 'metrics': []}],
    }]
    actual = [{
        'doi': '10.test/a',
        'evidence': [{'constraint_ids': ['C1', 'C9'], 'metrics': []}],
    }]
    decision = {'hypotheses': []}

    result = evaluate_output(golden=golden, actual=actual, decision=decision, case_id='T')
    assert result.constraint_precision == 0.5
    assert result.unsupported_constraint_mappings == 1
    assert ('10.test/a', 'C9') in result.extra_pairs


def test_output_evaluator_catches_numeric_hallucination():
    golden = [{
        'doi': '10.test/a',
        'evidence': [{'constraint_ids': ['C1'], 'metrics': [{'name': 'temperature reduction', 'value': '>13%'}]}],
    }]
    actual = [{
        'doi': '10.test/a',
        'evidence': [{'constraint_ids': ['C1'], 'metrics': [{'name': 'temperature reduction', 'value': '>30%'}]}],
    }]
    decision = {'hypotheses': []}

    result = evaluate_output(golden=golden, actual=actual, decision=decision, case_id='T')
    assert result.numeric_precision == 0.0
    assert result.numeric_recall == 0.0
    assert result.deterministic_gate == 'FAIL'


def test_live_output_v2_improves_constraint_coverage_without_precision_loss():
    golden = _jsonl('data/evidence/hbm_thermal_verified_seed.jsonl')
    actual = _jsonl('runs/hbm_thermal_output_v2_2026-09-27/06_evidence.jsonl')
    decision = json.loads(Path('runs/hbm_thermal_output_v2_2026-09-27/07_decision.json').read_text())

    result = evaluate_output(golden=golden, actual=actual, decision=decision)

    assert result.citation_validity == 1.0
    assert result.constraint_precision == 1.0
    assert round(result.constraint_recall, 4) == 0.9444
    assert round(result.constraint_f1, 4) == 0.9714
    assert result.unsupported_constraint_mappings == 0
    assert result.missed_constraint_mappings == 1
    assert ('10.1109/tcpmt.2022.3201673', 'C4') in result.missed_pairs
    assert result.numeric_precision == 1.0
    assert result.numeric_recall == 1.0
    assert result.hypothesis_traceability == 1.0
    assert result.deterministic_gate == 'PASS'
