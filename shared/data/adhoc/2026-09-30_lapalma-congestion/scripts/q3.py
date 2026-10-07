import sys, pandas as pd
sys.path.insert(0, "."); import dl
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
con = dl.read_csv("ercot/metadata/objects/contingency.csv.gz"); print(con.columns.tolist())
cmap = dict(zip(con.OBJECTID, con.iloc[:, 1]))
FAM = ["LA_PALMA_XF1A","LA_PALMA_XF1B","LA_PAL_VCAVAZ1_1","HAINE__LA_PAL1_1"]
rt = pd.read_parquet("../raw/rt_lapalma_2026Q3.parquet"); rt["dt"] = pd.to_datetime(rt.DATETIME)
rt = rt[rt.CONSTRAINTNAME.isin(FAM)]
print(rt.groupby(["CONSTRAINTNAME","CONTINGENCY"]).agg(n=("PRICE","size"), mean=("PRICE","mean"), mx=("PRICE","max"), lim=("LIMITMW","median"), val=("VALUEMW","median")).to_string())
rt["d"] = rt.dt.dt.date; rt["he"] = rt.dt.dt.hour + 1
print(rt[rt.CONSTRAINTNAME.str.startswith("LA_PALMA_XF")].pivot_table(index="d", columns="CONSTRAINTNAME", values="PRICE", aggfunc=["count","mean","max"]).round(0).to_string())
x = rt[rt.CONSTRAINTNAME=="LA_PALMA_XF1A"]
print(x.groupby("he").PRICE.agg(["count","mean","max"]).round(0).T.to_string())
da = pd.read_parquet("../raw/da_constraints_2026Q3.parquet"); da = da[da.CONSTRAINTNAME.isin(FAM)]
da["cont"] = da.CONTINGENCYID.map(cmap)
print(da.groupby(["CONSTRAINTNAME","cont"]).agg(n=("PRICE","size"), mean=("PRICE","mean"), mx=("PRICE","max"), lim=("LIMITMW","median")).to_string())
print(da.pivot_table(index="date", columns="CONSTRAINTNAME", values="PRICE", aggfunc="count").fillna(0).astype(int).to_string())
