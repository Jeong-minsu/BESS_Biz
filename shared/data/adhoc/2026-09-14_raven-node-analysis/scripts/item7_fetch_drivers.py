"""ITEM 7 — hourly driver panel 2023-09-01..2026-09-13 for the top-10 constraint driver analysis.
Extends the GKS/Houston projects' fetch_panel.py / build_threshold_panel.py (same tables, same headerless
layouts: col0 OBJECTID, col2 DATETIME (period-ending CT), col4 VALUE) to all regions and the full 3-year window.
  wind   ercot/gen/wind_rti/{YYYYMMDD}.csv.gz         GR_* geographic regions (MW)
  solar  ercot/gen/generation_solar_rt/{YYYYMMDD}     solar regions + ERCOT total (MW)
  load   ercot/load/rtload_hourly_wz/{YYYYMMDD}       weather-zone loads (MW)
  temp   ercot/weather/actual/{YYYYMMDD}              station drybulb (F), col4 NAME, col7 DRYBULB
Output raw/item7_driver_panel.parquet (hourly, one row per period-ending hour). Real data only, no fill.
"""
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl

R = Path(__file__).resolve().parents[1]
OUT = R / "raw" / "item7_driver_panel.parquet"
WIND = {10004189446: "wind_coastal", 10004189447: "wind_south", 10004189450: "wind_west", 10004189449: "wind_north",
        10004189445: "wind_panhandle", 10017078074: "wind_houston", 10004189442: "wind_ercot"}
SOLAR = {10017006228: "solar_southeast", 10017014635: "solar_farwest", 10017006224: "solar_centerwest",
         10017006229: "solar_centereast", 10017006225: "solar_northwest", 10017006227: "solar_fareast", 10000712973: "solar_ercot"}
LOAD = {10002211345: "load_coast", 10002211351: "load_southern", 10002211350: "load_southcentral", 10002211348: "load_north",
        10002211349: "load_northcentral", 10002211346: "load_east", 10002211352: "load_west", 10002211347: "load_farwest",
        10002211353: "load_ercot"}
TEMP = {"TX - Galveston/Scholes": "temp_galveston", "TX - Houston/William P. Hobby": "temp_hobby",
        "TX - Dallas-Fort Worth/Intl": "temp_dfw", "TX - San Antonio/Intl": "temp_sanantonio",
        "TX - Corpus Christi/Intl": "temp_corpus", "TX - Brownsville/Intl": "temp_brownsville",
        "TX - Midland-Odessa": "temp_midland", "TX - Austin/Bergstrom/Intl": "temp_austin"}
DAYS = pd.date_range("2023-09-01", "2026-09-13", freq="D")


def id_series(key, idmap):
    df = dl.try_read_csv(key, header=None)
    if df is None: return None
    df = df[df[0].isin(idmap)]
    if df.empty: return None
    df = df.rename(columns={0: "oid", 2: "dt", 4: "val"})[["oid", "dt", "val"]]
    df["dt"] = pd.to_datetime(df["dt"], format="%m/%d/%Y %H:%M:%S")
    df["var"] = df["oid"].map(idmap)
    return df.pivot_table(index="dt", columns="var", values="val", aggfunc="mean")


def temp_series(key):
    df = dl.try_read_csv(key, header=None)
    if df is None: return None
    df = df[df[4].isin(TEMP)]
    if df.empty: return None
    df = df.rename(columns={2: "dt", 4: "name", 7: "val"})[["dt", "name", "val"]]
    df["dt"] = pd.to_datetime(df["dt"], format="%m/%d/%Y %H:%M:%S")
    df["var"] = df["name"].map(TEMP)
    return df.pivot_table(index="dt", columns="var", values="val", aggfunc="mean")


def one_day(d):
    ds = d.strftime("%Y%m%d")
    parts = [id_series(f"ercot/gen/wind_rti/{ds}.csv.gz", WIND),
             id_series(f"ercot/gen/generation_solar_rt/{ds}.csv.gz", SOLAR),
             id_series(f"ercot/load/rtload_hourly_wz/{ds}.csv.gz", LOAD),
             temp_series(f"ercot/weather/actual/{ds}.csv.gz")]
    parts = [p for p in parts if p is not None]
    if not parts: return None
    df = pd.concat(parts, axis=1)
    return df.groupby(level=0).first().resample("h").mean()  # hourly grid; sub-hourly wind/solar averaged


def main():
    if OUT.exists():
        print("cached", OUT); return
    rows = []
    with ThreadPoolExecutor(24) as ex:
        for i, r in enumerate(ex.map(one_day, DAYS)):
            if r is not None: rows.append(r)
            if i % 100 == 0: print("day", i, "/", len(DAYS), flush=True)
    panel = pd.concat(rows).sort_index()
    panel = panel[~panel.index.duplicated(keep="first")]
    panel.to_parquet(OUT)
    print("saved", OUT, panel.shape)
    print(panel.notna().mean().round(3).to_string())
    print(panel.describe().T[["mean", "min", "max"]].round(0).to_string())


if __name__ == "__main__":
    main()
