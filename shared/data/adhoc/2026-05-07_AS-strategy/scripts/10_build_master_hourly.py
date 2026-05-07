"""
Adhoc AS-strategy — build unified hourly master table

Joins:
  - DA/RT LMP @ GKS_BESS_RN, HB_HOUSTON   (derived/lmp_hourly.parquet)
  - DAM AS MCPC (5 products)              (derived/as_dam_mcpc_hourly.parquet)
  - Yes Energy forecasts + actuals        (derived/forecast_actual_hourly.parquet)
  - Tenaska GKS hourly (DA/RT/AS revenue) (shared/data/pnl/gks/hourly/*.json)

Time convention: datetime_ct = HE-1 (Hour Ending → Hour Beginning).
                 Tenaska is UTC; convert with America/Chicago.

Output:
  derived/master_hourly.parquet
  derived/master_summary.json
"""
from __future__ import annotations

import glob
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC_ROOT = Path(__file__).resolve().parents[1]
DERIVED = ADHOC_ROOT / "derived"
PROJECT_ROOT = Path(__file__).resolve().parents[5]
TENASKA_DIR = PROJECT_ROOT / "shared" / "data" / "pnl" / "gks" / "hourly"

START = pd.Timestamp("2026-01-01", tz="America/Chicago")
END   = pd.Timestamp("2026-03-07", tz="America/Chicago")  # exclusive
# Winter Storm Fern — exclude tail-event days (per user 2026-05-07)
EXCLUDE_DATES = pd.to_datetime([
    "2026-01-24", "2026-01-25", "2026-01-26", "2026-01-27", "2026-01-28"
]).date


def load_lmp() -> pd.DataFrame:
    df = pd.read_parquet(DERIVED / "lmp_hourly.parquet")
    df["datetime_ct"] = pd.to_datetime(df["datetime_ct"]).dt.tz_localize(
        "America/Chicago", ambiguous="infer", nonexistent="shift_forward"
    )
    # YE returns HE label; datetime_ct = HE start? Verify: YE format "01/01/2026 01:00:00" with HOURENDING=1
    # That timestamp 01:00 with HE=1 means hour 0->1, so timestamp is HE label time (= HE end).
    # Convert to HE start (= datetime_ct - 1h) so that datetime_ct represents the hour interval start.
    df["datetime_ct"] = df["datetime_ct"] - pd.Timedelta(hours=1)
    pv = df.pivot_table(
        index="datetime_ct", columns=["data_type", "node"], values="price"
    )
    pv.columns = [f"{c[0]}_{c[1]}" for c in pv.columns]  # e.g., DALMP_GKS_BESS_RN
    return pv.reset_index()


def load_as() -> pd.DataFrame:
    df = pd.read_parquet(DERIVED / "as_dam_mcpc_hourly.parquet")
    # ERCOT API returns hourEnding "HH:MM" string and deliveryDate ISO
    df["he"] = df["hourEnding"].str.slice(0, 2).astype(int)
    df["delivery_date"] = pd.to_datetime(df["deliveryDate"]).dt.date
    # datetime_ct = HE start = delivery_date + (HE-1) hours
    df["datetime_ct"] = pd.to_datetime(df["delivery_date"]) + pd.to_timedelta(df["he"] - 1, unit="h")
    df["datetime_ct"] = df["datetime_ct"].dt.tz_localize(
        "America/Chicago", ambiguous="infer", nonexistent="shift_forward"
    )
    pv = df.pivot_table(index="datetime_ct", columns="ancillaryType", values="MCPC")
    pv.columns = [f"AS_MCPC_{c}" for c in pv.columns]
    return pv.reset_index()


def load_forecasts() -> pd.DataFrame:
    df = pd.read_parquet(DERIVED / "forecast_actual_hourly.parquet")
    df["datetime_ct"] = pd.to_datetime(df["datetime_ct"]).dt.tz_localize(
        "America/Chicago", ambiguous="infer", nonexistent="shift_forward"
    )
    df["datetime_ct"] = df["datetime_ct"] - pd.Timedelta(hours=1)
    pv = df.pivot_table(index="datetime_ct", columns="data_type", values="value")
    return pv.reset_index()


