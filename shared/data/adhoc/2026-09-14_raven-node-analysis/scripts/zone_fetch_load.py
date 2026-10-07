"""zone_: fetch hourly actual load by ERCOT load zone (ercot/load/rtload_hourly: HOUSTON/NORTH/SOUTH/WEST/ERCOT)
and by weather zone (ercot/load/rtload_hourly_wz) 2023-01-01 .. 2026-09-13. Real data only.
Output: raw/zone_load_hourly.parquet (hour_end CT string, objectname, load_mw, flowday). Idempotent, day-chunked.
"""
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import dl  # noqa: E402
OUT = ROOT / "raw/zone_load_hourly.parquet"
NAMES = {10000712969: "LZ_NORTH", 10000712970: "LZ_SOUTH", 10000712971: "LZ_WEST", 10000712972: "LZ_HOUSTON",
         10000712973: "ERCOT",
         10002211345: "WZ_Coast", 10002211346: "WZ_East", 10002211347: "WZ_FarWest", 10002211348: "WZ_North",
         10002211349: "WZ_NorthCentral", 10002211350: "WZ_SouthCentral", 10002211351: "WZ_Southern",
         10002211352: "WZ_West", 10002211353: "WZ_ERCOT"}

def one_day(d):
    ds = d.strftime("%Y%m%d"); parts = []
    for path in ("ercot/load/rtload_hourly", "ercot/load/rtload_hourly_wz"):
        df = dl.try_read_csv(f"{path}/{ds}.csv.gz", header=None)
        if df is None: continue
        df = df[df[0].isin(NAMES)]
        parts.append(pd.DataFrame({"hour_end": df[2].values, "tz": df[3].values,
                                   "objectname": df[0].map(NAMES).values, "load_mw": df[4].values}))
    if not parts: return None
    out = pd.concat(parts, ignore_index=True); out["flowday"] = d
    return out

if __name__ == "__main__":
    days = pd.date_range("2023-01-01", "2026-09-13", freq="D")
    have, parts = set(), []
    if OUT.exists():
        old = pd.read_parquet(OUT); have = set(old.flowday.unique()); parts = [old]; print("cached days:", len(have))
    todo = [d for d in days if d not in have]
    with ThreadPoolExecutor(max_workers=16) as ex:
        for i, r in enumerate(ex.map(one_day, todo)):
            if r is not None: parts.append(r)
            if i % 100 == 0: print(i, "/", len(todo), flush=True)
    f = pd.concat(parts, ignore_index=True).drop_duplicates(["hour_end", "tz", "objectname"])
    f.to_parquet(OUT, index=False)
    print(f.shape, f.flowday.min(), f.flowday.max())
    print(f.groupby("objectname").load_mw.agg(["count", "mean", "max"]))
