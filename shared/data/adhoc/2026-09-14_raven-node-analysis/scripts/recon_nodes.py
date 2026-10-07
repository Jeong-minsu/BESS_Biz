import sys, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl
pd.set_option("display.width",250)
a = dl.read_csv("ercot/metadata/objects/all.csv.gz")
pn = a[a.OBJECTTYPE.isin(["price_node","lmpbus_node","ercot_unit","settlement_point"])]
print("objecttypes:", sorted(a.OBJECTTYPE.dropna().unique()))
for n in ["RVN_RN","CBEC_ALL","RBN_BESS1","TAV_RN","GKS_BESS_RN"]:
    h = a[a.OBJECTNAME.astype(str).str.upper().str.startswith(n)]
    print(f"\n--- {n} ({len(h)}) ---"); print(h.to_string())
# all HOUSTON price_node GENERATOR containing RVN / RAV
h2 = a[(a.OBJECTTYPE=="price_node") & a.OBJECTNAME.astype(str).str.upper().str.contains("RAV|RVN")]
print("\n--- price_node RAV|RVN ---"); print(h2.to_string())
