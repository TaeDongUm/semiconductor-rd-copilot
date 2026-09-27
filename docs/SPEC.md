# MVP Specification

## Problem

공개 반도체 R&D 자료를 조사할 때 검색어 선택에 따라 발견되는 논문의 질이 크게 달라지고, 이후 AI 분석은 Retrieval 품질에 의존합니다.

본 프로젝트는 다음 흐름을 지원합니다.

`Engineering Problem → Constraints → Multi-query Retrieval → Evidence → Trade-off / Unknown → Hypothesis → Validation`

## Input

사용자는 특정 반도체 기술 문제를 입력합니다. HBM Thermal은 첫 Benchmark Case일 뿐 시스템의 고정 도메인이 아닙니다.

현재 Case 입력은 JSON으로 표현합니다.

- Problem statement
- Domain terms
- Problem terms
- Engineering constraints
- Constraint별 search terms

향후 LLM이 자연어 입력을 이 구조로 자동 변환합니다.

## Retrieval Principle

하나의 AI-generated query에 의존하지 않습니다.

- Keyword multi-query
- Semantic query
- Query 결과 merge / deduplication
- Golden Corpus가 존재하는 Case에서는 Recall@K 평가

## Expected Output

- Problem Map
- Engineering Constraints
- Retrieved Papers
- Evidence Units
- Approach × Constraint Matrix
- Conflicting Evidence
- Unknowns
- Candidate Hypotheses
- Next Validation
- Evaluation Result

## Roles

### AI
- 자연어 문제 구조화
- 검색 용어/동의어 보완
- Evidence 추출
- Trade-off 정리
- Hypothesis 생성

### Code
- Query Plan 생성/저장
- OpenAlex 호출
- 결과 통합/중복 제거
- Golden Recall@K
- Citation / Numeric / Schema / Unsupported Claim 평가

### Human
- 문제/Constraint 검토
- Golden Corpus 검토
- 기술적 타당성 최종 판단

## Guardrails

- Evidence 없는 효과를 사실처럼 표현하지 않음
- 논문에 없는 숫자를 생성하지 않음
- Unknown/Conflict를 숨기지 않음
- Hypothesis를 검증 결과처럼 표현하지 않음
- 실제 Fab/실험 데이터 없이 root cause 또는 성능 개선을 확정하지 않음
