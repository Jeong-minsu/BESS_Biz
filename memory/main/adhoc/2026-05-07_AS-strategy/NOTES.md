---
name: adhoc-2026-05-07-AS-strategy
description: Ad-hoc 분석 — 최적 보조서비스 전략 (Q1 hourly optimal AS / Q2 DA-RT split / Q3 RT>DA 가설 검증). 분석 기간 2026-01-01 ~ 03-06. 의사결정 시점 D-1 08:30 CT.
type: project
---

# AS Strategy Analysis — Working Notes

## Scope (확정 2026-05-07)

| 항목 | 값 |
|---|---|
| 분석 기간 | 2026-01-01 ~ 2026-03-06 (post-RTC+B, 60-day disclosure 가용) |
| 노드 | AS = system / Energy LMP = GKS_BESS_RN + HB_HOUSTON |
| 의사결정 시점 | D-1 08:30 CT |
| 깊이 | Descriptive + Causal-ish (SHAP/PDP). Predictive X |
| 산출물 | 단일 HTML (dashboard-report.skill) |

## Key Questions

1. **Q1**: 시간별 최적 AS product mix (ex-post)
2. **Q2**: SoC-aware optimal DA/RT energy split (ex-post LP) + GKS actual gap
3. **Q3-a**: RT>DA 시간대 특성 (descriptive)
4. **Q3-b**: 가설 — RT 급등 시 BESS가 AS→Energy migration → AS pool 이탈 → marginal supply shift → RT push-up

## Data Inventory (2026-05-07)

### 보유
- Tenaska GKS hourly: 2026-01-01 ~ 2026-05-05 (125일치 energy_as_detail.json)

### 필요
- [ ] Yes Energy DA/RT LMP @ GKS_BESS_RN, HB_HOUSTON (Jan-Mar)
- [ ] Yes Energy LOAD/WIND/SOLAR FC (D-1 vintage, bidclose) + actual (RTI)
- [ ] Net-load forecast bidclose
- [ ] ERCOT API: DAM AS clearing prices (5종)
- [ ] ERCOT API: AS procurement amount (hourly demand)
- [ ] ERCOT API: ORDC adder (5-min)
- [ ] ERCOT API: RT AS deployment / Released capacity
- [ ] 60-Day SCED Disclosure: DAM AS Offers + Resource Output Schedule + Base Points
- [ ] AG2 weather (historical observed)

## Phases

| # | Status | Description |
|---|---|---|
| P1 | done | 데이터 백필 (LMP, DAM AS MCPC, forecasts, Tenaska 90일) |
| P2 | done | Q1 — NSPIN top in 62.8% hours but LP picks RRS+NSPIN+REGDN; ceiling $1.04M (AS only naive) |
| P3 | done | Q2 LP — ex-post $2.72M (E $2.16M / AS $560K); GKS captured 10.8%; energy gap dominant |
| P4 | done | Q3-a — RT>DA mostly in scarcity events (1/28 wind bust); HE 17-19 highest spike rate |
| P5 | done | Q3-b — DAM AS spike & RT spike disjoint (joint=0); hypothesis needs RT AS + 60-day SCED to fully test |
| P6 | done | D-1 08:30 vintage — Wind FC<5GW or NetLoad FC>50GW → 87.5% recall, 7% precision |
| P7 | done | HTML dashboard at `reports/ad-hoc/2026-05-07_AS-strategy.html` |

## v4 Update (2026-05-07): DA + RT AS commit + buyback LP

새로운 LP 두 개 추가:
- **31_q2_dam_rt_split_lp.py** (Pure-arb): a_DA (SoC 무관), a_RT (SoC capability), s_DA shortfall buyback at RT_MCPC. LP가 마음껏 commit 후 buyback 가능.
  - 결과: DA share 86-99%, total $1.75M, AS $653K (단 s_DA가 a_DA의 90%+ — 비현실적)
- **32_q2_delivery_required_lp.py** (Compliance-realistic): s_DA = 0 강제. a_DA + a_RT ≤ capability.
  - 결과: DA share 73-99%, total $1.22M, AS $170K, GKS AS capture 112%

**사용자 질문 답 (평균 최적 DA/RT split)**:
- Delivery-LP 기준: REGUP 80% / REGDN 73% / RRS 99% / ECRS 98% / NSPIN 96%
- Revenue-weighted average DA share ≈ 87%
- RT는 backstop으로 ~13% 정도, REGDN/REGUP 위주

