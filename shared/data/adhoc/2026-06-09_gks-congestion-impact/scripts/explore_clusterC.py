import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")
import dl
pd.set_option("display.width", 280); pd.set_option("display.max_columns", 40)

D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
raw = pd.read_parquet(D/"gks_msf_raw.parquet")
print("cols:", list(raw.columns), "total rows:", len(raw))
TARGETS = ["E_PASP","LARDVN_LASCRU1_1","CATARI_PILONC1_1"]
raw = raw[raw["SHADOWPRICE"]>0].copy()
raw["dt"] = pd.to_datetime(raw["DATETIME"], format="%m/%d/%Y %H:%M:%S")
sub = raw[raw["CONSTRAINTNAME"].isin(TARGETS)].copy()

# decode facility + contingency
fac = dl.read_csv("ercot/metadata/objects/facility.csv.gz")
con = dl.read_csv("ercot/metadata/objects/contingency.csv.gz")
print("\nfacility cols:", list(fac.columns))
fcol = "REPORTED_NAME" if "REPORTED_NAME" in fac.columns else fac.columns[1]
facname = dict(zip(fac["OBJECTID"], fac[fcol]))
conname = dict(zip(con["OBJECTID"], con["CONTINGENCYNAME"]))

for cn in TARGETS:
    s = sub[sub.CONSTRAINTNAME==cn]
    print("\n"+"="*90)
    print(cn, "| rows:", len(s), "| window:", s.dt.min(), "->", s.dt.max())
    for mkt in ["DA","RT"]:
        m = s[s.MARKET==mkt]
        if len(m)==0: 
            print(f"  {mkt}: none"); continue
        print(f"  {mkt}: rows={len(m)} SF mean={m.SHIFTFACTOR.mean():.4f} min={m.SHIFTFACTOR.min():.4f} max={m.SHIFTFACTOR.max():.4f}")
        print(f"       lambda mean={m.SHADOWPRICE.mean():.1f} med={m.SHADOWPRICE.median():.1f} P90={m.SHADOWPRICE.quantile(.9):.1f} P99={m.SHADOWPRICE.quantile(.99):.1f} max={m.SHADOWPRICE.max():.1f}")
        # dominant facility + contingency
        domf = m.FACILITYID.value_counts().head(3)
        domc = m.CONTINGENCYID.value_counts().head(5)
        print("    facilities:", {facname.get(k,k):int(v) for k,v in domf.items()})
        print("    contingencies:", {conname.get(k,k):int(v) for k,v in domc.items()})
