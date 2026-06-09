"""bus_lmp schema + single-interval RT MCC reconstruction cross-check for GKS."""
import sys, json
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl
pd.set_option("display.width", 240); pd.set_option("display.max_columns", 40)

d = json.loads(dl.raw("ercot/prices/bus_lmp/ddl.json"))
BL = [c["colName"] for c in d["columns"]]
print("bus_lmp cols:", BL)
for c in d["columns"]:
    print("   ", c["colName"], "-", c.get("colDesc","")[:60], "| ref:", c.get("refObjType",""))

# GKS bus nodes from metadata: GKS_BESS1 (lmpbus_node 10017907512), GKS_BESS_RN price_node 10017907494
df = dl.read_csv("ercot/prices/bus_lmp/20260501.csv.gz", header=None)
df.columns = BL[:df.shape[1]]
print("\nsample rows:\n", df.head(3).to_string())
idcol = BL[0]
for nid in [10017907512, 10017907494]:
    sub = df[df[idcol]==nid]
    print(f"\n  bus_lmp rows for OBJECTID {nid}: {len(sub)}")
    if len(sub): print(sub.head(2).to_string())
