# Semiconductor R&D Copilot

반도체 기술 문제를 공개 연구 근거로 조사하고, **Evidence / Trade-off / Unknown / Hypothesis**를 구조화해 다음 검증 의사결정을 지원하는 AI 기반 PoC입니다.

> AI가 반도체 문제의 정답을 대신 만드는 것이 아니라, 공개 근거를 바탕으로 기술 조사 과정을 구조화하고 AI의 오류를 검증해 사람의 판단 비용을 줄이는 것이 목표입니다.

## 전체 흐름

```text
Engineering Problem
        ↓
Problem / Constraint 구조화
        ↓
Multi-query Generation
        ↓
OpenAlex Retrieval
        ↓
Evidence Extraction + Validation
        ↓
Approach × Constraint Matrix
        ↓
Conflict / Unknown
        ↓
Candidate Hypothesis
        ↓
Next Validation
        ↓
Investigation Brief
```

그림 중심 설명은 [`docs/PROJECT_FLOW.md`](docs/PROJECT_FLOW.md)를 참고합니다.

## 첫 Benchmark Case

첫 검증 사례는 **HBM 적층 증가에 따른 Thermal Management 문제**입니다.

HBM Thermal은 시스템에 하드코딩된 규칙이 아니라 `data/cases/hbm_thermal.json`에 저장된 첫 번째 Case입니다. 다른 공학 문제도 동일한 Case 구조로 추가할 수 있습니다.

## 검색 품질 개선 결과

동일한 수작업 검증 Golden Corpus v1 **7편을 고정**하고 검색 전략만 변경했습니다.

| Strategy | V1 Recall@20 | V2 Recall@20 | 변화 |
|---|---:|---:|---:|
| Single keyword | 28.6% | 28.6% | +0.0%p |
| **Multi-query + RRF** | **28.6%** | **71.4%** | **+42.9%p** |
| Semantic | 14.3% | 14.3% | +0.0%p |
| Hybrid + RRF | 42.9% | 71.4% | +28.6%p |

```text
낮은 Recall 발견
   ↓
Golden 7편 Source Coverage 검사
   ↓
7/7 OpenAlex 색인 확인
   ↓
Source 누락이 아닌 Query / Ranking 문제로 분리
   ↓
Concept-family Query + Reciprocal Rank Fusion 적용
   ↓
Multi-query Recall@20  2/7 → 5/7
Multi-query Recall@50  3/7 → 6/7
```

현재 HBM Thermal 소규모 Benchmark에서는 `multi_query_rrf_v2`를 기본 검색 전략으로 사용합니다. Golden Corpus가 7편뿐이므로 이 결과를 다른 논문 검색 문제에 일반화하지 않습니다.

상세 결과: [`reports/retrieval_benchmark_v2.md`](reports/retrieval_benchmark_v2.md)

## 현재 구현

- 자연어 공학 문제 → Case JSON용 Problem Decomposition Prompt
- 범용 Engineering Case / Constraint 구조
- Constraint 기반 Multi-query Generator
- OpenAlex keyword / semantic retrieval
- Reciprocal Rank Fusion 기반 Multi-query / Hybrid ranking
- Golden Corpus 버전 관리 및 `Recall@K` 평가
- OpenAlex Source Coverage 진단
- 논문별 Evidence Extraction Prompt
- Evidence JSON schema / DOI / Paper ID / Constraint 검증
- Approach × Constraint Matrix
- Conflict / Unknown / Candidate Hypothesis / Next Validation
- Investigation Brief 자동 생성
- Streamlit UI
- 설치 없이 열 수 있는 정적 HTML Demo
- 실제 HBM 논문 기반 저장 Demo Run
- V1/V2 Retrieval 평가 이력 보존

## 실행

### 정적 데모

`demo/index.html`을 브라우저로 엽니다.

### Streamlit

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Retrieval Benchmark

```bash
python -m src.retrieval_benchmark
```

또는 설치가 제한된 환경에서는 `demo/retrieval-benchmark.html`을 브라우저로 실행합니다.

### Tests

```bash
python -m unittest discover -s tests
```

## 주요 평가 파일

```text
evals/retrieval/history/
├─ hbm_thermal_v1_user_run_2026-09-27.json
└─ hbm_thermal_v2_user_run_2026-09-27.json

reports/
├─ retrieval_benchmark_v1.md
├─ retrieval_benchmark_v2.md
└─ hbm_thermal_investigation_brief.md
```

## 핵심 원칙

1. 단일 검색 Query에 의존하지 않습니다.
2. 검색 품질 자체를 Golden Corpus로 평가합니다.
3. Fact / Inference / Hypothesis를 구분합니다.
4. Evidence가 없으면 Unknown으로 남깁니다.
5. Conflict를 임의로 하나의 결론으로 합치지 않습니다.
6. 검증 가능한 항목은 LLM Judge보다 코드 검증을 우선합니다.
7. Golden Corpus 제목을 보고 검색어를 역설계하지 않습니다.
