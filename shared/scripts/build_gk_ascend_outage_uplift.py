"""Augment build_gk_ascend_fullcap_uplift.py with an **outage-uplift** line
for the user-reported scheduled outage 2026-03-24 .. 2026-04-13 (21 days).

Methodology for outage uplift:
  1. Identify outage days from user input (3/24 .. 4/13).
  2. From the **non-outage** days in March (3/1–3/23) and April (4/14–4/30),
     compute GK's average daily $/kW for physical and virtual separately.
     We use a 41-day adjacent window (Mar+Apr ex-outage) to capture
     spring conditions specific to the outage period — not a 6-mo average.
  3. Outage-uplift = (avg daily $/kW)  ×  21 outage days.
  4. Apply 0.8× conservative haircut on top, consistent with the
     capacity-scaling treatment in the parent script.
       Rationale: GK's adjacent-day rate is its own demonstrated
       capability, so this is less optimistic than the linear cap-scale
       case — but we keep the same 0.8× for methodological consistency
       and to acknowledge day-to-day variance.

We attribute the outage uplift to the months it overlaps:
  - March  : 3/24 .. 3/31  =  8 days
  - April  : 4/01 .. 4/13  = 13 days

Outputs:
  shared/data/pnl/gks/monthly/gk_ascend_fullcap_uplift_with_outage.csv
"""
from __future__ import annotations
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env_loader import load_env_sections
from fetch_pnl_data import smartbidder_token
from build_smartbidder_benchmark_monthly import month_chunks, PRODUCT_LABEL
from build_gk_ascend_fullcap_uplift import (
    fetch_realized_revenue, fetch_realized_soc,
    NAMEPLATE_MWH, BIND_THRESHOLD, CONSERVATIVE_FACTOR,
)

ENV_PATH       = Path(__file__).resolve().parents[2] / ".env"
OUT_DIR        = Path(__file__).resolve().parents[2] / "shared/data/pnl/gks/monthly"
CPT            = ZoneInfo("America/Chicago")
GKS_KW         = 100_000

OUTAGE_START   = date(2026, 3, 24)
OUTAGE_END     = date(2026, 4, 13)   # inclusive
# adjacent-day baseline window (Mar + Apr, ex-outage)
BASELINE_RANGES = [
    (date(2026, 3, 1),  date(2026, 3, 23)),   # 23 days
    (date(2026, 4, 14), date(2026, 4, 30)),   # 17 days
]


