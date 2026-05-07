# ERCOT Congestion Prediction Project

**Owner**: Minsoo (GridFlex Inc.)
**Agent**: `congestion-analyst`
**Last updated**: 2026-04-30
**Current stage**: Stage 0 — Infrastructure setup (not yet started)

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

### Stage 0 — Infrastructure (Month 1-2) — CURRENT
- [ ] ERCOT API ingestion (DAM/RTM clearing, binding constraints, SCED)
- [ ] NMMS network model parsing → bus, branch, generator tables
- [ ] PTDF / LODF matrix extraction (monthly snapshots)
- [ ] CRR auction history ingestion
- [ ] Outage data (60-day disclosure + transmission)
- [ ] Weather pipeline (NOAA HRRR, by zone, hub-height wind)
- [ ] Henry Hub + Waha gas
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

### Static (rarely changes)
- Network topology (bus, branch, transformer)
- PTDF / LODF matrices (monthly)
- Generator → bus mapping, fuel type, capacity
- Constraint definitions (monitored element + contingency pairs)

### Daily
- ERCOT 60-day disclosure (settlement prices, SCED, AS, binding constraints)
- DAM / RTM clearing
- CRR auction results (monthly issuance, accumulated)
- Outage schedules (planned + forced)

### Hourly / sub-hourly
- Load forecast and actual by weather zone
- Wind/solar forecast (STWPF, STPPF, WGRPP, PVGRPP, all vintages) and actual
- Real-time SCED outputs
- Weather (NOAA HRRR, by zone — hub-height wind, GHI, DNI, temperature)
- Henry Hub + Waha gas

### Critical features (priority order)
**Tier 1 — required**
- PTDF / LODF matrix
- Constraint definitions
- Generator-bus mapping, fuel, capacity
- Outage list
- Load by zone (forecast + actual)
- Wind/solar forecast by zone
- DAM clearing (also input to RTM model)

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

- [ ] CRR data subscription path — direct ERCOT API vs YES Energy
- [ ] HRRR weather pipeline — direct NOMADS download vs commercial provider
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
│   ├── raw/                        # API pulls, untouched
│   ├── interim/                    # cleaned, time-aligned
│   ├── features/                   # ML-ready Parquet
│   └── network/                    # NMMS, PTDF, LODF
├── src/
│   ├── ingestion/                  # ERCOT API, weather, gas
│   ├── network/                    # PTDF, topology, constraint embedding
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
