# Shift Factor 4 Variants — Unified Column Schema

**Generated**: 2026-05-26  
**Source**: Yes Energy datalake `yedatalake://ercot/transmission/constraints/{variant}/ddl.json`

---

## Column Mapping Table

| Column | market_shift_factors | ercot_sced_shift_factors | settle_shift_factors_ercot | shift_factors |
|--------|---------------------|------------------------|--------------------------|---------------|
| Timestamp | `DATETIME` | `DATETIME` | `DATETIME` | `DATETIME` |
| Day reference | — | — | — | `CONSTRAINT_DAY` |
| Timezone | `TIMEZONE` ❌ | `TIMEZONE` ❌ | `TIMEZONE` ❌ | — |
| Pricenode ID | `PRICENODEID` ✅ | — | — | `PNODEID` ✅ |
| Pricenode name | — | — | — | `PNODENAME` ✅ |
| Settlement point | — | `SETTLEMENTPOINT` ✅ | `SETTLEMENTPOINT` ✅ | — |
| Resource name | — | `RESOURCENAME` ✅ | — | — |
| Facility ID | `FACILITYID` ✅ | — | — | `FACILITYID` ✅ |
| Contingency ID | `CONTINGENCYID` ✅ | — | — | `CONTINGENCYID` ✅ |
| Contingency name | `CONTINGENCY` ❌ | `CONTINGENCY` ❌ | `CONTINGENCY` ❌ | — |
| Constraint ID | `CONSTRAINTID` ❌ | `CONSTRAINTID` ✅ | `CONSTRAINTID` ✅ | — |
| Constraint name | `CONSTRAINTNAME` ❌ | `CONSTRAINTNAME` ❌ | `CONSTRAINTNAME` ❌ | — |
| Market | `MARKET` ✅ | — | — | — |
| Shift factor | `SHIFTFACTOR` ✅ | `SHIFTFACTOR` ✅ | `SHIFTFACTOR` ✅ | `SHIFT_FACTOR` ✅ |
| Shadow price | `SHADOWPRICE` ❌ | — | — | `SHADOWPRICE` ✅ |
| Limit MW | `LIMIT` ❌ | — | — | — |
| Quality metric | — | — | — | `QUALITY_METRIC` ✅ |
| ISO | — | — | — | `ISO` ✅ |
| Load ID | `LOADID` ❌ | `LOADID` ❌ | `LOADID` ❌ | — |

✅ = retained in W2 parquet   ❌ = dropped (redundant or analytically low-value)

---

## Column Name Normalization

The shift factor column is inconsistently named across variants:
- `market_shift_factors`: `SHIFTFACTOR` (camelCase-ish)
- `ercot_sced_shift_factors`: `SHIFTFACTOR`
- `settle_shift_factors_ercot`: `SHIFTFACTOR`
- `shift_factors`: `SHIFT_FACTOR` (with underscore — note the difference!)

**When joining across variants**, normalize to `SHIFTFACTOR` or handle this difference explicitly.

---

## Constraint Identity Key

Different variants use different identifiers for constraints:

| Variant | Constraint Key | Type | Join Path |
|---------|---------------|------|-----------|
| market_shift_factors | (FACILITYID, CONTINGENCYID) | int64 pair | facility.OBJECTID + contingency.OBJECTID |
| ercot_sced_shift_factors | CONSTRAINTID | float64 | constraint_binding_history.CONSTRAINTID |
| settle_shift_factors_ercot | CONSTRAINTID | int64 | constraint_binding_history.CONSTRAINTID |
| shift_factors | (FACILITYID, CONTINGENCYID) | int64 pair | facility.OBJECTID + contingency.OBJECTID |

The `market_shift_factors.CONSTRAINTID` column exists in the raw file but was dropped
in W2 parquets (redundant given FACILITYID + CONTINGENCYID). If needed, re-derive via
the metadata join.

---

## Temporal Resolution

| Variant | Resolution | Notes |
|---------|-----------|-------|
| market_shift_factors | Hourly (~5min interval within hour) | DATETIME includes HH:MM:SS — aggregate to hourly |
| ercot_sced_shift_factors | 5-minute | Real-time SCED cycle cadence |
| settle_shift_factors_ercot | 15-minute | Settlement interval (SPP period) |
| shift_factors | 5-minute | Multiple intervals per constraint day |

When joining to `constraint_binding_history` (hourly), truncate DATETIME to the hour.

---

## Storage Layout

```
data/raw/ercot/transmission/constraints/
├── market_shift_factors/
│   ├── year=2020/part.parquet   (~788K rows/day × 335 days)
│   ├── year=2021/part.parquet
│   ├── ...
│   └── year=2026/part.parquet
├── ercot_sced_shift_factors/
│   └── year=YYYY/part.parquet
├── settle_shift_factors_ercot/
│   └── year=YYYY/part.parquet   (starts 2020-02-23, not 2020-02-01)
└── shift_factors/
    └── year=YYYY/part.parquet
```

**Compression**: zstd (better than snappy for this data — ~0.35-0.45× gz size)
