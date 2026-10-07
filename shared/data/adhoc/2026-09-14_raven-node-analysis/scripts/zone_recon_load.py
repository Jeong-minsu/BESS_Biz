"""zone_ recon: which OBJECTIDs appear in one day of load / wind / solar tables, joined to object registry."""
import sys, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); import dl
obj = pd.read_parquet(ROOT / "raw/objects_all.parquet")
pd.set_option("display.width", 300); pd.set_option("display.max_rows", 500)
print(obj[obj.SUBTYPE.isin(["ZONE", "WEATHER ZONE", "GEOGRAPHIC REGION", "SOLAR REGION", "RTI"])]
      .sort_values(["SUBTYPE", "OBJECTNAME"]).to_string())
for path in ["ercot/load/rtload_hourly", "ercot/load/rtload_hourly_wz", "ercot/gen/wind_rti",
             "ercot/gen/generation_solar_rt", "ercot/gen/eia930_net_gen_gas", "ercot/load/hsl_cd"]:
    df = dl.try_read_csv(f"{path}/20260601.csv.gz", header=None)
    print("\n===", path, None if df is None else df.shape)
    if df is None: continue
    print(df.head(3).to_string())
    ids = df[0].unique()
    j = obj[obj.OBJECTID.isin(ids)][["OBJECTID", "OBJECTNAME", "OBJECTTYPE", "ZONE", "SUBTYPE"]]
    print(j.to_string()); print("unmatched ids:", [i for i in ids if i not in set(obj.OBJECTID)])
    print(df.groupby(0)[4].agg(["mean", "max", "count"]).to_string())
