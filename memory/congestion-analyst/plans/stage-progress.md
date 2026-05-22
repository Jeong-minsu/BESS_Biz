# CONGESTION_PROJECT — Stage Progress Tracker

**Source of truth**: `agensts/CONGESTION_PROJECT.md`
**Maintained by**: `congestion-analyst` agent
**Updated**: 2026-05-22

---

## Current Stage

**Stage 0 — Infrastructure setup** (시작 전 / not yet started)

### Stage 0 Checklist (from CONGESTION_PROJECT.md §4)

- [ ] ERCOT API ingestion (DAM/RTM clearing, binding constraints, SCED)
- [ ] NMMS network model parsing → bus, branch, generator tables
- [ ] PTDF / LODF matrix extraction (monthly snapshots)
- [ ] CRR auction history ingestion
- [ ] Outage data (60-day disclosure + transmission)
- [ ] Weather pipeline (NOAA HRRR, by zone, hub-height wind)
- [ ] Henry Hub + Waha gas
- [ ] Unified time-aligned storage (Parquet + DuckDB)
- [ ] Data quality dashboard (missingness, drift)

---

## Open Decisions (from CONGESTION_PROJECT.md §9)

- [ ] CRR data subscription path — direct ERCOT API vs YES Energy
- [ ] HRRR weather pipeline — direct NOMADS download vs commercial provider
- [ ] Initial constraint subset for Stage 1 — full list vs top-N by historical binding frequency
- [ ] Online learning vs scheduled retraining cadence
- [ ] Inference latency target for RTM (5-min cycle hard cap)

---

## Daily output during Stage 0

본 stage 동안 congestion-analyst가 산출 가능한 것:
- **Hub-pair basis 히스토리**: 단순 `DALMP:WEST_HUB - DALMP:NORTH_HUB` 평균/분포 — 정량 view
- **Binding constraint 빈도** (60-day disclosure 가공): 어떤 constraint가 자주 binding하는지 통계
- **Top constraint list**: 다음 단계 모델링 후보군

산출물 형식: 위 두 가지로 D+1 outlook 제한적 작성. **shadow price 모델링은 Stage 2까지 미실시**.

### Stage 0 heuristic signals established (as of 2026-05-22)

Through daily provisional outlook cycles (2026-05-05, 2026-05-22, 2026-05-23), the following heuristic signals have been validated as internally consistent and useful at Stage 0:

1. **Enverus wind STPF midday trough**: ERCOT-wide wind at HE10-13 is the primary quantitative proxy for WEST_TO_NORTH binding probability. Proposed threshold: STPF trough < 4,000 MW AND solar > 15,000 MW → P(binding) MEDIUM-HIGH.
2. **Smartbidder P(DA<RT) HE09-13**: Values of 0.60-0.65 are consistent with West zone DA prices being bid below expected RT — canonical West export congestion signature.
3. **Net load ramp magnitude (Enverus) HE17-20**: Ramp > 8,000 MW in 3 hours → MEDIUM probability South/Houston import binding.
4. **Smartbidder DA-RT spread at HE20**: The aggregate hub DA-RT spread at the evening peak is the best available shadow price proxy until hub-pair LMP data is obtained.

These heuristics should be formalized into the Stage 1 LightGBM feature set.

### Critical data gaps blocking Stage 1

1. **Hub-pair LMP data** (HB_NORTH, HB_SOUTH, HB_WEST, HB_HOUSTON): Not in current Yes Energy pull. Required for basis view and constraint calibration. Action: modify fetch_market_data.py to add hub LMP endpoint.
2. **ERCOT 60-day disclosure**: No constraint-level binding history. Blocking constraint enumeration for Stage 1 model. Action: ERCOT MIS API ingestion (cdr.00013068 or equivalent).

---

## Stage transition gates

| Stage | Trigger | KPI |
|---|---|---|
| 0 → 1 | All Stage 0 checklist done | Data quality dashboard green for 14 days |
| 1 → 2 | Hub-pair backtest end-to-end run | LightGBM beat naive 7-day persistence on 4/6 paths |
| 2 → 3 | Universal model stable on DAM | binding AUC ≥ 0.85, λ pinball loss ≤ baseline |
| 3 → 4 | Stage 3 has clear topology-failure cases | Stage 3 OOD test 3-month MAE > Stage 2 by ≥ 30% |

---

## Weekly update template

```markdown
## Week YYYY-WW
- 진행: <Stage 0 체크리스트 중 N개 완료>
- 블로커: <…>
- 다음주 목표: <…>
```
