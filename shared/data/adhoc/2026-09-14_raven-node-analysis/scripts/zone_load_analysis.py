"""zone_: Houston load-zone demand growth 2023..2026YTD vs NORTH/SOUTH/WEST/ERCOT.
Input: raw/zone_load_hourly.parquet (ercot/load/rtload_hourly = ERCOT *load zones* HOUSTON/NORTH/SOUTH/WEST;
ercot/load/rtload_hourly_wz = weather zones, used only for the COAST cross-check).
Output: derived/zone_load_summary.json, derived/zone_load_monthly.csv
"""
import json
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
df = pd.read_parquet(ROOT / "raw/zone_load_hourly.parquet")
df["ts"] = pd.to_datetime(df.hour_end, format="%m/%d/%Y %H:%M:%S")
df["year"] = df.ts.dt.year; df["month"] = df.ts.dt.month
LZ = ["LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH", "LZ_WEST", "ERCOT"]
lz = df[df.objectname.isin(LZ)]
last = df.ts.max(); ytd_end = (last.month, last.day)
print("coverage:", df.ts.min(), "->", last)

# hours per zone-year (sanity)
print(lz.groupby(["objectname", "year"]).load_mw.count().unstack())

# --- annual: full-year mean & peak, plus YTD (Jan-1 .. Sep-13) mean for like-for-like growth
ann = lz.groupby(["objectname", "year"]).load_mw.agg(avg_mw="mean", peak_mw="max").reset_index()
ytd_mask = (lz.ts.dt.month < ytd_end[0]) | ((lz.ts.dt.month == ytd_end[0]) & (lz.ts.dt.day <= ytd_end[1]))
ytd = lz[ytd_mask].groupby(["objectname", "year"]).load_mw.agg(ytd_avg_mw="mean", ytd_peak_mw="max").reset_index()
ann = ann.merge(ytd, on=["objectname", "year"])
# night-minimum / load-factor proxies for industrial base load
ann["load_factor"] = (ann.avg_mw / ann.peak_mw).round(3)
mins = lz.groupby(["objectname", "year", lz.ts.dt.date]).load_mw.min().groupby(level=[0, 1]).mean().rename("avg_daily_min_mw").reset_index()
ann = ann.merge(mins, on=["objectname", "year"])
ann["daily_min_to_avg"] = (ann.avg_daily_min_mw / ann.avg_mw).round(3)
# share of ERCOT (YTD basis so 2026 is comparable)
erc = ann[ann.objectname == "ERCOT"].set_index("year")
ann["share_of_ercot_ytd"] = ann.apply(lambda r: round(r.ytd_avg_mw / erc.loc[r.year, "ytd_avg_mw"], 4), axis=1)
ann["share_of_ercot_peak"] = ann.apply(lambda r: round(r.peak_mw / erc.loc[r.year, "peak_mw"], 4), axis=1)
for c in ["avg_mw", "peak_mw", "ytd_avg_mw", "ytd_peak_mw", "avg_daily_min_mw"]: ann[c] = ann[c].round(0)
print(ann.to_string())

# --- growth: YTD 2023 -> YTD 2026 CAGR (3 yrs, like-for-like), and full-year 2023 -> 2025 (2 yrs)
g = {}
for z in LZ:
    a = ann[ann.objectname == z].set_index("year")
    g[z] = {
        "cagr_ytd_2023_2026": round((a.loc[2026, "ytd_avg_mw"] / a.loc[2023, "ytd_avg_mw"]) ** (1 / 3) - 1, 4),
        "cagr_fullyear_2023_2025": round((a.loc[2025, "avg_mw"] / a.loc[2023, "avg_mw"]) ** (1 / 2) - 1, 4),
        "peak_growth_2023_2026_pct": round(a.loc[2026, "peak_mw"] / a.loc[2023, "peak_mw"] - 1, 4),
        "yoy_ytd": {int(y): round(a.loc[y, "ytd_avg_mw"] / a.loc[y - 1, "ytd_avg_mw"] - 1, 4) for y in (2024, 2025, 2026)},
    }
print(json.dumps(g, indent=1))

# --- monthly series (all zones) for the dashboard
mon = lz.groupby(["objectname", "year", "month"]).load_mw.agg(avg_mw="mean", peak_mw="max").round(0).reset_index()
mon.to_csv(ROOT / "derived/zone_load_monthly.csv", index=False)

# --- hourly shape by season (Houston vs ERCOT): summer (Jun-Sep) and winter (Dec-Feb) mean by hour, 2025-26
shape = {}
sub = lz[lz.year >= 2025].copy(); sub["hr"] = sub.ts.dt.hour
for name, months in (("summer", [6, 7, 8, 9]), ("winter", [12, 1, 2])):
    s = sub[sub.month.isin(months)].groupby(["objectname", "hr"]).load_mw.mean().unstack(0)
    s = (s / s.mean()).round(3)  # normalised to daily mean
    shape[name] = {z: s[z].tolist() for z in LZ}
    print(name, "peak/mean ratio:", {z: round(s[z].max(), 3) for z in LZ})

# --- weather-zone cross-check: COAST vs LZ_HOUSTON
wz = df[df.objectname == "WZ_Coast"].groupby("year").load_mw.agg(avg_mw="mean", peak_mw="max").round(0)
print("WZ_Coast:\n", wz)

out = {
    "source": "Yes Energy datalake ercot/load/rtload_hourly (ERCOT load zones HOUSTON/NORTH/SOUTH/WEST + ERCOT total), hourly actual, period-ending CT",
    "coverage": [str(df.ts.min()), str(last)],
    "ytd_definition": f"Jan-01 .. {last.month:02d}-{last.day:02d} of each year (like-for-like with 2026)",
    "annual": ann.to_dict(orient="records"),
    "growth": g,
    "hourly_shape_norm_2025_2026": shape,
    "wz_coast_crosscheck": wz.reset_index().to_dict(orient="records"),
}
(ROOT / "derived/zone_load_summary.json").write_text(json.dumps(out, indent=1, default=float))
print("wrote derived/zone_load_summary.json")
