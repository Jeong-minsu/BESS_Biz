---
name: estimate-bess-energy-as
description: Use when estimating DA/RT energy + ancillary-service (RegUp/RegDown/RRS/ECRS/NonSpin) revenue for ERCOT BESS resources from public ERCOT 60-day SCED/DAM disclosure data — e.g. the pnl-manager weekly all-BESS energy/AS revenue ranking, optimization-rate, or TB-index work. Computes Two-Settlement revenue for every ERCOT storage resource over a date range, with dual-era (pre/post RTC+B) handling. Vendored from the user's ERCOT_SCED_PJT project. Triggers - "estimate all BESS energy/AS revenue", "fleet BESS revenue ranking from SCED", "optimization rate vs TB index", "60-day disclosure revenue".
---

# Estimate BESS Energy + AS Revenue — ERCOT SCED/DAM Disclosure

Estimates **DA/RT energy + ancillary-service revenue** for **every ERCOT BESS
(ESR / PWRSTR) resource** over a date range, straight from ERCOT's public
60-day disclosure data. Also produces the **TB index** (theoretical-best
revenue) and the **optimization rate** (actual ÷ theoretical).

This is the engine behind the `pnl-manager` weekly *all-BESS energy/AS revenue
dashboard + ranking* deliverable. It estimates the **whole fleet from public
data** — it is not Tenaska PTP (which is GKS-only settled data).

The code under `scripts/src/` and `scripts/config.py` is **vendored verbatim**
from the user's `ERCOT_SCED_PJT` project. The skill adds one thin orchestration
runner (`scripts/run_estimate.py`); it does **not** re-implement the settlement
logic. See "Provenance & re-sync" at the bottom.

---

## When to use / not use

**Use for:** weekly all-BESS energy+AS revenue ranking; optimization-rate /
TB-index analysis; any historical fleet revenue estimate from public ERCOT data.

**Do NOT use for:**
- GKS settled actuals → that is Tenaska PTP, skill `fetch-tenaska-ptp-data`.
- DART **virtual** (energy-only offer/bid) revenue → skill
  `estimate-bess-dart-virtual`. Virtual trades are a separate dataset; the two
  skills sum to a fleet's total — do not double-count.
- Forward bidding / strategy → that is the `bess-optimizer` agent.

---

## How to run

Run from the **BESS_Biz repo root**. Install deps once:

```bash
pip install -r skills/estimate-bess-energy-as/scripts/requirements.txt
```

Then:

```bash
python skills/estimate-bess-energy-as/scripts/run_estimate.py \
    --start 2026-01-01 --end 2026-05-20
```

- `--start` / `--end` — flow dates, `YYYY-MM-DD`, both inclusive.
- `--out-dir` — optional; default `shared/data/pnl/all_bess/energy_as/`.

The runner loads ERCOT + Yes Energy Datalake credentials from `BESS_Biz/.env`
(via `shared/scripts/_env_loader.py`), runs the vendored pipeline, and writes
parquet outputs. It prints a fleet total, median optimization rate, and a
Top-10 revenue table to stdout.

> **Runtime:** first run of a date range downloads + caches ERCOT/S3 data to
> `scripts/data/cache/` (parquet). Re-runs of the same range are fast (cache
> hit). A full Jan→May fleet run is minutes, not seconds.

---

## Method

### Data sources (dual-era — auto-selected per date)

RTC+B cutover = **2025-12-05**. The pipeline splits any range that straddles it.

| Item | Pre-RTC+B (`< 2025-12-05`) | Post-RTC+B (`>= 2025-12-05`) |
|---|---|---|
| DA energy/AS | 60d DAM Gen Resource Data (PWRSTR) | 60d DAM ESR Data (ERCOT API) |
| RT output | 60d SCED Gen Resource Data | 60d ESR Data in SCED (ERCOT API) |
| DA AS MCPC | DAM Gen Resource Data | embedded in DAM ESR Data |
| RT AS MCPC | Yes Energy S3 `rtc_mcpc_*` (system-level) | same |
| RT LMP | Yes Energy S3 `bus_lmp` / SPP 15-min | same |

Yes Energy here is the **Datalake (S3)** — `YES_ENERGY_ACCESS_KEY` /
`YES_ENERGY_SECRET_KEY`, not the DataSignals API.

### Revenue formula — Two-Settlement (single unified equation)

Energy and every AS product use the **same** formula (ERCOT Nodal Protocol
§4.6 + §6.7):

```
Total Revenue = DA_MW · DA_Price + (RT_MW − DA_MW) · RT_Price
```

- Energy: `DA_MW·DA_LMP + (RT_MW−DA_MW)·RT_LMP`
- AS (per product): `DA_MW·DA_MCPC + (RT_MW−DA_MW)·RT_MCPC`
- The `(RT_MW − DA_MW)` term is the **RT imbalance / AS buyback** — RT AS
  awards are typically 30–40 % of DA (SOC limits), and RT MCPC ≠ $0, so this
  term is material and is always included.
- Revenue is computed at the **native granularity** (5-min SCED / 15-min),
  scaled by interval length, then summed to hourly — never `mean(P)·mean(Q)`.

AS products: **RegUp, RegDown, RRS, ECRS, NonSpin**. A deviation penalty is
applied when SCED Base Point and Telemetered Net Output diverge (pre-RTC+B).

### TB index + optimization rate

