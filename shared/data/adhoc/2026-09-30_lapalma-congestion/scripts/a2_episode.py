import sys, pandas as pd
sys.path.insert(0, "."); import dl
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300)
con = dl.read_csv("ercot/metadata/objects/contingency.csv.gz"); cm = dict(zip(con.OBJECTID, con.CONTINGENCYNAME))
rt = pd.read_parquet("../raw/rt_lapalma_2026Q3.parquet"); rt["cont"] = rt.CONTINGENCYID.map(cm); rt["ts"] = pd.to_datetime(rt.DATETIME)
x = rt[rt.CONSTRAINTNAME.str.startswith("LA_PALMA_XF")]
print(x.groupby(["CONSTRAINTNAME","cont"]).agg(n=("PRICE","size"), mean=("PRICE","mean"), lim=("LIMITMW","median"), flow=("VALUEMW","median"), maxp=("MAXPRICE","max")).to_string())
x["h"] = x.ts.dt.floor("h")
print(x.groupby(["CONSTRAINTNAME","h"]).agg(n=("PRICE","size"), px=("PRICE","mean"), lim=("LIMITMW","mean"), flow=("VALUEMW","mean"), cont=("cont","first")).round(0).to_string())
h = pd.read_parquet("../raw/drivers_hourly.parquet")
print(h.loc["2026-09-14":"2026-09-30"].between_time("16:00","21:00").resample("D").mean().round(0).to_string())
