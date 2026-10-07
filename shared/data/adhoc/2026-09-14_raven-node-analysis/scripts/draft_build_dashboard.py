"""Assemble the Raven draft dashboard payload (JSON) from the item1/2/3a + draft derived files."""
import json, glob
from pathlib import Path
import pandas as pd, numpy as np

BASE = Path(__file__).resolve().parents[1]; D = BASE/"derived"
P = {}

i1 = json.load(open(D/"item1_summary.json"))
P["item1"] = {
    "meta": i1["meta"],
    "tb2_stats": i1["tb2_stats"],
    "monthly": i1["tb2_monthly_mean"],
    "cum": i1["cumulative_usd_per_100MW"],
    "decomp": i1["delta_decomposition"],
    "hub": i1.get("hub_decomposition"),
    "hourly": i1.get("hourly_profile"),
    "tails": i1.get("tails"),
}
# daily series for the chart
dd = pd.read_csv(D/"item1_daily_tb2.csv")
P["daily"] = {}
for mkt in ["DA","RT"]:
    s = dd[dd.mkt==mkt] if "mkt" in dd.columns else dd
    P["daily"][mkt] = json.loads(s.to_json(orient="records"))
P["daily_cols"] = list(dd.columns)

fc = json.load(open(D/"draft_forecast_2027.json")); P["forecast"] = fc
mo = pd.read_csv(D/"draft_monthly_tb2_by_year.csv", index_col=0)
P["monthly_tb2_by_year"] = {c: [None if pd.isna(v) else round(float(v),1) for v in mo[c]] for c in mo.columns}

hou = pd.read_csv(D/"draft_houston_mix_jan_may2026.csv")
P["peers"] = json.loads(hou.head(20).to_json(orient="records"))
fleet = pd.read_csv(D/"draft_fleet_mix_jan_may2026.csv")
gks = fleet[fleet.settlement_point=="GKS_BESS_RN"]
P["gks_row"] = json.loads(gks.to_json(orient="records"))[0] if len(gks) else None
P["fleet_median"] = {"all_rev_per_mw": float(fleet.rev_per_mw.median()),
                     "all_opt": float(fleet.opt_rate_pct.median()),
                     "hou_rev_per_mw": float(hou.rev_per_mw.median()),
                     "hou_opt": float(hou.opt_rate_pct.median()),
                     "hou_as_share": float(hou.as_share_pct.median())}

cg = json.load(open(D/"item2_congestion_top10_profiles.json"))
P["congestion"] = []
for name, v in cg.items():
    P["congestion"].append({
        "name": name, "element": v.get("element"), "zone": v.get("element_zone"),
        "sign": v.get("sign_at_raven"), "cum": v.get("cum_mcc"),
        "binding_months": v.get("binding_months"),
        "da_vs_rt": v.get("da_vs_rt"), "lean": (v.get("da_rt_agreement") or {}).get("dart_lean"),
        "fwd": v.get("forward_relevance"), "month_matrix": v.get("month_matrix"),
        "hourly": v.get("hourly_profile"),
    })
P["proxy"] = json.load(open(D/"item2_proxy_definition.json"))

d3 = json.load(open(D/"item3a_dart_stats.json"))
P["dart_meta"] = d3["meta"]; P["dart_ranking"] = d3["ranking"]
P["dart_patterns"] = {k: v for k, v in d3["patterns"].items()}
h = pd.read_csv(D/"item3a_hourly_RVN_RN.csv")
P["dart_hourly"] = json.loads(h.to_json(orient="records"))

xo = pd.read_csv(D/"item3b_hourly_crossover_summer.csv"); P["crossover"] = json.loads(xo.to_json(orient="records"))
rg = pd.read_csv(D/"item3b_regime_2x2_summer.csv"); P["regime"] = json.loads(rg.to_json(orient="records"))

json.dump(P, open(D/"draft_dashboard_payload.json","w"), indent=1, default=str)
print("payload keys:", list(P))
print("daily cols:", P["daily_cols"])
print("congestion n:", len(P["congestion"]))
print("peers n:", len(P["peers"]))
