import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")
import dl
pd.set_option("display.width", 320); pd.set_option("display.max_columns", 50)

D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
raw = pd.read_parquet(D/"gks_msf_raw.parquet")
raw = raw[raw["SHADOWPRICE"]>0].copy()
raw["dt"] = pd.to_datetime(raw["DATETIME"], format="%m/%d/%Y %H:%M:%S")
TARGETS = ["E_PASP","LARDVN_LASCRU1_1","CATARI_PILONC1_1"]
sub = raw[raw["CONSTRAINTNAME"].isin(TARGETS)].copy()

fac = dl.read_csv("ercot/metadata/objects/facility.csv.gz")
# get all FACILITYIDs in our subset
fids = sub.FACILITYID.unique()
fd = fac[fac.OBJECTID.isin(fids)]
print("=== FACILITY DECODE ===")
print(fd[["OBJECTID","FACILITYNAME","FACILITYTYPE","VOLTAGE","FROMSTATION","FROMZONE","TOSTATION","TOZONE","FROMKV","TOKV","STATUS"]].to_string(index=False))

# contingency names
con = dl.read_csv("ercot/metadata/objects/contingency.csv.gz")
cids = sub.CONTINGENCYID.unique()
cd = con[con.OBJECTID.isin(cids)]
print("\n=== CONTINGENCY DECODE ===")
print(cd[["OBJECTID","CONTINGENCYNAME","STATUS"]].to_string(index=False))

# E_PASP Jan-2026 concentration
print("\n=== E_PASP monthly cum impact (DA) ===")
e = sub[sub.CONSTRAINTNAME=="E_PASP"].copy()
e["impact"]=-e.SHIFTFACTOR*e.SHADOWPRICE
e["dur"]=np.where(e.MARKET=="DA",1.0,1/12)
e["cum"]=e.impact*e.dur
e["ym"]=e.dt.dt.strftime("%Y-%m")
for mkt in ["DA","RT"]:
    g=e[e.MARKET==mkt].groupby("ym").agg(cum=("cum","sum"), hrs=("dur","sum"), lam_med=("SHADOWPRICE","median"), lam_max=("SHADOWPRICE","max"), n=("dt","nunique"))
    print(f"\n--- E_PASP {mkt} by month ---")
    print(g.round(1).to_string())

# Jan-2026 day-level detail for E_PASP DA
print("\n=== E_PASP Jan-2026 DA day-level ===")
ej = e[(e.MARKET=="DA")&(e.ym=="2026-01")].copy()
ej["d"]=ej.dt.dt.date
gd=ej.groupby("d").agg(cum=("cum","sum"), hrs=("dur","sum"), lam_med=("SHADOWPRICE","median"), lam_max=("SHADOWPRICE","max"))
print(gd.round(1).to_string())
