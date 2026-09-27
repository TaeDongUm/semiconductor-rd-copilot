# Architecture

## Current MVP Flow

```text
HBM Thermal Problem
        ↓
Fixed Search Queries
        ↓
OpenAlex Retrieval
        ↓
Paper Metadata / Abstract
        ↓
Human-reviewed Golden Corpus candidates
        ↓
(Mock) Evidence / Claim
        ↓
Deterministic Evaluator
        ↓
PASS / FAIL
```

현재 단계에서는 Retrieval과 Evaluation을 우선 분리해 검증합니다. LLM은 아직 연결하지 않았습니다.

## Target MVP Flow

```text
User Problem
    ↓
Problem Decomposition (LLM)
    ↓
Search Query Generation
    ↓
OpenAlex Retrieval
    ↓
Evidence Extraction (LLM)
    ↓
Approach × Constraint Matrix
    ↓
Unknown / Conflict
    ↓
Candidate Hypothesis / Next Validation
    ↓
Deterministic Evaluation Harness
    ↓
Investigation Brief
```

## Retrieval Layer

`src/openalex.py`는 표준 라이브러리만 사용하여 OpenAlex Works API를 호출합니다.

- keyword search와 semantic search 지원
- abstract가 있는 논문만 조회 가능
- 기본값은 Open Access 논문만 조회
- DOI/OpenAlex ID 기반 중복 제거
- 여러 query에서 반복 등장한 논문을 우선 정렬
- OpenAlex inverted abstract를 일반 문자열로 복원

`src/retrieve_hbm.py`는 `data/hbm_thermal_queries.json`의 검색어를 사용해 HBM Thermal 후보 논문을 JSONL로 저장합니다.

## Golden Corpus Policy

검색 결과를 곧바로 Golden Corpus로 사용하지 않습니다.

```text
OpenAlex Result
      ↓
Candidate
      ↓
Human Review
  ┌───┴────────────┐
accepted         rejected / needs_full_text
  ↓
Golden Corpus
```

현재 `data/hbm_thermal_golden_candidates.jsonl`의 10편은 모두 `candidate` 상태입니다.

## Why Retrieval Is Kept Deterministic First

처음부터 LLM을 검색/선정 전 과정에 넣으면 어떤 단계에서 오류가 생겼는지 분리하기 어렵습니다.

따라서 MVP는 다음 순서로 확장합니다.

1. 고정 query로 Retrieval 품질 확인
2. Golden Corpus와 검색 결과 비교
3. 이후 LLM query decomposition 추가
4. 동일 Eval Set으로 before/after 비교

## External Dependency

현재 OpenAlex client는 Python 표준 라이브러리만 사용합니다.

실제 OpenAlex 호출에는 인터넷 연결이 필요하지만 API key는 선택 사항입니다. `OPENALEX_API_KEY` 환경변수가 있으면 자동으로 사용합니다.
