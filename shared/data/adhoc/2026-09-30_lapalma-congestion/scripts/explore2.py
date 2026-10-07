import sys, pandas as pd, concurrent.futures as cf
sys.path.insert(0, "."); import dl
hrs = pd.date_range("2026-07-01 00:00", "2026-09-30 23:00", freq="h")
def f(h):
    df = dl.read_rt(h.strftime("%Y%m%d%H"))
    if df is None: return None
    df = df[df.PRICE > 0]
    m = df.CONSTRAINTNAME.astype(str).str.contains("PAL|LPL|HAINE|WESLCO", case=False)
    return df[m]
with cf.ThreadPoolExecutor(24) as ex: parts = [x for x in ex.map(f, hrs) if x is not None]
rt = pd.concat(parts); rt.to_parquet("../raw/rt_lapalma_2026Q3.parquet")
rt["dt"] = pd.to_datetime(rt.DATETIME)
print(rt.groupby(["CONSTRAINTNAME"]).agg(n=("PRICE","size"), mean=("PRICE","mean"), p90=("PRICE", lambda s: s.quantile(.9)), mx=("PRICE","max"), first=("dt","min"), last=("dt","max")).sort_values("n", ascending=False).head(20).to_string())
da = pd.read_parquet("../raw/da_constraints_2026Q3.parquet")
print(da[da.CONSTRAINTNAME.str.contains("LPLMK|WESLCO", na=False)].groupby(["CONSTRAINTNAME","REPORTED_NAME"]).size())
fac = dl.read_csv("ercot/metadata/objects/facility.csv.gz") if False else None
print(dl.ls("ercot/metadata/objects/")[:40])
