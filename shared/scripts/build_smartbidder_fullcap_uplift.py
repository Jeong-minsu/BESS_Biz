"""Estimate monthly revenue uplift IF the GKS BESS had been fully operational
at 100 MW / 200 MWh nameplate over 2025-12-01 .. today.

Methodology (transparent first-order estimate):

  1. Pull benchmark `/revenue` (hourly) and `/soc-detailed` (5-min) for
     the requested window, strategy = `AA - Mount Blue Sky with Virtuals
     (RTC version)`.
  2. Split each month's revenue into:
       physical = Total − (DA Virtual Energy + RT Virtual Energy)
       virtual  = DA Virtual Energy + RT Virtual Energy
     Virtual is a *financial* position that does not depend on physical
     battery capacity, so do NOT scale it.
  3. For each day, decide whether the benchmark strategy was
     capacity-bound:
         bound  ⇔  peak_soc_mwh / cap_max  >  0.93
     The threshold (93%) recognises that the optimiser parks within a
     small reserve of the ceiling on truly-bound days.
  4. Per-day uplift factor:
         bound day      → (nameplate / cap_max) − 1   (≥ 0)
         not-bound day  → 0   (more capacity ≠ more revenue when the
                               strategy already chose to stay low)
  5. Monthly uplift = month_physical_$/kW × (weighted-mean of daily
     uplift factors, weighted equally by day).

Assumptions / caveats:

  • Linear scaling of physical revenue with available MWh. Slightly
    optimistic for energy arbitrage at large multipliers (price
    spreads compress), reasonable for AS / Non-Spin.
  • Power (MW) is assumed to scale proportionally with energy (MWh) —
    /soc-detailed only exposes energy capacity. Typical BESS
    commissioning ramps the two together, so this is the standard
    convention.
  • "Strategy choice" months (Apr/May) get zero uplift. If the user
    believes full power was already required to capture the available
    spread on those days, the true uplift is still ≈ zero.
  • Pure-virtual months get zero uplift (DART virtual ⊥ capacity).
"""
from __future__ import annotations
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env_loader import load_env_sections
from fetch_pnl_data import smartbidder_token
from build_smartbidder_benchmark_monthly import (
    month_chunks, fetch_revenue, fetch_soc, PRODUCT_LABEL,
)

ENV_PATH       = Path(__file__).resolve().parents[2] / ".env"
OUT_DIR        = Path(__file__).resolve().parents[2] / "shared/data/benchmarks/smartbidder/monthly"
CPT            = ZoneInfo("America/Chicago")
GKS_KW         = 100_000
NAMEPLATE_MWH  = 200.0
BIND_THRESHOLD = 0.93  # peak_soc_mwh / cap_max above this ⇒ capacity-bound day


def main():
    sb = load_env_sections(ENV_PATH).get("smartbidder", {})
    token = smartbidder_token(sb)

    start = date(2025, 12, 1)
    end   = datetime.now(CPT).date()
    print(f"🎯 window: {start} .. {end} (exclusive)")

    # -------- revenue --------
    rev_parts = []
    for s, e in month_chunks(start, end):
        df = fetch_revenue(token, sb, s, e)
        if not df.empty:
            rev_parts.append(df)
    rev = pd.concat(rev_parts, ignore_index=True)
    rev["ts"] = pd.to_datetime(rev["timestamp"], utc=True).dt.tz_convert(CPT)
    period = (rev["ts"] - pd.Timedelta(minutes=1)).dt.tz_localize(None).dt.to_period("M")
    rev["month"] = period.dt.strftime("%Y-%m")
    rev = rev[rev["month"] >= start.strftime("%Y-%m")]
    rev["label"] = rev["product"].map(PRODUCT_LABEL).fillna(rev["product"])

    is_virtual = rev["label"].isin(["DA Virtual Energy", "RT Virtual Energy"])
    is_total   = rev["label"] == "Total"

    by_month = (rev[~is_total].assign(virt=is_virtual[~is_total])
                .groupby(["month", "virt"])["revenue"].sum().unstack(fill_value=0.0))
    by_month.columns = ["physical_usd", "virtual_usd"]
    by_month["total_usd"] = by_month["physical_usd"] + by_month["virtual_usd"]

    # cross-check vs stored 'Total' rows
    stored_total = rev[is_total].groupby("month")["revenue"].sum()
    by_month["stored_total_usd"] = stored_total
    by_month["recon_diff_usd"]   = (by_month["total_usd"] - by_month["stored_total_usd"]).round(2)
    if (by_month["recon_diff_usd"].abs() > 1).any():
        print("⚠️ physical+virtual ≠ stored Total in some months — investigate:")
        print(by_month[["physical_usd","virtual_usd","total_usd","stored_total_usd","recon_diff_usd"]])

    # -------- soc / per-day binding --------
    soc_parts = []
    for s, e in month_chunks(start, end):
        df = fetch_soc(token, sb, s, e)
        if not df.empty:
            soc_parts.append(df)
    soc = pd.concat(soc_parts, ignore_index=True)
    soc["ts"]  = pd.to_datetime(soc["timestamp"], utc=True).dt.tz_convert(CPT)
    soc["day"] = soc["ts"].dt.date
    daily = soc.groupby("day").agg(
        peak_soc_mwh = ("soc_mwh", "max"),
        cap_max      = ("soc_mwh_max", "max"),
    ).reset_index()
    daily["month"] = pd.to_datetime(daily["day"]).dt.strftime("%Y-%m")
    daily["fill_ratio"]  = daily["peak_soc_mwh"] / daily["cap_max"].replace(0, pd.NA)
    daily["is_bound"]    = daily["fill_ratio"] > BIND_THRESHOLD
    daily["uplift_fac"]  = ((NAMEPLATE_MWH / daily["cap_max"]) - 1).clip(lower=0) \
                            .where(daily["is_bound"], 0.0)

    month_uplift = daily.groupby("month").agg(
        days              = ("day",         "size"),
        bound_days        = ("is_bound",    "sum"),
        avg_cap_mwh       = ("cap_max",     "mean"),
        avg_uplift_factor = ("uplift_fac",  "mean"),
    ).round(3)

    # -------- combine --------
    out = (by_month.join(month_uplift, how="outer") / 1).copy()
    out["physical_$/kW"]      = (out["physical_usd"]      / GKS_KW).round(3)
    out["virtual_$/kW"]       = (out["virtual_usd"]       / GKS_KW).round(3)
    out["stored_total_$/kW"]  = (out["stored_total_usd"]  / GKS_KW).round(3)
    out["uplift_$/kW"]        = (out["physical_$/kW"] * out["avg_uplift_factor"]).round(3)
    out["fullcap_total_$/kW"] = (out["stored_total_$/kW"] + out["uplift_$/kW"]).round(3)

    cols = ["physical_$/kW", "virtual_$/kW", "stored_total_$/kW",
            "bound_days", "days", "avg_cap_mwh", "avg_uplift_factor",
            "uplift_$/kW", "fullcap_total_$/kW"]
    print("\n=== Monthly uplift if fully operational at 100MW / 200MWh ===")
    pd.set_option("display.width", 220); pd.set_option("display.max_columns", None)
    print(out[cols].to_string())

    ytd = out[["physical_$/kW","virtual_$/kW","stored_total_$/kW",
               "uplift_$/kW","fullcap_total_$/kW"]].sum().round(3)
    print("\n--- YTD sum ---")
    print(ytd.to_string())

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv = OUT_DIR / "benchmark_fullcap_uplift.csv"
    out[cols].to_csv(csv)
    print(f"\n💾 wrote {csv}")


if __name__ == "__main__":
    main()
