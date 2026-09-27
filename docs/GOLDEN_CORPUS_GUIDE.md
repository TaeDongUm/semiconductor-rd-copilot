# Golden Corpus Review Guide

`data/hbm_thermal_golden_candidates.jsonl`은 최종 정답 데이터가 아니라 사람이 검토할 후보 목록입니다.

## Review Procedure

각 후보에 대해 다음 네 가지만 확인합니다.

1. **Relevant**: HBM thermal-management 의사결정에 직접 또는 보조적으로 관련 있는가?
2. **Usable Evidence**: abstract 또는 접근 가능한 full text에서 실제 claim을 확인할 수 있는가?
3. **Constraint**: C1~C6 중 어떤 항목에 근거를 제공하는가?
4. **Caution**: 특정 package/process 조건에서만 성립하는 결과를 일반화하고 있지 않은가?

## Review Result

후보 JSON의 `review_status`를 다음 중 하나로 변경합니다.

- `accepted`: Golden Corpus에 사용
- `rejected`: 관련성이 낮거나 근거 확인 불가
- `abstract_only`: 관련성은 있으나 현재 abstract 수준에서만 확인
- `needs_full_text`: 핵심 claim 검증에 full text 확인 필요

MVP에서는 10개 후보를 모두 채택할 필요가 없습니다. **근거를 직접 설명할 수 있는 6~8편**만 남겨도 충분합니다.
