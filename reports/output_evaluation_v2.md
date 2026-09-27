# AI Output Evaluation V2

## 결과

| Metric | Result |
| --- | ---: |
| Evaluated retrieved papers | 5 |
| Citation validity | 100.0% |
| Constraint mapping precision | 100.0% |
| Constraint mapping recall | 94.4% |
| Constraint mapping F1 | 97.1% |
| Unsupported constraint mappings | 0 |
| Missed constraint mappings | 1 |
| Numeric precision | 100.0% |
| Numeric recall | 100.0% |
| Hypothesis traceability | 100.0% |
| Deterministic quality gate | **PASS** |

## 놓친 Golden Constraint Mapping

- `10.1109/tcpmt.2022.3201673` → `C4`

## 근거 없이 추가된 Mapping

- 없음

## 해석

- 현재 출력은 deterministic quality gate를 통과했습니다. 근거 없는 constraint를 추가하지 않는 precision을 유지하면서 Golden Evidence coverage를 확보했습니다.
- 남은 miss가 있다면 source wording과 Golden label을 사람이 다시 확인합니다. 점수를 높이기 위해 근거 없는 constraint를 강제로 채우지 않습니다.
- 이 평가는 Retrieval 이후 단계만 측정합니다. 논문 검색 Recall은 별도 Retrieval Benchmark에서 관리합니다.
- 자유문장 의미가 원문과 완전히 동일한지까지 자동 판정하는 평가는 아닙니다. 현재 단계에서는 사람이 검토한 Golden Evidence의 DOI·constraint·numeric metric과 output traceability를 deterministic하게 비교합니다.

## 다음 단계

현재 Prompt를 기준선으로 고정하고, 실제 End-to-End Run에서 동일 평가를 재사용합니다. Golden label이 source보다 강한 해석을 포함하는지도 별도로 점검합니다.
