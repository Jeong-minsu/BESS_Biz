"""Fetch panel for the 2026-09-17 low-regional-wind analog study (real data only).

1) D+1 (2026-09-17) leakage-free forecast: regional wind STWPF + system MTLF + solar STPPF
   (latest vintage <= D-1 13:59 GMT).
2) History: hourly regional wind actuals (ercot/gen/wind_rti, GEOGRAPHIC REGION objects)
   for Jul 1 - Oct 31 of 2021..2026.
Outputs raw/fc_20260917.parquet, raw/wind_region_hourly.parquet (idempotent).
"""
from __future__ import annotations
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAVEN = ROOT.parent / "2026-09-14_raven-node-analysis" / "scripts"
sys.path.insert(0, str(RAVEN))
import dl  # noqa: E402

OUT = ROOT / "raw"
SYS = 10000712973
REGIONS = {10004189450: "west", 10004189446: "coastal", 10004189447: "south",
           10004189449: "north", 10004189445: "panhandle", 10004189442: "gr_ercot"}


def _dt(s):
    return pd.to_datetime(s, format="%m/%d/%Y %H:%M:%S")


# ---------- 1) D+1 forecast ----------
def latest_vintage(kind: str, dminus1: str, cutoff_hhmm: str = "1359"):
    keys = [k for k, _ in dl.ls(f"ercot/vintage/{kind}/{dminus1}")]
    keys = [k for k in keys if Path(k).name[:12][8:12] <= cutoff_hhmm]
    return sorted(keys)[-1] if keys else None


def fetch_fc(flowday="2026-09-17", dminus1="20260916"):
    rows = {}
    for kind in ("wind_stwpf", "load_forecast", "solar_stppf"):
        key = latest_vintage(kind, dminus1)
        if key is None:
            print(f"  !! no vintage for {kind}")
            continue
        df = dl.read_csv(key, header=None)
        df["dt"] = _dt(df[2])
        df = df[df["dt"].dt.strftime("%Y-%m-%d").eq(flowday) |
                (df["dt"] == pd.Timestamp(flowday) + pd.Timedelta(days=1))]
        if kind == "wind_stwpf":
            d = df[df[0].isin(REGIONS)].copy()
            d["region"] = d[0].map(REGIONS)
            p = d.pivot_table(index="dt", columns="region", values=4, aggfunc="mean")
            p.columns = [f"wind_fc_{c}" for c in p.columns]
            rows["wind"] = p
        else:
            d = df[df[0] == SYS]
            col = "load_fc" if kind == "load_forecast" else "solar_fc"
            rows[col] = pd.Series(pd.to_numeric(d[4].values), index=d["dt"].values,
                                  name=col).groupby(level=0).mean()
        print(f"  {kind}: {key}")
    out = rows.pop("wind")
    for k, s in rows.items():
        out = out.join(s, how="left")
    out["solar_fc"] = out.get("solar_fc", pd.Series(dtype=float)).fillna(0.0)
    out.index.name = "hour_end"
    out.to_parquet(OUT / f"fc_{flowday.replace('-', '')}.parquet")
    print(out.round(0).to_string())


# ---------- 2) historical regional wind actuals ----------
def wind_day(d):
    df = dl.try_read_csv(f"ercot/gen/wind_rti/{d:%Y%m%d}.csv.gz", header=None)
    if df is None:
        return None
    df = df[df[0].isin(REGIONS)].copy()
    if df.empty:
        return None
    df["region"] = df[0].map(REGIONS)
    p = df.pivot_table(index=_dt(df[2]), columns="region", values=4, aggfunc="mean")
    p.columns = [f"wind_{c}" for c in p.columns]
    p.index.name = "hour_end"
    p["flowday"] = pd.Timestamp(d)
    return p.reset_index()


def fetch_wind():
    f = OUT / "wind_region_hourly.parquet"
    have = set()
    if f.exists():
        have = set(pd.read_parquet(f)["flowday"].unique())
    days = []
    for y in range(2021, 2027):
        days += list(pd.date_range(f"{y}-07-01", min(pd.Timestamp(f"{y}-10-31"),
                                                     pd.Timestamp("2026-09-15")), freq="D"))
    days = [d for d in days if d not in have and d <= pd.Timestamp("2026-09-15")]
    print(f"  fetching {len(days)} wind days")
    with ThreadPoolExecutor(16) as ex:
        parts = [p for p in ex.map(wind_day, days) if p is not None]
    if parts:
        new = pd.concat(parts, ignore_index=True)
        if f.exists():
            new = pd.concat([pd.read_parquet(f), new], ignore_index=True)
        new = new.drop_duplicates(subset=["hour_end"]).sort_values("hour_end")
        new.to_parquet(f, index=False)
        print(f"  wind rows={len(new)} {new.hour_end.min()} .. {new.hour_end.max()}")


if __name__ == "__main__":
    print("[1] D+1 forecast")
    fetch_fc()
    print("[2] historical regional wind actuals")
    fetch_wind()
