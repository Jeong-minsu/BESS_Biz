"""Build a monthly product × $/kW table of Smartbidder benchmark-strategy
revenue (`AA - Mount Blue Sky with Virtuals (RTC version)`) for GKS BESS
from 2026-01-01 through the latest available day, plus an avg-of-daily-max
SoC column.

Per-MW reference: GKS BESS = 100 MW / 200 MWh → 100,000 kW.

Outputs:
  shared/data/benchmarks/smartbidder/monthly/
     benchmark_monthly_revenue_per_kw.csv
     benchmark_monthly_revenue_per_kw_raw.parquet  (raw $ totals, before kW scale)

Usage:
  python shared/scripts/build_smartbidder_benchmark_monthly.py
  python shared/scripts/build_smartbidder_benchmark_monthly.py --start 2026-01-01 --end 2026-05-19
"""
from __future__ import annotations

import argparse
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
from fetch_pnl_data import smartbidder_token, SMARTBIDDER_BASE, BENCHMARK_NAME

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
OUT_DIR  = Path(__file__).resolve().parents[2] / "shared" / "data" / "benchmarks" / "smartbidder" / "monthly"
CPT      = ZoneInfo("America/Chicago")
GKS_KW   = 100_000  # 100 MW

# Product label map — Ascend's internal id → display name.
# Unknown ids fall through with the raw id.
PRODUCT_LABEL = {
    "energy_da_60":          "DA Energy",
    "energy_rt_5":           "RT Energy",
    "energy_rt_5_deviation": "RT Energy Deviation",
    "energy_da_60_virtual":  "DA Virtual Energy",
    "energy_rt_5_virtual":   "RT Virtual Energy",
    "regup_da":              "DA RegUp",
    "regdown_da":            "DA RegDown",
    "ecrs_da":               "DA ECRS",
    "nonspin_da":            "DA Non-Spin",
    # SmartBidder's `spin_*` is what the UI labels "RRS" (verified against the
    # 2026-05-10 revenue_summary JSON: hourly DA RRS values 6.93 / 4.218
    # match Spin Da Revenue Pos exactly).
    "spin_da":               "DA RRS",
    "sync_reserve_da_60":    "DA Sync Reserve",
    "regup_rt_5":            "RT RegUp",
    "regdown_rt_5":          "RT RegDown",
    "ecrs_rt_5":             "RT ECRS",
    "nonspin_rt_5":          "RT Non-Spin",
    "spin_rt_5":             "RT RRS",
    "sync_reserve_rt_5":     "RT Sync Reserve",
    "ordc":                  "ORDC Adder",
    "total":                 "Total",
}

# Row order in the output (Total kept at the bottom).
ROW_ORDER = [
    "DA Energy", "RT Energy", "RT Energy Deviation",
    "DA Virtual Energy", "RT Virtual Energy",
    "DA RegUp", "DA RegDown", "DA RRS", "DA ECRS", "DA Non-Spin", "DA Sync Reserve",
    "RT RegUp", "RT RegDown", "RT RRS", "RT ECRS", "RT Non-Spin", "RT Sync Reserve",
    "ORDC Adder",
    "Total",
]


def _iso_cpt(d: date) -> str:
    """ISO-8601 with the correct CPT offset (handles DST)."""
    return datetime(d.year, d.month, d.day, tzinfo=CPT).isoformat()


def fetch_revenue(token: str, sb: dict, start: date, end: date) -> pd.DataFrame:
    """One call to /revenue at hourly resolution. Returns a DataFrame; empty if 204."""
    client   = first(sb, "SMARTBIDDER_CLIENT", default="apex")
    resource = first(sb, "Resource", "SMARTBIDDER_RESOURCE", default="Kiskadee Storage")
    params = {
        "client": client, "iso": "ERCOT", "resource": resource,
        "start_date": _iso_cpt(start),
        "end_date":   _iso_cpt(end),
        "return_format": "json",
        "strategy":   BENCHMARK_NAME,
        "resolution": "hourly",
    }
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    r = requests.get(f"{SMARTBIDDER_BASE}/revenue", params=params, headers=headers, timeout=300)
    if r.status_code == 204:
        return pd.DataFrame()
    if r.status_code >= 400:
        raise RuntimeError(f"/revenue {r.status_code}: {r.text[:400]}")
    j = r.json()
    return pd.DataFrame(j["data"], columns=j["columns"])


def fetch_soc(token: str, sb: dict, start: date, end: date) -> pd.DataFrame:
    """One call to /soc-detailed for the benchmark strategy. 5-min granular."""
    client   = first(sb, "SMARTBIDDER_CLIENT", default="apex")
    resource = first(sb, "Resource", "SMARTBIDDER_RESOURCE", default="Kiskadee Storage")
    params = {
        "client": client, "iso": "ERCOT", "resource": resource,
        "start_date": _iso_cpt(start),
        "end_date":   _iso_cpt(end),
        "return_format": "json",
        "strategy":   BENCHMARK_NAME,
    }
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    r = requests.get(f"{SMARTBIDDER_BASE}/soc-detailed", params=params, headers=headers, timeout=300)
    if r.status_code == 204:
        return pd.DataFrame()
    if r.status_code >= 400:
        raise RuntimeError(f"/soc-detailed {r.status_code}: {r.text[:400]}")
    j = r.json()
    return pd.DataFrame(j["data"], columns=j["columns"])


