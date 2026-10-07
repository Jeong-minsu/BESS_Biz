"""Reconstruct GKS physical (energy + AS, no virtual) revenue from ERCOT
public data and compare to Ascend `/revenue` (realized) physical for the
window 2026-01-01 .. 2026-03-18.

Why: the user wants to know whether public-data reconstruction can stand
in for Ascend's settled-estimate when the latter isn't available — and
to quantify any divergence.

ERCOT-public formula per hour (standard 2-settlement, BESS = gen+load):

  DA_net_qty   = DA_Sales_Qty - DA_Purchases_Qty            # MWh
  RT_net_qty   = RT_Generation_Qty - RT_Consumption_Qty     # MWh

  DA_Energy_$  = DA_net_qty * DALMP_GKS_BESS_RN             # DA settlement
  RT_Energy_$  = (RT_net_qty - DA_net_qty) * RTLMP_GKS_BESS_RN
                                                             # RT-only deviation
  DA_RRS_$     = Gen_RRS_Qty  * AS_MCPC_RRS
  DA_ECRS_$    = Gen_ECRS_Qty * AS_MCPC_ECRS
  DA_NSpin_$   = Gen_NS_Qty   * AS_MCPC_NSPIN
  (GKS does not bid Reg → 0)

All quantities come from master_hourly.parquet (Tenaska-sourced settlement
quantities — which mirror ERCOT DAM/SCED disclosure awards). All prices
come from ERCOT public feeds (Yes Energy mirror).

Output: shared/data/adhoc/2026-05-07_AS-strategy/derived/gk_ercot_vs_ascend_2026Q1.csv
"""
from __future__ import annotations
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env_loader import load_env_sections, first
from fetch_pnl_data import smartbidder_token, SMARTBIDDER_BASE
from build_smartbidder_benchmark_monthly import month_chunks, _iso_cpt, PRODUCT_LABEL
from build_gk_ascend_fullcap_uplift import fetch_realized_revenue

ENV_PATH    = Path(__file__).resolve().parents[2] / ".env"
MASTER_PATH = Path(__file__).resolve().parents[2] / \
              "shared/data/adhoc/2026-05-07_AS-strategy/derived/master_hourly.parquet"
OUT_DIR     = Path(__file__).resolve().parents[2] / \
              "shared/data/adhoc/2026-05-07_AS-strategy/derived"
CPT         = ZoneInfo("America/Chicago")
GKS_KW      = 100_000

WIN_START = date(2026, 1, 1)
WIN_END   = date(2026, 3, 18)   # inclusive flowday


# --------------- ERCOT-public reconstruction ---------------
def build_ercot_public() -> pd.DataFrame:
    m = pd.read_parquet(MASTER_PATH)
    m["dt"] = pd.to_datetime(m["datetime_ct"])
    # HE = hour-ending: the row at 2026-01-01 01:00 covers 00:00→01:00.
    # Flowday = the calendar date of the *start* of that interval (= dt − 1 minute).
    m["flowday"] = (m["dt"] - pd.Timedelta(minutes=1)).dt.tz_localize(None).dt.date
    m = m[(m["flowday"] >= WIN_START) & (m["flowday"] <= WIN_END)].copy()

    # NaN → 0 for quantity fields
    for c in ["GKS_DA_Sales_Qty","GKS_DA_Purchases_Qty",
              "GKS_RT_Generation_Qty","GKS_RT_Consumption_Qty",
              "GKS_Gen_RRS_Qty","GKS_Gen_ECRS_Qty","GKS_Gen_NS_Qty"]:
        m[c] = m[c].fillna(0.0)

    da_net = m["GKS_DA_Sales_Qty"]      - m["GKS_DA_Purchases_Qty"]
    rt_net = m["GKS_RT_Generation_Qty"] - m["GKS_RT_Consumption_Qty"]

    m["DA Energy $"]   = da_net * m["DALMP_GKS_BESS_RN"]
    m["RT Energy $"]   = (rt_net - da_net) * m["RTLMP_GKS_BESS_RN"]
    m["DA RRS $"]      = m["GKS_Gen_RRS_Qty"]  * m["AS_MCPC_RRS"]
    m["DA ECRS $"]     = m["GKS_Gen_ECRS_Qty"] * m["AS_MCPC_ECRS"]
    m["DA Non-Spin $"] = m["GKS_Gen_NS_Qty"]   * m["AS_MCPC_NSPIN"]

    m["month"] = pd.to_datetime(m["flowday"]).dt.strftime("%Y-%m")
    rev_cols = ["DA Energy $","RT Energy $","DA RRS $","DA ECRS $","DA Non-Spin $"]
    monthly_usd = m.groupby("month")[rev_cols].sum()
    monthly_usd["Total Physical $"] = monthly_usd.sum(axis=1)

    # Also a Tenaska-_Amt cross-check (mixes physical+virtual via DA/RT Energy_Amt)
    amt_cols = ["GKS_DA_Energy_Amt","GKS_RT_Energy_Amt",
                "GKS_DA_RRS_Amt","GKS_DA_ECRS_Amt","GKS_DA_NS_Amt"]
    for c in amt_cols:
        m[c] = m[c].fillna(0.0)
    tenaska_usd = m.groupby("month")[amt_cols].sum()
    tenaska_usd.columns = ["Tenaska DA Energy_Amt $","Tenaska RT Energy_Amt $",
                           "Tenaska DA RRS_Amt $","Tenaska DA ECRS_Amt $",
                           "Tenaska DA NS_Amt $"]
    tenaska_usd["Tenaska Total _Amt $"] = tenaska_usd.sum(axis=1)
    return monthly_usd.join(tenaska_usd), m


