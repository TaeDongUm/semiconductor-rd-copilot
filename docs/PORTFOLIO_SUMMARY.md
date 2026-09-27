# Portfolio Summary

## 프로젝트 한 줄 설명

**공개 연구 근거를 바탕으로 반도체 기술 조사 과정을 구조화하고, AI의 검색·추출 오류를 평가하여 사람이 다음 검증 항목을 결정할 수 있도록 지원하는 Semiconductor R&D Copilot PoC**

## 문제

```text
반도체 공학 문제
  ↓
검색어 설계
  ↓
여러 논문 탐색
  ↓
근거/한계 비교
  ↓
Trade-off 정리
  ↓
다음 조사·실험 결정
```

자료가 많아질수록 사람이 직접 Context를 조립하는 비용이 커진다는 점을 병목으로 정의했습니다.

## 해결

```text
Engineering Problem
→ Constraint 구조화
→ Multi-query + OpenAlex Retrieval
→ Evidence Extraction
→ Deterministic Validation
→ Approach × Constraint Matrix
→ Unknown / Hypothesis
→ Next Validation
→ Investigation Brief
```

AI가 답을 확정하는 것이 아니라 **조사 공간을 줄이고, 근거가 없는 부분을 Unknown으로 남기는 구조**를 설계했습니다.

## 대표 Case

**HBM 적층 증가에 따른 Thermal Management**

- Thermal performance
- Stack / interconnect integration
- Thermo-mechanical reliability
- Manufacturability
- Electrical / signal integrity
- Cost / yield

## Eval-driven 개선

### Retrieval

```text
V1 Multi-query Recall@20   2/7 · 28.6%
          ↓
Source Coverage 7/7 확인
          ↓
Concept-family Query + RRF
          ↓
V2 Multi-query Recall@20   5/7 · 71.4%
V2 Multi-query Recall@50   6/7 · 85.7%
```

### AI Output

```text
V1 Constraint Recall   77.8% · FAIL
        ↓
Constraint Coverage Check 추가
        ↓
V2 Constraint Recall   94.4% · PASS
Precision              100%
Unsupported Mapping    0
```

## 최종 End-to-End 결과

```text
OpenAlex Source Coverage     7/7
Retrieval Recall@20          71.4%
Evidence Accepted            5/5
Evidence Validation Error    0
Constraint Precision         100%
Constraint Recall            94.7%
Constraint F1                97.3%
Hypothesis Traceability      100%
Overall Gate                 PASS
```

## AI 활용 방식

```text
AI
├─ Problem Decomposition
├─ Query 후보 생성
└─ Evidence Extraction

Code
├─ Schema Validation
├─ DOI / Paper ID Validation
├─ Numeric Validation
├─ Constraint Mapping Evaluation
├─ Retrieval Recall Evaluation
└─ Quality Gate

Human
├─ Golden Corpus 검토
├─ Golden Evidence 검토
├─ Query / 결과 검토
└─ 최종 공학 판단
```

## 강조할 점

- LLM 한 번의 답변이 아니라 **검색 → 근거 → 판단 → 평가**의 workflow를 설계했습니다.
- Semantic Search가 자동으로 우월할 것이라는 가설도 실제 Benchmark에서 기각했습니다.
- 성능을 높이기 위해 근거가 약한 Constraint를 억지로 추가하지 않고 miss로 남겼습니다.
- 실제 Fab 데이터나 장비 없이 공개 연구 기반으로 검증 가능한 범위만 다루었습니다.

## 한계

Golden Retrieval 7편, downstream 5편의 작은 PoC입니다. 실제 수율 개선이나 root cause 발견을 주장하지 않으며, 결과는 엔지니어의 최종 판단을 대체하지 않습니다.
