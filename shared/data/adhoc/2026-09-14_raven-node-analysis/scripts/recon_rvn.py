"""Recon: locate RVN_RN + proxy candidates in datalake metadata; find price table layout."""
import sys, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dl
pd.set_option("display.width",250); pd.set_option("display.max_columns",60)

allobj = dl.read_csv("ercot/metadata/objects/all.csv.gz")
print("cols:", list(allobj.columns), "rows:", len(allobj))
for pat in ["RVN","RAVEN","CBEC","RBN_BESS","TAV_RN","GKS"]:
    m = allobj.apply(lambda c: c.astype(str).str.contains(pat, case=False, na=False)).any(axis=1)
    h = allobj[m]
    print(f"\n=== {pat}: {len(h)} ===")
    with pd.option_context("display.max_colwidth",34):
        print(h.head(20).to_string())

print("\n=== prices/ subdirs ===")
seen=set()
for k,_ in dl.ls("ercot/prices/", max_keys=600):
    p="/".join(k.split("/")[:4])
    if p not in seen:
        seen.add(p); print("  ", p)
