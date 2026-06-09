"""Cluster E GTC deep-dive: VALEXP (Valley Export) + WESTEX (West Texas Export) impact on GKS_BESS_RN.
Real data only (Yes Energy Datalake S3). Adapts Houston template to GTC/interface constraints.

Outputs derived/:
  clusterE_binding_stats.json     - DA+RT binding hrs, lambda median/P90/P99/max per GTC
  clusterE_month_hour.json        - month + hour-of-day profiles (cum impact + binding-hr count)
  clusterE_limit_history.json     - GTC operator-set limit (MW) monthly samples (GTC caveat evidence)
  clusterE_drivers.json           - renewable binding-vs-nonbinding comparison + thresholds
  clusterE_hourly_panel.parquet   - hourly renewable panel joined w/ binding flag (for audit)
Convention: impact($/MWh)=-SF*lambda. Pos=raises GKS LMP(discharge), Neg=lowers(charge).
"""
import sys, io, json, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np, pandas as pd
sys.path.insert(0, r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")
import dl

D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
GTCS = ["VALEXP", "WESTEX"]
SEAS = {12:"Winter",1:"Winter",2:"Winter",3:"Spring",4:"Spring",5:"Spring",
        6:"Summer",7:"Summer",8:"Summer",9:"Fall",10:"Fall",11:"Fall"}
# wind region objectids (GR_* geographic) + solar regions + load
WIND_IDS = {10004189447:"wind_GR_SOUTH", 10004189450:"wind_GR_WEST", 10004189445:"wind_GR_PANHANDLE",
            10004189446:"wind_GR_COASTAL", 10004189449:"wind_GR_NORTH", 10004189442:"wind_GR_ERCOT"}
SOLAR_IDS = {10017006228:"solar_SouthEast", 10017014635:"solar_FarWest", 10017006224:"solar_CenterWest",
             10017006229:"solar_CenterEast", 10017006225:"solar_NorthWest", 10017006227:"solar_FarEast",
             10000712973:"solar_ERCOT"}
GTC_IFACE = {"VALEXP":10016657233, "WESTEX":10016469330}  # interface objectids in flow GTC files

# ---------- A. binding panel from msf raw ----------
raw = pd.read_parquet(D/"gks_msf_raw.parquet")
raw = raw[raw.CONSTRAINTNAME.isin(GTCS) & (raw.SHADOWPRICE>0)].copy()
raw["dt"] = pd.to_datetime(raw["DATETIME"], format="%m/%d/%Y %H:%M:%S")
raw["hour_dt"] = raw["dt"].dt.floor("h")
raw["impact"] = -raw["SHIFTFACTOR"]*raw["SHADOWPRICE"]
raw["dur"] = np.where(raw["MARKET"]=="DA", 1.0, 1/12)
raw["cum"] = raw["impact"]*raw["dur"]
raw["month"] = raw["dt"].dt.month
raw["he"] = raw["dt"].dt.hour + 1  # hour-ending 1..24

def pctl(s, q): return float(np.percentile(s, q)) if len(s) else None
binding_stats = {}
for cn in GTCS:
    binding_stats[cn] = {}
    for mkt in ["DA","RT"]:
        m = raw[(raw.CONSTRAINTNAME==cn)&(raw.MARKET==mkt)]
        if not len(m):
            binding_stats[cn][mkt] = {"binding_hours":0}; continue
        binding_stats[cn][mkt] = {
            "binding_hours": round(float(m["dur"].sum()),1),
            "binding_intervals": int(len(m)),
            "distinct_hours": int(m["hour_dt"].nunique()),
            "distinct_days": int(m["dt"].dt.normalize().nunique()),
            "lambda_median": round(pctl(m.SHADOWPRICE,50),2),
            "lambda_P90": round(pctl(m.SHADOWPRICE,90),2),
            "lambda_P99": round(pctl(m.SHADOWPRICE,99),2),
            "lambda_max": round(float(m.SHADOWPRICE.max()),2),
            "mean_abs_SF": round(float(m.SHIFTFACTOR.abs().mean()),4),
            "cum_impact_$": round(float(m["cum"].sum()),1),
        }
json.dump(binding_stats, open(D/"clusterE_binding_stats.json","w"), indent=2)
print("binding_stats:", json.dumps(binding_stats, indent=1))

# ---------- B. month + hour profiles ----------
mh = {}
for cn in GTCS:
    mh[cn] = {}
    for mkt in ["DA","RT"]:
        m = raw[(raw.CONSTRAINTNAME==cn)&(raw.MARKET==mkt)]
        mon = m.groupby("month").agg(cum=("cum","sum"), bind_hrs=("dur","sum")).round(1)
        he = m.groupby("he").agg(cum=("cum","sum"), bind_hrs=("dur","sum")).round(1)
        mh[cn][mkt] = {"by_month": mon.to_dict("index"), "by_HE": he.to_dict("index")}
json.dump(mh, open(D/"clusterE_month_hour.json","w"), indent=2, default=str)
print("saved month_hour")

# ---------- C. GTC limit history (operator-set limit, GTC caveat) ----------
# pull first available day each month from ercot_rt_generic_constraints; VALUE constant intraday = limit MW
def fetch_limit(day):
    key = f"ercot/flow/ercot_rt_generic_constraints/{day}.csv.gz"
    try:
        df = dl.read_csv(key, header=None)
    except Exception:
        return None
    df = df[df[0].isin(GTC_IFACE.values())]
    out = {}
    for cn, oid in GTC_IFACE.items():
        v = df[df[0]==oid][4]
        if len(v):
            vv = v[v < 90000]  # 99999 = unconstrained sentinel
            out[cn] = round(float(vv.median()),0) if len(vv) else None
    return (day, out)
months = pd.date_range("2024-07-01","2026-06-01",freq="MS")
limit_hist = {}
for ms in months:
    # try first 5 days of month until one returns
    got=None
    for off in range(5):
        d=(ms+pd.Timedelta(days=off)).strftime("%Y%m%d")
        r=fetch_limit(d)
        if r and r[1]: got=r; break
    if got: limit_hist[ms.strftime("%Y-%m")] = got[1]
json.dump(limit_hist, open(D/"clusterE_limit_history.json","w"), indent=2)
print("limit_history:", json.dumps(limit_hist, indent=1))

# ---------- D. renewable driver panel (binding vs non-binding) ----------
days = [d.strftime("%Y%m%d") for d in pd.date_range("2024-07-03","2026-06-08",freq="D")]
def fetch_ren(day):
    rows=[]
    for path,idmap in [("ercot/gen/wind_rti",WIND_IDS),("ercot/gen/generation_solar_rt",SOLAR_IDS)]:
        try:
            df = dl.read_csv(f"{path}/{day}.csv.gz", header=None)
        except Exception:
            continue
        df = df[df[0].isin(idmap)]
        if not len(df): continue
        df = df[[0,2,4]].copy(); df.columns=["oid","dt","val"]
        df["var"]=df["oid"].map(idmap)
        rows.append(df[["dt","var","val"]])
    if not rows: return None
    return pd.concat(rows)
print(f"fetching renewables for {len(days)} days...")
parts=[]; t0=time.time()
with ThreadPoolExecutor(max_workers=24) as ex:
    futs={ex.submit(fetch_ren,d):d for d in days}
    done=0
    for f in as_completed(futs):
        r=f.result(); done+=1
        if r is not None: parts.append(r)
        if done%300==0: print(f"  {done}/{len(days)} {time.time()-t0:.0f}s")
ren = pd.concat(parts, ignore_index=True)
ren["dt"]=pd.to_datetime(ren["dt"], format="%m/%d/%Y %H:%M:%S").dt.floor("h")
panel = ren.pivot_table(index="dt", columns="var", values="val", aggfunc="mean")
panel["wind_WESTEX_basin"] = panel.get("wind_GR_WEST",0)+panel.get("wind_GR_PANHANDLE",0)
panel = panel.reset_index().sort_values("dt")
print("renewable panel hours:", len(panel), panel["dt"].min(), "->", panel["dt"].max())

# binding flag per GTC per market at hour level (RT focus; DA too)
drivers={}
for cn in GTCS:
    drivers[cn]={}
    for mkt in ["DA","RT"]:
        b = raw[(raw.CONSTRAINTNAME==cn)&(raw.MARKET==mkt)]
        bind_hours = set(b["hour_dt"])
        p = panel.copy()
        p["bind"] = p["dt"].isin(bind_hours)
        # lambda per hour (max within hour)
        lam = b.groupby("hour_dt")["SHADOWPRICE"].max()
        p["lambda"] = p["dt"].map(lam).fillna(0)
        # primary driver var
        pv = "wind_GR_SOUTH" if cn=="VALEXP" else "wind_WESTEX_basin"
        sv = "solar_SouthEast" if cn=="VALEXP" else "solar_FarWest"
        res={"primary_var":pv,"solar_var":sv,"n_bind_hr":int(p["bind"].sum()),"n_total_hr":int(len(p))}
        for var in [pv,sv,"wind_GR_ERCOT"]:
            if var not in p: continue
            bvals=p.loc[p["bind"],var].dropna(); nvals=p.loc[~p["bind"],var].dropna()
            res[var]={
                "bind_median":round(float(bvals.median()),0) if len(bvals) else None,
                "bind_P25":round(float(np.percentile(bvals,25)),0) if len(bvals) else None,
                "nonbind_median":round(float(nvals.median()),0) if len(nvals) else None,
                "nonbind_P90":round(float(np.percentile(nvals,90)),0) if len(nvals) else None,
            }
        # correlation lambda vs primary var (binding hours only)
        bb=p[p["bind"]]
        if len(bb)>5 and pv in bb:
            res["corr_lambda_vs_"+pv]=round(float(bb[["lambda",pv]].corr().iloc[0,1]),3)
        # threshold: P(bind | primary var bucket)
        if pv in p:
            p["bkt"]=pd.cut(p[pv], bins=[-1,500,1000,1500,2000,3000,4000,99999])
            pr=p.groupby("bkt", observed=True)["bind"].mean().round(3)
            res["P_bind_by_"+pv+"_bucket"]={str(k):float(v) for k,v in pr.items()}
        drivers[cn][mkt]=res
json.dump(drivers, open(D/"clusterE_drivers.json","w"), indent=2, default=str)
panel.to_parquet(D/"clusterE_hourly_panel.parquet", index=False)
print("drivers:", json.dumps(drivers, indent=1, default=str))
print("DONE")
