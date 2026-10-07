"""zone_ recon: unit-level generation tables and whether registry ercot_unit objects carry ZONE."""
import sys, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); import dl
pd.set_option("display.width", 300); pd.set_option("display.max_columns", 60); pd.set_option("display.max_colwidth", 40)
obj = pd.read_parquet(ROOT / "raw/objects_all.parquet")
print(obj.OBJECTTYPE.value_counts())
for t in ["ercot_unit", "unit", "ercot_plant", "plant"]:
    u = obj[obj.OBJECTTYPE == t]
    if len(u): print("\n", t, len(u), "\n", u.ZONE.value_counts(dropna=False), "\n", u.head(5).to_string())
for path in ["ercot/gen/ercot_60d_sced_gen_resource_data/20260601.csv.gz",
             "ercot/gen/ercot_sced_gen_raw/20260601.csv.gz",
             "ercot/cems/20260601.csv.gz"]:
    ls = dl.ls(path.rsplit("/", 1)[0] + "/2026060", 5)
    print("\n===", path, "listing sample:", ls[:3])
    df = dl.try_read_csv(path, header=None, nrows=5)
    if df is None:
        df = dl.try_read_csv(path, header=0, nrows=5)
    print(None if df is None else df.to_string())
