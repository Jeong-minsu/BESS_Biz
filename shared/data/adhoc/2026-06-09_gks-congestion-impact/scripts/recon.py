"""Cross-check: reconstruct GKS_BESS_RN DA congestion MCC = sum(-SF*lambda) over all binding
constraints in an hour, compare to independent nodal LMP congestion component."""
import sys, json, gzip
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl
pd.set_option("display.width", 240); pd.set_option("display.max_columns", 40)

# what price tables exist?
print("=== prices/ subdirs ===")
seen=set()
for k,_ in dl.ls("ercot/prices/", max_keys=400):
    p=k.split("/")[2] if len(k.split("/"))>2 else k
    if p not in seen: seen.add(p); print("  ", p)
