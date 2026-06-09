"""Inspect raw schema of shift-factor files + search for GKS node."""
import sys, io, gzip
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 50)

def peek(key, n=3):
    print(f"\n===== {key} =====")
    try:
        b = dl.raw(key)
    except Exception as e:
        print("  ERR", e); return
    txt = gzip.decompress(b).decode("utf-8", "replace")
    lines = txt.splitlines()
    print(f"  total lines={len(lines)}")
    for ln in lines[:n]:
        print("  |", ln[:260])

peek("ercot/transmission/constraints/market_shift_factors/20260501.csv.gz")
peek("ercot/transmission/constraints/ercot_sced_shift_factors/20260501.csv.gz")
