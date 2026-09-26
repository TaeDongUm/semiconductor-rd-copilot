# Semiconductor R&D Copilot

반도체 기술 문제를 공개 연구 근거를 바탕으로 구조화하고, 근거·상충 정보·불확실성을 추적하여 다음 조사 및 검증 의사결정을 지원하는 AI 기반 PoC입니다.

## MVP Case

첫 번째 검증 사례는 **HBM 적층 증가에 따른 Thermal Management 문제**입니다.

프로젝트는 단순히 논문을 요약하거나 새로운 아이디어를 생성하는 데 목적을 두지 않습니다. 다음 흐름을 통해 기술 조사 과정의 판단 비용을 줄이는 것이 목표입니다.

`Problem → Engineering Constraints → Evidence → Approach × Constraint Matrix → Unknown / Conflict → Hypothesis → Next Validation`

## MVP Scope

- 반도체 기술 문제 입력
- 문제를 Engineering Constraint로 구조화
- 관련 논문/근거 검색 결과 수용
- 논문별 Evidence 구조화
- 해결 접근법과 Constraint 연결
- 근거가 없는 항목은 Unknown으로 표시
- 상충 근거는 Conflict로 보존
- Candidate Hypothesis와 Next Validation 생성
- 주요 Claim을 Evidence와 연결
- Citation / Numeric / Schema / Unsupported Claim 검증
- Investigation Brief 생성

## 현재 단계

현재 저장소는 **외부 API 없이도 데이터 구조와 Evaluation 흐름을 검증할 수 있는 Mock 기반 초기 버전**입니다.

향후 순서:

1. OpenAlex Retrieval 연결
2. LLM 기반 Problem Decomposition / Evidence Extraction 연결
3. Evaluation Harness 강화
4. Streamlit UI 연결
5. 실제 HBM Thermal Case 검증

## 프로젝트 구조

```text
semiconductor-rd-copilot/
├─ README.md
├─ docs/
│  ├─ SPEC.md
│  └─ ARCHITECTURE.md
├─ src/
│  ├─ __init__.py
│  ├─ models.py
│  ├─ evaluator.py
│  └─ mock_pipeline.py
├─ data/
│  └─ sample_case.json
├─ evals/
│  └─ sample_eval_cases.jsonl
├─ reports/
│  └─ .gitkeep
└─ tests/
   └─ test_evaluator.py
```

## 실행

초기 Mock 흐름은 표준 라이브러리만 사용합니다.

```bash
python -m src.mock_pipeline
```

테스트:

```bash
python -m unittest discover -s tests
```

## 핵심 설계 원칙

1. **Fact / Inference / Hypothesis를 구분합니다.**
2. **근거가 없으면 Unknown으로 남깁니다.**
3. **상충하는 연구 결과를 임의로 하나의 결론으로 합치지 않습니다.**
4. **AI가 제안한 아이디어는 검증된 사실이 아니라 Hypothesis로 취급합니다.**
5. **가능한 검증은 LLM Judge보다 deterministic code evaluator를 우선합니다.**
6. **실제 반도체 성능·수율 개선을 검증하지 않은 상태에서 개선 효과를 주장하지 않습니다.**
