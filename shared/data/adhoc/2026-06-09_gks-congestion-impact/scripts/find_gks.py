"""Locate GKS node in SCED shift factors (string) + metadata objects (OBJECTID for DA)."""
import sys, gzip
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 50)

# 1) SCED shift factors: col3 = resource node string. Grep GKS lines.
print("===== SCED shift factors 20260501: lines containing GKS =====")
b = dl.raw("ercot/transmission/constraints/ercot_sced_shift_factors/20260501.csv.gz")
txt = gzip.decompress(b).decode("utf-8","replace")
gks_lines = [ln for ln in txt.splitlines() if "GKS" in ln.upper()]
print(f"  GKS lines: {len(gks_lines)}")
seen=set()
for ln in gks_lines[:8]:
    print("  |", ln[:240])
# distinct node names in col3 containing GKS
import csv, io
nodes=set()
for row in csv.reader(io.StringIO("\n".join(gks_lines))):
    if len(row)>=4: nodes.add(row[3])
print("  distinct col3 GKS node strings:", sorted(nodes)[:30])

# 2) metadata objects/all.csv.gz : find GKS objectids (headered)
print("\n===== metadata objects/all.csv.gz: rows matching GKS =====")
allobj = dl.read_csv("ercot/metadata/objects/all.csv.gz")
print("  columns:", list(allobj.columns))
m = allobj.apply(lambda c: c.astype(str).str.contains("GKS", case=False, na=False)).any(axis=1)
hit = allobj[m]
print(f"  matches: {len(hit)}")
with pd.option_context("display.max_colwidth", 40):
    print(hit.to_string())
