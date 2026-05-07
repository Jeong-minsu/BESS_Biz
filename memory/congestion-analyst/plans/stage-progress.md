# CONGESTION_PROJECT — Stage Progress Tracker

**Source of truth**: `agensts/CONGESTION_PROJECT.md`
**Maintained by**: `congestion-analyst` agent
**Updated**: 2026-04-30 (initial)

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
