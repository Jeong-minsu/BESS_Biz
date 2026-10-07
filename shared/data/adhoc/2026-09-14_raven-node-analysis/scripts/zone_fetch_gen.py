"""zone_: sampled actual generation by unit from ercot/gen/ercot_sced_gen_raw (ercot_unit OBJECTID, ~5-min SCED, MW).
5 sampled days per month (5,10,15,20,25) 2023-01..2026-09; per unit per day mean MW (= daily energy / 24).
Zone/fuel attribution is done later by joining ercot_unit OBJECTNAME (= resource_name) to the DAM resource map.
Output: raw/zone_sced_gen_sample.parquet (day, objectid, mw_mean, n_obs). Idempotent per day.
"""
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import dl  # noqa: E402
P = "ercot/gen/ercot_sced_gen_raw"
OUT = ROOT / "raw/zone_sced_gen_sample.parquet"

def one_day(d):
    df = dl.try_read_csv(f"{P}/{d:%Y%m%d}.csv.gz", header=None, usecols=[0, 4])
    if df is None: return None
    g = df.groupby(0)[4].agg(mw_mean="mean", n_obs="count").reset_index().rename(columns={0: "objectid"})
    g["day"] = d
    return g

if __name__ == "__main__":
    days = [d for d in pd.date_range("2023-01-01", "2026-09-13", freq="D") if d.day in (5, 10, 15, 20, 25)]
    have, parts = set(), []
    if OUT.exists():
        old = pd.read_parquet(OUT); have = set(old.day.unique()); parts = [old]
    todo = [d for d in days if d not in have]
    with ThreadPoolExecutor(max_workers=12) as ex:
        for i, r in enumerate(ex.map(one_day, todo)):
            if r is not None: parts.append(r)
            if i % 20 == 0: print(i, "/", len(todo), flush=True)
    f = pd.concat(parts, ignore_index=True)
    f.to_parquet(OUT, index=False)
    print(f.shape, f.day.min(), f.day.max(), "units/day ~", round(f.groupby("day").size().mean()))
