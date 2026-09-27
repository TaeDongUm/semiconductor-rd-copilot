# HBM Thermal Retrieval Benchmark — V1 → V2

> 동일한 Golden Corpus v1(7편)을 고정한 상태에서 검색 전략만 변경한 결과입니다.

## 결과

| Strategy | V1 Recall@20 | V2 Recall@20 | Δ |
|---|---:|---:|---:|
| Single keyword | 28.6% | 28.6% | +0.0%p |
| Multi-query | 28.6% | 71.4% | +42.9%p |
| Semantic | 14.3% | 14.3% | +0.0%p |
| Hybrid | 42.9% | 71.4% | +28.6%p |

## 진단 흐름

```text
낮은 Recall 발견
  ↓
Golden 7편 Source Coverage 검사
  ↓
7/7 OpenAlex 색인 확인
  ↓
Source 누락이 아니라 Query / Ranking 문제로 분리
  ↓
Concept-family Query + RRF 적용
  ↓
Multi-query Recall@20: 2/7 → 5/7
Multi-query Recall@50: 3/7 → 6/7
```

## 해석

- V2 Multi-query + RRF는 Recall@20을 **28.6% → 71.4%**로 개선했습니다.
- Recall@50은 **42.9% → 85.7%**로 개선되었습니다.
- Semantic Search 단독은 **14.3%**로 개선되지 않았습니다.
- Hybrid는 Recall@20에서 Multi-query와 동일한 **71.4%**였지만 Recall@50은 **71.4%**로 Multi-query보다 낮았습니다.
- 따라서 이 HBM Thermal 소규모 Benchmark에서는 `multi_query_rrf_v2`를 기본 검색 전략으로 채택합니다.

## 제한

- Golden Corpus는 수작업 검증 7편뿐이므로 한 편이 14.3%p를 차지합니다.
- 이 결과를 모든 논문 검색 문제에 일반화하지 않습니다.
- Golden 논문 제목을 보고 검색어를 역설계하지 않았습니다. Query는 Engineering Problem/Constraint의 concept family에서 생성했습니다.
