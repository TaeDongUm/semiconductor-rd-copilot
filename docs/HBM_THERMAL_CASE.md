# HBM Thermal Management MVP Case

## 1. Case Goal

본 MVP는 HBM 적층 증가로 인해 커지는 열 문제를 하나의 정답 기술로 해결하려는 프로젝트가 아닙니다.

공개 연구 근거를 이용하여 다음 의사결정 흐름을 구조화하는 것이 목표입니다.

`Technical Problem → Engineering Constraints → Evidence → Approaches → Trade-offs → Unknown / Conflict → Hypothesis → Next Validation`

## 2. Fixed Problem Statement

> HBM의 적층 수가 증가하면서 내부 die에서 외부 냉각면까지의 열전달 경로가 길어지고, 여러 bonding/interface를 통과하면서 내부 열 축적과 hotspot 위험이 커진다. Thermal 성능만 높이는 것이 아니라 reliability, manufacturability, signal integrity, cost/yield 관점의 trade-off를 함께 고려하여 어떤 thermal-management 접근을 우선 조사해야 하는지 구조화하고 싶다.

## 3. Engineering Constraints

| ID | Constraint | MVP에서 확인할 질문 |
|---|---|---|
| C1 | Thermal performance | peak temperature, thermal resistance, hotspot을 낮추는 근거가 있는가? |
| C2 | Stack / interconnect integration | stack height, bonding pitch, TSV/interconnect 구조와 양립 가능한가? |
| C3 | Thermo-mechanical reliability | CTE mismatch, warpage, delamination, interface/void 등 신뢰성 문제가 보고되는가? |
| C4 | Manufacturability | 공정 복잡도, bonding/process integration, fabrication feasibility 근거가 있는가? |
| C5 | Electrical / signal integrity | thermal 개선이 signal integrity나 electrical performance를 악화시키지 않는가? |
| C6 | Cost / yield | 비용 또는 수율 영향에 직접적인 근거가 있는가? 없다면 Unknown으로 남기는가? |

## 4. Initial Approach Categories

초기 검색에서 다음 범주의 접근을 탐색합니다. 이 목록은 정답 목록이 아니라 검색 시작점입니다.

- Hybrid bonding / direct Cu bonding
- Thermal TSV / heat-transfer path engineering
- Embedded / microfluidic cooling
- Thermal interface materials and underfill
- Heat spreader / structural heat spreading
- Package-level reliability-aware thermal design

## 5. Expected Investigation Output

시스템은 아래 결과를 생성해야 합니다.

1. Problem Map
2. Engineering Constraints
3. Retrieved Papers
4. Evidence Units
5. Approach × Constraint Matrix
6. Conflicting Evidence
7. Unknowns
8. Candidate Hypotheses
9. Next Validation
10. Evaluation Result

## 6. Guardrails for This Case

- `좋아 보인다`는 이유만으로 기술 우선순위를 확정하지 않습니다.
- 논문이 thermal benefit만 보고했다면 cost/yield 효과까지 추론하지 않습니다.
- 서로 다른 package/process 조건의 수치를 직접 비교할 때 조건 차이를 보존합니다.
- Hybrid bonding, cooling 구조 등의 조합이 corpus에서 직접 검증되지 않았다면 `Hypothesis`로 표시합니다.
- 실제 fab/실험 데이터가 없으므로 실제 HBM 제품의 성능 개선을 달성했다고 주장하지 않습니다.
- 논문에서 확인할 수 없는 constraint는 `Unknown`으로 유지합니다.

## 7. Evidence Basis for Problem Definition

문제 정의의 출발점으로 아래 최신 review를 사용합니다.

- Seung-Hoon Lee et al., *Thermal Issues Related to Hybrid Bonding of 3D-Stacked High Bandwidth Memory: A Comprehensive Review*, Electronics, 2025. DOI: `10.3390/electronics14132682`
- *Thermal Management and Reliability Engineering of Advanced HBM Packages: Materials, Interfaces, and Integrated Design Strategies*, Micromachines, 2026. DOI: `10.3390/mi17091065`

두 review는 HBM 고적층화에서 내부 열전달 경로, hotspot, bonding/interface, thermal-mechanical reliability를 함께 고려해야 한다는 문제를 정리하고 있습니다.

## 8. Human Review Rule

Golden Corpus는 검색 결과를 자동으로 Golden으로 승격하지 않습니다.

각 후보 논문에 대해 사람이 최소한 다음을 확인한 뒤 `accepted`로 변경합니다.

- 제목/초록이 HBM 또는 직접적으로 연관된 3D stacked memory 문제를 다루는가?
- 사용하려는 claim이 실제 abstract/full text에서 확인되는가?
- 수치가 있다면 조건과 단위를 같이 기록했는가?
- 해당 논문이 어떤 constraint를 지원하는지 설명 가능한가?
- limitation 또는 적용 조건을 누락하지 않았는가?
