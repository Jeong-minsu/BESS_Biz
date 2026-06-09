"""Driver 5-lens for Cluster A POS constraints (HAINE__LA_PAL1_1, 1710__C, 421__A).
Merges DA hourly binding flag (from gks_msf_raw) with zonal load + South solar + South/Coastal wind
for each constraint's peak-binding month. Compares binding vs non-binding hours -> conditional P(bind).
Real data only (Yes Energy datalake). Output: derived/drivers_clusterA.json
"""
import sys, io, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl

D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")

LOAD = {"10002211351":"load_South","10002211348":"load_North","10002211349":"load_NorthCentral","10002211350":"load_SouthCentral","10002211345":"load_Coast"}
SOLAR = {"10017006228":"solar_SouthEast","10000712973":"solar_ERCOT"}
WIND = {"10004189447":"wind_GR_SOUTH","10004189446":"wind_GR_COASTAL","10004189442":"wind_GR_ERCOT"}

def fetch_day(ds, day, idmap):
    key=f"ercot/gen/{ds}/{day}.csv.gz" if ds!="load" else f"ercot/load/rtload_hourly_wz/{day}.csv.gz"
    try:
        df=dl.read_csv(key, header=None, dtype={0:str})
    except Exception:
        return None
    df=df[df[0].isin(idmap)]
    if df.empty: return None
    df=df.rename(columns={0:"oid",2:"dt",4:"val"})[["oid","dt","val"]]
    df["dt"]=pd.to_datetime(df["dt"], format="%m/%d/%Y %H:%M:%S")
    df["var"]=df["oid"].map(idmap)
    return df.pivot_table(index="dt", columns="var", values="val", aggfunc="mean")

def pull(days):
    frames=[]
    tasks=[]
    with ThreadPoolExecutor(max_workers=24) as ex:
        for d in days:
            tasks.append(ex.submit(fetch_day,"load",d,LOAD))
            tasks.append(ex.submit(fetch_day,"generation_solar_rt",d,SOLAR))
            tasks.append(ex.submit(fetch_day,"wind_rti",d,WIND))
        for f in as_completed(tasks):
            r=f.result()
            if r is not None: frames.append(r)
    if not frames: return pd.DataFrame()
    # combine: group by dt, take first non-null across the per-dataset frames
    big=pd.concat(frames)
    return big.groupby(level=0).first()

# binding flags (DA, hourly)
raw=pd.read_parquet(D/"gks_msf_raw.parquet")
raw=raw[(raw.SHADOWPRICE>0)&(raw.MARKET=="DA")].copy()
raw["dt"]=pd.to_datetime(raw["DATETIME"], format="%m/%d/%Y %H:%M:%S").dt.floor("h")

SPEC={
 "HAINE__LA_PAL1_1":("2025-03-01","2025-03-31","load_South","solar_SouthEast","wind_GR_SOUTH"),
 "1710__C":("2024-08-01","2024-08-31","load_North","solar_SouthEast","wind_GR_SOUTH"),
 "421__A":("2025-04-01","2025-04-30","load_SouthCentral","solar_SouthEast","wind_GR_SOUTH"),
}
out={}
for cn,(d0,d1,loadvar,solvar,windvar) in SPEC.items():
    days=[d.strftime("%Y%m%d") for d in pd.date_range(d0,d1,freq="D")]
    drv=pull(days)
    if drv.empty:
        out[cn]={"error":"no driver data"}; print(cn,"NO DRIVER DATA"); continue
    drv=drv.resample("h").mean()
    # binding hours for this constraint in this month
    bset=set(raw[(raw.CONSTRAINTNAME==cn)&(raw.dt>=d0)&(raw.dt<=d1+" 23:00")].dt)
    drv["bind"]=[1 if t in bset else 0 for t in drv.index]
    drv["he"]=drv.index.hour+1
    drv["lam"]= [raw[(raw.CONSTRAINTNAME==cn)&(raw.dt==t)].SHADOWPRICE.mean() if t in bset else 0 for t in drv.index]
    n=len(drv); nb=int(drv.bind.sum())
    res={"month":d0[:7],"hours":n,"binding_hours":nb,"base_rate":round(nb/n,3)}
    # binding vs non-binding means
    for v in [loadvar,solvar,windvar,"load_North","load_SouthCentral","solar_ERCOT","wind_GR_ERCOT"]:
        if v in drv.columns:
            res[f"{v}_bind_mean"]=round(drv.loc[drv.bind==1,v].mean(),1)
            res[f"{v}_nonbind_mean"]=round(drv.loc[drv.bind==0,v].mean(),1)
    # conditional P(bind) by driver tercile (solar + load + wind)
    thr={}
    for v in [loadvar,solvar,windvar]:
        if v not in drv.columns: continue
        q=drv[v].quantile([.33,.66,.9]).round(0).to_dict()
        buckets={}
        for lab,(lo,hi) in {"low":(-1e9,q[.33]),"mid":(q[.33],q[.66]),"high":(q[.66],q[.9]),"top10":(q[.9],1e12)}.items():
            mask=(drv[v]>lo)&(drv[v]<=hi)
            if mask.sum()>0:
                buckets[lab]={"range":[round(lo if lo>-1e8 else None,0) if lo>-1e8 else None, round(hi if hi<1e11 else None,0) if hi<1e11 else None],
                              "n":int(mask.sum()),"p_bind":round(drv.loc[mask,"bind"].mean(),2),
                              "mean_lam_when_bind":round(drv.loc[mask&(drv.bind==1),"lam"].mean(),0) if (mask&(drv.bind==1)).sum()>0 else 0}
        thr[v]=buckets
    res["thresholds"]=thr
    # hour-of-day p(bind)
    res["p_bind_by_he"]={int(h):round(g.bind.mean(),2) for h,g in drv.groupby("he")}
    out[cn]=res
    print("="*60); print(cn, d0[:7], f"hours={n} binding={nb} base_rate={nb/n:.2f}")
    for v in [loadvar,solvar,windvar]:
        if v in drv.columns:
            print(f"  {v}: bind_mean={res[f'{v}_bind_mean']} nonbind_mean={res[f'{v}_nonbind_mean']}")

json.dump(out, open(D/"drivers_clusterA.json","w"), indent=2, default=str)
print("\nsaved", D/"drivers_clusterA.json")
