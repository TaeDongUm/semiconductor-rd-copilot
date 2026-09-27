# Semiconductor R&D Copilot

반도체 기술 문제를 공개 연구 근거를 바탕으로 구조화하고, 근거·상충 정보·불확실성을 추적하여 다음 조사 및 검증 의사결정을 지원하는 AI 기반 PoC입니다.

## MVP Case

첫 번째 검증 사례는 **HBM 적층 증가에 따른 Thermal Management 문제**입니다.

프로젝트는 단순히 논문을 요약하거나 새로운 아이디어를 생성하는 데 목적을 두지 않습니다. 다음 흐름을 통해 기술 조사 과정의 판단 비용을 줄이는 것이 목표입니다.

`Problem → Engineering Constraints → Evidence → Approach × Constraint Matrix → Unknown / Conflict → Hypothesis → Next Validation`

세부 문제 정의는 [`docs/HBM_THERMAL_CASE.md`](docs/HBM_THERMAL_CASE.md)에 고정했습니다.

## MVP Scope

- 반도체 기술 문제 입력
- 문제를 Engineering Constraint로 구조화
- OpenAlex 기반 관련 논문 Retrieval
- 논문별 Evidence 구조화
- 해결 접근법과 Constraint 연결
- 근거가 없는 항목은 Unknown으로 표시
- 상충 근거는 Conflict로 보존
- Candidate Hypothesis와 Next Validation 생성
- 주요 Claim을 Evidence와 연결
- Citation / Numeric / Schema / Unsupported Claim 검증
- Investigation Brief 생성

## 현재 단계

현재 저장소에는 다음이 구현되어 있습니다.

- HBM Thermal MVP 문제/Constraint 고정
- Golden Corpus 후보 10편 정리 (`human_review_required`)
- HBM 검색 query 세트
- OpenAlex keyword / semantic search client
- 여러 query 결과 DOI/OpenAlex ID 기반 중복 제거
- Mock 기반 Evaluation 흐름
- Retrieval / Evaluator unit test

아직 LLM 기반 Problem Decomposition과 Evidence Extraction은 연결하지 않았습니다.

향후 순서:

1. Golden Corpus 후보 사람 검토
2. 실제 OpenAlex 검색 결과와 Golden 후보 비교
3. LLM 기반 Problem Decomposition / Evidence Extraction 연결
4. Evaluation Harness 강화
5. Streamlit UI 연결
6. 실제 HBM Thermal Investigation Brief 생성

## 프로젝트 구조

```text
semiconductor-rd-copilot/
├─ README.md
├─ docs/
│  ├─ SPEC.md
│  ├─ ARCHITECTURE.md
│  ├─ HBM_THERMAL_CASE.md
│  └─ GOLDEN_CORPUS_GUIDE.md
├─ src/
│  ├─ __init__.py
│  ├─ models.py
│  ├─ evaluator.py
│  ├─ openalex.py
│  ├─ retrieve_hbm.py
│  └─ mock_pipeline.py
├─ data/
│  ├─ sample_case.json
│  ├─ hbm_thermal_queries.json
│  └─ hbm_thermal_golden_candidates.jsonl
├─ evals/
│  └─ sample_eval_cases.jsonl
├─ reports/
│  └─ .gitkeep
└─ tests/
   ├─ test_evaluator.py
   └─ test_openalex.py
```

## 실행

### 1. Mock Evaluation

표준 라이브러리만 사용합니다.

```bash
python -m src.mock_pipeline
```

### 2. OpenAlex HBM Retrieval

기본값은 abstract가 있는 Open Access 논문만 검색합니다.

```bash
python -m src.retrieve_hbm
```

semantic search를 사용하려면:

```bash
python -m src.retrieve_hbm --mode semantic
```

API key를 발급받은 경우 선택적으로 환경변수로 설정할 수 있습니다.

```bash
export OPENALEX_API_KEY="YOUR_KEY"
python -m src.retrieve_hbm
```

검색 결과는 기본적으로 `data/openalex_hbm_results.jsonl`에 저장됩니다.

### 3. Tests

```bash
python -m unittest discover -s tests
```

## Golden Corpus

`data/hbm_thermal_golden_candidates.jsonl`에는 현재 10편의 후보가 있습니다.

이 파일은 **AI/검색기가 만든 결과를 그대로 정답으로 사용하는 데이터가 아닙니다.** 논문의 abstract/full text에서 실제 claim을 사람이 확인한 뒤 Golden Corpus로 승격합니다.

검토 기준은 [`docs/GOLDEN_CORPUS_GUIDE.md`](docs/GOLDEN_CORPUS_GUIDE.md)를 따릅니다.

## 핵심 설계 원칙

1. **Fact / Inference / Hypothesis를 구분합니다.**
2. **근거가 없으면 Unknown으로 남깁니다.**
3. **상충하는 연구 결과를 임의로 하나의 결론으로 합치지 않습니다.**
4. **AI가 제안한 아이디어는 검증된 사실이 아니라 Hypothesis로 취급합니다.**
5. **가능한 검증은 LLM Judge보다 deterministic code evaluator를 우선합니다.**
6. **검색 결과를 자동으로 Golden Evidence로 승격하지 않습니다.**
7. **실제 반도체 성능·수율 개선을 검증하지 않은 상태에서 개선 효과를 주장하지 않습니다.**
