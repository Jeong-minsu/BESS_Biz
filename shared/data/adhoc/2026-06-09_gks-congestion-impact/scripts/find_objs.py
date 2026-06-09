import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")
import dl
pd.set_option("display.width",300); pd.set_option("display.max_columns",30); pd.set_option("display.max_rows",120)
allo = dl.read_csv("ercot/metadata/objects/all.csv.gz")
print("cols:", list(allo.columns))
# load weather zones
lz = allo[allo.apply(lambda r: r.astype(str).str.contains("rtload|wz|weather.?zone|load.?zone", case=False).any(), axis=1)]
# Simpler: search by name token
name_col = [c for c in allo.columns if "NAME" in c.upper()][0]
print("name col:", name_col)
def show(tok):
    m = allo[allo[name_col].astype(str).str.contains(tok, case=False, na=False)]
    print(f"\n--- '{tok}' ({len(m)}) ---")
    print(m.head(40).to_string(index=False))
for t in ["South","SOUTH","Valley","wind","solar"]:
    pass
# weather zone load objects: look at one rtload file's OBJECTIDs and map
df = dl.read_csv("ercot/load/rtload_hourly_wz/20250715.csv.gz", header=None)
df.columns=["OBJECTID","DATATYPEID","DATETIME","TIMEZONE","VALUE","LOADID"][:df.shape[1]]
oids = df.OBJECTID.unique()
print("\n=== rtload_hourly_wz OBJECTIDs ===")
m = allo[allo.OBJECTID.isin(oids)]
print(m[["OBJECTID",name_col]].to_string(index=False) if len(m) else "none in all.csv.gz; raw oids:"+str(list(oids)))
# solar regions
sdf = dl.read_csv("ercot/gen/generation_solar_rt/20250715.csv.gz", header=None)
sdf.columns=["OBJECTID","DATATYPEID","DATETIME","TIMEZONE","VALUE","SEQ"][:sdf.shape[1]]
soids=sdf.OBJECTID.unique()
print("\n=== solar_rt regions ===")
ms=allo[allo.OBJECTID.isin(soids)]
print(ms[["OBJECTID",name_col]].to_string(index=False) if len(ms) else "raw:"+str(list(soids)))
# wind regions
wdf = dl.read_csv("ercot/gen/wind_rti/20250715.csv.gz", header=None)
wdf.columns=["OBJECTID","DATATYPEID","DATETIME","TIMEZONE","VALUE","SEQ"][:wdf.shape[1]]
woids=wdf.OBJECTID.unique()
print("\n=== wind_rti regions ===")
mw=allo[allo.OBJECTID.isin(woids)]
print(mw[["OBJECTID",name_col]].to_string(index=False) if len(mw) else "raw:"+str(list(woids)))
