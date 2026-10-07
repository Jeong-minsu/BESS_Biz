import sys, pandas as pd
sys.path.insert(0, "."); import dl
pd.set_option("display.width", 250)
pn = dl.read_csv("ercot/metadata/objects/price_node.csv.gz", low_memory=False)
print(pn.columns.tolist())
pn["PNODE"] = pn.OBJECTID.astype(str)
pn[["PNODE","OBJECTNAME","ZONE","SUBTYPE"]].to_parquet("../raw/price_node_meta.parquet")
a = pd.read_parquet("../raw/allnode_sf_lapalma_sample.parquet").merge(pn[["PNODE","OBJECTNAME","ZONE","SUBTYPE"]], on="PNODE", how="left")
for c, g in a.groupby("CONSTRAINTNAME"):
    s = g.groupby(["OBJECTNAME","SUBTYPE"]).SHIFTFACTOR.mean().sort_values()
    print(f"\n=== {c}  rows={len(g)} markets={g.MARKET.unique()} contingencies={g.CONTINGENCYID.nunique()}")
    print("most NEG (inject relieves):"); print(s.head(12).round(3).to_string())
    print("most POS (inject aggravates):"); print(s.tail(15).round(3).to_string())
    print("GKS:", s.filter(like="GKS").round(3).to_dict())
