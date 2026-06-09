"""Hourly driver panel for Cluster-C South-Texas export NEG constraints.
Series: WZ_Southern + WZ_SouthCentral load, GR_SOUTH + GR_COASTAL wind, SouthEast solar (real datalake).
Binding flag + lambda (DA) for E_PASP / LARDVN_LASCRU1_1 / CATARI_PILONC1_1 from gks_msf_raw."""
import sys, concurrent.futures as cf
from pathlib import Path
import pandas as pd, numpy as np
sys.path.insert(0, r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")
import dl

WZ_S, WZ_SC = 10002211351, 10002211350
GR_SOUTH, GR_COASTAL = 10004189447, 10004189446
SOLAR_SE = 10017006228
START, END = "2024-07-01", "2026-06-08"
D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
TARGETS = ["E_PASP","LARDVN_LASCRU1_1","CATARI_PILONC1_1"]

def load_day(d):
    df=dl.try_read_csv(f"ercot/load/rtload_hourly_wz/{d:%Y%m%d}.csv.gz",header=None)
    if df is None: return None
    df.columns=["OBJECTID","DATATYPEID","DATETIME","TIMEZONE","VALUE","LOADID"][:df.shape[1]]
    out={}
    for oid,c in [(WZ_S,"load_south"),(WZ_SC,"load_southcentral")]:
        out[c]=df[df.OBJECTID==oid].groupby("DATETIME")["VALUE"].mean().rename(c)
    return pd.concat(out.values(),axis=1).reset_index()

def wind_day(d):
    df=dl.try_read_csv(f"ercot/gen/wind_rti/{d:%Y%m%d}.csv.gz",header=None)
    if df is None: return None
    df.columns=["OBJECTID","DATATYPEID","DATETIME","TIMEZONE","VALUE","SEQ"][:df.shape[1]]
    out={}
    for oid,c in [(GR_SOUTH,"wind_south"),(GR_COASTAL,"wind_coastal")]:
        out[c]=df[df.OBJECTID==oid].groupby("DATETIME")["VALUE"].mean().rename(c)
    return pd.concat(out.values(),axis=1).reset_index()

def solar_day(d):
    df=dl.try_read_csv(f"ercot/gen/generation_solar_rt/{d:%Y%m%d}.csv.gz",header=None)
    if df is None: return None
    df.columns=["OBJECTID","DATATYPEID","DATETIME","TIMEZONE","VALUE","SEQ"][:df.shape[1]]
    return df[df.OBJECTID==SOLAR_SE].groupby("DATETIME")["VALUE"].mean().rename("solar_se").reset_index()

def gather(fn,days):
    with cf.ThreadPoolExecutor(max_workers=32) as ex:
        parts=[x for x in ex.map(fn,days) if x is not None and len(x)]
    return pd.concat(parts,ignore_index=True) if parts else None

days=pd.date_range(START,END,freq="D")
load=gather(load_day,days); print("load",None if load is None else load.DATETIME.nunique())
wind=gather(wind_day,days); print("wind",None if wind is None else wind.DATETIME.nunique())
solar=gather(solar_day,days); print("solar",None if solar is None else solar.DATETIME.nunique())
for df in (load,wind,solar):
    df["dt"]=pd.to_datetime(df.DATETIME)
panel=load.set_index("dt")[["load_south","load_southcentral"]]
panel=panel.join(wind.set_index("dt")[["wind_south","wind_coastal"]],how="outer")
panel=panel.join(solar.set_index("dt")[["solar_se"]],how="left")

raw=pd.read_parquet(D/"gks_msf_raw.parquet")
raw=raw[(raw.SHADOWPRICE>0)&(raw.MARKET=="DA")&(raw.CONSTRAINTNAME.isin(TARGETS))].copy()
raw["dt"]=pd.to_datetime(raw.DATETIME,format="%m/%d/%Y %H:%M:%S")
for cn in TARGETS:
    lam=raw[raw.CONSTRAINTNAME==cn].groupby("dt")["SHADOWPRICE"].max()
    panel[cn+"_bind"]=panel.index.isin(lam.index).astype(int)
    panel[cn+"_lam"]=lam.reindex(panel.index)
panel=panel[(panel.index>=START)&(panel.index<=END+" 23:59")].copy()
panel["year"]=panel.index.year; panel["month"]=panel.index.month; panel["hour"]=panel.index.hour
panel.to_parquet(D/"driver_panel_clusterC.parquet")
print("\npanel rows",len(panel))
print("coverage:\n",panel.notna().mean().round(3).to_string())
for cn in TARGETS:
    print(f"{cn} bind-hrs", int(panel[cn+"_bind"].sum()))
