"""Sample-day GKS impact with correct SHADOWPRICE col + sign-convention sanity check.
Convention under test (CONGESTION_PROJECT.md L32): nodal MCC contribution = -SHIFTFACTOR * SHADOWPRICE.
Pos = raises GKS LMP (good for discharge); Neg = lowers (good for charging)."""
import sys, json
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl
pd.set_option("display.width", 280); pd.set_option("display.max_columns", 60)

MSF = ['PRICENODEID','FACILITYID','CONTINGENCYID','DATETIME','TIMEZONE','MARKET','SHIFTFACTOR','SHADOWPRICE','LIMIT','CONSTRAINTID','CONSTRAINTNAME','LOADID']
GKS = 10017907494

# metadata: facility + contingency names
fac = dl.read_csv("ercot/metadata/objects/facility.csv.gz")
con = dl.read_csv("ercot/metadata/objects/contingency.csv.gz")
facname = dict(zip(fac["OBJECTID"], fac.get("REPORTED_NAME", fac.get("FACILITYNAME", fac.iloc[:,1]))))
conname = dict(zip(con["OBJECTID"], con["CONTINGENCYNAME"]))

df = dl.read_csv("ercot/transmission/constraints/market_shift_factors/20260501.csv.gz", header=None)
df.columns = MSF[:df.shape[1]]
g = df[df["PRICENODEID"]==GKS].copy()
g["impact"] = -g["SHIFTFACTOR"]*g["SHADOWPRICE"]
g["elem"] = g["FACILITYID"].map(facname)
g["ctg"]  = g["CONTINGENCYID"].map(conname)

for mkt in ["DA","RT"]:
    gm=g[g["MARKET"]==mkt]
    print(f"\n===== MARKET={mkt}: {len(gm)} rows, SHADOWPRICE range [{gm.SHADOWPRICE.min():.1f},{gm.SHADOWPRICE.max():.1f}] =====")
    agg = gm.groupby(["CONSTRAINTNAME","elem"]).agg(
        sumimpact=("impact","sum"), meanSF=("SHIFTFACTOR","mean"),
        meanSP=("SHADOWPRICE","mean"), n=("impact","size")).reset_index().sort_values("sumimpact")
    print("  most NEGATIVE (lowers GKS LMP):")
    print(agg.head(4).to_string())
    print("  most POSITIVE (raises GKS LMP):")
    print(agg.tail(4).to_string())

# SANITY: GKS is SOUTH-zone generator node. Find a constraint where GKS clearly aggravates (SF>0, e.g. SF~1.0
# self/local) -> impact should be NEGATIVE (node that helps overload gets LOWER LMP). Inspect the SF~1.0 row.
print("\n===== SANITY: DA rows with |SF|>0.3 =====")
hi = g[(g.MARKET=="DA") & (g.SHIFTFACTOR.abs()>0.3)][["DATETIME","CONSTRAINTNAME","elem","ctg","SHIFTFACTOR","SHADOWPRICE","impact"]]
print(hi.drop_duplicates(["CONSTRAINTNAME","SHIFTFACTOR"]).to_string())
