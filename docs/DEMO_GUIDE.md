# Demo Guide

## 1~2분 데모 순서

```text
1. 문제 정의
   HBM 적층 증가 → Thermal + Reliability + Manufacturability 등 동시 고려

2. Retrieval Eval
   V1 Multi-query Recall@20 28.6%
   → 실패 원인 분석
   → V2 71.4%

3. Approach × Constraint Matrix
   어떤 접근법이 어떤 Constraint에 근거가 있는지 확인
   근거 없음 = ?

4. Unknown / Hypothesis
   정답을 단정하지 않고 다음 검증 항목으로 연결

5. AI Output Eval
   Constraint Recall 77.8% → 94.4%
   Precision 100%, Unsupported Mapping 0

6. End-to-End
   Overall Gate PASS
```

## 데모에서 꼭 말할 문장

> 이 프로젝트는 AI가 반도체 기술의 정답을 발명하는 시스템이 아니라, 공개 근거를 이용해 조사 범위를 줄이고 AI의 오류를 검증하여 사람이 다음 판단에 집중하도록 만드는 PoC입니다.

## 질문을 받았을 때

### 왜 HBM Thermal인가?

첫 Benchmark Case입니다. 시스템은 Case JSON 기반이라 HBM Constraint가 코드에 고정되어 있지 않습니다.

### 왜 Golden Corpus가 7편뿐인가?

마감이 짧은 PoC에서 사람이 직접 검증할 수 있는 작은 Benchmark를 우선 만들었습니다. 그래서 절대 수치보다 동일 Golden을 고정한 V1→V2 비교에 의미를 둡니다.

### Semantic Search가 왜 낮나?

이번 7편 Benchmark에서는 전문 용어를 명시적으로 확장한 Multi-query가 더 잘 동작했습니다. 이를 모든 논문 검색 문제에 일반화하지 않습니다.

### AI가 만든 아이디어를 믿을 수 있나?

Hypothesis는 Fact와 분리하며, citation/constraint/numeric/traceability는 코드 기반 Quality Gate로 검증합니다. 근거가 없으면 Unknown으로 남깁니다.
