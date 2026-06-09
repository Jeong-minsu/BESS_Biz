"""Explore shift-factor table schemas + locate GKS_BESS_RN. Real datalake only."""
import sys, io
from pathlib import Path
import pandas as pd
# reuse the validated dl client from the sibling adhoc folder
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl

pd.set_option("display.width", 240); pd.set_option("display.max_columns", 40)

def head_keys(prefix, n=5):
    print(f"\n### ls {prefix}")
    for k, sz in dl.ls(prefix, max_keys=n)[:n]:
        print(f"  {k}  ({sz} bytes)")

for sub in ["market_shift_factors", "ercot_sced_shift_factors", "shift_factors", "settle_shift_factors_ercot"]:
    head_keys(f"ercot/transmission/constraints/{sub}/", 3)