def daily_rev_split(rev: pd.DataFrame) -> pd.DataFrame:
    """Return per-day physical & virtual & stored-total $/kW."""
    is_total = rev["label"] == "Total"
    is_virt  = rev["label"].isin(["DA Virtual Energy", "RT Virtual Energy"])

    phys = (rev[~is_total & ~is_virt].groupby("day")["revenue"].sum()
            .rename("physical_usd"))
    virt = (rev[is_virt].groupby("day")["revenue"].sum()
            .rename("virtual_usd"))
    tot  = (rev[is_total].groupby("day")["revenue"].sum()
            .rename("stored_total_usd"))

    out = pd.concat([phys, virt, tot], axis=1).fillna(0.0).reset_index()
    out["physical_$/kW"]     = (out["physical_usd"]     / GKS_KW).round(4)
    out["virtual_$/kW"]      = (out["virtual_usd"]      / GKS_KW).round(4)
    out["stored_total_$/kW"] = (out["stored_total_usd"] / GKS_KW).round(4)
    return out


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sb = load_env_sections(ENV_PATH).get("smartbidder", {})
    token = smartbidder_token(sb)

    start = date(2025, 12, 1)
    end   = datetime.now(CPT).date()
    print(f"🎯 window: {start} .. {end}  outage: {OUTAGE_START}..{OUTAGE_END}")

    # -------- revenue (realized) --------
    rev_parts = []
    print("\n📥 /revenue  (realized, hourly)")
    for s, e in month_chunks(start, end):
        df = fetch_realized_revenue(token, sb, s, e)
        print(f"   {s} .. {e}  rows={len(df):>6}")
        if not df.empty:
            rev_parts.append(df)
    rev = pd.concat(rev_parts, ignore_index=True)
    rev["ts"]   = pd.to_datetime(rev["timestamp"], utc=True).dt.tz_convert(CPT)
    rev["day"]  = (rev["ts"] - pd.Timedelta(minutes=1)).dt.tz_localize(None).dt.date
    rev["month"] = pd.to_datetime(rev["day"]).dt.strftime("%Y-%m")
    rev = rev[rev["month"] >= start.strftime("%Y-%m")]
    rev["label"] = rev["product"].map(PRODUCT_LABEL).fillna(rev["product"])

    daily_rev = daily_rev_split(rev)

    # -------- SoC (realized) → bound days --------
    soc_parts = []
    print("\n📥 /soc-detailed  (realized)")
    for s, e in month_chunks(start, end):
        df = fetch_realized_soc(token, sb, s, e)
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

    # -------- exclude outage days from capacity-uplift calc --------
    in_outage = daily_soc["day"].between(OUTAGE_START, OUTAGE_END)
    daily_soc_capcalc = daily_soc[~in_outage].copy()
    daily_soc_capcalc["month"] = pd.to_datetime(daily_soc_capcalc["day"]).dt.strftime("%Y-%m")
    cap_mu = daily_soc_capcalc.groupby("month").agg(
        days_ex_outage   = ("day", "size"),
        bound_days       = ("bound", "sum"),
        avg_cap_mwh      = ("cap_max", "mean"),
        avg_cap_factor   = ("fac", "mean"),
    ).round(3)

    # -------- adjacent-day baseline (Mar 1-23 + Apr 14-30) --------
    in_baseline = pd.Series(False, index=daily_rev.index)
    for bs, be in BASELINE_RANGES:
        in_baseline |= daily_rev["day"].between(bs, be)
    baseline = daily_rev[in_baseline]
    base_phys_per_day = baseline["physical_$/kW"].mean()
    base_virt_per_day = baseline["virtual_$/kW"].mean()
    base_tot_per_day  = baseline["stored_total_$/kW"].mean()
    print(f"\n🧭 Adjacent-day baseline ({in_baseline.sum()} days, Mar 1–23 + Apr 14–30)")
    print(f"   avg physical $/kW per day  = {base_phys_per_day:.4f}")
    print(f"   avg virtual  $/kW per day  = {base_virt_per_day:.4f}")
    print(f"   avg stored-total $/kW/day  = {base_tot_per_day:.4f}")

    # -------- outage uplift per month (attribute to month of overlap) --------
    outage_days = pd.date_range(OUTAGE_START, OUTAGE_END, freq="D").date
    outage_by_month = pd.Series(outage_days).to_frame("day")
    outage_by_month["month"] = pd.to_datetime(outage_by_month["day"]).dt.strftime("%Y-%m")
    outage_counts = outage_by_month.groupby("month").size().rename("outage_days")
    print(f"\n📅 outage days per month: {dict(outage_counts)}  total={outage_counts.sum()}")

    # -------- monthly stored-total revenue (actuals) --------
    daily_rev["month"] = pd.to_datetime(daily_rev["day"]).dt.strftime("%Y-%m")
    monthly = daily_rev.groupby("month").agg(
        physical_per_kw     = ("physical_$/kW",     "sum"),
        virtual_per_kw      = ("virtual_$/kW",      "sum"),
        stored_total_per_kw = ("stored_total_$/kW", "sum"),
    ).round(3)

    # -------- assemble --------
    out = monthly.copy()
    out["bound_days_ex_outage"] = cap_mu.apply(
        lambda r: f"{int(r['bound_days'])}/{int(r['days_ex_outage'])}", axis=1)
    out["avg_cap_mwh_ex_outage"] = cap_mu["avg_cap_mwh"]
    out["cap_uplift_factor"]     = cap_mu["avg_cap_factor"]
    out["cap_uplift_naive"]      = (out["physical_per_kw"] * out["cap_uplift_factor"]).round(3)
    out["cap_uplift_consv"]      = (out["cap_uplift_naive"] * CONSERVATIVE_FACTOR).round(3)

    # outage uplift = baseline daily $/kW × outage days in that month
    out["outage_days"]            = outage_counts.reindex(out.index, fill_value=0)
    out["outage_phys_uplift"]     = (out["outage_days"] * base_phys_per_day).round(3)
    out["outage_virt_uplift"]     = (out["outage_days"] * base_virt_per_day).round(3)
    out["outage_total_uplift"]    = (out["outage_days"] * base_tot_per_day).round(3)
    out["outage_uplift_consv"]    = (out["outage_total_uplift"] * CONSERVATIVE_FACTOR).round(3)

    out["total_uplift_consv"]     = (out["cap_uplift_consv"] + out["outage_uplift_consv"]).round(3)
    out["fullcap_total_$/kW"]     = (out["stored_total_per_kw"] + out["total_uplift_consv"]).round(3)

    cols = ["physical_per_kw", "virtual_per_kw", "stored_total_per_kw",
            "bound_days_ex_outage", "avg_cap_mwh_ex_outage", "cap_uplift_factor",
            "cap_uplift_consv",
            "outage_days", "outage_total_uplift", "outage_uplift_consv",
            "total_uplift_consv", "fullcap_total_$/kW"]

    pd.set_option("display.width", 240); pd.set_option("display.max_columns", None)
    print("\n=== GK Ascend full-cap uplift (capacity + outage, 0.8× conservative) ===")
    print(out[cols].to_string())

    ytd = out[["physical_per_kw","virtual_per_kw","stored_total_per_kw",
               "cap_uplift_consv","outage_uplift_consv",
               "total_uplift_consv","fullcap_total_$/kW"]].sum().round(3)
    print("\n--- YTD ---")
    print(ytd.to_string())

    out[cols].to_csv(OUT_DIR / "gk_ascend_fullcap_uplift_with_outage.csv")
    print(f"\n💾 wrote {OUT_DIR / 'gk_ascend_fullcap_uplift_with_outage.csv'}")


if __name__ == "__main__":
    main()
