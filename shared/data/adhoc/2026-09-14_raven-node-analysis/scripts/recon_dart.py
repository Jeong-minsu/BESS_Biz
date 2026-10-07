import sys, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl
pd.set_option("display.width",260); pd.set_option("display.max_columns",40)
try: print(dl.raw("ercot/prices/lmp/hourly/ddl.json").decode()[:2500])
except Exception as e: print("ddl err", e)
for d in ["20260901","20260701","20260601"]:
    df = dl.try_read_csv(f"ercot/prices/lmp/hourly/{d}.csv.gz", header=None)
    print(f"\n### {d}: shape={None if df is None else df.shape}")
    if df is not None:
        print(df.head(4).to_string())
        ids = set(df[0].unique())
        for name,oid in [("RVN_RN",10019925379),("GKS_BESS_RN",10017907494),("RBN_BESS1",10017290064),("TAV_RN",10016969364),("CBEC_ALL",10001765766)]:
            sub=df[df[0]==oid]
            print(f"   {name:12s} rows={len(sub)} datatypes={sorted(sub[1].unique()) if len(sub) else []}")
        break
