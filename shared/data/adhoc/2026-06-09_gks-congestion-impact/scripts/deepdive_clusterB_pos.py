"""Cluster-B POS deep-dive: BLESSING_1382, 15060__B, STPELM27_1 (constraints that RAISE GKS_BESS_RN LMP).
Reproduces SF/binding/seasonality stats from gks_msf_raw.parquet (real Yes Energy datalake) + decodes
element/contingency names. RT cross-check vs transmission/constraints/rt/ done separately (see plan).
impact($/MWh) = -SHIFTFACTOR*SHADOWPRICE (ERCOT MCC sign; CONGESTION_PROJECT.md L32). Pos raises GKS LMP.
Output: derived/clusterB_pos_deepdive.json
"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl

D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
TARGETS = ["BLESSING_1382", "15060__B", "STPELM27_1"]

raw = pd.read_parquet(D/"gks_msf_raw.parquet")
raw = raw[raw.SHADOWPRICE > 0].copy()
raw["dt"] = pd.to_datetime(raw.DATETIME, format="%m/%d/%Y %H:%M:%S")
raw["month"] = raw.dt.dt.month; raw["hour"] = raw.dt.dt.hour; raw["year"] = raw.dt.dt.year
raw["impact"] = -raw.SHIFTFACTOR * raw.SHADOWPRICE

fac = dl.read_csv("ercot/metadata/objects/facility.csv.gz")
con = dl.read_csv("ercot/metadata/objects/contingency.csv.gz")
facname = dict(zip(fac.OBJECTID, fac.FACILITYNAME))
conname = dict(zip(con.OBJECTID, con.CONTINGENCYNAME))

out = {}
for t in TARGETS:
    rec = {"facilities": {}, "markets": {}}
    fids = raw[raw.CONSTRAINTNAME == t].FACILITYID.unique()
    for fid in fids:
        r = fac[fac.OBJECTID == fid]
        if len(r):
            r = r.iloc[0]
            rec["facilities"][str(fid)] = {
                "name": r.FACILITYNAME, "type": r.FACILITYTYPE, "kv": float(r.VOLTAGE),
                "from": f"{r.FROMSTATION}({r.FROMZONE})",
                "to": f"{r.get('TOSTATION','')}({r.get('TOZONE','')})" if pd.notna(r.get("FROMSTATIONID")) else ""}
    for mkt in ["DA", "RT"]:
        s = raw[(raw.CONSTRAINTNAME == t) & (raw.MARKET == mkt)]
        if not len(s):
            continue
        dur = 1.0 if mkt == "DA" else 1/12
        l = s.SHADOWPRICE
        s2 = s.assign(cn=s.CONTINGENCYID.map(conname))
        rec["markets"][mkt] = {
            "rows": int(len(s)), "binding_intervals": int(s.dt.nunique()),
            "binding_hours_equiv": round(len(s)*dur, 1),
            "SF_mean": round(s.SHIFTFACTOR.mean(), 4), "SF_median": round(s.SHIFTFACTOR.median(), 4),
            "SF_neg_pct": round(100*(s.SHIFTFACTOR < 0).mean(), 1),
            "cum_impact_$": round((s.impact*dur).sum(), 0),
            "lambda": {"mean": round(l.mean(), 1), "median": round(l.median(), 1),
                       "P90": round(l.quantile(.9), 1), "P99": round(l.quantile(.99), 1), "max": round(l.max(), 1)},
            "years": {int(k): int(v) for k, v in s.year.value_counts().sort_index().items()},
            "base_case_pct": round(100*(s2.cn == "BASE CASE").mean(), 1),
            "top_contingencies": [[conname.get(k, str(k)), int(v)] for k, v in s.CONTINGENCYID.value_counts().head(4).items()],
            "cum_by_month": {int(k): round(v, 0) for k, v in s.groupby("month").apply(lambda x: (-x.SHIFTFACTOR*x.SHADOWPRICE*dur).sum()).items()},
            "rows_by_hour": {int(k): int(v) for k, v in s.groupby("hour").size().items()},
            "peak_episodes": [[r.dt.strftime("%Y-%m-%d %H:%M"), round(r.SHADOWPRICE), round(r.SHIFTFACTOR, 3)] for r in s.nlargest(5, "SHADOWPRICE").itertuples()],
        }
    out[t] = rec

json.dump(out, open(D/"clusterB_pos_deepdive.json", "w"), indent=2)
print("saved", D/"clusterB_pos_deepdive.json")
for t in TARGETS:
    print("\n===", t, out[t]["facilities"])
    for m, v in out[t]["markets"].items():
        print(f"  {m}: cum=${v['cum_impact_$']} hrs={v['binding_hours_equiv']} SFmed={v['SF_median']} neg%={v['SF_neg_pct']} lam_med=${v['lambda']['median']} max=${v['lambda']['max']} ctgs={[c[0] for c in v['top_contingencies']]}")
