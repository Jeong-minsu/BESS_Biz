# Raven (RVN_RN) Node Analysis — Shared Brief

**Requested**: 2026-09-14 by Minsu. Goal = FY2027 revenue outlook for Raven BESS.
**Assumed asset spec**: 100 MW / 200 MWh (2h), same as GKS. TB2 = 2-hour theoretical best.
**Deliverable**: HTML dashboard (`dashboard-report` skill) + markdown report, single **Base** forecast.

---

## Reconnaissance already completed (do NOT redo)

### Node identity (from `ercot/metadata/objects/all.csv.gz`)

| Node | OBJECTID | ZONE | SUBTYPE | Note |
|---|---|---|---|---|
| `RVN_RN` | 10019925379 | **HOUSTON** | GENERATOR | Raven Storage (EIA plant "Raven Storage", CEMS unit `RAVEB`) |
| `GKS_BESS_RN` | 10017907494 | **SOUTH** | GENERATOR | our existing 100MW/200MWh asset |
| `RBN_BESS1` | 10017290064 | **HOUSTON** | GENERATOR | Brazos Bend BESS — proxy candidate |
| `TAV_RN` | 10016969364 | **HOUSTON** | GENERATOR | proxy candidate |
| `CBEC_ALL` | 10001765766 | **SOUTH** | GENERATOR | proxy candidate — **NB: SOUTH zone, not Houston** |

> RVN_RN is a **HOUSTON** zone node while GKS is **SOUTH**. This is the single most
> important structural fact for the GKS-vs-Raven comparison — different zone, different
> binding constraint set, different congestion sign behaviour.

### Price history coverage (`ercot/prices/lmp/hourly`, probed day-by-day)

- `RVN_RN`: **RT LMP from 2026-06-02**, **DA LMP from 2026-06-04**. Nothing before.
  - ⇒ Summer 2026 (6/1–8/31) comparison **uses real RVN_RN data**, no proxy needed
    (only 6/1–6/3 missing).
  - ⇒ 2026-06-04 .. 2026-09-13 (~102 days) is the **out-of-sample window for proxy validation**.
- `GKS_BESS_RN`: from 2024-08 (COD 2024-07).
- `RBN_BESS1`: from 2023-12.
- `TAV_RN`, `CBEC_ALL`: full 3-year history.

---

## Data access

### Yes Energy Datalake (S3 `yedatalake`)

Use `shared/data/adhoc/2026-09-14_raven-node-analysis/scripts/dl.py`.
It is the `2026-06-09_houston-constraint-validation/scripts/dl.py` helper **plus
`verify=False`** — the corporate proxy presents a self-signed chain and boto3 otherwise
fails with `CERTIFICATE_VERIFY_FAILED`. This is the established repo workaround
(see `skills/fetch-ercot-data/SKILL.md`). Do not "fix" it another way.

```python
import sys; sys.path.insert(0, ".../2026-09-14_raven-node-analysis/scripts")
import dl
df = dl.read_csv("ercot/prices/lmp/hourly/20260701.csv.gz", header=None)
```

### Key datalake tables

| Path | Content | Grain | File |
|---|---|---|---|
| `ercot/prices/lmp/hourly/{YYYYMMDD}.csv.gz` | **DA + RT LMP, nodal** | hourly | daily |
| `ercot/prices/lmp/15min/{YYYYMMDDHH}.csv.gz` | RT 15-min nodal | 15min | hourly |
| `ercot/prices/lmp/5min/hourly/{YYYYMMDDHH}.csv.gz` | RT 5-min nodal | 5min | hourly |
| `ercot/prices/bus_lmp/{YYYYMMDD}.csv.gz` | RT bus LMP | 5min | daily |
| `ercot/transmission/constraints/da/{YYYYMMDD}.csv.gz` | DA binding constraints + shadow price λ | hourly | daily |
| `ercot/transmission/constraints/rt/{YYYYMMDDHH}.csv.gz` | RT binding constraints + λ | 5min | hourly |
| `ercot/transmission/constraints/ercot_sced_shift_factors/{YYYYMMDD}.csv.gz` | SCED shift factors (headerless; col3 = resource node string) | | daily |
| `ercot/ancillary/rtc_mcpc_{ecrs,nspin,regdn,regup,rrs}/` | RT AS MCPC (system-wide) | 5min | daily |
| `ercot/metadata/objects/all.csv.gz` | object registry | | |
| `ercot/metadata/catalog.csv.gz` | series catalog (DATATYPEID ↔ PATH) | | |

`ercot/prices/lmp/hourly` column order (headerless):
`OBJECTID, DATETIME, TIMEZONE, DALMP, DACONG, DALOSS, RTLMP, RTCONG, RTLOSS, RTFINAL, LOADID, HALMP, HACONG, HALOSS, ISO, ALT`
— **`DACONG`/`RTCONG`/`*LOSS` are always NULL** (ERCOT does not report components).
Congestion must be derived: `MCC = -Σ(SF × λ)` over binding constraints, or as
`LMP − hub/reference`. DA/RT constraint tables carry λ in the `PRICE` column.
`DATETIME` is **period-ending, America/Chicago** (`TIMEZONE` col = CDT/CST).

### Pre-built panel

`raw/price_panel/{YYYYMM}.parquet` — all ERCOT price_nodes, 2023-09-01 .. 2026-09-13,
columns `OBJECTID, DATETIME, TIMEZONE, DALMP, RTLMP, RTFINAL, FLOWDAY`.
Built by `scripts/fetch_price_panel.py` (idempotent, monthly chunks). **Use this** —
do not re-download from S3 for price work.

### Other sources

- `skills/estimate-bess-energy-as/` — fleet DA/RT energy + AS revenue from ERCOT 60-day
  SCED/DAM disclosure; gives per-resource product mix and TB index / optimization rate.
  **RTC+B cutover = 2025-12-05** (pre/post eras use different disclosure tables).
- `skills/estimate-bess-dart-virtual/` — fleet DART virtual (energy-only offer/bid) revenue.
- `skills/fetch-ercot-data/` — vendor auth/endpoint reference.

---

## Conventions (project-wide, must follow)

- **Spread sign**: `spread = DA − RT`. Positive ⇒ DA expensive ⇒ **short DA / long RT**.
- **Congestion sign**: `MCC = −SF × λ`.
- **AS prices are ERCOT system-wide** (RRS/ECRS/NSPIN/RegUp/RegDn MCPC have no nodal
  component). Only energy LMP is nodal. Never apply a nodal/transmission multiplier to AS.
- All wall-clock times are **CT (America/Chicago)**, DST-aware.
- **Real data only — no mock.** If a source is unavailable, say so; do not synthesise.
- Memory-safety: chunk long ranges (a prior whole-range load OOM'd at 16 GiB).

## TB2 definition to use

Per flowday and per node, separately for DA and RT hourly price series:
`TB2 = (mean of top-2 hours) − (mean of bottom-2 hours)`, in $/MWh.
Daily revenue proxy for a 100MW/2h asset = `TB2 × 200 MWh` (before efficiency).
State round-trip efficiency assumption explicitly if you apply one.
