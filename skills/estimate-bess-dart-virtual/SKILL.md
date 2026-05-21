---
name: estimate-bess-dart-virtual
description: Use when estimating DART virtual (energy-only offer/bid) revenue for ERCOT BESS resources from public ERCOT 60-day disclosure data — e.g. the pnl-manager weekly all-BESS DART virtual revenue ranking. Computes Virtual Short (DA−RT)·MW and Virtual Long (RT−DA)·MW PnL plus win rate, profit-loss ratio, and participation rate for every ERCOT storage node over a date range. Vendored from the user's ERCOT-Dart-Tracker project. Triggers - "estimate all BESS DART virtual revenue", "fleet DART PnL ranking", "virtual short/long revenue from disclosure", "win rate / participation rate".
---

# Estimate BESS DART Virtual Revenue — ERCOT 60-day Disclosure

Estimates **DART virtual revenue** — the financial PnL of energy-only
offers/bids — for **every ERCOT BESS (PWRSTR) node** over a date range, from
ERCOT's public NP3-966-ER 60-day DAM disclosure.

This is the engine behind the `pnl-manager` weekly *all-BESS DART virtual
revenue dashboard* deliverable.

The code under `scripts/src/` is **vendored verbatim** from the user's
`ERCOT-Dart-Tracker` project. The skill adds one thin orchestration runner
(`scripts/run_estimate.py`); it does **not** re-implement the calculation.
See "Provenance & re-sync" at the bottom.

---

## What "DART virtual" is (and is not)

DART virtual = **financial** energy-only trades, settled against the DA-vs-RT
price spread. They are a *separate dataset and a separate revenue stream* from
a battery's physical energy/AS dispatch:

- This skill — `EnergyOnlyOfferAwards` + `EnergyBidAwards` (virtual trades).
- `estimate-bess-energy-as` — `ESR_Data` physical resource awards (energy+AS).

A fleet's total ≈ energy/AS + DART virtual. **Do not double-count** — keep the
two skills' outputs distinct.

**Do NOT use for:** GKS settled actuals (`fetch-tenaska-ptp-data`); forward
DART positioning (`dart-virtual-trader` agent); physical energy/AS revenue
(`estimate-bess-energy-as`).

---

## How to run

Run from the **BESS_Biz repo root**. Install deps once:

```bash
pip install -r skills/estimate-bess-dart-virtual/scripts/requirements.txt
```

Then:

```bash
python skills/estimate-bess-dart-virtual/scripts/run_estimate.py \
    --start 2026-01-01 --end 2026-03-15
```

- `--start` / `--end` — flow dates, `YYYY-MM-DD`, both inclusive.
- `--out-dir` — optional; default `shared/data/pnl/all_bess/dart_virtual/`.

The runner loads ERCOT + Yes Energy API credentials from `BESS_Biz/.env`, runs
the 3-phase pipeline, writes parquet (+ daily csv), and prints a fleet total
and Top-10 node ranking to stdout.

> **60-day lag — pick dates carefully.** A flow date's DAM disclosure is only
> published ~60 days later. Requesting a date inside the last ~60 days returns
> "no archive". For an "up to latest" run, set `--end` to ≈ today − 62 days.

> **Runtime.** Phase 1 downloads one archive ZIP per flow date (rate-limited,
> ~1.5 s min spacing); a 90-day cold range ≈ a few minutes. Archive-confirmed
> dates are cached to `scripts/data/cache/{date}/` (parquet) by the runner, so
> re-runs and weekly "up to latest" jobs only fetch new dates. Dates with no
> archive yet (60-day lag) are **not** cached, so they retry once published.

---

## Method — 3-phase pipeline

**Phase 1 — ERCOT archive, per flow date.** For each date, discover the
archive posting date (delivery + ~60 d), download the NP3-966-ER ZIP, and
extract: `ESR_Data` (→ BESS settlement-point names + HSL), `EnergyOnlyOfferAwards`
(virtual short), `EnergyBidAwards` (virtual long). Awards are filtered to the
BESS node list. Legacy archives fall back to `Gen_Resource_Data` filtered by
resource type (`PWRSTR`/`ESR`/`BESS`).

**Phase 2 — Yes Energy LMP, bulk.** Fetch DA + RT hourly LMP for the *union* of
all BESS nodes across the whole range in one bulk call (DataSignals
`/timeseries/multiple.csv`, ≤75 nodes/request). This is the Yes Energy **API**
(`YES_ENERGY_USERNAME`/`PASSWORD`) — a different product from the Datalake S3
keys the energy-as skill uses.

**Phase 3 — revenue calculation, per date.**

```
Virtual Short (offer) = (DA_LMP − RT_LMP) · Offer_Award_MW
Virtual Long  (bid)   = (RT_LMP − DA_LMP) · Bid_Award_MW
Net DART revenue      = Short + Long
```

