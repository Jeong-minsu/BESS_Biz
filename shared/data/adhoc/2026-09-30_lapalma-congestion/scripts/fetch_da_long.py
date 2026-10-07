import sys, pandas as pd, concurrent.futures as cf
sys.path.insert(0, "."); import dl
days = pd.date_range("2024-07-03", "2026-06-30")
def f(d):
    df = dl.read_da(d.strftime("%Y%m%d"))
    if df is None: return None
    df["date"] = d; return df
with cf.ThreadPoolExecutor(24) as ex: parts = [x for x in ex.map(f, days) if x is not None]
pd.concat(parts).to_parquet("../raw/da_constraints_2024_2026H1.parquet"); print("done")
