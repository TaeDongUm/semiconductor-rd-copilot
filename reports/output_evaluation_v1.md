# AI Output Evaluation V1

## 결과

| Metric | Result |
| --- | ---: |
| Evaluated retrieved papers | 5 |
| Citation validity | 100.0% |
| Constraint mapping precision | 100.0% |
| Constraint mapping recall | 77.8% |
| Constraint mapping F1 | 87.5% |
| Unsupported constraint mappings | 0 |
| Missed constraint mappings | 4 |
| Numeric precision | 100.0% |
| Numeric recall | 100.0% |
| Hypothesis traceability | 100.0% |
| Deterministic quality gate | **FAIL** |

## 놓친 Golden Constraint Mapping

- `10.1109/tcpmt.2022.3201673` → `C2`
- `10.1109/tcpmt.2022.3201673` → `C3`
- `10.1109/tcpmt.2022.3201673` → `C4`
- `10.5573/jsts.2026.26.2.97` → `C2`

## 근거 없이 추가된 Mapping

- 없음

## 해석

- 현재 출력은 **근거 없는 constraint를 추가하지 않는 precision은 높지만, source가 지원하는 constraint 일부를 놓쳐 recall이 부족**합니다.
- 이 평가는 Retrieval 이후 단계만 측정합니다. 논문 검색 Recall은 별도 Retrieval Benchmark에서 관리합니다.
- 자유문장 의미가 원문과 완전히 동일한지까지 자동 판정하는 평가는 아닙니다. 현재 단계에서는 사람이 검토한 Golden Evidence의 DOI·constraint·numeric metric과 output traceability를 deterministic하게 비교합니다.

## 다음 개선 목표

Evidence Extraction Prompt에 `Constraint Coverage Check`를 추가해, source가 명시적으로 지원하는 constraint가 누락되지 않았는지 출력 직전에 한 번 더 확인합니다. 단, 근거가 없는 constraint를 채우도록 강제하지 않습니다.