Computed per Hour-Ending (1–24), per node, then aggregated to a daily summary
with these metrics:

- **Win rate** = hours with positive net revenue ÷ hours participated.
- **Profit-Loss ratio** = avg revenue per winning hour ÷ |avg per losing hour|.
- **Participation rate** = total awarded MW ÷ (HSL × 24).

Sign convention matches the project rule `spread = DA − RT` (positive ⇒ DA
expensive ⇒ a profitable virtual short).

---

## Critical gotchas (handled by the vendored code — do not "fix")

1. **Fuzzy column matching.** ERCOT API column names vary
   ("Settlement Point" vs "SettlementPointName", "Interval End" vs
   "HourEnding"). `DARTCalculator._find_col()` resolves them — extend its
   candidate lists if a new format appears, don't hard-code.
2. **Hour-ending from interval columns.** When only `Interval End` is present,
   HE is derived from it; `00:00` maps to HE24 of the *previous* day.
3. **Posting-date search.** The archive posting date is searched ±14 days
   around delivery+60 and cached, because ERCOT's posting cadence drifts.
4. **Empty days are normal.** A date with no BESS virtual awards (or outside
   the published window) is skipped, not an error.

---

## Output schema

Written to `--out-dir` (default `shared/data/pnl/all_bess/dart_virtual/`),
tagged `{start}_{end}`:

| File | Grain | Key columns |
|---|---|---|
| `dart_hourly_{tag}.parquet` | node × date × hour | `node`, `date`, `hour`, `offer_mw`, `offer_revenue`, `bid_mw`, `bid_revenue`, `net_revenue`, `dart_spread`, `da_lmp`, `rt_lmp` |
| `dart_daily_{tag}.parquet` / `.csv` | node × date | `node`, `date`, `offer_revenue`, `bid_revenue`, `net_revenue`, `total_offer_mw`, `total_bid_mw`, `win_rate`, `profit_loss_ratio`, `participation_rate`, `avg_dart_spread`, `hsl` |

`dart_daily_*.csv` is the direct input for the `pnl-manager` weekly all-BESS
DART virtual ranking dashboard (render with the `dashboard-report` skill).

> **Estimate, not settlement.** Public-data estimate — flag it as such; do not
> reconcile to invoiced settlement.

---

## Credentials

From `BESS_Biz/.env`, sections **ERCOT** and **Yes Energy API**:

```
ERCOT_USERNAME, ERCOT_PASSWORD, ERCOT_SUBSCRIPTION_KEY
YES_ENERGY_USERNAME, YES_ENERGY_PASSWORD
```

The runner loads these via `shared/scripts/_env_loader.py` — no secrets are
printed. Vendor domains may be blocked on some corporate networks; run locally
or on VPN.

---

## Provenance & re-sync (vendored snapshot)

Everything under `scripts/src/` is copied **verbatim** from `ERCOT-Dart-Tracker`.
Only `scripts/run_estimate.py` is original to this skill. SQLite storage,
Google Sheets sync, and the Streamlit dashboard from the source repo are
intentionally **not** vendored — this skill outputs parquet/csv for BESS_Biz.

> **Accepted duplication.** The sibling skill `estimate-bess-energy-as` vendors
> its own independent ERCOT Public API client. The two snapshots are
> intentionally isolated — an ERCOT auth or archive-endpoint change must be
> re-synced into **both** skills.

| Vendored | Source (`ERCOT-Dart-Tracker/`) |
|---|---|
| `scripts/src/extractors/ercot_api.py` | `src/extractors/ercot_api.py` |
| `scripts/src/extractors/yes_energy_api.py` | `src/extractors/yes_energy_api.py` |
| `scripts/src/processors/dart_calculator.py` | `src/processors/dart_calculator.py` |
| `scripts/src/utils/logger.py` | `src/utils/logger.py` |

Snapshot: **2026-05-21**, source commit `5d94fc4`.

**This is a snapshot — it does not auto-track the source repo.** When the
calculation logic in `ERCOT-Dart-Tracker` is improved, re-sync:

```bash
SRC="C:/Users/00904/ERCOT Projects/ERCOT-Dart-Tracker"
DST="C:/Users/00904/ERCOT Projects/BESS_Biz/skills/estimate-bess-dart-virtual/scripts"
cp "$SRC/src/extractors/ercot_api.py"        "$DST/src/extractors/ercot_api.py"
cp "$SRC/src/extractors/yes_energy_api.py"   "$DST/src/extractors/yes_energy_api.py"
cp "$SRC/src/processors/dart_calculator.py"  "$DST/src/processors/dart_calculator.py"
cp "$SRC/src/utils/logger.py"                "$DST/src/utils/logger.py"
```

Then re-run the import smoke test and update the snapshot commit/date above.
The runner deliberately omits the source's `db_manager`/`gsheets_manager` — if
those are still excluded after a re-sync, no change to `run_estimate.py` is
needed.
