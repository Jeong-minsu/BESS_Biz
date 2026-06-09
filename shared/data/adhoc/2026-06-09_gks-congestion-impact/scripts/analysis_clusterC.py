import sys, json
from pathlib import Path
import pandas as pd, numpy as np
pd.set_option("display.width",300); pd.set_option("display.max_columns",40)
D=Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
p=pd.read_parquet(D/"driver_panel_clusterC.parquet")
TARGETS=["E_PASP","LARDVN_LASCRU1_1","CATARI_PILONC1_1"]
p["net_south"]=p.wind_south+p.solar_se-p.load_south  # rough south injection surplus proxy

def binned(df,col,bins,cn):
    b=df.copy(); b["bin"]=pd.cut(b[col],bins)
    g=b.groupby("bin",observed=True).agg(n=("hour","size"),pbind=(cn+"_bind","mean"),
        lam_med=(cn+"_lam","median"),lam_p90=(cn+"_lam",lambda s:s.quantile(.9)))
    g["pbind"]=(g.pbind*100).round(1)
    return g.round(1)

WIND=[0,500,1000,1500,2000,2500,3000,4000,6000]
LOAD=[0,2000,2500,3000,3500,4000,5000,7000]
NET =[-6000,-2000,-1000,0,500,1000,1500,2000,3000,5000]
for cn in TARGETS:
    base=p[cn+"_bind"].mean()*100
    print("\n"+"#"*100); print(cn,f"| base P(bind)={base:.1f}%  bind-hrs={int(p[cn+'_bind'].sum())}")
    print("-- by South wind (MW) --"); print(binned(p,"wind_south",WIND,cn).to_string())
    print("-- by South load (MW) --"); print(binned(p,"load_south",LOAD,cn).to_string())
    print("-- by net_south surplus (wind+solar-load, MW) --"); print(binned(p,"net_south",NET,cn).to_string())
    # hour profile
    hp=p.groupby("hour").agg(pbind=(cn+"_bind","mean"),lam=(cn+"_lam","median"))
    hp["pbind"]=(hp.pbind*100).round(1)
    print("-- hour profile P(bind)% --"); print(hp["pbind"].to_string())

# corr of binding with drivers
print("\n=== point-biserial corr (bind vs driver) ===")
for cn in TARGETS:
    row={c:round(p[cn+"_bind"].corr(p[c]),3) for c in ["wind_south","wind_coastal","load_south","solar_se","net_south"]}
    print(cn,row)
