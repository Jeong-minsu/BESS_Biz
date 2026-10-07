"""Houston zone overview — price character of ERCOT hubs, 2023-09 .. 2026-09.

Uses the pre-built nodal panel (raw/price_panel). For each trading hub: average price premium vs
the ERCOT bus average, midday vs evening premium, daily TB2 (top-2 minus bottom-2 hours), RT
volatility, and frequency of scarcity hours (RT > $500). Real data only.
"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl

BASE = Path(__file__).resolve().parents[1]; D = BASE / "derived"

obj = dl.read_csv("ercot/metadata/objects/all.csv.gz")
want = ["HB_HOUSTON", "HB_SOUTH", "HB_NORTH", "HB_WEST", "HB_PAN", "HB_BUSAVG"]
hub = obj[(obj.OBJECTTYPE == "price_node") & obj.OBJECTNAME.isin(want)][["OBJECTID", "OBJECTNAME"]]
ID = dict(zip(hub.OBJECTID, hub.OBJECTNAME))
print("hubs found:", sorted(ID.values()))

parts = []
for f in sorted(glob.glob(str(BASE / "raw/price_panel/*.parquet"))):
    d = pd.read_parquet(f)
    parts.append(d[d.OBJECTID.isin(ID.keys())])
df = pd.concat(parts, ignore_index=True)
df["hub"] = df.OBJECTID.map(ID)
df["dt"] = pd.to_datetime(df.DATETIME)
df["year"] = df.dt.dt.year
df["he"] = df.dt.dt.hour.where(df.dt.dt.hour != 0, 24)
df = df[df.year >= 2024]          # full calendar years + 2026 YTD

rt = df.pivot_table(index="dt", columns="hub", values="RTLMP")
da = df.pivot_table(index="dt", columns="hub", values="DALMP")
HUBS = [h for h in ["HB_HOUSTON", "HB_SOUTH", "HB_NORTH", "HB_WEST", "HB_PAN"] if h in rt.columns]

he = rt.index.hour.where(rt.index.hour != 0, 24)
yrs = rt.index.year
rows = []
for h in HUBS:
    for y in sorted(set(yrs)):
        m = yrs == y
        prem = (rt.loc[m, h] - rt.loc[m, "HB_BUSAVG"])
        mid = prem[(he[m] >= 10) & (he[m] <= 15)].mean()
        eve = prem[(he[m] >= 18) & (he[m] <= 22)].mean()
        # daily TB2 on RT
        s = rt.loc[m, h].dropna()
        g = s.groupby(s.index.normalize())
        tb2 = (g.apply(lambda x: x.nlargest(2).mean() - x.nsmallest(2).mean())).mean()
        rows.append(dict(hub=h, year=int(y),
                         rt_avg=float(rt.loc[m, h].mean()),
                         premium_vs_busavg=float(prem.mean()),
                         premium_midday_HE10_15=float(mid),
                         premium_evening_HE18_22=float(eve),
                         rt_tb2=float(tb2),
                         rt_std=float(rt.loc[m, h].std()),
                         hours_rt_gt_500=int((rt.loc[m, h] > 500).sum()),
                         hours_rt_lt_0=int((rt.loc[m, h] < 0).sum())))
t = pd.DataFrame(rows)
pd.set_option("display.width", 220)
print(t.round(2).to_string(index=False))

# hourly premium profile (2025-2026) Houston & South vs bus average
recent = yrs >= 2025
prof = {}
for h in ["HB_HOUSTON", "HB_SOUTH", "HB_WEST", "HB_NORTH"]:
    if h in rt.columns:
        prof[h] = (rt.loc[recent, h] - rt.loc[recent, "HB_BUSAVG"]).groupby(he[recent]).mean().round(2).to_dict()
print("\nHouston RT premium vs bus average by HE (2025-26):")
print({int(k): v for k, v in prof["HB_HOUSTON"].items()})

json.dump({"source": "raw/price_panel (Yes Energy datalake hourly DA/RT LMP), hubs",
           "by_hub_year": t.to_dict(orient="records"),
           "rt_premium_profile_2025_26": {h: {int(k): v for k, v in p.items()} for h, p in prof.items()}},
          open(D / "zone_price.json", "w"), indent=1)
print("\nwrote zone_price.json")
