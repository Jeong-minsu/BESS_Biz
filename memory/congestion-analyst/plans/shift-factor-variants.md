# Shift Factor 4 Variants — Usage Guide

**Decision date**: 2026-05-26  
**Applies to**: Stage 0 W2, all subsequent modeling stages

---

## Overview

ERCOT publishes 4 shift factor (PTDF) variants in the Yes Energy datalake under
`yedatalake://ercot/transmission/constraints/{variant}/{YYYYMMDD}.csv.gz`.

All 4 variants share the same physical meaning:
  **SHIFTFACTOR** = ΔFlow_constraint / ΔInjection_resource  (unitless, dimensionless)
  MCC_node = -Σ_c (SHIFTFACTOR_{node,c} × λ_c)   [Stage 2 projection formula]

They differ in the **reference entity** (pricenode vs resource vs settlement point),
**market context** (DAM vs SCED vs settlement), and **availability period**.

---

## Variant Table

| ID | S3 Path | Ref Entity | Market | Available From | Rows/Day (2026) | W2 Parquet |
|----|---------|-----------|--------|---------------|-----------------|-----------|
| 0.4 | `market_shift_factors/` | PRICENODEID | DAM+RT | 2016-01 | ~788K | `year=YYYY/part.parquet` |
| 0.5 | `ercot_sced_shift_factors/` | RESOURCENAME, SETTLEMENTPOINT | SCED 5-min | 2011-12 | ~445K | `year=YYYY/part.parquet` |
| 0.6 | `settle_shift_factors_ercot/` | SETTLEMENTPOINT | Settlement | 2020-02-23 | ~340K | `year=YYYY/part.parquet` |
| 0.7 | `shift_factors/` | PNODEID | DAM | 2015-01 | ~9.7K | `year=YYYY/part.parquet` |

---

## 0.4 market_shift_factors — PRIMARY for DAM Modeling

**Use case**: Stage 2 DAM binding classifier + λ regressor. This is the PTDF matrix
that ERCOT's DAM optimizer actually used when clearing the market. λ values in this
file match the DA constraint shadow prices in `constraint_binding_history.parquet`.

**Key columns retained** (after W2 pruning):
- `PRICENODEID` — pricenode (join to DA LMP bus)
- `FACILITYID` — monitored facility (join to facility metadata)
- `CONTINGENCYID` — contingency scenario (join to contingency metadata)
- `DATETIME` — interval end timestamp (CDT/CST)
- `MARKET` — "RT" or "DA" (DA = DAM clearing PTDF)
- `SHIFTFACTOR` — the PTDF value

**Dropped**: TIMEZONE, SHADOWPRICE (in DA constraints), LIMIT (in DA constraints),
CONSTRAINTID (derivable), CONSTRAINTNAME (in metadata), LOADID (batch ID).

**W2 join**: `market_shift_factors` × `constraint_binding_history` on
(FACILITYID, CONTINGENCYID, date+hour) → (PRICENODEID, λ) for MCC reconstruction.

---

## 0.5 ercot_sced_shift_factors — RTM Model Input

**Use case**: Stage 2 RTM (real-time) binding classifier. Resource-level PTDF from
the actual SCED run. Required for gen-level contribution analysis and RTM λ prediction.

**Key columns retained**:
- `DATETIME` — SCED interval timestamp (5-min resolution)
- `CONSTRAINTID` — constraint being monitored
- `RESOURCENAME` — generating resource name
- `SETTLEMENTPOINT` — settlement point for the resource
- `SHIFTFACTOR` — the PTDF value

**Dropped**: TIMEZONE, CONSTRAINTNAME, CONTINGENCY, LOADID.

**Critical size note**: ~445K rows/day × 2304 days = ~1 billion rows total.
Largest of the 4 variants. Parquet (zstd) estimated ~8-12 GB.

---

## 0.6 settle_shift_factors_ercot — P&L Attribution (SP-Level)

**Use case**: Post-hoc settlement P&L attribution. Maps settlement point → constraint
→ shift factor as used in final settlement. Starts 2020-02-23.

**Key columns retained**:
- `DATETIME` — settlement interval
- `CONSTRAINTID` — constraint
- `SETTLEMENTPOINT` — settlement point (SP)
- `SHIFTFACTOR` — SP-level PTDF

**Dropped**: TIMEZONE, CONSTRAINTNAME, CONTINGENCY, LOADID.

**History note**: Only available from 2020-02-23 onward. This is the binding constraint
on the training window start date (2020-02-01). Files 2020-02-01 through 2020-02-22
do not exist in the datalake.

---

## 0.7 shift_factors — Quality Filter

**Use case**: Cross-validation / sanity check. Contains `QUALITY_METRIC` column
(1.0 = high confidence, <1.0 = degraded). Use to filter out low-quality PTDF rows
before feeding Stage 2 features. Dataset is tiny (~0.2 GB total).

**All columns retained** (dataset is small):
- `CONSTRAINT_DAY` — the day the constraint was active
- `DATETIME` — specific interval
- `FACILITYID`, `CONTINGENCYID` — constraint keys
- `ISO` — always ERCOT
- `PNODEID`, `PNODENAME` — pricenode reference
- `SHIFT_FACTOR` — the PTDF value (note: column name uses underscore, not CAMEL)
- `QUALITY_METRIC` — 1.0 = full confidence
- `SHADOWPRICE` — shadow price at this interval

---

## Join Key Cross-Reference

| Variant | Entity Column | Joins to |
|---------|--------------|---------|
| market_shift_factors | PRICENODEID | LMP bus metadata |
| market_shift_factors | FACILITYID | facility.OBJECTID → FACILITYNAME |
| market_shift_factors | CONTINGENCYID | contingency.OBJECTID → CONTINGENCYNAME |
| ercot_sced_shift_factors | CONSTRAINTID | constraint_binding_history.CONSTRAINTID |
| settle_shift_factors_ercot | CONSTRAINTID | constraint_binding_history.CONSTRAINTID |
| settle_shift_factors_ercot | SETTLEMENTPOINT | settlement point metadata |
| shift_factors | FACILITYID | facility.OBJECTID |
| shift_factors | CONTINGENCYID | contingency.OBJECTID |

---

## MCC Reconstruction Formula (W2 Exit Gate)

For a given pricenode `n` and hour `h`:

```
MCC_n_h = -Σ_c (SF_{n,c,h} × λ_{c,h})
```

where:
- `SF_{n,c,h}` comes from `market_shift_factors` (MARKET='DA', matching hour)
- `λ_{c,h}` comes from `constraint_binding_history.PRICE` (same facility+contingency+hour)

**Sanity check target**: reconstructed MCC should match actual DAM LMP MCC component
within ±5% for the top-50 most binding constraints.