- **TB index** — theoretical-best one-cycle-per-day revenue from RT LMP:
  top-N consecutive hours minus bottom-N, charge-before-discharge, with
  fractional-duration interpolation (e.g. TB(1.5h) = TB1·0.5 + TB2·0.5).
- Battery duration priority: ESS-capacity CSV → SCED SOC estimate
  `(MaxSOC−MinSOC)/HSL` → fleet median fallback.
- **Optimization rate** = `Σ daily actual revenue ÷ Σ daily TB revenue × 100`,
  matched day-for-day per resource. `TB revenue = TB index ($/MW) × MW`.

---

## Critical gotchas (already handled by the vendored code — do not "fix")

1. **AS merge after hourly aggregation.** Energy is sub-hourly (5-min SCED), AS
   is hourly (DAM). Energy must be aggregated to hourly *first*, then AS merged
   at hourly level. Merging on raw timestamps loses ~87 % of AS revenue.
2. **Hour-ending vs hour-beginning.** DA/AS timestamps are hour-ending
   (`01:00` = HE1); SCED/RT are hour-beginning. The pipeline subtracts 1 h to
   align. Mixing them shifts revenue by an hour.
3. **Interval scaling.** A 5-min row is `MW·price·(1/12)`. Without scaling,
   sub-hourly revenue is overstated 12×.
4. **Settlement-point ↔ objectid.** DA data uses SP *names*; RT LMP uses
   numeric *objectids*. A name→objectid map is built from `dam_en_off_awrd`;
   on mapping failure DA LMP is the RT fallback.
5. **SCED ZIP de-duplication.** ERCOT sometimes posts identical SCED ZIPs for
   two operating dates; `_operating_date` (delivery date) is the canonical date.
6. **`sequenceOptions` / versioned data** — latest version only, else double-count.

---

## Output schema

Written to `--out-dir` (default `shared/data/pnl/all_bess/energy_as/`), tagged
`{start}_{end}`:

| File | Grain | Key columns |
|---|---|---|
| `revenue_hourly_{tag}.parquet` | resource × hour | `resource_name`, `datetime`, `da_energy_rev`, `rt_energy_rev`, `regup_rev`, `regdn_rev`, `rrs_rev`, `ecrs_rev`, `nonspin_rev`, `deviation_penalty`, `total_rev`, `da_lmp`, `rt_lmp` |
| `summary_{tag}.parquet` / `.csv` | resource | `resource_name`, per-product `*_rev`, `total_rev`, `tb_index`, `theoretical_rev`, `optimization_rate`, `duration_hours`, `capacity_mw`, `company`, `site`, `settlement_point`, `hsl` |
| `tb_index_{tag}.parquet` | resource × day | `resource_name`, `date`, `tb_index`, `tb_rev`, `daily_actual_rev`, `duration_hours`, `capacity_mw` |

`summary_*.csv` is the direct input for the `pnl-manager` weekly all-BESS
energy/AS ranking dashboard (render with the `dashboard-report` skill).

> **Estimate, not settlement.** This is a public-data estimate. Flag it as such
> in any deliverable; do not reconcile it to invoiced settlement.

---

## Credentials

From `BESS_Biz/.env`, sections **ERCOT** and **Yes Energy Datalake**:

```
ERCOT_USERNAME, ERCOT_PASSWORD, ERCOT_SUBSCRIPTION_KEY
YES_ENERGY_ACCESS_KEY, YES_ENERGY_SECRET_KEY
```

The runner loads these via `shared/scripts/_env_loader.py` — no secrets are
printed. Vendor domains may be blocked on some corporate networks; run locally
or on VPN.

---

## Provenance & re-sync (vendored snapshot)

`scripts/config.py` and everything under `scripts/src/` are copied **verbatim**
from `ERCOT_SCED_PJT`. `scripts/ESS capacity.csv` is its BESS capacity
reference. Only `scripts/run_estimate.py` is original to this skill.

> **Accepted duplication.** The sibling skill `estimate-bess-dart-virtual`
> vendors its own independent ERCOT Public API client (B2C auth + retry +
> archive ZIP). The two snapshots are intentionally isolated — an ERCOT auth
> or archive-endpoint change must be re-synced into **both** skills.

| Vendored | Source (`ERCOT_SCED_PJT/`) |
|---|---|
| `scripts/config.py` | `config.py` |
| `scripts/src/*.py` | `src/*.py` (data_fetcher, ercot_api_fetcher, revenue_calculator, tb_index, pipeline) |
| `scripts/ESS capacity.csv` | `ESS capacity.csv` |

Snapshot: **2026-05-21** (ERCOT_SCED_PJT is a local, non-git project).

**This is a snapshot — it does not auto-track the source repo.** When the
estimation logic in `ERCOT_SCED_PJT` is improved, re-sync:

```bash
SRC="C:/Users/00904/ERCOT Projects/ERCOT_SCED_PJT"
DST="C:/Users/00904/ERCOT Projects/BESS_Biz/skills/estimate-bess-energy-as/scripts"
cp "$SRC/config.py" "$DST/config.py"
cp "$SRC/src/"{data_fetcher,ercot_api_fetcher,revenue_calculator,tb_index,pipeline}.py "$DST/src/"
cp "$SRC/ESS capacity.csv" "$DST/ESS capacity.csv"
```

Then re-run the smoke test (`python -c "import sys; ..."` — import check) and
update the snapshot date above. If the source's import structure or
`config.py` credential keys change, also review `run_estimate.py`.
