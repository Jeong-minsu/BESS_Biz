"""Probe first appearance of RVN_RN (and peers) in ercot/prices/lmp/hourly, monthly grid."""
import sys, pandas as pd
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl

NODES = {"RVN_RN":10019925379,"GKS_BESS_RN":10017907494,"RBN_BESS1":10017290064,
         "TAV_RN":10016969364,"CBEC_ALL":10001765766}
COLS = ["OBJECTID","DATETIME","TIMEZONE","DALMP","DACONG","DALOSS","RTLMP","RTCONG",
        "RTLOSS","RTFINAL","LOADID","HALMP","HACONG","HALOSS","ISO","ALT"]

def probe(d):
    df = dl.try_read_csv(f"ercot/prices/lmp/hourly/{d}.csv.gz", header=None)
    if df is None: return d, None
    df.columns = COLS[:df.shape[1]]
    out = {}
    for n,oid in NODES.items():
        s = df[df.OBJECTID==oid]
        out[n] = (len(s), int(s.DALMP.notna().sum()), int(s.RTLMP.notna().sum()))
    return d, out

dates = [f"{y}{m:02d}01" for y in range(2023,2027) for m in range(1,13)]
dates = [d for d in dates if "20230101" <= d <= "20260901"]
with ThreadPoolExecutor(12) as ex:
    res = list(ex.map(probe, dates))
for d,o in res:
    if o is None: print(d, "MISSING"); continue
    print(d, "  ".join(f"{n}:{v[0]}/{v[1]}/{v[2]}" for n,v in o.items()))
