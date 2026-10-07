"""zone_: monthly market-resource capacity by ERCOT load zone x resource type from ERCOT 60-day DAM Gen Resource Data
(ercot/gen/ercot_60d_dam_gen_resource_data; headerless: col2 resource_name, col4 resource_type, col29 HSL, col33 settlement_point).
Capacity proxy = max DAM HSL of each resource over ~10 sampled days per month (market resources only, ex-PUN; wind/solar
HSL is availability-based so it understates nameplate somewhat). Zone = settlement_point -> price_node ZONE.
Output: raw/zone_dam_resource_monthly.parquet (month, res, rtype, sp, zone, hsl_max, n_days). Idempotent per month.
"""
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import dl  # noqa: E402
P = "ercot/gen/ercot_60d_dam_gen_resource_data"
OUT = ROOT / "raw/zone_dam_resource_monthly.parquet"
SAMPLE_DAYS = [1, 4, 7, 10, 13, 16, 19, 22, 25, 28]
obj = pd.read_parquet(ROOT / "raw/objects_all.parquet")
PN = obj[(obj.OBJECTTYPE == "price_node") & obj.ZONE.notna()].drop_duplicates("OBJECTNAME").set_index("OBJECTNAME").ZONE

def one_day(d):
    df = dl.try_read_csv(f"{P}/{d:%Y%m%d}.csv.gz", header=None, usecols=[2, 4, 29, 33])
    if df is None: return None
    df.columns = ["res", "rtype", "hsl", "sp"]
    g = df.groupby(["res", "rtype", "sp"], as_index=False).hsl.max(); g["day"] = d
    return g

def one_month(m):
    days = [m.replace(day=x) for x in SAMPLE_DAYS]
    with ThreadPoolExecutor(max_workers=10) as ex:
        parts = [r for r in ex.map(one_day, days) if r is not None]
    if not parts: return None
    df = pd.concat(parts, ignore_index=True)
    g = df.groupby(["res", "rtype", "sp"], as_index=False).agg(hsl_max=("hsl", "max"), n_days=("day", "nunique"))
    g["month"] = m.strftime("%Y-%m"); g["zone"] = g.sp.map(PN)
    return g

if __name__ == "__main__":
    months = pd.date_range("2023-01-01", "2026-09-01", freq="MS")
    have, parts = set(), []
    if OUT.exists():
        old = pd.read_parquet(OUT); have = set(old.month.unique()); parts = [old]
    for m in months:
        if m.strftime("%Y-%m") in have: continue
        r = one_month(m)
        print(m.strftime("%Y-%m"), None if r is None else (len(r), int(r.n_days.max()), "unmatched MW", round(r[r.zone.isna()].hsl_max.sum())), flush=True)
        if r is not None: parts.append(r)
    f = pd.concat(parts, ignore_index=True)
    f.to_parquet(OUT, index=False)
    print(f.pivot_table(index="month", columns="zone", values="hsl_max", aggfunc="sum").round(0).to_string())
