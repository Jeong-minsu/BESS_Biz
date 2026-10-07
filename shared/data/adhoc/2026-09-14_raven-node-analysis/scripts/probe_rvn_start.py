import sys, pandas as pd
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl
COLS=["OBJECTID","DATETIME","TIMEZONE","DALMP","DACONG","DALOSS","RTLMP","RTCONG","RTLOSS","RTFINAL","LOADID","HALMP","HACONG","HALOSS","ISO","ALT"]
OID=10019925379
def probe(d):
    df = dl.try_read_csv(f"ercot/prices/lmp/hourly/{d}.csv.gz", header=None)
    if df is None: return d,"MISSING"
    df.columns=COLS[:df.shape[1]]
    s=df[df.OBJECTID==OID]
    return d, f"rows={len(s)} da={s.DALMP.notna().sum()} rt={s.RTLMP.notna().sum()}"
dates=[f"202606{i:02d}" for i in range(1,31)]+[f"202609{i:02d}" for i in range(8,15)]
with ThreadPoolExecutor(12) as ex: res=list(ex.map(probe,dates))
for d,v in res: print(d,v)
