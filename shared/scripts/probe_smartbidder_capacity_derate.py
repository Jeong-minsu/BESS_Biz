"""Pull /soc-detailed for the benchmark strategy across 2025-12-01..today and
look at how the *available* capacity (soc_mwh_max) trended.

Goal: distinguish (a) days when the BESS was capacity-derated (soc_mwh_max
falls below nameplate 200 MWh) from (b) days when the strategy simply chose
not to fill the battery (soc_mwh_max stayed at full but soc_pct was low).

Reports per month:
  - mean(soc_mwh_max)               → average available capacity
  - mean(daily peak soc_mwh)        → average peak energy actually held
  - mean(daily peak soc_pct)        → average peak fill ratio (same as table)
  - capacity_util = peak_soc_mwh / 200 MWh nameplate
"""
from __future__ import annotations
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env_loader import load_env_sections, first
from fetch_pnl_data import smartbidder_token, SMARTBIDDER_BASE, BENCHMARK_NAME
from build_smartbidder_benchmark_monthly import month_chunks, _iso_cpt, fetch_soc

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
NAMEPLATE_MWH = 200.0
CPT = ZoneInfo("America/Chicago")


def main():
    sb = load_env_sections(ENV_PATH).get("smartbidder", {})
    token = smartbidder_token(sb)

    start = date(2025, 12, 1)
    end   = datetime.now(CPT).date()
    parts = []
    for s, e in month_chunks(start, end):
        df = fetch_soc(token, sb, s, e)
        if not df.empty:
            parts.append(df)
    soc = pd.concat(parts, ignore_index=True)

    soc["ts"]  = pd.to_datetime(soc["timestamp"], utc=True).dt.tz_convert(CPT)
    soc["day"] = soc["ts"].dt.date

    # daily aggregates
    daily = soc.groupby("day").agg(
        peak_soc_mwh    = ("soc_mwh",    "max"),
        peak_soc_pct    = ("soc_pct",    "max"),
        cap_min         = ("soc_mwh_max","min"),
        cap_mean        = ("soc_mwh_max","mean"),
        cap_max         = ("soc_mwh_max","max"),
    ).reset_index()
    daily["month"] = pd.to_datetime(daily["day"]).dt.strftime("%Y-%m")
    daily["util_vs_nameplate_pct"] = daily["peak_soc_mwh"] / NAMEPLATE_MWH * 100

    # monthly aggregates
    monthly = daily.groupby("month").agg(
        avg_peak_soc_mwh   = ("peak_soc_mwh",   "mean"),
        avg_peak_soc_pct   = ("peak_soc_pct",   "mean"),
        avg_cap_mwh        = ("cap_mean",       "mean"),
        min_cap_mwh        = ("cap_min",        "min"),
        max_cap_mwh        = ("cap_max",        "max"),
        avg_util_vs_nameplate_pct = ("util_vs_nameplate_pct", "mean"),
    ).round(2)
    print("=== Monthly capacity / utilization ===")
    pd.set_option("display.width", 200); pd.set_option("display.max_columns", None)
    print(monthly.to_string())

    # also: how many days were derated? (cap_min < 0.9 × nameplate)
    print("\n=== Days with available capacity < 180 MWh (i.e. > 10% derate) ===")
    derated = daily[daily["cap_min"] < 0.9 * NAMEPLATE_MWH]
    print(f"  count = {len(derated)} / {len(daily)} days")
    if len(derated) and len(derated) <= 40:
        print(derated[["day","cap_min","cap_max","peak_soc_mwh","peak_soc_pct"]].to_string(index=False))

    # save
    out = Path(__file__).resolve().parents[2] / "shared/data/benchmarks/smartbidder/monthly/benchmark_capacity_summary.csv"
    monthly.to_csv(out)
    print(f"\n💾 wrote {out}")


if __name__ == "__main__":
    main()
