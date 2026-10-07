"""Inspect daily Ascend SoC cap + revenue around the user-reported outage
window 2026-03-24 .. 2026-04-13 (inclusive). Goal: confirm outage shape
(cap_max collapses to near-zero, revenue ≈ 0) so the outage-uplift
calc can use the right day count.
"""
from __future__ import annotations
import sys
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env_loader import load_env_sections
from fetch_pnl_data import smartbidder_token
from build_smartbidder_benchmark_monthly import month_chunks, PRODUCT_LABEL
from build_gk_ascend_fullcap_uplift import fetch_realized_revenue, fetch_realized_soc

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
CPT      = ZoneInfo("America/Chicago")
GKS_KW   = 100_000


def main():
    sb = load_env_sections(ENV_PATH).get("smartbidder", {})
    token = smartbidder_token(sb)

    start = date(2026, 3, 15)
    end   = date(2026, 4, 25)

    # revenue
    rev_parts = []
    for s, e in month_chunks(start, end):
        rev_parts.append(fetch_realized_revenue(token, sb, s, e))
    rev = pd.concat([d for d in rev_parts if not d.empty], ignore_index=True)
    rev["ts"]   = pd.to_datetime(rev["timestamp"], utc=True).dt.tz_convert(CPT)
    rev["day"]  = (rev["ts"] - pd.Timedelta(minutes=1)).dt.tz_localize(None).dt.date
    rev["label"] = rev["product"].map(PRODUCT_LABEL).fillna(rev["product"])
    is_total = rev["label"] == "Total"
    daily_rev = (rev[is_total]
                 .groupby("day")["revenue"].sum()
                 .rename("total_usd").reset_index())
    daily_rev["total_$/kW"] = (daily_rev["total_usd"] / GKS_KW).round(3)

    # also non-virtual physical
    is_virt = rev["label"].isin(["DA Virtual Energy", "RT Virtual Energy"])
    phys = (rev[~is_total & ~is_virt]
            .groupby("day")["revenue"].sum()
            .rename("physical_usd").reset_index())
    phys["physical_$/kW"] = (phys["physical_usd"] / GKS_KW).round(3)
    virt = (rev[is_virt]
            .groupby("day")["revenue"].sum()
            .rename("virtual_usd").reset_index())
    virt["virtual_$/kW"] = (virt["virtual_usd"] / GKS_KW).round(3)

    # soc
    soc_parts = []
    for s, e in month_chunks(start, end):
        soc_parts.append(fetch_realized_soc(token, sb, s, e))
    soc = pd.concat([d for d in soc_parts if not d.empty], ignore_index=True)
    soc["ts"]  = pd.to_datetime(soc["timestamp"], utc=True).dt.tz_convert(CPT)
    soc["day"] = soc["ts"].dt.date
    daily_soc = soc.groupby("day").agg(
        peak_soc_mwh = ("soc_mwh", "max"),
        cap_max      = ("soc_mwh_max", "max"),
        cap_min      = ("soc_mwh_max", "min"),
        cap_mean     = ("soc_mwh_max", "mean"),
    ).round(2).reset_index()

    # merge
    out = daily_soc.merge(daily_rev[["day","total_$/kW"]], on="day", how="left") \
                   .merge(phys[["day","physical_$/kW"]], on="day", how="left") \
                   .merge(virt[["day","virtual_$/kW"]], on="day", how="left")
    out = out.fillna({"total_$/kW": 0, "physical_$/kW": 0, "virtual_$/kW": 0})

    # flag user-reported outage window
    o_start, o_end = date(2026, 3, 24), date(2026, 4, 13)
    out["in_outage"] = out["day"].between(o_start, o_end)

    pd.set_option("display.width", 200); pd.set_option("display.max_columns", None)
    print("=== Daily SoC cap + revenue 2026-03-15 .. 2026-04-24 ===")
    print(out.to_string(index=False))

    print(f"\nUser-reported outage: {o_start} .. {o_end}  ({(o_end - o_start).days + 1} days)")
    print(f"  Days with cap_max < 10 MWh in window: {((out['in_outage']) & (out['cap_max'] < 10)).sum()}")
    print(f"  Days with cap_max < 50 MWh in window: {((out['in_outage']) & (out['cap_max'] < 50)).sum()}")
    print(f"  Days with physical $/kW < 0.005 in window: {((out['in_outage']) & (out['physical_\\$/kW'].abs() < 0.005)).sum()}")


if __name__ == "__main__":
    main()
