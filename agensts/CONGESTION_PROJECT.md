# ERCOT Congestion Prediction Project

**Owner**: Minsoo (GridFlex Inc.)
**Agent**: `congestion-analyst`
**Last updated**: 2026-05-26
**Current stage**: Stage 0 — Infrastructure (in progress, datalake-only, 3-4 weeks)

---

## 1. Goal

Build a universal congestion prediction system for ERCOT that predicts:

- **Binding probability** for each transmission constraint
- **Conditional shadow price** (λ) for each constraint
- For both **DAM** (24h hourly, day-ahead) and **RTM** (5-min, real-time)

Nodal LMP congestion components (MCC) are then derived deterministically via PTDF projection — they are not directly modeled.

## 2. Use case

- **Primary**: Direct support for GK node trading (the GK price prediction LightGBM is a separate system; do not conflate)
- **Secondary**: Hub-level CRR / virtual bidding strategy
- **Long-term**: Once universal congestion is solved, any node-pair analysis reduces to PTDF arithmetic

## 3. Core architectural decisions

### Modeling target

**Constraint-level shadow price** (λ per constraint), not nodal LMP.

Rationale: nodal MCC = -Σ(shift_factor × λ). Predicting the upstream λ is more parsimonious and physically grounded. Training a model on derived nodal MCC discards information.

### Two-stage prediction

For each constraint:
1. **P(binding)** — classifier
2. **E[λ | binding]** — quantile regressor (P50/P90/P99)

Single-stage regression is forbidden. Shadow price distribution is too sparse (most observations = 0, long right tail).

### DAM and RTM share backbone, separate heads

- Shared: network topology encoder, weather/load encoder, constraint embedding
- DAM head: input cutoff D-1 10:00 CT, output 24h × N_constraint
- RTM head: input cutoff t-5min, output next ~12 intervals (1 hour at 5-min)
- Auxiliary input to RTM head: that hour's DAM-cleared shadow price

### Constraint universe is dynamic — use embedding, not one-hot