# --------------- Ascend physical (no virtual) ---------------
def build_ascend_physical() -> pd.DataFrame:
    sb = load_env_sections(ENV_PATH).get("smartbidder", {})
    token = smartbidder_token(sb)
    # Pull a slightly extended range so the month boundary buckets line up.
    parts = []
    print("\n📥 Ascend /revenue  (realized, hourly)")
    for s, e in month_chunks(WIN_START, WIN_END + timedelta(days=1)):
        df = fetch_realized_revenue(token, sb, s, e)
        print(f"   {s} .. {e}  rows={len(df):>6}")
        if not df.empty:
            parts.append(df)
    rev = pd.concat(parts, ignore_index=True)
    rev["ts"]    = pd.to_datetime(rev["timestamp"], utc=True).dt.tz_convert(CPT)
    rev["flowday"] = (rev["ts"] - pd.Timedelta(minutes=1)).dt.tz_localize(None).dt.date
    rev = rev[(rev["flowday"] >= WIN_START) & (rev["flowday"] <= WIN_END)]
    rev["month"] = pd.to_datetime(rev["flowday"]).dt.strftime("%Y-%m")
    rev["label"] = rev["product"].map(PRODUCT_LABEL).fillna(rev["product"])

    is_virtual = rev["label"].isin(["DA Virtual Energy", "RT Virtual Energy"])
    is_total   = rev["label"] == "Total"
    phys = rev[~is_total & ~is_virtual]
    pivot = phys.pivot_table(index="month", columns="label",
                              values="revenue", aggfunc="sum", fill_value=0.0)
    pivot["Ascend Total Physical $"] = pivot.sum(axis=1)
    return pivot


def main():
    print(f"🎯 window {WIN_START} .. {WIN_END}  (inclusive flowdays)")
    ercot, _hourly = build_ercot_public()
    ascend = build_ascend_physical()

    # ------------- side-by-side $/kW comparison -------------
    # ERCOT-public per-product
    ercot_kw = (ercot / GKS_KW).round(3)
    ascend_kw = (ascend / GKS_KW).round(3)

    # Align by month
    months = sorted(set(ercot_kw.index) | set(ascend_kw.index))
    ercot_kw = ercot_kw.reindex(months, fill_value=0.0)
    ascend_kw = ascend_kw.reindex(months, fill_value=0.0)

    # Build a comparison frame: per product, ERCOT vs Ascend
    pairs = [
        ("DA Energy",    "DA Energy $",    "DA Energy"),
        ("RT Energy",    "RT Energy $",    "RT Energy"),
        ("DA RRS",       "DA RRS $",       "DA RRS"),
        ("DA ECRS",      "DA ECRS $",      "DA ECRS"),
        ("DA Non-Spin",  "DA Non-Spin $",  "DA Non-Spin"),
    ]
    out = pd.DataFrame(index=months)
    for label, ercot_col, ascend_col in pairs:
        out[f"{label} (ERCOT)"]   = ercot_kw[ercot_col]
        out[f"{label} (Ascend)"]  = ascend_kw.get(ascend_col, pd.Series(0.0, index=months))
        out[f"{label} Δ"]         = (out[f"{label} (ERCOT)"] - out[f"{label} (Ascend)"]).round(3)

    out["TOTAL (ERCOT)"]  = ercot_kw["Total Physical $"]
    out["TOTAL (Ascend)"] = ascend_kw["Ascend Total Physical $"]
    out["TOTAL Δ"]        = (out["TOTAL (ERCOT)"] - out["TOTAL (Ascend)"]).round(3)
    out["TOTAL Δ %"]      = ((out["TOTAL (ERCOT)"] / out["TOTAL (Ascend)"] - 1) * 100).round(1)

    pd.set_option("display.width", 260); pd.set_option("display.max_columns", None)
    print("\n=== ERCOT-public reconstruction ($/kW) ===")
    print(ercot_kw.to_string())
    print("\n=== Ascend realized physical ($/kW) ===")
    print(ascend_kw.to_string())

    print("\n=== Side-by-side per product ===")
    pair_cols = []
    for label, _, _ in pairs:
        pair_cols += [f"{label} (ERCOT)", f"{label} (Ascend)", f"{label} Δ"]
    print(out[pair_cols].to_string())

    print("\n=== TOTAL comparison ===")
    print(out[["TOTAL (ERCOT)","TOTAL (Ascend)","TOTAL Δ","TOTAL Δ %"]].to_string())

    # YTD-window totals
    ytd_ercot = out["TOTAL (ERCOT)"].sum()
    ytd_ascend = out["TOTAL (Ascend)"].sum()
    print(f"\n--- Window total {WIN_START}..{WIN_END} ---")
    print(f"  ERCOT public reconstruction : {ytd_ercot:>8.3f} $/kW")
    print(f"  Ascend realized physical    : {ytd_ascend:>8.3f} $/kW")
    print(f"  Δ                           : {ytd_ercot - ytd_ascend:>8.3f} $/kW  ({(ytd_ercot/ytd_ascend - 1)*100:+.1f}%)")

    out.to_csv(OUT_DIR / "gk_ercot_vs_ascend_2026Q1.csv")
    print(f"\n💾 wrote {OUT_DIR / 'gk_ercot_vs_ascend_2026Q1.csv'}")


if __name__ == "__main__":
    main()
