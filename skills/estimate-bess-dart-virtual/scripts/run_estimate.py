#!/usr/bin/env python
"""
run_estimate.py — all-BESS DART virtual revenue estimator (ERCOT 60-day disclosure).

Orchestration runner for the `estimate-bess-dart-virtual` skill. It is the ONLY
file in scripts/ that is not vendored verbatim from ERCOT-Dart-Tracker —
everything under scripts/src/ is that project's pipeline, unchanged.

DART virtual = financial energy-only trades settled against DA vs RT price:
    Virtual Short (offer) = (DA_LMP - RT_LMP) * Offer_Award_MW
    Virtual Long  (bid)   = (RT_LMP - DA_LMP) * Bid_Award_MW
    Net DART revenue      = Short + Long

What it does (mirrors ERCOT-Dart-Tracker's batch pipeline, minus SQLite/Sheets):
  1. Load ERCOT + Yes Energy API credentials from BESS_Biz/.env.
  2. Phase 1 — per flow date, fetch the ERCOT NP3-966-ER archive
     (ESR_Data -> BESS nodes/HSL, EnergyOnlyOfferAwards, EnergyBidAwards).
  3. Phase 2 — bulk-fetch DA + RT hourly LMP from Yes Energy for the node union.
  4. Phase 3 — per date, compute DART revenue + win rate / P-L ratio /
     participation rate, then write parquet (+ daily csv) to
     shared/data/pnl/all_bess/dart_virtual/.

Usage (run from the BESS_Biz repo root):
    python skills/estimate-bess-dart-virtual/scripts/run_estimate.py \
        --start 2026-01-01 --end 2026-03-15

NOTE: ERCOT 60-day disclosure means a flow date is only available ~60 days
after it occurs. Choose --start/--end accordingly. See ../SKILL.md.
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)  # so vendored `src.*` resolves

# BESS_Biz root: skills/estimate-bess-dart-virtual/scripts -> up 3 levels
BESS_BIZ_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
DEFAULT_OUT = os.path.join(
    BESS_BIZ_ROOT, "shared", "data", "pnl", "all_bess", "dart_virtual"
)
# Disk cache for archive-confirmed ERCOT fetches (gitignored via scripts/data/).
# The vendored ERCOT client caches only in-memory; this makes weekly re-runs
# skip ZIP re-downloads of already-published flow dates.
CACHE_DIR = os.path.join(SCRIPT_DIR, "data", "cache")


def _load_credentials() -> None:
    """Populate os.environ with ERCOT + Yes Energy API creds from BESS_Biz/.env.

    Uses the project's section-aware loader (shared/scripts/_env_loader.py).
    The DART pipeline needs the Yes Energy *API* (DataSignals, user/pass) — a
    different product from the Datalake S3 keys the energy-as skill uses.
    """
    loader_dir = os.path.join(BESS_BIZ_ROOT, "shared", "scripts")
    try:
        sys.path.insert(0, loader_dir)
        from _env_loader import load_env_sections

        sections = load_env_sections()
        for sec in ("ercot", "yes_energy"):
            for k, v in sections.get(sec, {}).items():
                os.environ.setdefault(k, v)
    except Exception as e:  # fallback: prefixed keys are unique, flat load is safe
        try:
            from dotenv import load_dotenv

            load_dotenv(os.path.join(BESS_BIZ_ROOT, ".env"))
        except Exception:
            print(f"[warn] credential load failed: {e}", file=sys.stderr)


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


# DataFrames the runner actually consumes downstream (esr_data is unused → not cached).
_CACHED_KEYS = ("offer_awards", "bid_awards", "hsl")


def _load_cached_bess_data(ds: str):
    """Return a cached fetch_all_bess_data() result for flow date `ds`, or None.

    Only archive-confirmed results are cached (see _cache_bess_data), so a cache
    miss always means 'not fetched yet', never 'archive not published'.
    """
    d = os.path.join(CACHE_DIR, ds)
    meta_p = os.path.join(d, "meta.json")
    if not os.path.exists(meta_p):
        return None
    try:
        with open(meta_p, encoding="utf-8") as f:
            meta = json.load(f)
        bd = {"nodes": meta["nodes"], "posting_date": meta["posting_date"]}
        for k in _CACHED_KEYS:
            p = os.path.join(d, f"{k}.parquet")
            bd[k] = pd.read_parquet(p) if os.path.exists(p) else pd.DataFrame()
        return bd
    except Exception:
        return None  # corrupt cache entry → re-fetch


def _cache_bess_data(ds: str, bd: dict) -> None:
    """Persist an archive-confirmed fetch result. Best-effort — a cache write
    failure is logged and never breaks the run."""
    try:
        d = os.path.join(CACHE_DIR, ds)
        os.makedirs(d, exist_ok=True)
        for k in _CACHED_KEYS:
            df = bd.get(k)
            if isinstance(df, pd.DataFrame):
                df.to_parquet(os.path.join(d, f"{k}.parquet"), index=False)
        with open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as f:
            json.dump({"nodes": bd["nodes"], "posting_date": bd["posting_date"]}, f)
    except Exception as e:
        print(f"  [warn] cache write failed for {ds}: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Estimate all-BESS DART virtual revenue from ERCOT 60-day disclosure."
    )
    ap.add_argument("--start", required=True, type=_parse_date,
                    help="flow start date, YYYY-MM-DD (inclusive)")
    ap.add_argument("--end", required=True, type=_parse_date,
                    help="flow end date, YYYY-MM-DD (inclusive)")
    ap.add_argument("--out-dir", default=DEFAULT_OUT,
                    help=f"output directory (default: {DEFAULT_OUT})")
    args = ap.parse_args()

    if args.start > args.end:
        ap.error("--start must be on or before --end")

    _load_credentials()

    from src.extractors.ercot_api import ErcotAPIClient
    from src.extractors.yes_energy_api import YesEnergyClient
    from src.processors.dart_calculator import DARTCalculator

    dates = [d.isoformat() for d in _daterange(args.start, args.end)]
    ercot = ErcotAPIClient()
    yes_energy = YesEnergyClient()
    calc = DARTCalculator()

    # --- Phase 1: ERCOT archive per flow date (posting dates differ per date) ---
    print(f"[1/3] ERCOT NP3-966-ER archive — {len(dates)} flow dates "
          f"(disk cache: {CACHE_DIR}) ...")
    nodes_union: set[str] = set()
    ercot_by_date: dict[str, dict] = {}
    for i, ds in enumerate(dates, 1):
        bd = _load_cached_bess_data(ds)
        if bd is not None:
            print(f"  [{i}/{len(dates)}] {ds}  cache hit")
        else:
            try:
                bd = ercot.fetch_all_bess_data(ds)
            except Exception as e:
                print(f"  [{i}/{len(dates)}] {ds}  ERCOT fetch failed: {e}")
                continue
            if bd["posting_date"] is None:
                print(f"  [{i}/{len(dates)}] {ds}  no archive (60-day lag not elapsed?)")
                continue  # not cached — archive may be published on a later run
            _cache_bess_data(ds, bd)  # archive confirmed → safe to cache
        if bd["offer_awards"].empty and bd["bid_awards"].empty:
            print(f"  [{i}/{len(dates)}] {ds}  no BESS virtual awards")
            continue
        ercot_by_date[ds] = bd
        nodes_union.update(bd["nodes"])

    if not ercot_by_date:
        print("[error] no ERCOT archive data for any date in range.", file=sys.stderr)
        return 1

    valid_dates = sorted(ercot_by_date)
    all_nodes = sorted(nodes_union)
    print(f"  -> {len(valid_dates)}/{len(dates)} dates valid, "
          f"{len(all_nodes)} unique BESS nodes")

    # --- Phase 2: bulk Yes Energy LMP for the node union x full range ---
    print(f"[2/3] Yes Energy LMP (bulk)  {valid_dates[0]} -> {valid_dates[-1]} ...")
    da_all = yes_energy.get_da_lmp(all_nodes, valid_dates[0], valid_dates[-1])
    rt_all = yes_energy.get_rt_lmp(all_nodes, valid_dates[0], valid_dates[-1])
    if da_all.empty and rt_all.empty:
        print("[error] no LMP data returned from Yes Energy.", file=sys.stderr)
        return 1

    # --- Phase 3: per-date DART revenue calculation ---
    print("[3/3] DART revenue calculation ...")
    all_hourly, all_daily = [], []
    for ds in valid_dates:
        bd = ercot_by_date[ds]
        da_day = da_all[da_all["date"] == ds].copy() if not da_all.empty else pd.DataFrame()
        rt_day = rt_all[rt_all["date"] == ds].copy() if not rt_all.empty else pd.DataFrame()
        if da_day.empty and rt_day.empty:
            print(f"  {ds}  no LMP — skipped")
            continue
        try:
            hourly, daily = calc.calculate_dart_revenue(
                bd["offer_awards"], bd["bid_awards"], da_day, rt_day, ds, bd["hsl"]
            )
        except Exception as e:
            print(f"  {ds}  calc failed: {e}")
            continue
        if not hourly.empty:
            all_hourly.append(hourly)
        if not daily.empty:
            all_daily.append(daily)

    if not all_daily:
        print("[error] no DART revenue computed for any date.", file=sys.stderr)
        return 1

    hourly_df = pd.concat(all_hourly, ignore_index=True)
    daily_df = pd.concat(all_daily, ignore_index=True)

    os.makedirs(args.out_dir, exist_ok=True)
    tag = f"{args.start}_{args.end}"
    h_path = os.path.join(args.out_dir, f"dart_hourly_{tag}.parquet")
    d_pq = os.path.join(args.out_dir, f"dart_daily_{tag}.parquet")
    d_csv = os.path.join(args.out_dir, f"dart_daily_{tag}.csv")
    hourly_df.to_parquet(h_path, index=False)
    daily_df.to_parquet(d_pq, index=False)
    daily_df.to_csv(d_csv, index=False)

    print("\nWrote:")
    print(f"  {h_path}  ({len(hourly_df)} hourly rows)")
    print(f"  {d_pq}  ({len(daily_df)} node-days)")
    print(f"  {d_csv}")

    rank = daily_df.groupby("node", as_index=False)["net_revenue"].sum()
    print(f"\nFleet net DART virtual revenue: ${rank['net_revenue'].sum():,.0f}")
    print("\nTop 10 nodes by net DART virtual revenue:")
    for _, r in rank.nlargest(10, "net_revenue").iterrows():
        print(f"  {str(r['node']):<30} ${r['net_revenue']:>13,.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
