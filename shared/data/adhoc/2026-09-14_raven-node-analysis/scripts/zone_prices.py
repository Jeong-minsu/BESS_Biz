"""zone_: zone-level price structure HOUSTON vs NORTH/SOUTH/WEST vs ERCOT (HB_BUSAVG) from raw/price_panel.
Premium/discount vs HB_BUSAVG, hourly profile, volatility, scarcity frequency. Per year 2023-09..2026-09-13.
Output: derived/zone_price_summary.json, derived/zone_price_hourly_premium.csv
"""
import json
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]
IDS = {10000697077: "HB_HOUSTON", 10000697078: "HB_NORTH", 10000697079: "HB_SOUTH", 10000697080: "HB_WEST",
       10000698380: "HB_BUSAVG", 10000698390: "LZ_HOUSTON", 10000698392: "LZ_NORTH", 10000698394: "LZ_SOUTH",
       10000698395: "LZ_WEST"}
parts = []
for f in sorted((ROOT / "raw/price_panel").glob("*.parquet")):
    d = pd.read_parquet(f, columns=["OBJECTID", "DATETIME", "DALMP", "RTLMP", "FLOWDAY"])
    d = d[d.OBJECTID.isin(IDS)]; d["name"] = d.OBJECTID.map(IDS); parts.append(d)
p = pd.concat(parts, ignore_index=True)
p["ts"] = pd.to_datetime(p.DATETIME); p["year"] = p.ts.dt.year; p["hr"] = p.ts.dt.hour
print("rows", len(p), p.ts.min(), p.ts.max()); print(p.groupby("name").size())
da = p.pivot_table(index="ts", columns="name", values="DALMP"); rt = p.pivot_table(index="ts", columns="name", values="RTLMP")
HUBS = ["HB_HOUSTON", "HB_NORTH", "HB_SOUTH", "HB_WEST", "HB_BUSAVG"]
LZS = ["LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH", "LZ_WEST"]

rows = []
for y, g in rt.groupby(rt.index.year):
    gd = da.loc[g.index]
    for z in HUBS + LZS:
        r, d_ = g[z].dropna(), gd[z].dropna()
        rows.append({"year": int(y), "node": z, "hours": int(len(r)),
                     "rt_mean": r.mean(), "da_mean": d_.mean(),
                     "rt_prem_vs_busavg": (g[z] - g["HB_BUSAVG"]).mean(), "da_prem_vs_busavg": (gd[z] - gd["HB_BUSAVG"]).mean(),
                     "rt_std": r.std(), "rt_p95": r.quantile(.95), "rt_p05": r.quantile(.05),
                     "rt_hours_gt100": int((r > 100).sum()), "rt_hours_gt500": int((r > 500).sum()), "rt_hours_gt1000": int((r > 1000).sum()),
                     "rt_hours_neg": int((r < 0).sum()),
                     "dart_mean_abs": (d_ - r).abs().mean(),
                     "tb2_rt_mean": g[z].groupby(g.index.date).apply(lambda s: (s.nlargest(2).mean() - s.nsmallest(2).mean()) if s.notna().sum() >= 20 else np.nan).mean(),
                     "tb2_da_mean": gd[z].groupby(gd.index.date).apply(lambda s: (s.nlargest(2).mean() - s.nsmallest(2).mean()) if s.notna().sum() >= 20 else np.nan).mean()})
ann = pd.DataFrame(rows).round(2)
pd.set_option("display.width", 250); print(ann[ann.node.isin(HUBS)].to_string())

# hourly premium profile vs BUSAVG (RT and DA), 2025-01 .. latest, by hub
recent = rt[rt.index >= "2025-01-01"]; recent_da = da.loc[recent.index]
prof = pd.DataFrame({f"{z}_rt": (recent[z] - recent["HB_BUSAVG"]).groupby(recent.index.hour).mean() for z in HUBS[:4]} |
                    {f"{z}_da": (recent_da[z] - recent_da["HB_BUSAVG"]).groupby(recent_da.index.hour).mean() for z in HUBS[:4]}).round(2)
prof.index.name = "hour_ending"; prof.to_csv(ROOT / "derived/zone_price_hourly_premium.csv"); print(prof.to_string())

# seasonal premium (RT) by hub, 2025-01..
seas = pd.DataFrame({z: (recent[z] - recent["HB_BUSAVG"]).groupby(recent.index.month).mean() for z in HUBS[:4]}).round(2)
seas.index.name = "month"; print(seas.to_string())

# midday (HE11-16) vs evening (HE18-21) premium by year, Houston vs South
blocks = {}
for y, g in rt.groupby(rt.index.year):
    blocks[int(y)] = {z: {"midday_HE11_16": round((g[z] - g["HB_BUSAVG"])[g.index.hour.isin(range(10, 16))].mean(), 2),
                          "evening_HE18_21": round((g[z] - g["HB_BUSAVG"])[g.index.hour.isin(range(17, 21))].mean(), 2)}
                     for z in HUBS[:4]}
out = {"source": "raw/price_panel (Yes Energy datalake ercot/prices/lmp/hourly), hourly DA/RT LMP, period-ending CT; HB_BUSAVG = ERCOT bus-average reference",
       "coverage": [str(p.ts.min()), str(p.ts.max())], "annual": ann.to_dict(orient="records"),
       "hourly_premium_2025on": prof.reset_index().to_dict(orient="records"), "monthly_rt_premium_2025on": seas.reset_index().to_dict(orient="records"),
       "block_premium_by_year": blocks}
(ROOT / "derived/zone_price_summary.json").write_text(json.dumps(out, indent=1, default=float)); print("wrote")
