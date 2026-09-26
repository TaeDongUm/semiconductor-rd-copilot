# Architecture

## Current Mock Architecture

```text
User Problem
    ↓
Mock Problem Map
    ↓
Mock Paper Evidence
    ↓
Approach × Constraint Mapping
    ↓
Candidate Claims / Hypotheses
    ↓
Deterministic Evaluator
    ↓
Investigation Brief (console)
```

## Target MVP Architecture

```text
User Problem
    ↓
Problem Decomposer (LLM)
    ↓
OpenAlex Retrieval
    ↓
Evidence Extractor (LLM)
    ↓
Approach × Constraint Mapper
    ↓
Conflict / Unknown Detector
    ↓
Hypothesis Generator (LLM)
    ↓
Evaluation Harness
    ├─ Schema Check
    ├─ Citation Check
    ├─ Numeric Check
    └─ Unsupported Claim Check
    ↓
Investigation Brief
```

## Design Decision

초기 단계에서는 Embedding DB, Multi-Agent framework, Docker, 별도 데이터베이스를 사용하지 않습니다.

이유:

- HBM Thermal 단일 Case 검증이 우선
- 설치 제한 환경에서도 저장소 구조를 이해하고 수정 가능해야 함
- AI 호출 수와 비용을 통제해야 함
- 필요성이 실제로 확인된 기능만 추가하기 위함
