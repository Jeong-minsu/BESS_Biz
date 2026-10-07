import sys, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl
pd.set_option("display.width",250); pd.set_option("display.max_columns",40)
seen={}
for k,s in dl.ls("ercot/prices/", max_keys=200000):
    p=k.split("/")[2]
    d=seen.setdefault(p,[0,None,None])
    d[0]+=1
    f=k.split("/")[-1]
    if d[1] is None or f<d[1]: d[1]=f
    if d[2] is None or f>d[2]: d[2]=f
for p,(n,a,b) in sorted(seen.items()):
    print(f"  {p:35s} n={n:7d}  {a} .. {b}")
