"""ITEM 6 - fetch ERCOT system hourly actuals (load, wind, solar) from the Yes Energy datalake for regime
classification. Real data only. Output: raw/item6_fundamentals.parquet  (hour_end CT, load_mw, wind_mw, solar_mw)
System total OBJECTID = 10000712973 in all three tables (ercot/load/rtload_hourly, ercot/gen/wind_rti,
ercot/gen/generation_solar_rt). Idempotent: skips days already present. Chunked by day, threaded.
"""
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import dl  # noqa: E402
SYS = 10000712973
TABLES = {"load_mw": "ercot/load/rtload_hourly", "wind_mw": "ercot/gen/wind_rti", "solar_mw": "ercot/gen/generation_solar_rt"}
OUT = ROOT / "raw/item6_fundamentals.parquet"

def one_day(d):
    ds = d.strftime("%Y%m%d"); cols = {}
    for c, path in TABLES.items():
        df = dl.try_read_csv(f"{path}/{ds}.csv.gz", header=None)
        if df is None: continue
        df = df[df[0] == SYS]
        s = pd.Series(df[4].values, index=pd.to_datetime(df[2], format="%m/%d/%Y %H:%M:%S").values)
        cols[c] = s.groupby(level=0).mean()
    if not cols: return None
    out = pd.DataFrame(cols); out.index.name = "hour_end"; out["flowday"] = d
    return out.reset_index()

if __name__ == "__main__":
    days = pd.date_range("2023-12-01", "2026-09-13", freq="D")
    have = set()
    if OUT.exists():
        have = set(pd.read_parquet(OUT).flowday.unique()); print("cached days:", len(have))
    todo = [d for d in days if d not in have]
    parts = [pd.read_parquet(OUT)] if have else []
    with ThreadPoolExecutor(max_workers=24) as ex:
        for i, r in enumerate(ex.map(one_day, todo)):
            if r is not None: parts.append(r)
            if i % 100 == 0: print(i, "/", len(todo), flush=True)
    f = pd.concat(parts, ignore_index=True).sort_values("hour_end").drop_duplicates("hour_end")
    f.to_parquet(OUT, index=False)
    print(f.shape, f.flowday.min(), f.flowday.max()); print(f.isna().sum()); print(f.describe().T)
