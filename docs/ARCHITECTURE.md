# Architecture

상세한 사용자 흐름은 [`PROJECT_FLOW.md`](PROJECT_FLOW.md)를 참고합니다.

## Current Flow

```text
Case JSON
  ↓
Deterministic Multi-query Generator
  ├─ Keyword Queries
  └─ Semantic Problem Query
  ↓
OpenAlex
  ↓
Merge / Deduplicate / Rank
  ↓
(Optional) Golden Corpus Recall@K
```

현재 단계에서는 LLM을 연결하기 전에 **검색 구조와 평가 구조를 분리해 검증**합니다.

## Case Definition

`data/cases/*.json`이 실행 입력입니다.

- `problem_statement`
- `domain_terms`
- `problem_terms`
- `constraints[]`
  - `id`
  - `name`
  - `search_terms`

HBM Thermal은 첫 번째 Benchmark Case이며 시스템 하드코딩이 아닙니다.

## Query Strategy

단일 검색어 대신 다음을 함께 사용합니다.

1. Broad keyword query
2. Domain alias query
3. Constraint별 focused query
4. Vocabulary expansion query
5. Problem statement semantic query

새 Constraint를 Case JSON에 추가하면 해당 Constraint의 focused query가 자동 생성됩니다.

향후 LLM은 `domain_terms`, `problem_terms`, `constraints`, `search_terms`를 자동 생성/보완하는 데 사용하며, 최종 Query Plan은 저장하여 사람이 확인 가능하게 합니다.

## Golden Corpus

Golden Corpus는 Retrieval을 위한 고정 DB가 아니라 Recall@K를 측정하는 버전 고정 Benchmark입니다.

현재 후보:

`evals/golden/hbm_thermal/v1/candidates.jsonl`

현재 모두 사람 검토 전이므로 Retrieval 실행 시 Recall은 `N/A`가 정상입니다.
