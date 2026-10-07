"""Houston zone overview — hourly load by ERCOT weather zone, 2023-01-01 .. 2026-09-13.

Source: Yes Energy datalake ercot/load/rtload_hourly_wz (RTI LOAD - WZ ERCOT, hourly, period-ending CT).
Houston = WZ_Coast. Growth compared on a like-for-like Jan-Aug window because 2026 is partial.
Idempotent: raw panel cached to raw/zone_load_wz.parquet. Real data only.
"""
import sys, json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
import pandas as pd, numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl

BASE = Path(__file__).resolve().parents[1]; D = BASE / "derived"
RAW = BASE / "raw" / "zone_load_wz.parquet"
NAMES = {10002211345: "COAST", 10002211346: "EAST", 10002211347: "FAR_WEST",
         10002211348: "NORTH", 10002211349: "NORTH_CENTRAL", 10002211350: "SOUTH_CENTRAL",
         10002211351: "SOUTH", 10002211352: "WEST", 10002211353: "ERCOT"}


def one(d):
    df = dl.try_read_csv(f"ercot/load/rtload_hourly_wz/{d:%Y%m%d}.csv.gz", header=None)
    if df is None:
        return None
    df = df.iloc[:, [0, 2, 4]]
    df.columns = ["oid", "dt", "mw"]
    return df


if RAW.exists():
    panel = pd.read_parquet(RAW)
else:
    days, d = [], date(2023, 1, 1)
    while d <= date(2026, 9, 13):
        days.append(d); d += timedelta(days=1)
    with ThreadPoolExecutor(16) as ex:
        parts = [p for p in ex.map(one, days) if p is not None]
    panel = pd.concat(parts, ignore_index=True)
    panel["zone"] = panel.oid.map(NAMES)
    panel["dt"] = pd.to_datetime(panel.dt)
    panel["mw"] = pd.to_numeric(panel.mw, errors="coerce")
    panel = panel.drop(columns="oid")
    panel.to_parquet(RAW, index=False)
    print(f"fetched {len(days)} days -> {len(panel):,} rows")

panel["year"] = panel.dt.dt.year
panel["month"] = panel.dt.dt.month
ja = panel[panel.month <= 8]          # like-for-like Jan-Aug

avg = ja.pivot_table(index="zone", columns="year", values="mw", aggfunc="mean")
peak = panel.pivot_table(index="zone", columns="year", values="mw", aggfunc="max")
# 2026 peak is Jan-Sep only; summer peak is in, so it is comparable for peak purposes

ORDER = ["ERCOT", "COAST", "NORTH_CENTRAL", "SOUTH_CENTRAL", "SOUTH", "FAR_WEST", "WEST", "EAST", "NORTH"]
avg = avg.reindex(ORDER); peak = peak.reindex(ORDER)
cagr = 100 * ((avg[2026] / avg[2023]) ** (1 / 3) - 1)
share = 100 * avg.div(avg.loc["ERCOT"], axis=1)

print("\n=== average load, Jan-Aug (MW) ===")
print(avg.round(0).to_string())
print("\n=== 3-yr CAGR of Jan-Aug average load (2023->2026), % ===")
print(cagr.round(2).to_string())
print("\n=== share of ERCOT load, % ===")
print(share.round(1).to_string())
print("\n=== annual peak hourly load (MW) ===")
print(peak.round(0).to_string())

# shape features: load factor & temperature-driven peakiness, midday vs evening
ja26 = panel[panel.year == 2025]
lf = (ja26.groupby("zone").mw.mean() / ja26.groupby("zone").mw.max()).reindex(ORDER)
panel["he"] = panel.dt.dt.hour.where(panel.dt.dt.hour != 0, 24)
summer = panel[(panel.year == 2025) & panel.month.isin([6, 7, 8])]
prof = summer.pivot_table(index="he", columns="zone", values="mw", aggfunc="mean")
peakiness = (prof.max() / prof.min()).reindex(ORDER)
print("\n=== 2025 load factor (avg/peak) and summer daily swing (max HE / min HE) ===")
print(pd.DataFrame({"load_factor": lf, "summer_daily_swing": peakiness}).round(3).to_string())

out = {
    "source": "Yes Energy datalake ercot/load/rtload_hourly_wz (RTI weather-zone load), hourly",
    "window_note": "growth on Jan-Aug like-for-like (2026 partial); peak = max hourly in calendar year (2026 through 9/13)",
    "avg_jan_aug_mw": {z: {str(y): float(avg.loc[z, y]) for y in avg.columns} for z in ORDER},
    "cagr_2023_2026_pct": {z: float(cagr[z]) for z in ORDER},
    "share_of_ercot_pct": {z: {str(y): float(share.loc[z, y]) for y in share.columns} for z in ORDER},
    "peak_mw": {z: {str(y): float(peak.loc[z, y]) for y in peak.columns} for z in ORDER},
    "load_factor_2025": {z: float(lf[z]) for z in ORDER},
    "summer_daily_swing_2025": {z: float(peakiness[z]) for z in ORDER},
    "coast_summer_profile_2025": {int(h): float(v) for h, v in prof["COAST"].items()},
}
json.dump(out, open(D / "zone_load.json", "w"), indent=1)
print("\nwrote zone_load.json")
