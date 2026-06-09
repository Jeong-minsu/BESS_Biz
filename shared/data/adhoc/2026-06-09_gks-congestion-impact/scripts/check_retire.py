import sys
from pathlib import Path
import pandas as pd, numpy as np
D=Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
raw=pd.read_parquet(D/"gks_msf_raw.parquet")
raw=raw[raw.SHADOWPRICE>0].copy()
raw["dt"]=pd.to_datetime(raw.DATETIME,format="%m/%d/%Y %H:%M:%S")
raw["ym"]=raw.dt.dt.strftime("%Y-%m")
for cn in ["E_PASP","LARDVN_LASCRU1_1","CATARI_PILONC1_1"]:
    s=raw[raw.CONSTRAINTNAME==cn]
    print(f"\n{cn}: first={s.dt.min()} last={s.dt.max()}")
    last6=sorted(s.ym.unique())[-8:]
    g=s.groupby(["ym","MARKET"]).size().unstack(fill_value=0)
    print(g.tail(10).to_string())
# Are OTHER constraints still binding at GKS after 2025-05 (proves data present)?
print("\nGKS total binding rows by month (all constraints) — confirms data continuity:")
print(raw.groupby("ym").size().tail(6).to_string())