def load_rt_as() -> pd.DataFrame:
    df = pd.read_parquet(DERIVED / "rt_as_hourly.parquet")
    df["datetime_ct"] = pd.to_datetime(df["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
    return df


def load_tenaska() -> pd.DataFrame:
    files = sorted(glob.glob(str(TENASKA_DIR / "2026-0[1-3]-*_energy_as_detail.json")))
    print(f"  Tenaska files: {len(files)}")
    rows = []
    for fp in files:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        rows.extend(data)
    df = pd.DataFrame(rows)
    df["datetime_utc"] = pd.to_datetime(df["interval_start_utc"], utc=True)
    df["datetime_ct"] = df["datetime_utc"].dt.tz_convert("America/Chicago")
    pv = df.pivot_table(
        index="datetime_ct", columns="datapoint", values="value", aggfunc="first"
    )
    pv.columns = [f"GKS_{c}" for c in pv.columns]
    return pv.reset_index()


def main() -> None:
    print("[10_build_master_hourly]")
    print("  loading LMP ...")
    lmp = load_lmp()
    print(f"    {lmp.shape}, range {lmp['datetime_ct'].min()} ~ {lmp['datetime_ct'].max()}")
    print("  loading DAM AS ...")
    asdf = load_as()
    print(f"    {asdf.shape}, range {asdf['datetime_ct'].min()} ~ {asdf['datetime_ct'].max()}")
    print("  loading forecasts ...")
    fc = load_forecasts()
    print(f"    {fc.shape}, range {fc['datetime_ct'].min()} ~ {fc['datetime_ct'].max()}")
    print("  loading RT AS ...")
    rtas = load_rt_as()
    print(f"    {rtas.shape}, range {rtas['datetime_ct'].min()} ~ {rtas['datetime_ct'].max()}")
    print("  loading Tenaska ...")
    tk = load_tenaska()
    print(f"    {tk.shape}, range {tk['datetime_ct'].min()} ~ {tk['datetime_ct'].max()}")

    # Merge — use LMP as anchor (full 65-day grid)
    master = lmp.merge(asdf, on="datetime_ct", how="left") \
                .merge(rtas,  on="datetime_ct", how="left") \
                .merge(fc,    on="datetime_ct", how="left") \
                .merge(tk,    on="datetime_ct", how="left")
    # Filter to analysis range
    master = master[(master["datetime_ct"] >= START) & (master["datetime_ct"] < END)]
    # Exclude Winter Storm Fern dates
    n_before = len(master)
    master = master[~pd.to_datetime(master["datetime_ct"]).dt.date.isin(EXCLUDE_DATES)]
    n_after = len(master)
    print(f"  excluded Storm Fern (1/24-1/28): {n_before-n_after} rows removed -> {n_after} rows remain")
    master = master.sort_values("datetime_ct").reset_index(drop=True)

    # Convenience cols
    master["he"]    = master["datetime_ct"].dt.hour + 1   # HE label
    master["date"]  = master["datetime_ct"].dt.date
    master["dow"]   = master["datetime_ct"].dt.dayofweek
    master["month"] = master["datetime_ct"].dt.month
    # Spread (DA - RT) per spec
    if "DALMP_GKS_BESS_RN" in master and "RTLMP_GKS_BESS_RN" in master:
        master["spread_gks"]   = master["DALMP_GKS_BESS_RN"] - master["RTLMP_GKS_BESS_RN"]
    if "DALMP_HB_HOUSTON" in master and "RTLMP_HB_HOUSTON" in master:
        master["spread_hub"]   = master["DALMP_HB_HOUSTON"] - master["RTLMP_HB_HOUSTON"]
    # Forecast errors (positive = under-forecasted, supply tighter than expected)
    if "LOAD_FORECAST" in master and "RTLOAD" in master:
        master["load_fc_err"] = master["RTLOAD"] - master["LOAD_FORECAST"]
    if "WIND_STWPF_BIDCLOSE" in master and "WIND_RTI" in master:
        master["wind_fc_err"] = master["WIND_RTI"] - master["WIND_STWPF_BIDCLOSE"]
    # AS DAM-RT spread per product (DAM > RT means DAM-commit better)
    for p in ["REGUP","REGDN","RRS","ECRS","NSPIN"]:
        d = f"AS_MCPC_{p}"; r = f"RT_AS_MCPC_{p}"
        if d in master and r in master:
            master[f"AS_SPREAD_{p}"] = master[d] - master[r]

    out = DERIVED / "master_hourly.parquet"
    master.to_parquet(out, index=False)
    print(f"\n  saved -> {out.name}  ({master.shape})")

    # Coverage summary
    summary = {
        "rows": len(master),
        "date_range": [str(master["datetime_ct"].min()), str(master["datetime_ct"].max())],
        "n_days": master["date"].nunique(),
        "columns": master.columns.tolist(),
        "non_null_counts": {c: int(master[c].notna().sum()) for c in master.columns},
    }
    summary_path = DERIVED / "master_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"  summary -> {summary_path.name}")
    print(f"\n  date coverage: {summary['n_days']} days")
    print(f"  columns ({len(master.columns)}): {list(master.columns)}")


if __name__ == "__main__":
    main()
