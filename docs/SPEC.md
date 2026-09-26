# MVP Specification

## 1. Problem Statement

반도체 R&D에서는 하나의 기술적 문제를 해결하기 위해 여러 논문과 기술 접근을 조사하고, 각 접근이 성능·신뢰성·제조성·비용 등의 제약조건에 어떤 영향을 주는지 비교해야 합니다.

공개 정보만 사용할 수 있는 개인 개발 환경에서는 실제 Fab 장비나 기업 내부 데이터를 활용할 수 없습니다. 따라서 본 MVP는 공개 연구 근거를 이용해 **기술 조사 및 의사결정 공간을 구조화하는 과정**을 지원합니다.

## 2. MVP Case

HBM 적층 증가에 따른 Thermal Management 문제를 대표 사례로 사용합니다.

예시 입력:

> HBM의 적층 수가 증가하면서 package 내부 heat accumulation과 thermal resistance가 증가한다. 성능을 유지하면서 reliability, manufacturability, cost를 함께 고려할 수 있는 thermal management 접근을 조사하고 싶다.

## 3. Expected Output

최종 결과는 하나의 '정답 기술'이 아니라 다음 항목을 포함한 Investigation Brief입니다.

- Problem Map
- Engineering Constraints
- Relevant Evidence
- Existing Approaches
- Approach × Constraint Matrix
- Conflicting Evidence
- Unknowns
- Candidate Hypotheses
- Next Validation
- Evaluation Result

## 4. AI Responsibilities

AI가 맡을 수 있는 작업:

- 자연어 문제 구조화
- 검색 query 생성
- 논문/초록에서 구조화된 Evidence 추출
- 접근법 간 관계 및 trade-off 정리
- 근거 기반 Candidate Hypothesis 생성
- 최종 자연어 Brief 작성

## 5. Code Responsibilities

코드가 우선 담당할 작업:

- JSON Schema/필수 필드 검증
- Paper ID / DOI / Citation 존재 여부 확인
- Numeric claim과 evidence 숫자 일치 확인
- Evidence 없는 Claim 탐지
- 허용된 Claim type 확인
- Eval case 자동 판정

## 6. Human Responsibilities

사람이 최종적으로 담당할 작업:

- 기술 문제 정의가 적절한지 판단
- Golden Corpus와 핵심 Evidence 검토
- 상충 근거의 의미 해석
- Hypothesis의 실제 기술적 타당성 검토
- 최종 의사결정

## 7. Guardrails

다음 행위는 금지합니다.

- Evidence가 없는 효과를 사실처럼 표현
- 논문에 없는 수치 생성
- Hypothesis를 검증된 결과처럼 표현
- 상충 Evidence를 숨기거나 임의로 통합
- 실제 공정 데이터 없이 physical root cause 확정
- 실제 실험 없이 성능/수율 개선을 달성했다고 주장

## 8. Initial Evaluation Criteria

초기 MVP는 다음 항목을 자동 평가합니다.

- `schema_pass`
- `citation_validity`
- `unsupported_claim_count`
- `hypothesis_labeling`
- `unknown_preservation`
- `conflict_preservation`

## 9. MVP Done Criteria

HBM Thermal 문제 1개에 대해 다음 흐름이 끊기지 않고 동작하면 MVP로 간주합니다.

`Input → Structured Problem → Evidence → Matrix → Unknown/Conflict → Hypothesis → Evaluation → Brief`
