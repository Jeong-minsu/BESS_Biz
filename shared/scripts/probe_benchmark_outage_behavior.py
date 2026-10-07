"""Does the Mount Blue Sky benchmark strategy honor the real-world outage
2026-03-24 .. 2026-04-13, or does it simulate dispatch as if the battery
were always fully available?

If it honors: daily benchmark $/kW ≈ 0 inside the outage window.
If it ignores: daily benchmark $/kW stays at non-trivial values.
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
from build_smartbidder_benchmark_monthly import (
    month_chunks, fetch_revenue, fetch_soc, PRODUCT_LABEL,
)

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
CPT      = ZoneInfo("America/Chicago")
GKS_KW   = 100_000


def main():
    sb = load_env_sections(ENV_PATH).get("smartbidder", {})
    token = smartbidder_token(sb)

    start = date(2026, 3, 15)
    end   = date(2026, 4, 25)

    rev_parts = []
    for s, e in month_chunks(start, end):
        rev_parts.append(fetch_revenue(token, sb, s, e))
    rev = pd.concat([d for d in rev_parts if not d.empty], ignore_index=True)
    rev["ts"]    = pd.to_datetime(rev["timestamp"], utc=True).dt.tz_convert(CPT)
    rev["day"]   = (rev["ts"] - pd.Timedelta(minutes=1)).dt.tz_localize(None).dt.date
    rev["label"] = rev["product"].map(PRODUCT_LABEL).fillna(rev["product"])

    is_total = rev["label"] == "Total"
    is_virt  = rev["label"].isin(["DA Virtual Energy", "RT Virtual Energy"])

    daily_phys = (rev[~is_total & ~is_virt].groupby("day")["revenue"].sum()
                  / GKS_KW).rename("bench_physical_$/kW").round(4)
    daily_virt = (rev[is_virt].groupby("day")["revenue"].sum()
                  / GKS_KW).rename("bench_virtual_$/kW").round(4)
    daily_tot  = (rev[is_total].groupby("day")["revenue"].sum()
                  / GKS_KW).rename("bench_total_$/kW").round(4)

    # soc (benchmark strategy)
    soc_parts = []
    for s, e in month_chunks(start, end):
        soc_parts.append(fetch_soc(token, sb, s, e))
    soc = pd.concat([d for d in soc_parts if not d.empty], ignore_index=True)
    soc["ts"]  = pd.to_datetime(soc["timestamp"], utc=True).dt.tz_convert(CPT)
    soc["day"] = soc["ts"].dt.date
    daily_soc = soc.groupby("day").agg(
        bench_peak_soc_mwh = ("soc_mwh", "max"),
        bench_cap_max      = ("soc_mwh_max", "max"),
    ).round(2)

    out = pd.concat([daily_soc, daily_phys, daily_virt, daily_tot], axis=1).reset_index()
    out["in_outage"] = out["day"].between(date(2026, 3, 24), date(2026, 4, 13))

    pd.set_option("display.width", 200); pd.set_option("display.max_columns", None)
    print("=== Benchmark (Mount Blue Sky) daily 2026-03-15 .. 2026-04-24 ===")
    print(out.to_string(index=False))

    in_window = out[out["in_outage"]]
    print(f"\nOutage window 2026-03-24..2026-04-13 ({len(in_window)} days):")
    print(f"  benchmark cap_max>0 days   : {(in_window['bench_cap_max']>0).sum()}")
    print(f"  benchmark physical $/kW    : sum={in_window['bench_physical_$/kW'].sum():.3f}  avg={in_window['bench_physical_$/kW'].mean():.4f}")
    print(f"  benchmark virtual  $/kW    : sum={in_window['bench_virtual_$/kW'].sum():.3f}  avg={in_window['bench_virtual_$/kW'].mean():.4f}")
    print(f"  benchmark total    $/kW    : sum={in_window['bench_total_$/kW'].sum():.3f}  avg={in_window['bench_total_$/kW'].mean():.4f}")


if __name__ == "__main__":
    main()