def month_chunks(start: date, end: date):
    """Yield (chunk_start, chunk_end) covering [start, end) split at month boundaries.
    `chunk_end` is exclusive."""
    cur = start
    while cur < end:
        if cur.month == 12:
            nxt = date(cur.year + 1, 1, 1)
        else:
            nxt = date(cur.year, cur.month + 1, 1)
        yield cur, min(nxt, end)
        cur = nxt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-01-01",
                    help="Inclusive start date (YYYY-MM-DD). Default 2026-01-01.")
    ap.add_argument("--end",   default=None,
                    help="Exclusive end date (YYYY-MM-DD). Default = today (CPT).")
    args = ap.parse_args()

    start = date.fromisoformat(args.start)
    end   = date.fromisoformat(args.end) if args.end else datetime.now(CPT).date()
    print(f"🎯 window: {start.isoformat()}  →  {end.isoformat()}  (exclusive)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sb_section = load_env_sections(ENV_PATH).get("smartbidder", {})
    token = smartbidder_token(sb_section)

    # -------- revenue (hourly, chunked by month) --------
    print("\n📥 /revenue  (hourly, chunked by month)")
    rev_parts = []
    for s, e in month_chunks(start, end):
        print(f"   {s} .. {e}  ", end="", flush=True)
        df = fetch_revenue(token, sb_section, s, e)
        print(f"rows={len(df):>6}")
        if not df.empty:
            rev_parts.append(df)
    if not rev_parts:
        sys.exit("❌ no revenue rows returned across the requested window")
    rev = pd.concat(rev_parts, ignore_index=True)

    rev["timestamp"] = pd.to_datetime(rev["timestamp"], utc=True).dt.tz_convert(CPT)
    # Period-ending: the row at HE=01:00 covers 00:00–01:00 → use the *prior* hour
    # for monthly bucketing so 01:00 belongs to the month of 00:00. Subtract 1 min,
    # then take month_start (tz dropped at to_period() — fine since we just want a label).
    period = (rev["timestamp"] - pd.Timedelta(minutes=1)).dt.tz_localize(None).dt.to_period("M")
    rev["month"] = period.dt.to_timestamp()
    # Trim period-ending bleed: drop any row whose bucket month sits before the
    # requested start (e.g. the 00:00 row of start_date covers prior-month 23:00→00:00).
    rev = rev[rev["month"] >= pd.Timestamp(start.replace(day=1))]
    rev["product_label"] = rev["product"].map(PRODUCT_LABEL).fillna(rev["product"])

    # Pivot $ totals per product per month.
    pivot_usd = (rev
                 .pivot_table(index="product_label", columns="month",
                              values="revenue", aggfunc="sum", fill_value=0.0))
    # Order rows; drop rows that are all zero (so unused products don't clutter).
    rows = [p for p in ROW_ORDER if p in pivot_usd.index]
    rows += [p for p in pivot_usd.index if p not in rows]  # any unmapped products at the end
    pivot_usd = pivot_usd.reindex(rows)
    pivot_usd = pivot_usd.loc[(pivot_usd != 0).any(axis=1)]

    pivot_kw = pivot_usd / GKS_KW
    pivot_kw.columns = [c.strftime("%Y-%m") for c in pivot_kw.columns]

    # -------- SoC (5-min, chunked by month) --------
    print("\n📥 /soc-detailed  (5-min, chunked by month)")
    soc_parts = []
    for s, e in month_chunks(start, end):
        print(f"   {s} .. {e}  ", end="", flush=True)
        df = fetch_soc(token, sb_section, s, e)
        print(f"rows={len(df):>6}")
        if not df.empty:
            soc_parts.append(df)
    if soc_parts:
        soc = pd.concat(soc_parts, ignore_index=True)
        soc["timestamp"] = pd.to_datetime(soc["timestamp"], utc=True).dt.tz_convert(CPT)
        # Daily max → monthly mean.
        soc["day"] = soc["timestamp"].dt.date
        daily_max = (soc.groupby("day", as_index=False)["soc_pct"].max())
        daily_max["month"] = pd.to_datetime(daily_max["day"]).dt.to_period("M").dt.strftime("%Y-%m")
        monthly_avg_max_soc_pct = (daily_max.groupby("month")["soc_pct"].mean() * 100).round(2)
    else:
        monthly_avg_max_soc_pct = pd.Series(dtype=float)
        print("   ⚠️ no SoC data — SoC column will be empty")

    # -------- assemble final table --------
    # Transpose so months are rows and products are columns; then add the SoC column.
    out = pivot_kw.T  # index=month label, columns=products
    out.index.name = "month"
    out["Avg of Daily Max SoC (%)"] = monthly_avg_max_soc_pct
    out = out.round(2)

    # Console preview
    print("\n=== Benchmark monthly revenue ($/kW) + Avg Daily Max SoC (%) ===")
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    print(out.to_string())

    # -------- persist --------
    csv_path     = OUT_DIR / "benchmark_monthly_revenue_per_kw.csv"
    parquet_path = OUT_DIR / "benchmark_monthly_revenue_per_kw_raw.parquet"
    out.to_csv(csv_path)
    pivot_usd.columns = [c.strftime("%Y-%m") for c in pivot_usd.columns]
    pivot_usd.to_parquet(parquet_path)
    print(f"\n💾 wrote {csv_path}")
    print(f"💾 wrote {parquet_path}  (raw USD totals — pre-kW divide)")


if __name__ == "__main__":
    main()
