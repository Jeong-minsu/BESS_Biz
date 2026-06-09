"""Aggregate GKS congestion impact -> Pos/Neg top-5 (DA & RT) + monthly/seasonal matrices.
impact ($/MWh) = -SHIFTFACTOR * SHADOWPRICE  (ERCOT MCC sign: CONGESTION_PROJECT.md L32).
cum $ impact = time-weighted: DA row=1h, RT row=1/12h. Pos=raises GKS LMP, Neg=lowers."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40)

D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
raw = pd.read_parquet(D/"gks_msf_raw.parquet")
raw = raw[raw["SHADOWPRICE"]>0].copy()
raw["dt"] = pd.to_datetime(raw["DATETIME"], format="%m/%d/%Y %H:%M:%S")
raw["month"] = raw["dt"].dt.month
raw["ym"] = raw["dt"].dt.strftime("%Y-%m")
SEAS = {12:"Winter",1:"Winter",2:"Winter",3:"Spring",4:"Spring",5:"Spring",6:"Summer",7:"Summer",8:"Summer",9:"Fall",10:"Fall",11:"Fall"}
raw["season"] = raw["month"].map(SEAS)
raw["dur"] = np.where(raw["MARKET"]=="DA", 1.0, 1/12)
raw["impact"] = -raw["SHIFTFACTOR"]*raw["SHADOWPRICE"]
raw["cum"] = raw["impact"]*raw["dur"]
print("window:", raw["dt"].min(), "->", raw["dt"].max(), "| binding rows:", len(raw))
print("by market:", raw["MARKET"].value_counts().to_dict())

# decode element + contingency names
fac = dl.read_csv("ercot/metadata/objects/facility.csv.gz")
con = dl.read_csv("ercot/metadata/objects/contingency.csv.gz")
fcol = "REPORTED_NAME" if "REPORTED_NAME" in fac.columns else fac.columns[1]
facname = dict(zip(fac["OBJECTID"], fac[fcol]))
conname = dict(zip(con["OBJECTID"], con["CONTINGENCYNAME"]))

def rank(mkt):
    m = raw[raw["MARKET"]==mkt]
    m = m.assign(absSF=m["SHIFTFACTOR"].abs())
    g = m.groupby("CONSTRAINTNAME")
    agg = pd.DataFrame({
        "cum_impact": g["cum"].sum(),
        "binding_intervals": g["dt"].nunique(),
        "binding_hours": g["dur"].sum(),   # row-weighted hours
        "mean_lambda": g["SHADOWPRICE"].mean(),
        "mean_abs_sf": g["absSF"].mean(),
        "n_rows": g.size(),
    })
    # dominant facility/contingency + peak season/months by |cum|
    dom_fac = g["FACILITYID"].agg(lambda s: s.value_counts().index[0])
    dom_ctg = g["CONTINGENCYID"].agg(lambda s: s.value_counts().index[0])
    agg["element"] = dom_fac.map(facname).fillna(dom_fac.astype(str))
    agg["dom_contingency"] = dom_ctg.map(conname).fillna(dom_ctg.astype(str))
    # peak season + top months by signed cum (for the constraint's own sign)
    seas_cum = m.groupby(["CONSTRAINTNAME","season"])["cum"].sum()
    mo_cum   = m.groupby(["CONSTRAINTNAME","month"])["cum"].sum()
    def peak_season(cn):
        s = seas_cum.loc[cn]; return (s.abs().idxmax(), round(s.loc[s.abs().idxmax()],1))
    def top_months(cn):
        s = mo_cum.loc[cn].sort_values(key=abs, ascending=False).head(3)
        return ",".join(f"{m}({v:+.0f})" for m,v in s.items())
    agg["peak_season"] = [peak_season(cn) for cn in agg.index]
    agg["top_months"] = [top_months(cn) for cn in agg.index]
    return agg.reset_index()

results={}
matrices={}
for mkt in ["DA","RT"]:
    agg = rank(mkt)
    pos = agg.sort_values("cum_impact", ascending=False).head(5)
    neg = agg.sort_values("cum_impact", ascending=True).head(5)
    results[mkt]={"pos":pos, "neg":neg}
    cols=["CONSTRAINTNAME","element","mean_abs_sf","cum_impact","binding_hours","binding_intervals","mean_lambda","dom_contingency","peak_season","top_months"]
    print(f"\n################ {mkt}  POS top5 (RAISE GKS LMP / favor DISCHARGE) ################")
    print(pos[cols].to_string(index=False))
    print(f"\n################ {mkt}  NEG top5 (LOWER GKS LMP / favor CHARGE) ################")
    print(neg[cols].to_string(index=False))
    # monthly matrix for the 10 ranked constraints (pos+neg)
    top_cn = list(pos["CONSTRAINTNAME"])+list(neg["CONSTRAINTNAME"])
    mm = raw[(raw.MARKET==mkt)&(raw.CONSTRAINTNAME.isin(top_cn))].pivot_table(
        index="CONSTRAINTNAME", columns="month", values="cum", aggfunc="sum").reindex(top_cn).fillna(0).round(1)
    matrices[mkt]=mm

# save
for mkt in ["DA","RT"]:
    for side in ["pos","neg"]:
        results[mkt][side].to_json(D/f"ranking_{mkt}_{side}.json", orient="records", indent=2)
    matrices[mkt].to_json(D/f"monthly_matrix_{mkt}.json", orient="index", indent=2)
meta={"window_start":str(raw['dt'].min()),"window_end":str(raw['dt'].max()),
      "binding_rows":int(len(raw)),"convention":"impact=-SHIFTFACTOR*SHADOWPRICE; Pos raises GKS_BESS_RN LMP",
      "source":"market_shift_factors PRICENODEID=10017907494 (GKS_BESS_RN)","rt_weight":"1/12 h per 5-min row"}
json.dump(meta, open(D/"meta.json","w"), indent=2)
print("\nMONTHLY MATRIX (DA):"); print(matrices["DA"].to_string())
print("\nMONTHLY MATRIX (RT):"); print(matrices["RT"].to_string())
print("\nsaved rankings + matrices + meta to", D)
