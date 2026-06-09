"""Per-constraint deep-dive stats dump for Cluster A POS (HAINE__LA_PAL1_1, 1710__C, 421__A).
Output: derived/deepdive_clusterA_stats.json  (binding stats DA+RT, month, hour, year, contingency, SF)."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl
D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
raw = pd.read_parquet(D/"gks_msf_raw.parquet")
raw = raw[raw.SHADOWPRICE>0].copy()
raw["dt"]=pd.to_datetime(raw["DATETIME"], format="%m/%d/%Y %H:%M:%S")
raw["month"]=raw.dt.dt.month; raw["he"]=raw.dt.dt.hour+1; raw["year"]=raw.dt.dt.year
fac=dl.read_csv("ercot/metadata/objects/facility.csv.gz"); con=dl.read_csv("ercot/metadata/objects/contingency.csv.gz")
F={r.OBJECTID:r for _,r in fac.iterrows()}; CN=dict(zip(con.OBJECTID,con.CONTINGENCYNAME))
out={}
for cn in ["HAINE__LA_PAL1_1","1710__C","421__A"]:
    s=raw[raw.CONSTRAINTNAME==cn]
    fid=s.FACILITYID.value_counts().index[0]; f=F[fid]
    rec={"facility":{"name":f.FACILITYNAME,"kv":f.VOLTAGE,"from":f.FROMSTATION,"fromzone":f.FROMZONE,
                     "to":f.TOSTATION,"tozone":f.TOZONE}}
    for mkt in ["DA","RT"]:
        m=s[s.MARKET==mkt]; lam=m.SHADOWPRICE
        rec[mkt]={"rows":int(len(m)),"intervals":int(m.dt.nunique()),
                  "binding_hours":round(len(m)*(1 if mkt=="DA" else 1/12),1),
                  "lam_median":round(lam.median(),1),"lam_p90":round(lam.quantile(.9),0),
                  "lam_p99":round(lam.quantile(.99),0),"lam_max":round(lam.max(),0),"lam_mean":round(lam.mean(),1),
                  "sf_mean":round(m.SHIFTFACTOR.mean(),4),"sf_min":round(m.SHIFTFACTOR.min(),4),"sf_max":round(m.SHIFTFACTOR.max(),4),
                  "cum_usd":round((-m.SHIFTFACTOR*m.SHADOWPRICE*(1 if mkt=="DA" else 1/12)).sum(),0)}
    rec["year_rows"]={int(k):int(v) for k,v in s.year.value_counts().sort_index().items()}
    rec["month_rows"]={int(k):int(v) for k,v in s.month.value_counts().sort_index().items()}
    rec["month_lam"]={int(k):round(v,0) for k,v in s.groupby("month").SHADOWPRICE.mean().items()}
    rec["he_rows"]={int(k):int(v) for k,v in s.he.value_counts().sort_index().items()}
    rec["contingencies"]=[{"name":CN.get(i,str(i)),"rows":int(n),"lam":round(s[s.CONTINGENCYID==i].SHADOWPRICE.mean(),0)}
                          for i,n in s.CONTINGENCYID.value_counts().head(6).items()]
    rec["pct_post_contingency"]=round(100*(s.CONTINGENCYID.map(CN).notna()).mean(),1)
    out[cn]=rec
json.dump(out, open(D/"deepdive_clusterA_stats.json","w"), indent=2, default=str)
print("saved", D/"deepdive_clusterA_stats.json")
print(json.dumps({k:{"facility":v["facility"],"DA_bind_hrs":v["DA"]["binding_hours"],"RT_lam_median":v["RT"]["lam_median"],"years":v["year_rows"]} for k,v in out.items()}, indent=1))
