"""
Fast SB raw → hourly capability merge (split out from 08 to keep separable).

Inputs (already on disk):
    raw/sb_power_availability.json   (5-min)
    raw/sb_soc_detailed.parquet      (5-min)

Output:
    derived/sb_capability_hourly.parquet
        cols: datetime_ct, avail_discharge_mw, avail_charge_mw, soc_mwh_max
              clipped to nameplate 100 MW / 200 MWh

5-min → hourly aggregation rules:
    avail_discharge_mw : min over the hour (most conservative cap)
    avail_charge_mw    : min over the hour
    soc_mwh_max        : min over the hour (most conservative)
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC = Path(__file__).resolve().parents[1]
RAW = ADHOC / "raw"
DERIVED = ADHOC / "derived"
DERIVED.mkdir(parents=True, exist_ok=True)

CPT = ZoneInfo("America/Chicago")
START = date(2026, 1, 1)
END   = date(2026, 5, 11)  # exclusive

NAMEPLATE_MW = 100.0
NAMEPLATE_MWH = 200.0


def parse_ts_mixed_tz(s: pd.Series) -> pd.Series:
    """Parse an ISO timestamp series that may have mixed offsets (CPT std/DST)."""
    return pd.to_datetime(s, utc=True).dt.tz_convert(CPT)


def main():
    print(f"[09_build_sb_capability_hourly]")

    # Build hourly grid
    grid = pd.DataFrame({
        "datetime_ct": pd.date_range(
            start=pd.Timestamp(START, tz=CPT),
            end=pd.Timestamp(END, tz=CPT),
            freq="h", inclusive="left",
        )
    })
    grid["avail_discharge_mw"] = NAMEPLATE_MW
    grid["avail_charge_mw"]    = NAMEPLATE_MW
    grid["soc_mwh_max"]        = NAMEPLATE_MWH

    # ---- power-availability ----
    pa = pd.read_json(RAW / "sb_power_availability.json")
    pa["ts_utc"] = parse_ts_mixed_tz(pa["timestamp"])
    # 5-min period-ending → HE start = ts - 5min, then floor to hour
    pa["datetime_ct"] = (pa["ts_utc"] - pd.Timedelta(minutes=5)).dt.floor("h")
    pa["discharge_power"] = pd.to_numeric(pa["discharge_power"], errors="coerce")
    pa["charge_power"]    = pd.to_numeric(pa["charge_power"], errors="coerce")
    print(f"  power-availability 5-min rows: {len(pa)}")
    pa_h = pa.groupby("datetime_ct").agg(
        avail_discharge_mw=("discharge_power", "min"),
        avail_charge_mw=("charge_power", "min"),
    ).reset_index()
    print(f"  power-availability hourly: {len(pa_h)}")

    # ---- soc-detailed ----
    soc = pd.read_parquet(RAW / "sb_soc_detailed.parquet")
    soc["ts_utc"] = parse_ts_mixed_tz(soc["timestamp"])
    soc["datetime_ct"] = (soc["ts_utc"] - pd.Timedelta(minutes=5)).dt.floor("h")
    soc["soc_mwh_max"] = pd.to_numeric(soc["soc_mwh_max"], errors="coerce")
    print(f"  soc-detailed 5-min rows: {len(soc)}")
    soc_h = soc.groupby("datetime_ct").agg(soc_mwh_max=("soc_mwh_max", "min")).reset_index()
    print(f"  soc-detailed hourly: {len(soc_h)}")

    # ---- merge into grid, fall back to nameplate where missing, clip to nameplate ----
    out = grid.merge(pa_h.rename(columns={"avail_discharge_mw": "ds_sb",
                                            "avail_charge_mw":    "ch_sb"}),
                     on="datetime_ct", how="left")
    out = out.merge(soc_h.rename(columns={"soc_mwh_max": "soc_sb"}),
                    on="datetime_ct", how="left")
    out["avail_discharge_mw"] = out["ds_sb"].combine_first(out["avail_discharge_mw"]).clip(0, NAMEPLATE_MW)
    out["avail_charge_mw"]    = out["ch_sb"].combine_first(out["avail_charge_mw"]).clip(0, NAMEPLATE_MW)
    out["soc_mwh_max"]        = out["soc_sb"].combine_first(out["soc_mwh_max"]).clip(0, NAMEPLATE_MWH)
    out = out[["datetime_ct", "avail_discharge_mw", "avail_charge_mw", "soc_mwh_max"]]

    p = DERIVED / "sb_capability_hourly.parquet"
    out.to_parquet(p, index=False)
    print(f"\n  saved -> {p.name}  ({len(out)} rows)")
    print(f"  discharge_mw  mean={out['avail_discharge_mw'].mean():.1f}  median={out['avail_discharge_mw'].median():.1f}  min={out['avail_discharge_mw'].min():.1f}  hrs<100MW={int((out['avail_discharge_mw'] < NAMEPLATE_MW).sum())}")
    print(f"  charge_mw     mean={out['avail_charge_mw'].mean():.1f}  median={out['avail_charge_mw'].median():.1f}  min={out['avail_charge_mw'].min():.1f}  hrs<100MW={int((out['avail_charge_mw'] < NAMEPLATE_MW).sum())}")
    print(f"  soc_mwh_max   mean={out['soc_mwh_max'].mean():.1f}  median={out['soc_mwh_max'].median():.1f}  min={out['soc_mwh_max'].min():.1f}  hrs<200MWh={int((out['soc_mwh_max'] < NAMEPLATE_MWH).sum())}")

    # daily summary
    out["date"] = out["datetime_ct"].dt.date
    daily = out.groupby("date").agg(
        avail_discharge_mw_min=("avail_discharge_mw", "min"),
        avail_charge_mw_min=("avail_charge_mw", "min"),
        soc_mwh_max_min=("soc_mwh_max", "min"),
        avail_discharge_mw_mean=("avail_discharge_mw", "mean"),
        soc_mwh_max_mean=("soc_mwh_max", "mean"),
    ).reset_index()
    dp = DERIVED / "sb_capability_daily.parquet"
    daily.to_parquet(dp, index=False)
    print(f"  saved daily -> {dp.name}  ({len(daily)} rows)")


if __name__ == "__main__":
    main()
