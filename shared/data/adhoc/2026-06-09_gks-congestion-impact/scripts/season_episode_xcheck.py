import sys, json
from pathlib import Path
import pandas as pd, numpy as np
sys.path.insert(0, r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")
import dl
pd.set_option("display.width",300); pd.set_option("display.max_columns",40)
D=Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
raw=pd.read_parquet(D/"gks_msf_raw.parquet")
raw=raw[raw.SHADOWPRICE>0].copy()
raw["dt"]=pd.to_datetime(raw.DATETIME,format="%m/%d/%Y %H:%M:%S")
raw["month"]=raw.dt.dt.month; raw["hour"]=raw.dt.dt.hour
raw["impact"]=-raw.SHIFTFACTOR*raw.SHADOWPRICE
raw["dur"]=np.where(raw.MARKET=="DA",1.0,1/12); raw["cum"]=raw.impact*raw.dur
TARGETS=["E_PASP","LARDVN_LASCRU1_1","CATARI_PILONC1_1"]

# ---- seasonality month profile + hour profile (DA & RT) ----
print("=== SEASONALITY: month cum$ and binding-hrs ===")
for cn in TARGETS:
    s=raw[raw.CONSTRAINTNAME==cn]
    for mkt in ["DA","RT"]:
        m=s[s.MARKET==mkt]
        mo=m.groupby("month").agg(cum=("cum","sum"),hrs=("dur","sum")).round(0)
        top=mo.cum.abs().sort_values(ascending=False).head(4)
        print(f"  {cn} {mkt}: top months by |cum|:", {int(k):int(mo.cum[k]) for k in top.index})

# ---- E_PASP Jan-2026 episode with/without ----
print("\n=== E_PASP episode resolution (Jan 24-26 2026) ===")
e=raw[(raw.CONSTRAINTNAME=='E_PASP')&(raw.MARKET=='DA')].copy()
e["d"]=e.dt.dt.date
epi=[pd.Timestamp("2026-01-24").date(),pd.Timestamp("2026-01-25").date(),pd.Timestamp("2026-01-26").date()]
tot=e.cum.sum(); epi_sum=e[e.d.isin(epi)].cum.sum()
print(f"  E_PASP DA total cum = {tot:.0f}; Jan24-26 episode = {epi_sum:.0f} ({100*epi_sum/tot:.1f}% of total)")
print(f"  E_PASP DA total EX-episode = {tot-epi_sum:.0f}")
jan=e[e.dt.dt.strftime('%Y-%m')=='2026-01']
print(f"  Jan-2026 total={jan.cum.sum():.0f}; ex-episode={jan[~jan.d.isin(epi)].cum.sum():.0f}")
# is it recurring? other 3-day-or-more clusters with |cum|>500/day
dd=e.groupby("d").cum.sum()
print("  worst 8 single-days (DA cum):"); print(dd.sort_values().head(8).round(0).to_string())

# ---- RT cross-check vs transmission/constraints/rt PRICE ----
print("\n=== RT cross-check: market_shift_factors RT SHADOWPRICE vs rt/ PRICE ===")
# pick E_PASP 2025-05 outlier + a normal LARDVN day + CATARINA overnight
def xcheck(cn, dt_target):
    # msf value
    m=raw[(raw.CONSTRAINTNAME==cn)&(raw.MARKET=='RT')&(raw.dt==dt_target)]
    # rt file
    hh=dt_target.strftime("%Y%m%d%H")
    rt=dl.read_rt(hh)
    if rt is None: return f"  {cn} {dt_target}: rt file missing"
    r=rt[(rt.CONSTRAINTNAME==cn)&(rt.PRICE>0)]
    r=r.assign(dt=pd.to_datetime(r.DATETIME))
    rr=r[r.dt==dt_target]
    msf_v = m.SHADOWPRICE.iloc[0] if len(m) else None
    rt_v = rr.PRICE.iloc[0] if len(rr) else (r.PRICE.tolist() if len(r) else None)
    return f"  {cn} {dt_target}: msf_RT_lambda={msf_v} | rt/_PRICE={rt_v}"

# find E_PASP RT max timestamp
emax=raw[(raw.CONSTRAINTNAME=='E_PASP')&(raw.MARKET=='RT')].nlargest(1,'SHADOWPRICE')
print("  E_PASP RT max row:", emax.dt.iloc[0], "lambda=",emax.SHADOWPRICE.iloc[0])
print(xcheck('E_PASP', emax.dt.iloc[0]))
# a LARDVN high-lambda RT
lmax=raw[(raw.CONSTRAINTNAME=='LARDVN_LASCRU1_1')&(raw.MARKET=='RT')].nlargest(1,'SHADOWPRICE')
print(xcheck('LARDVN_LASCRU1_1', lmax.dt.iloc[0]))
cmax=raw[(raw.CONSTRAINTNAME=='CATARI_PILONC1_1')&(raw.MARKET=='RT')].nlargest(1,'SHADOWPRICE')
print(xcheck('CATARI_PILONC1_1', cmax.dt.iloc[0]))

# ---- save seasonality month x hour matrices for the 3 (DA & RT, p-proxy via cum and hrs) ----
out={"meta":{"constraints":TARGETS,"note":"month(1-12) x hour(0-23) cum$ and binding-row-hrs, DA & RT"},"grids":[]}
for cn in TARGETS:
    for mkt in ["DA","RT"]:
        m=raw[(raw.CONSTRAINTNAME==cn)&(raw.MARKET==mkt)]
        for metric in ["cum","hrs"]:
            val="cum" if metric=="cum" else "dur"
            mat=m.pivot_table(index="month",columns="hour",values=val,aggfunc="sum").reindex(index=range(1,13),columns=range(24)).fillna(0).round(2)
            out["grids"].append({"constraint":cn,"market":mkt,"metric":metric,"matrix":mat.values.tolist()})
json.dump(out, open(D/"seasonality_clusterC.json","w"))
print("\nsaved seasonality_clusterC.json")
