"""Per-node shift factors for the top constraints: is the location SF a Raven property or a proxy-member artifact?"""
import glob, json, pandas as pd, numpy as np
from pathlib import Path
R = Path(__file__).resolve().parents[1]
N = {10019925379:"RVN_RN",10017290064:"RBN_BESS1",10001765766:"CBEC_ALL",10016969364:"TAV_RN",10018682155:"WAL_RN",10016934052:"SBE_RN_1",10016239529:"WGU_RN"}
top = list(json.load(open(R/"derived/item2_congestion_top10_profiles.json")).keys())
ov = pd.read_csv(R/"derived/item2_congestion_proxy_sf_check.csv").CONSTRAINTNAME.head(12).tolist()
want = list(dict.fromkeys(top+ov))
parts=[]
for f in sorted(glob.glob(str(R/"raw/msf_nodes/*.parquet"))):
    d = pd.read_parquet(f, columns=["PRICENODEID","DATETIME","MARKET","SHIFTFACTOR","SHADOWPRICE","CONSTRAINTNAME"])
    d = d[d.CONSTRAINTNAME.isin(want) & (d.SHADOWPRICE>0) & d.PRICENODEID.isin(N)]
    parts.append(d)
d = pd.concat(parts); d["node"]=d.PRICENODEID.map(N); d["yr"]=d.DATETIME.str[6:10]
sf = d.pivot_table(index="CONSTRAINTNAME", columns="node", values="SHIFTFACTOR", aggfunc="mean").reindex(want)[["RVN_RN","RBN_BESS1","CBEC_ALL","TAV_RN","WAL_RN","SBE_RN_1","WGU_RN"]]
print("mean SF (binding intervals, DA+RT, full window) by node:"); print(sf.round(4).to_string())
# RVN-overlap-only comparison (same intervals) for constraints that bound while RVN existed
o = d[d.DATETIME.str[6:10].eq("2026") & d.DATETIME.str[0:2].isin(["06","07","08","09"])]
sfo = o.pivot_table(index="CONSTRAINTNAME", columns="node", values="SHIFTFACTOR", aggfunc="mean").reindex(want)[["RVN_RN","RBN_BESS1","CBEC_ALL","TAV_RN","WAL_RN"]]
print("\nmean SF in 2026-06..09 overlap (same intervals):"); print(sfo.round(4).to_string())
# WHARTN: which years does each node have it?
w = d[d.CONSTRAINTNAME=="WHARTN"]; print("\nWHARTN rows by node x year:"); print(w.pivot_table(index="node",columns="yr",values="SHIFTFACTOR",aggfunc=["count","mean"]).round(3).to_string())
sf.round(4).to_csv(R/"derived/item2_congestion_sf_by_node.csv")