## v3 Update (2026-05-07): DAM AS는 SoC 무관

- 사용자 정정: DAM AS commit은 ERCOT가 SoC telemetry 검사하지 않음. RT AS만 telemetry 기반 award 제한 (예: SoC 100 MWh → RT NSpin max 25 MW).
- LP에서 SoC reservation 제약 (NSpin 4× / RRS 2× / ECRS 1×) 완전 제거.
- 결과: LP AS optimal $119K → $234K (+96%). NSpin LP $20K → $103K로 정상화.
- GKS AS capture 160% → 81% (LP 대비 over-perform 더 합리적 수준).
- LP total $1.19M → $1.30M, GKS capture 38.8% → 35.5%.
- "NSpin 수수께끼" 해소.

## v2 Update (2026-05-07): SoC factors + RT AS market

- SoC reservation factors (사용자 입력): NSpin 4× / RRS 2× / ECRS 1× / Reg 1×
- RT AS prices fetched (NP6-331-CD, 15-min, post-RTC+B): mean DAM/RT ratio 1.4-3.3×
- Q2 redefined → AS market DAM vs RT split: Always-DAM = 89.4% of optimal
- Q3 redefined → RT > DAM driver: wind bust for NSPIN/ECRS/RRS, solar ramp for REGDN
- LP AS allocation shifted dramatically (NSpin 4× SoC factor → LP only $20K NSpin)
  - But GKS actual NSpin $156K = 8× LP — suggests ERCOT doesn't strict-enforce 4hr SoC, 또는 NSpin rarely deployed → factor may need revision

## Key Findings (TL;DR) — Storm Fern (1/24-28) 제외, 60일 분석

1. **Ex-post LP optimal: $1.21M (60 days) vs GKS actual $460K (38%)** — 정상 gap 수준 (이전 65일 분석 10.8%는 1/28 winter event tail이 dominant했음).
2. **AS 전략은 이미 잘 작동** — GKS AS $190K vs LP AS $155K = **122% capture**. NSPIN-heavy 단순 전략으로 normal-day에서 LP 다양화 전략을 능가. AS 측 추가 최적화 marginal 이익 제한적.
3. **핵심 개선 영역 = Energy round-trip** — GKS Energy net $270K vs LP $1.05M (25.6% capture). DA에 commit한 만큼 RT 손실. 원인 추적 필요: HSL 변동, dispatch 응답성, 가격 추정 gap.
4. **RT spike 모두 wind bust** — Storm 제외 후 RT-DA spread > $50인 시간 단 3h, 모두 wind err −1.5~−5.9 GW. Wind STWPF 일관되게 over-forecast.
5. **사용자 가설 (BESS migration)** — Storm 제외 시 표본 부족 (DAM AS spike 0h, RT spike 3h). 정밀 검증은 RT AS price + 60-day SCED disclosure 필요.
6. **연환산 개선 여지** — GKS $2.58M/year vs LP $6.79M/year. 실전 LP의 30-50% capture 가정 시 $2.0-3.4M/year 추가 가능.

## Limitations / Out of scope

- RT AS prices (5-min): not fetched
- 60-day SCED disclosure (resource-level base point + AS released cap): not fetched
- ORDC adder: not fetched
- Weather (AG2): not fetched
- True D-1 08:30 CT vintage forecast: bidclose proxies are ~10:00 CT (~1.5h late)
- LP is perfect-foresight (overstates achievable); industry typical is 30-50% capture of LP optimum
- GKS HSL variations not modeled
- 1/28 RT generation = 0 may reflect HSL constraint or response failure — need physical investigation

## Working Files

```
shared/data/adhoc/2026-05-07_AS-strategy/
├── raw/         ← 벤더별 raw cache
├── derived/     ← 합쳐진 분석 테이블
└── scripts/     ← 백필 + 분석 스크립트
```

## Conventions

- HE 1-24 → datetime hour = HE-1
- Spread = DA - RT (positive ⇒ DA expensive)
- All wall-clock CT (America/Chicago)
- Vintage: D-1 08:30 CT = bidclose snapshot (closest available proxy; bidclose is actually 10:00 but it's what YE/Enverus expose)
