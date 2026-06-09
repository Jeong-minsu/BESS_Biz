"""Cluster D (Laredo/border NEG) deep-dive: BRUNI_69_1, LOYOLA_69_1, LASCRU_MILO1_1.
All three positive GKS SF -> aggravates -> LOWERS GKS_BESS_RN LMP (charge-favorable).
Stats from gks_msf_raw.parquet (binding rows only). impact=-SF*lambda; cum $=impact*dur (DA 1h, RT 1/12h).
Real data only (Yes Energy datalake market_shift_factors at GKS pricenode)."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, r'C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts')
import dl
pd.set_option("display.width", 240); pd.set_option("display.max_columns", 40)

D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
TARGETS = ["BRUNI_69_1", "LOYOLA_69_1", "LASCRU_MILO1_1"]

raw = pd.read_parquet(D/"gks_msf_raw.parquet")
raw = raw[raw["SHADOWPRICE"] > 0].copy()
raw["dt"] = pd.to_datetime(raw["DATETIME"], format="%m/%d/%Y %H:%M:%S")
raw["month"] = raw["dt"].dt.month
raw["he"] = raw["dt"].dt.hour + 1            # hour-ending
raw["dur"] = np.where(raw["MARKET"] == "DA", 1.0, 1/12)
raw["impact"] = -raw["SHIFTFACTOR"] * raw["SHADOWPRICE"]
raw["cum"] = raw["impact"] * raw["dur"]

con = dl.read_csv("ercot/metadata/objects/contingency.csv.gz")
conname = dict(zip(con.OBJECTID, con.CONTINGENCYNAME))

out = {}
for t in TARGETS:
    sub = raw[raw.CONSTRAINTNAME == t]
    rec = {}
    for mkt in ["DA", "RT"]:
        m = sub[sub.MARKET == mkt]
        if len(m) == 0:
            continue
        lam = m.SHADOWPRICE
        rec[mkt] = {
            "binding_rows": int(len(m)),
            "binding_intervals": int(m.dt.nunique()),
            "binding_hours": round(float(m.dur.sum()), 1),
            "lambda_median": round(float(lam.median()), 1),
            "lambda_mean": round(float(lam.mean()), 1),
            "lambda_p90": round(float(lam.quantile(.90)), 1),
            "lambda_p99": round(float(lam.quantile(.99)), 1),
            "lambda_max": round(float(lam.max()), 1),
            "sf_median": round(float(m.SHIFTFACTOR.median()), 4),
            "sf_max": round(float(m.SHIFTFACTOR.max()), 4),
            "cum_impact_$": round(float(m.cum.sum()), 0),
            "mean_impact_$perMWh": round(float(m.impact.mean()), 2),
        }
        # month profile (cum $)
        rec[mkt]["month_cum"] = {int(k): round(float(v),0) for k,v in m.groupby("month").cum.sum().items()}
        # hour profile (cum $)
        rec[mkt]["he_cum"] = {int(k): round(float(v),0) for k,v in m.groupby("he").cum.sum().items()}
        # contingency split: cum $ + intervals by contingency name
        cg = m.groupby("CONTINGENCYID").agg(rows=("dt","size"), cum=("cum","sum"), lam=("SHADOWPRICE","mean"))
        cg["name"] = [conname.get(i,str(i)) for i in cg.index]
        cg = cg.sort_values("cum")  # most negative first
        rec[mkt]["top_contingencies"] = [
            {"name": r["name"], "rows": int(r["rows"]), "cum_$": round(r["cum"],0), "mean_lam": round(r["lam"],0)}
            for _, r in cg.head(6).iterrows()]
    out[t] = rec

print(json.dumps(out, indent=2))
json.dump(out, open(D/"clusterD_stats.json","w"), indent=2)
print("\nsaved", D/"clusterD_stats.json")

# month x hour heatmap (cum $) per constraint+market for seasonality reporting
hm = {}
for t in TARGETS:
    for mkt in ["DA","RT"]:
        m = raw[(raw.CONSTRAINTNAME==t)&(raw.MARKET==mkt)]
        if len(m)==0: continue
        pv = m.pivot_table(index="month", columns="he", values="cum", aggfunc="sum").fillna(0).round(0)
        hm[f"{t}_{mkt}"] = pv.to_dict()
json.dump(hm, open(D/"clusterD_month_hour.json","w"), indent=2)
print("saved", D/"clusterD_month_hour.json")
