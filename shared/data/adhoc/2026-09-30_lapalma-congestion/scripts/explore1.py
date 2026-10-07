import sys, pandas as pd, concurrent.futures as cf
sys.path.insert(0, "."); import dl
days = pd.date_range("2026-07-01", "2026-09-30")
def f(d):
    df = dl.read_da(d.strftime("%Y%m%d"))
    if df is None: return None
    df["date"] = d
    return df
with cf.ThreadPoolExecutor(16) as ex: parts = [x for x in ex.map(f, days) if x is not None]
da = pd.concat(parts)
print("days", da.date.nunique(), da.date.max())
m = da.CONSTRAINTNAME.astype(str).str.contains("PAL", case=False) | da.REPORTED_NAME.astype(str).str.contains("PAL", case=False)
g = da[m].groupby(["CONSTRAINTNAME","REPORTED_NAME"]).agg(hrs=("PRICE","size"), days=("date","nunique"), mean_px=("PRICE","mean"), max_px=("PRICE","max"), last=("date","max"))
print(g.sort_values("hrs", ascending=False).to_string())
# Top overall constraints in window for context
print(da.groupby("CONSTRAINTNAME").agg(hrs=("PRICE","size"), sum_px=("PRICE","sum")).sort_values("sum_px", ascending=False).head(25))
da.to_parquet("../raw/da_constraints_2026Q3.parquet")
