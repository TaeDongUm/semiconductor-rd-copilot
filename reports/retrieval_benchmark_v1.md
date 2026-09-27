# Retrieval Benchmark — V1 Baseline

> 이 파일은 2026-09-27 사용자가 실제 OpenAlex 브라우저 Benchmark를 실행한 결과를 그대로 보존한다. V2 검색 전략 개발 후에도 수정하지 않는다.

| Strategy | Recall@10 | Recall@20 | Recall@50 |
|---|---:|---:|---:|
| single_keyword | 2/7 (28.6%) | 2/7 (28.6%) | 3/7 (42.9%) |
| multi_query_keyword | 2/7 (28.6%) | 2/7 (28.6%) | 3/7 (42.9%) |
| semantic | 1/7 (14.3%) | 1/7 (14.3%) | 1/7 (14.3%) |
| hybrid | 3/7 (42.9%) | 3/7 (42.9%) | 3/7 (42.9%) |

## V1에서 확인된 문제

- Multi-query가 single keyword보다 Recall을 개선하지 못했다.
- Semantic search가 Golden 7편 중 1편만 찾았다.
- Hybrid가 상대적으로 가장 높았지만 Recall@20은 42.9%에 머물렀다.
- Source coverage와 retrieval miss가 분리되어 있지 않아 낮은 Recall의 원인을 바로 진단하기 어려웠다.

V2에서는 Golden DOI 직접 조회로 Source Coverage를 분리하고, concept-family Boolean query와 Reciprocal Rank Fusion을 적용한다.
