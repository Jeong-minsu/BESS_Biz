"""Full column lists + GKS sample-day rows from market_shift_factors."""
import sys, json
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 50)

def cols(sub):
    d = json.loads(dl.raw(f"ercot/transmission/constraints/{sub}/ddl.json"))
    return [c["colName"] for c in d["columns"]]

MSF = cols("market_shift_factors")
SSF = cols("ercot_sced_shift_factors")
RT  = cols("rt")
print("market_shift_factors cols:", MSF)
print("ercot_sced_shift_factors cols:", SSF)
print("rt cols:", RT)

GKS_PNODE = 10017907494
print("\n===== market_shift_factors 20260501, PRICENODEID==GKS_BESS_RN =====")
df = dl.read_csv("ercot/transmission/constraints/market_shift_factors/20260501.csv.gz", header=None)
df.columns = MSF[:df.shape[1]]
g = df[df["PRICENODEID"]==GKS_PNODE].copy()
print("  rows:", len(g), " of total", len(df))
print("  MARKET distinct:", g["MARKET"].value_counts().to_dict())
print("  DATETIME sample:", sorted(g["DATETIME"].unique())[:6])
sfcol = [c for c in g.columns if "SHIFT" in c.upper()][0]
spcol = [c for c in g.columns if "SHADOW" in c.upper() or "PRICE" in c.upper()][0]
print("  using SF col:", sfcol, " SP col:", spcol)
g["impact"] = -g[sfcol]*g[spcol]
for mkt in g["MARKET"].unique():
    gm=g[g["MARKET"]==mkt]
    print(f"\n  --- MARKET={mkt}: {len(gm)} rows; sum impact={gm['impact'].sum():.1f}")
    show=[c for c in ["DATETIME","FACILITYID","CONTINGENCYID","REPORTED_NAME",sfcol,spcol,"impact"] if c in gm.columns]
    print(gm.sort_values("impact").head(4)[show].to_string())
    print(gm.sort_values("impact").tail(4)[show].to_string())
