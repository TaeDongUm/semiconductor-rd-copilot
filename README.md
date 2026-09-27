# Semiconductor R&D Copilot

반도체 기술 문제를 공개 연구 근거로 조사하고, **Evidence / Trade-off / Unknown / Hypothesis**를 구조화하여 다음 검증 의사결정을 지원하는 AI 기반 PoC입니다.

> 목표는 AI가 반도체 문제의 정답을 대신 만드는 것이 아니라, 공개 근거를 바탕으로 기술 조사 과정을 구조화하고 AI의 오류를 검증하여 사람의 판단 비용을 줄이는 것입니다.

## 전체 흐름

```text
Engineering Problem
        ↓
Problem / Constraint 구조화
        ↓
Multi-query Generation
        ↓
Keyword + Semantic Retrieval
        ↓
Evidence
        ↓
Approach × Constraint
        ↓
Conflict / Unknown
        ↓
Hypothesis / Next Validation
        ↓
Evaluation Harness
```

그림 중심 설명은 [`docs/PROJECT_FLOW.md`](docs/PROJECT_FLOW.md)를 참고합니다.

## 첫 Benchmark Case

첫 검증 사례는 **HBM 적층 증가에 따른 Thermal Management 문제**입니다.

HBM Thermal은 시스템에 하드코딩된 문제가 아니라 `data/cases/hbm_thermal.json`에 저장된 첫 번째 Case입니다. 다른 공학 문제는 같은 형식의 Case 파일을 추가해 실행할 수 있습니다.

## 현재 구현

- 범용 Engineering Case JSON loader
- Constraint 기반 deterministic Multi-query Generator
- 새 Constraint 추가 시 focused query 자동 반영
- OpenAlex keyword / semantic search
- Hybrid retrieval 결과 통합 및 중복 제거
- DOI/OpenAlex ID 기반 정렬
- 버전 고정 Golden Corpus 후보 구조
- Golden 확정 시 Retrieval `Recall@K` 평가
- Mock Investigation Evaluator
- 전체 unit test

아직 연결하지 않은 부분:

- 자연어 → Case JSON을 만드는 LLM Problem Decomposition
- 실제 논문 Evidence Extraction
- Approach × Constraint Matrix 생성
- Hypothesis / Investigation Brief 생성
- Streamlit UI

## 프로젝트 구조

```text
semiconductor-rd-copilot/
├─ README.md
├─ data/
│  ├─ cases/
│  │  └─ hbm_thermal.json
│  └─ sample_case.json
├─ docs/
│  ├─ PROJECT_FLOW.md
│  ├─ SPEC.md
│  ├─ ARCHITECTURE.md
│  ├─ HBM_THERMAL_CASE.md
│  └─ GOLDEN_CORPUS_GUIDE.md
├─ evals/
│  ├─ sample_eval_cases.jsonl
│  └─ golden/
│     └─ hbm_thermal/v1/
│        ├─ metadata.json
│        └─ candidates.jsonl
├─ src/
│  ├─ case_definition.py
│  ├─ query_generator.py
│  ├─ openalex.py
│  ├─ retrieve_case.py
│  ├─ retrieval_eval.py
│  ├─ models.py
│  ├─ evaluator.py
│  └─ mock_pipeline.py
└─ tests/
```

## 실행

### Mock Evaluation

```bash
python -m src.mock_pipeline
```

### Case 기반 OpenAlex Retrieval

먼저 API 호출 없이 생성된 검색어를 확인할 수 있습니다.

```bash
python -m src.retrieve_case --dry-run --save-query-plan data/query_plan.json
```

Case의 `constraints/search_terms`를 수정하면 Query Plan에도 반영됩니다. 검색어를 확인한 뒤 실제 Retrieval을 실행합니다.

기본은 Keyword + Semantic을 함께 사용하는 Hybrid 모드입니다.

```bash
python -m src.retrieve_case --case data/cases/hbm_thermal.json
```

Keyword만:

```bash
python -m src.retrieve_case --mode keyword
```

Semantic만:

```bash
python -m src.retrieve_case --mode semantic
```

Golden 후보는 아직 사람이 `accepted`로 검토하지 않았으므로 현재 `Recall@K: N/A`가 정상입니다.

### Tests

```bash
python -m unittest discover -s tests
```

## 핵심 원칙

1. 단일 검색 Query에 의존하지 않습니다.
2. 검색 품질 자체를 평가 대상으로 봅니다.
3. Golden Corpus는 서비스 검색 범위를 제한하지 않는 고정 Benchmark입니다.
4. Fact / Inference / Hypothesis를 구분합니다.
5. Evidence가 없으면 Unknown으로 남깁니다.
6. Conflict를 임의로 하나의 결론으로 합치지 않습니다.
7. 검증 가능한 항목은 LLM Judge보다 코드 검증을 우선합니다.