Each constraint represented by feature vector:
- Monitored element location (zone + voltage)
- Contingency type (BASECASE / line outage / gen outage)
- Historical binding statistics (30d / 365d)
- PTDF column statistics (max shift factor, # affected nodes)
- Direction sensitivity

This handles new constraints without retraining.

## 4. Stage roadmap

### Stage 0 — Infrastructure (3-4 weeks, datalake-only) — CURRENT

> **2026-05-26**: 9개 항목 전부 Yes Energy Datalake (S3 bucket `yedatalake`) 단독으로 페치 가능함이 메인 thread에서 실측 검증됨. ERCOT MIS direct 의존 0개. Week-level breakdown은 `memory/congestion-analyst/plans/stage-progress.md` 참조.

- [x] DAM/RTM constraint + λ + SCED ingestion  ← `yedatalake://ercot/transmission/constraints/da/{YYYYMMDD}.csv.gz` (**2020-02-01+**, 2,030,085 rows, 100% coverage — W1 complete 2026-05-26), `ercot_sced_shift_factors/{YYYYMMDD}.csv.gz` (2011-12+, W2)
- [x] Network metadata (facility / contingency / plant / unit) — NMMS parsing 대체  ← `yedatalake://ercot/metadata/objects/{facility,contingency,ercot_plant,ercot_unit,all}.csv.gz` (W1 complete 2026-05-26: facility 172,492 rows, contingency 6,711, ercot_plant 1,318, ercot_unit 2,739)
- [ ] PTDF / LODF — shift factor 4종이 datalake에 있어 NMMS direct 불필요 (2026-05-26 확인). Base-case + post-contingency PTDF 모두 한 테이블 (CONSTRAINT, CONTINGENCY, RESOURCE|PNODE|SP) → SHIFTFACTOR. 별도 LODF 행렬 계산 불필요.  ← `yedatalake://ercot/transmission/constraints/{market_shift_factors,ercot_sced_shift_factors,settle_shift_factors_ercot,shift_factors}/{YYYYMMDD}.csv.gz`
- [ ] CRR / FTR auction history  ← `yedatalake://ercot/ftr/auction/{YYYY_MM_monthly|YYYY_annual}/{results,obligationmcp,optionmcp}.csv.gz` (2010-12+)
- [ ] Transmission outages (hourly granular)  ← `yedatalake://ercot/transmission/outages/actual/{YYYYMMDDHH}.csv.gz` (2017-01+)
- [ ] Weather — Stage 0 한정 datalake zone-level forecast + actual. HRRR 은 Stage 2 로 deferred.  ← `yedatalake://ercot/weather/{forecast,actual}/{YYYYMMDD}.csv.gz`
- [ ] Henry Hub + Waha gas  ← `yedatalake://ercot/prices/gas/` (정확한 경로 W4 진입 시 확인)
- [ ] Vintage forecasts (publish-time snapshots) — D-1 cutoff leakage 자연 방지  ← `yedatalake://ercot/vintage/...`
- [ ] Bus-level (nodal) LMP + hub/zone 15-min LMP  ← `yedatalake://ercot/prices/bus_lmp/{YYYYMMDD}.csv.gz` (2017-01+), `prices/lmp/15min/{YYYYMMDDHH}.csv.gz` (2012-11+)
- [ ] GTC (Generic Transmission Constraints) DA/RT  ← `yedatalake://ercot/flow/ercot_{da,rt}_generic_constraints/` (2016-03+)
- [ ] Unified time-aligned storage (Parquet + DuckDB)
- [ ] Data quality dashboard (missingness, drift)

### Stage 1 — Hub-pair baseline (Month 3-4)
- LightGBM, 4-6 hub-pair spread models (DAM only first)
- Quantile regression
- First end-to-end backtest → P&L benchmark
- **Purpose**: data pipeline validation, not the real model

### Stage 2 — Universal constraint model (Month 5-7)
- Constraint embedding design
- Binding classifier + conditional shadow price regressor (LightGBM or shallow MLP)
- DAM first, RTM added once DAM is stable
- Multi-task / shared backbone introduced
- PTDF projection → nodal MCC reconstruction
- GK node P&L validation

### Stage 3 — DCOPF-informed (Month 8-10)
- Two-tower architecture (network state encoder + constraint encoder)
- KKT-informed loss (primal feasibility, dual feasibility, complementarity)
- Out-of-distribution / outage scenario testing
- Production inference latency optimization

### Stage 4 — GNN (optional, Month 11-12)
- Decision gate: only proceed if Stage 3 has clear topology-change failures
- Node = bus, edge = line, message passing
- Realistic expectation: marginal improvement over Stage 3 except for outage robustness

## 5. Data inventory

> All Stage 0 sources resolved to `yedatalake://` paths (2026-05-26). Column schemas live in each folder's `ddl.json`.

> **Historical training window**: Training data starts **2020-02-01**, aligned with the earliest `settle_shift_factors_ercot` availability. No data prior to 2020-02-01 is ingested even if datalake has earlier history — the cap is intentional for shift-factor alignment. Decision: 2026-05-26.

### Static (rarely changes)
- Network topology (bus, branch, transformer)  ← `yedatalake://ercot/metadata/objects/{facility,all}.csv.gz`
- PTDF / LODF matrices — **shift factor variants** (see Tier 1)
- Generator → bus mapping, fuel type, capacity  ← `yedatalake://ercot/metadata/objects/{ercot_plant,ercot_unit}.csv.gz`
- Constraint definitions (monitored element + contingency pairs)  ← `yedatalake://ercot/metadata/objects/contingency.csv.gz` + DA constraint history

### Daily
- ERCOT 60-day disclosure (settlement prices, SCED, AS, binding constraints)  ← `yedatalake://ercot/transmission/constraints/da/{YYYYMMDD}.csv.gz` + `ercot_sced_shift_factors/...`
- DAM / RTM clearing  ← `yedatalake://ercot/prices/bus_lmp/{YYYYMMDD}.csv.gz` + `prices/lmp/15min/...`
- CRR auction results (monthly issuance, accumulated)  ← `yedatalake://ercot/ftr/auction/{YYYY_MM_monthly|YYYY_annual}/*.csv.gz`
- Outage schedules (planned + forced)  ← `yedatalake://ercot/transmission/outages/actual/{YYYYMMDDHH}.csv.gz`

### Hourly / sub-hourly
- Load forecast and actual by weather zone  ← `yedatalake://ercot/vintage/...` (publish-time vintage tree) + actual via weather/REST
- Wind/solar forecast (STWPF, STPPF, WGRPP, PVGRPP, all vintages) and actual  ← `yedatalake://ercot/vintage/...`
- Real-time SCED outputs  ← `yedatalake://ercot/transmission/constraints/ercot_sced_shift_factors/...`
- Weather (zone-level forecast + actual) — Stage 0/1. HRRR hub-height wind / GHI 는 Stage 2.  ← `yedatalake://ercot/weather/{forecast,actual}/{YYYYMMDD}.csv.gz`
- Henry Hub + Waha gas  ← `yedatalake://ercot/prices/gas/` (W4 진입 시 정확한 sub-path 확인)

### Critical features (priority order)
**Tier 1 — required**
- PTDF / LODF matrix — **shift factor 4종 variants** (all `yedatalake://ercot/transmission/constraints/...`):
  - `market_shift_factors/` — DAM pricenode-level + SHADOWPRICE + LIMIT (2016-01+) — DAM model PTDF projection 1차 source
  - `ercot_sced_shift_factors/` — RT/SCED resource-level (2011-12+) — RTM model PTDF input
  - `settle_shift_factors_ercot/` — SP-level (2020-02+) — P&L attribution
  - `shift_factors/` — generic pricenode-level + QUALITY_METRIC (2015-01+) — quality filter
  - Base case + post-contingency PTDF (LODF effect) 모두 (CONSTRAINT, CONTINGENCY, RESOURCE|PNODE|SP) → SHIFTFACTOR 트리플로 발행됨 — 별도 LODF 행렬 계산 불필요.
- Constraint definitions  ← `yedatalake://ercot/metadata/objects/contingency.csv.gz`, `facility.csv.gz`
- Generator-bus mapping, fuel, capacity  ← `yedatalake://ercot/metadata/objects/{ercot_plant,ercot_unit}.csv.gz`
- Outage list  ← `yedatalake://ercot/transmission/outages/actual/...`
- Load by zone (forecast + actual)  ← `yedatalake://ercot/vintage/...` (forecast vintages) + `weather/actual/...`
- Wind/solar forecast by zone  ← `yedatalake://ercot/vintage/...`
- DAM clearing (also input to RTM model)  ← `yedatalake://ercot/prices/bus_lmp/...`

**Tier 2 — high lift**
- Hub-height wind speed by zone (NOAA HRRR, 80m & 100m)
- Solar GHI/DNI by zone + cloud cover
- Henry Hub + Waha gas
- CRR auction clearing prices (forward expectation)
- Net load + ramp rate
- Inter-zone wind generation gradient
- Reserve margin / PRC
- DC tie schedules (SPP, MISO South, Mexico)

**Tier 3 — margin**
- Forecast error history by vintage
- Virtual bid distribution
- Operator action history
- Temperature by zone (load + thermal derating)
- Constraint binding lag features (1h, 6h, 24h, 168h)

**Regime indicators**
- Summer peak season flag (Jun-Sep)
- Winter weather event flag
- ORDC scarcity active flag
- Holiday flag

## 6. Data leakage rules — strictly enforced

### DAM model
- **Cutoff**: D-1 10:00 CT (DAM bid submission close)
- **Allowed**: settlement up to D-2, D day weather forecast received before cutoff, D day load forecast, latest outage report, most recent CRR auction
- **Forbidden**: any D day RT data, any forecast updated after D-1 10:00

### RTM model
- **Cutoff**: t - 5min (next SCED cycle)
- **Allowed**: SCED outputs through t-5min, RT load/wind/solar through t-5min, that day's DAM cleared (already known from D-1), latest 15-min nowcast
- **Forbidden**: anything timestamped at t-5min or later

## 7. Validation methodology

### Splits — temporal only
- Train: ~3 years
- Validation: trailing 3-6 months
- Test: most recent 1-3 months
- Random splits are **forbidden**

### Stratified evaluation
Always report metrics broken down by:
- Season (summer peak / winter / shoulder)
- Binding event vs non-binding
- Major weather event (Uri-class) separately
- High wind vs low wind
- Tx outage active vs not

### Metrics
- **Constraint-level**: AUC, Brier score, top-K binding hit rate, pinball loss per quantile
- **Nodal-level (after PTDF projection)**: dollar-weighted MAE (weight by |LMP|)
- **GK node**: separate report (primary use case)
- **Trading P&L**: virtual bid sim + CRR auction sim — *the* metric

### Backtest discipline
- Cutoff every input strictly to leakage rules
- No retraining on test data
- Report metrics for at least 3 distinct months

## 8. Known ERCOT-specific gotchas

- **Constraint universe changes** — handled via embedding (see §3)
- **Settlement vs SCED granularity** — SCED 5-min, settlement 15-min SPP. Define target precisely per model.
- **Operator overrides** — manual constraint enforcement happens; treat as outliers, do not train naively
- **GTBD (generic transmission constraints)** — not standard thermal, ERCOT-specific stability constraints. Separate handling.
- **DC ties** — SPP, MISO South, Mexico CFE. Schedules matter for South Texas congestion.
- **Bitcoin miner vs AI data center load** — different price responsiveness; separate metadata if available.

## 9. Open decisions

- [x] CRR data subscription path — ✅ **datalake로 결정 (2026-05-26)** — `yedatalake://ercot/ftr/auction/`. ERCOT API 별도 subscription 불필요.
- [x] HRRR weather pipeline — ⏸ **Stage 2 로 deferred (2026-05-26)** — Stage 0/1 은 datalake zone-level (`yedatalake://ercot/weather/{forecast,actual}/`) 로 충분. Stage 2 universal constraint model 이 hub-height wind / GHI 를 요구할 때 NOMADS 직접 vs commercial 재논의.
- [ ] Initial constraint subset for Stage 1 — full list vs top-N by historical binding frequency
- [ ] Online learning vs scheduled retraining cadence (regime change handling)
- [ ] Inference latency target for RTM (5-min cycle is hard cap)

## 10. Repo layout (planned)

```
ercot-congestion/
├── CONGESTION_PROJECT.md          # this file — project state
├── .claude/
│   ├── agents/
│   │   └── congestion-analyst.md
│   └── agent-memory/
│       └── congestion-analyst/
│           └── MEMORY.md           # accumulated session notes
├── data/
│   ├── raw/                        # datalake mirror — Hive-partitioned by year
│   │   └── ercot/                  # mirrors yedatalake://ercot/ key prefix
│   │       ├── transmission/
│   │       │   ├── constraints/{da, market_shift_factors, ercot_sced_shift_factors, settle_shift_factors_ercot, shift_factors}/year=YYYY/*.parquet
│   │       │   └── outages/actual/year=YYYY/*.parquet
│   │       ├── prices/{bus_lmp, lmp/15min, gas}/year=YYYY/*.parquet
│   │       ├── ftr/auction/year=YYYY/*.parquet
│   │       ├── flow/ercot_{da,rt}_generic_constraints/year=YYYY/*.parquet
│   │       ├── weather/{forecast,actual}/year=YYYY/*.parquet
│   │       ├── vintage/<series>/year=YYYY/*.parquet
│   │       └── metadata/objects/*.parquet
│   ├── interim/                    # cleaned, time-aligned, normalized join keys
│   ├── features/                   # ML-ready Parquet
│   └── network/                    # NMMS-derived auxiliaries. shift factor 는 raw 에서 직접 load — 별도 PTDF 행렬 파일 불필요.
├── src/
│   ├── ingestion/                  # Stage 0 deliverable — 9 datalake modules (2026-05-26)
│   │   ├── _datalake_client.py             # boto3 factory + ddl.json parser
│   │   ├── datalake_metadata.py            # facility/contingency/plant/unit/all
│   │   ├── datalake_constraints.py         # DA binding constraints + λ
│   │   ├── datalake_shift_factors.py       # 4종 PTDF variants
│   │   ├── datalake_lmp.py                 # bus_lmp + lmp/15min
│   │   ├── datalake_outages.py             # transmission/outages/actual
│   │   ├── datalake_ftr.py                 # CRR/FTR auction
│   │   ├── datalake_vintage.py             # publish-time forecast snapshots
│   │   ├── datalake_weather.py             # weather/forecast + actual
│   │   └── datalake_gas.py                 # Henry Hub + Waha
│   ├── network/                    # PTDF query helpers, topology, constraint embedding
│   ├── features/
│   ├── models/
│   │   ├── stage1_baseline/
│   │   ├── stage2_universal/
│   │   └── stage3_dcopf/
│   ├── validation/
│   └── backtest/
├── notebooks/                      # exploration only
├── runs/                           # model training outputs
│   └── <YYYYMMDD-HHMMSS-tag>/
│       ├── config.yaml
│       ├── metrics.json
│       ├── predictions.parquet
│       └── summary.md
├── configs/
└── tests/
```

## 11. References

- ERCOT NMMS documentation
- ERCOT Nodal Operating Guide (constraint definitions, ORDC mechanics)
- NOAA HRRR data access (NOMADS / Google Cloud public dataset)
- YES Energy Data Lake schema (S3, DuckDB)
- DCOPF formulation: standard textbook (Wood & Wollenberg, ch. 6)
- KKT-informed neural networks: relevant papers in `references/papers/` (to be added)
