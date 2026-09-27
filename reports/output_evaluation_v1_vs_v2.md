# AI Output Evaluation V1 → V2

## 동일 조건

- Golden Evidence: `data/evidence/hbm_thermal_verified_seed.jsonl`
- Retrieved papers: 동일 5편
- 변경점: Evidence Extraction Prompt에 `Constraint Coverage Check` 추가
- 원칙: 점수를 높이기 위해 source에 없는 constraint를 강제로 추가하지 않음

## 결과

| Metric | V1 | V2 | 변화 |
| --- | ---: | ---: | ---: |
| Citation validity | 100.0% | 100.0% | +0.0%p |
| Constraint precision | 100.0% | 100.0% | +0.0%p |
| **Constraint recall** | **77.8%** | **94.4%** | **+16.7%p** |
| Constraint F1 | 87.5% | 97.1% | +9.6%p |
| Numeric precision | 100.0% | 100.0% | +0.0%p |
| Numeric recall | 100.0% | 100.0% | +0.0%p |
| Hypothesis traceability | 100.0% | 100.0% | +0.0%p |
| Quality Gate | **FAIL** | **PASS** | - |

Constraint mapping 누락은 **4 → 1**, 근거 없는 mapping은 **0 → 0**입니다.

## 남은 1개 Miss

`10.1109/tcpmt.2022.3201673 → C4 Manufacturability`가 Golden에는 있으나 V2에서는 의도적으로 추가하지 않았습니다. 현재 extractor에 제공된 source text는 structural reliability와 package dimensions는 명시하지만 manufacturability를 직접 확정하지 않습니다. **Golden v1은 비교 공정성을 위해 수정하지 않고 유지**하며, benchmark 확대 전 사람이 이 label을 재검토합니다.
