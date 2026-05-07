# Organization & R&R Matrix

8개 에이전트의 역할/책임 매트릭스. **R&R 겹침을 막기 위해 각 항목은 단일 owner에게만 할당**한다.

---

## 1. R&R Quick Map (한 줄 요약)

| Office | Agent | One-line R&R |
|---|---|---|
| Front | **bess-optimizer** | GKS BESS의 다음날 DA/RT Energy + AS revenue stack 최적 제안 |
| Front | **dart-virtual-trader** | DART virtual short/long 포지션 추천 (가격·물량) |
| Front | **crr-trader** | CRR 트레이딩 기회 발굴 (지역간 basis 활용) |
| Middle | **market-analyst** | 다음날 ERCOT 시황 브리핑 + 시장 구조/매크로 분석 |
| Middle | **congestion-analyst** | Congestion / Constraint 분석 (CONGESTION_PROJECT 활용) |
| Back | **pnl-manager** | GKS 전일 실적 / Smartbidder benchmark / ERCOT BESS 랭킹 |
| Back | **evaluator** | 전 에이전트 work process / approach / resource 점검 |
| Back | **reporter** | Daily/Weekly 리포트 생성 (전 에이전트 결과 취합) |

---

## 2. 책임 영역 매트릭스 (RACI)

> **R** = Responsible (실행), **A** = Accountable (의사결정), **C** = Consulted (자문), **I** = Informed (정보 수신)

| 작업 영역 | bess-opt | dart | crr | mkt-a | cng-a | pnl | eval | rpt |
|---|---|---|---|---|---|---|---|---|
| DA/RT Energy 입찰 전략 | **R/A** | I | – | C | C | I | I | I |
| DA/RT AS (RRS/ECRS/Non-spin/Reg) 입찰 전략 | **R/A** | – | – | C | C | I | I | I |
| BESS 충방전 스케줄 | **R/A** | – | – | C | C | I | I | I |
| DART Virtual 포지션 (short/long) | – | **R/A** | – | C | C | I | I | I |
| CRR 트레이딩 기회 발굴 | – | – | **R/A** | C | C | I | I | I |
| 다음날 시황 / 가격 예측 종합 | C | C | C | **R/A** | C | I | I | I |
| 시장 구조·정책·발전소 mix 분석 | I | I | I | **R/A** | I | I | I | I |
| Congestion / Constraint 분석 | C | C | C | C | **R/A** | I | I | I |
| 전일 GKS 실적 (Tenaska) 정리 | I | I | – | I | I | **R/A** | I | I |
| Smartbidder benchmark 비교 | I | I | – | I | I | **R/A** | I | I |
| ERCOT BESS 랭킹 (주 1회) | I | I | – | I | I | **R/A** | I | I |
| 에이전트 효과성·효율성 점검 | I | I | I | I | I | I | **R/A** | I |
| Daily / Weekly 리포트 생성 | C | C | C | C | C | C | C | **R/A** |

---

## 3. 에이전트 간 정보 흐름

```
                         ┌─────────────────────────────┐
                         │   shared/data/  (공통 저장소) │
                         └──────────┬──────────────────┘
                                    ▲
   ┌────────────────────┬───────────┴──────────────┬────────────────┐
   │                    │                          │                │
   ▼                    ▼                          ▼                ▼
[market-analyst]   [congestion-analyst]      [pnl-manager]     [evaluator]
   │                    │                          │                ▲
   │ 시황·예측          │ 혼잡 분석                │ 전일 실적      │ 모든 에이전트
   │                    │                          │                │ 결과 점검
   ▼                    ▼                          ▼                │
   ┌────────────────────────────────────────┐                       │
   │ [bess-optimizer]  [dart-trader]  [crr] │  ◄────  self-review ──┘
   └────────────────────┬───────────────────┘
                        │ 다음날 포지션·전략
                        ▼
                   [reporter]
                        │
                        ▼
                   사용자 (07:30 CT, Houston)
```

---

## 4. R&R 충돌 방지 규칙 (Tie-Breakers)

| 잠재적 겹침 | 해결 규칙 |
|---|---|
| BESS Optimizer가 시황을 직접 예측하려는 경우 | ❌ Market Analyst의 산출물만 input으로 사용. 자체 시황 예측은 금지. |
| Market Analyst가 입찰 전략을 제시하려는 경우 | ❌ 시황·예측까지만. 입찰 전략·물량은 BESS Optimizer의 영역. |
| DART Trader가 BESS 물리 dispatch를 고려 | ❌ DART Virtual은 financial product. 물리 dispatch는 BESS Optimizer. |
| Congestion Analyst가 가격 예측을 종합하려는 경우 | ❌ 혼잡·constraint 분석에 집중. 가격은 Market Analyst. |
| Reporter가 자체 분석/판단을 추가하는 경우 | ❌ 취합·요약만. 새로운 분석/판단은 다른 에이전트로 위임. |
| P&L Manager가 미래 전략을 제안 | ❌ 전일 실적·벤치마크·랭킹만. 미래 전략은 Front office. |

---

## 5. 메모리 분리 원칙

각 에이전트는 `memory/<agent-name>/` 하위에 다음을 별도 관리:

```
memory/<agent-name>/
├── history/          ← 과거 산출물 (날짜별)
├── learnings/        ← self-review에서 얻은 인사이트 누적
└── plans/            ← 향후 개선 계획 (Evaluator로부터 받은 제안 포함)
```

**plans와 history가 섞이지 않도록** 별도 파일로 관리.

---

## 6. 자가 피드백 (Self-Review) 의무 대상

> Front/Middle Office 5개 에이전트는 **매일 전날 본인의 의사결정을 lookback**하고 `memory/<agent>/learnings/YYYY-MM-DD.md`로 저장.

- bess-optimizer
- dart-virtual-trader
- crr-trader
- market-analyst
- congestion-analyst

Self-review 항목:
1. 전날 내 제안과 실제 결과 비교 (P&L Manager 데이터 기반)
2. 최적 대비 아쉬웠던 점 (delta 정량화)
3. 다음번 적용할 개선 포인트 (구체적·검증 가능)
