"""Mirror of build_gk_ascend_outage_uplift.py but for the BENCHMARK
(`AA - Mount Blue Sky with Virtuals (RTC version)`) — so we can compare
benchmark vs GK on equal footing (both with capacity uplift AND outage
uplift applied).

Confirmed empirically (see probe_benchmark_outage_behavior.py): the
benchmark simulator goes dormant during the real-world outage window
(physical revenue ≈ 0 across 21 days), apparently because Ascend bases
the benchmark on actual telemetry / awards. So the benchmark numbers
shipped earlier under-count the same way GK's do — both need an outage
uplift to reach a "full operation" comparison.
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
from build_gk_ascend_fullcap_uplift import NAMEPLATE_MWH, BIND_THRESHOLD, CONSERVATIVE_FACTOR

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
OUT_DIR  = Path(__file__).resolve().parents[2] / "shared/data/benchmarks/smartbidder/monthly"
CPT      = ZoneInfo("America/Chicago")
GKS_KW   = 100_000

OUTAGE_START   = date(2026, 3, 24)
OUTAGE_END     = date(2026, 4, 13)
BASELINE_RANGES = [
    (date(2026, 3, 1),  date(2026, 3, 23)),
    (date(2026, 4, 14), date(2026, 4, 30)),
]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sb = load_env_sections(ENV_PATH).get("smartbidder", {})
    token = smartbidder_token(sb)

    start = date(2025, 12, 1)
    end   = datetime.now(CPT).date()
    print(f"🎯 window: {start} .. {end}  outage: {OUTAGE_START}..{OUTAGE_END}")

    # revenue
    rev_parts = []
    print("\n📥 /revenue  (benchmark, hourly)")
    for s, e in month_chunks(start, end):
        df = fetch_revenue(token, sb, s, e)
        print(f"   {s} .. {e}  rows={len(df):>6}")
        if not df.empty:
            rev_parts.append(df)
    rev = pd.concat(rev_parts, ignore_index=True)
    rev["ts"]    = pd.to_datetime(rev["timestamp"], utc=True).dt.tz_convert(CPT)
    rev["day"]   = (rev["ts"] - pd.Timedelta(minutes=1)).dt.tz_localize(None).dt.date
    rev["month"] = pd.to_datetime(rev["day"]).dt.strftime("%Y-%m")
    rev = rev[rev["month"] >= start.strftime("%Y-%m")]
    rev["label"] = rev["product"].map(PRODUCT_LABEL).fillna(rev["product"])

    is_total = rev["label"] == "Total"
    is_virt  = rev["label"].isin(["DA Virtual Energy", "RT Virtual Energy"])

    daily_rev = (pd.concat([
        rev[~is_total & ~is_virt].groupby("day")["revenue"].sum().rename("physical_usd"),
        rev[is_virt].groupby("day")["revenue"].sum().rename("virtual_usd"),
        rev[is_total].groupby("day")["revenue"].sum().rename("stored_total_usd"),
    ], axis=1).fillna(0.0).reset_index())
    for c in ["physical_usd", "virtual_usd", "stored_total_usd"]:
        daily_rev[c.replace("_usd", "_$/kW")] = (daily_rev[c] / GKS_KW).round(4)
    daily_rev["month"] = pd.to_datetime(daily_rev["day"]).dt.strftime("%Y-%m")

    # soc → bound days (ex-outage)
    soc_parts = []
    print("\n📥 /soc-detailed  (benchmark)")
    for s, e in month_chunks(start, end):
        df = fetch_soc(token, sb, s, e)
        print(f"   {s} .. {e}  rows={len(df):>6}")
        if not df.empty:
            soc_parts.append(df)
    soc = pd.concat(soc_parts, ignore_index=True)
    soc["ts"]  = pd.to_datetime(soc["timestamp"], utc=True).dt.tz_convert(CPT)
    soc["day"] = soc["ts"].dt.date
    daily_soc = soc.groupby("day").agg(
        peak_soc_mwh = ("soc_mwh", "max"),
        cap_max      = ("soc_mwh_max", "max"),
    ).reset_index()
    daily_soc["fill"]  = daily_soc["peak_soc_mwh"] / daily_soc["cap_max"].replace(0, pd.NA)
    daily_soc["bound"] = (daily_soc["fill"] > BIND_THRESHOLD).fillna(False)
    daily_soc["fac"]   = ((NAMEPLATE_MWH / daily_soc["cap_max"]) - 1).clip(lower=0) \
                          .where(daily_soc["bound"], 0.0)

    in_outage_soc = daily_soc["day"].between(OUTAGE_START, OUTAGE_END)
    cap = daily_soc[~in_outage_soc].copy()
    cap["month"] = pd.to_datetime(cap["day"]).dt.strftime("%Y-%m")
    cap_mu = cap.groupby("month").agg(
        days_ex_outage = ("day", "size"),
        bound_days     = ("bound", "sum"),
        avg_cap_mwh    = ("cap_max", "mean"),
        avg_cap_factor = ("fac", "mean"),
    ).round(3)

    # baseline (benchmark's own non-outage adjacent days)
    in_baseline = pd.Series(False, index=daily_rev.index)
    for bs, be in BASELINE_RANGES:
        in_baseline |= daily_rev["day"].between(bs, be)
    base = daily_rev[in_baseline]
    base_phys = base["physical_$/kW"].mean()
    base_virt = base["virtual_$/kW"].mean()
    base_tot  = base["stored_total_$/kW"].mean()
    print(f"\n🧭 Benchmark adjacent-day baseline ({in_baseline.sum()} days)")
    print(f"   avg physical $/kW per day  = {base_phys:.4f}")
    print(f"   avg virtual  $/kW per day  = {base_virt:.4f}")
    print(f"   avg stored-total $/kW/day  = {base_tot:.4f}")

    # outage day attribution
    outage_days = pd.date_range(OUTAGE_START, OUTAGE_END, freq="D").date
    outage_by_month = pd.Series(outage_days).to_frame("day")
    outage_by_month["month"] = pd.to_datetime(outage_by_month["day"]).dt.strftime("%Y-%m")
    outage_counts = outage_by_month.groupby("month").size().rename("outage_days")

    # assemble
    monthly = daily_rev.groupby("month").agg(
        physical_per_kw     = ("physical_$/kW",     "sum"),
        virtual_per_kw      = ("virtual_$/kW",      "sum"),
        stored_total_per_kw = ("stored_total_$/kW", "sum"),
    ).round(3)
    out = monthly.copy()
    out["bound_days_ex_outage"]   = cap_mu.apply(
        lambda r: f"{int(r['bound_days'])}/{int(r['days_ex_outage'])}", axis=1)
    out["avg_cap_mwh_ex_outage"]  = cap_mu["avg_cap_mwh"]
    out["cap_uplift_factor"]      = cap_mu["avg_cap_factor"]
    out["cap_uplift_naive"]       = (out["physical_per_kw"] * out["cap_uplift_factor"]).round(3)
    out["cap_uplift_consv"]       = (out["cap_uplift_naive"] * CONSERVATIVE_FACTOR).round(3)

    out["outage_days"]            = outage_counts.reindex(out.index, fill_value=0)
    out["outage_total_uplift"]    = (out["outage_days"] * base_tot).round(3)
    out["outage_uplift_consv"]    = (out["outage_total_uplift"] * CONSERVATIVE_FACTOR).round(3)

    out["total_uplift_consv"]     = (out["cap_uplift_consv"] + out["outage_uplift_consv"]).round(3)
    out["fullcap_total_$/kW"]     = (out["stored_total_per_kw"] + out["total_uplift_consv"]).round(3)

    cols = ["physical_per_kw","virtual_per_kw","stored_total_per_kw",
            "bound_days_ex_outage","avg_cap_mwh_ex_outage","cap_uplift_factor",
            "cap_uplift_consv","outage_days","outage_total_uplift",
            "outage_uplift_consv","total_uplift_consv","fullcap_total_$/kW"]
    pd.set_option("display.width", 240); pd.set_option("display.max_columns", None)
    print("\n=== BENCHMARK full-cap uplift (capacity + outage, 0.8× consv) ===")
    print(out[cols].to_string())

    ytd = out[["physical_per_kw","virtual_per_kw","stored_total_per_kw",
               "cap_uplift_consv","outage_uplift_consv",
               "total_uplift_consv","fullcap_total_$/kW"]].sum().round(3)
    print("\n--- YTD ---")
    print(ytd.to_string())

    out[cols].to_csv(OUT_DIR / "benchmark_fullcap_uplift_with_outage.csv")
    print(f"\n💾 wrote {OUT_DIR / 'benchmark_fullcap_uplift_with_outage.csv'}")


if __name__ == "__main__":
    main()
