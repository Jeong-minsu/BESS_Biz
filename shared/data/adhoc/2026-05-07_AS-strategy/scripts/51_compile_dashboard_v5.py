"""v5 dashboard data compiler — focused on AS-only analysis.

Inputs:
    derived/master_hourly.parquet            (1/1~5/10, Storm Fern included)
    derived/q2_coopt_lp_per_day.parquet      (new co-opt LP)
    derived/q2_coopt_lp_summary.json
    derived/q2_coopt_lp_he_alloc.parquet
    derived/q2_q3_as_summary.json            (Q2 levels + Q3 RT>DAM)

Output:
    derived/dashboard_v5_data.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC = Path(__file__).resolve().parents[1]
DERIVED = ADHOC / "derived"

PRODS = ["REGUP", "REGDN", "RRS", "ECRS", "NSPIN"]

df  = pd.read_parquet(DERIVED / "master_hourly.parquet")
lp  = pd.read_parquet(DERIVED / "q2_coopt_lp_per_day.parquet")
he_alloc = pd.read_parquet(DERIVED / "q2_coopt_lp_he_alloc.parquet")
with open(DERIVED / "q2_coopt_lp_summary.json") as f:
    coopt = json.load(f)

# regenerate Q2/Q3 levels here directly (don't depend on stale json)
PROD_DAM = {p: df[f"AS_MCPC_{p}"] for p in PRODS}
PROD_RT  = {p: df[f"RT_AS_MCPC_{p}"] for p in PRODS}

# --- AS levels (DAM vs RT) ---
levels = {}
for p in PRODS:
    d = PROD_DAM[p].dropna()
    r = PROD_RT[p].dropna()
    # align
    merged = pd.concat([d, r], axis=1, join="inner").dropna()
    merged.columns = ["DAM", "RT"]
    levels[p] = {
        "DAM_mean": float(merged["DAM"].mean()),
        "RT_mean":  float(merged["RT"].mean()),
        "ratio":    float(merged["DAM"].mean() / merged["RT"].mean()) if merged["RT"].mean() > 0 else None,
        "dam_gt_rt_hrs": int((merged["DAM"] > merged["RT"]).sum()),
        "rt_gt_dam_hrs": int((merged["RT"] > merged["DAM"]).sum()),
        "dam_win_pct":   float((merged["DAM"] > merged["RT"]).mean()),
        "n_hours":       int(len(merged)),
    }

# DAM win share by HE
dam_win_share = {p: [] for p in PRODS}
for he in range(1, 25):
    g = df[df["he"] == he]
    for p in PRODS:
        d = g[f"AS_MCPC_{p}"]; r = g[f"RT_AS_MCPC_{p}"]
        valid = d.notna() & r.notna()
        if valid.sum() == 0:
            dam_win_share[p].append(None)
        else:
            dam_win_share[p].append(round(float((d[valid] > r[valid]).mean()), 3))

# --- Q3 RT > DAM characterization ---
rt_gt_summary = {}
for p in PRODS:
    d = df[f"AS_MCPC_{p}"]; r = df[f"RT_AS_MCPC_{p}"]
    diff = r - d
    valid = diff.dropna()
    spike = (valid > 5).sum()
    rt_gt_summary[p] = {
        "rt_ge_dam_hrs": int((valid >= 0).sum()),
        "n_hours":       int(len(valid)),
        "pct_rt_ge_dam": float((valid >= 0).mean()),
        "spike_hrs":     int(spike),
        "avg_rt_dam_gap_when_positive": float(valid[valid > 0].mean()) if (valid > 0).any() else 0.0,
    }

# Top RT>>DAM spikes (largest RT-DAM)
spikes = []
for p in PRODS:
    sub = df[["datetime_ct", "he", f"AS_MCPC_{p}", f"RT_AS_MCPC_{p}",
              "DALMP_GKS_BESS_RN", "RTLMP_GKS_BESS_RN",
              "load_fc_err", "wind_fc_err"]].copy()
    sub["gap"] = sub[f"RT_AS_MCPC_{p}"] - sub[f"AS_MCPC_{p}"]
    sub["product"] = p
    spikes.append(sub.rename(columns={f"AS_MCPC_{p}": "DAM_MCPC",
                                        f"RT_AS_MCPC_{p}": "RT_MCPC"}))
top = pd.concat(spikes, ignore_index=True).nlargest(12, "gap")
top["date_str"] = pd.to_datetime(top["datetime_ct"]).dt.strftime("%Y-%m-%d")
top_records = top[["date_str", "he", "product", "gap", "DALMP_GKS_BESS_RN",
                    "RTLMP_GKS_BESS_RN", "load_fc_err", "wind_fc_err"]].round(2).to_dict("records")

# correlation table (RT-DAM gap vs features per product)
features = ["load_fc_err", "wind_fc_err", "RTLMP_GKS_BESS_RN", "DALMP_GKS_BESS_RN",
            "RTLOAD", "WIND_RTI"]
corr_table = {}
for p in PRODS:
    gap = df[f"RT_AS_MCPC_{p}"] - df[f"AS_MCPC_{p}"]
    corr_table[p] = {f: float(gap.corr(df[f]) or 0.0) for f in features}

# --- Smartbidder capability stats ---
cap_stats = {
    "discharge_mw_mean":  float(df["avail_discharge_mw"].mean()),
    "discharge_mw_median": float(df["avail_discharge_mw"].median()),
    "discharge_mw_min":   float(df["avail_discharge_mw"].min()),
    "charge_mw_mean":     float(df["avail_charge_mw"].mean()),
    "charge_mw_median":   float(df["avail_charge_mw"].median()),
    "charge_mw_min":      float(df["avail_charge_mw"].min()),
    "soc_mwh_max_mean":   float(df["soc_mwh_max"].mean()),
    "soc_mwh_max_median": float(df["soc_mwh_max"].median()),
    "hrs_disch_lt_nameplate": int((df["avail_discharge_mw"] < 100).sum()),
    "hrs_soc_lt_nameplate":   int((df["soc_mwh_max"]        < 200).sum()),
    "total_hrs":              int(len(df)),
    "outage_days":            int(((df.groupby("date")["avail_discharge_mw"]
                                     .max() <= 0.5)).sum()),
}

# --- HE × product mean MCPC for heatmaps ---
mean_dam = df.groupby("he")[[f"AS_MCPC_{p}" for p in PRODS]].mean().round(2)
mean_rt  = df.groupby("he")[[f"RT_AS_MCPC_{p}" for p in PRODS]].mean().round(2)

# --- LP allocation by HE ---
he_alloc_dict = {p: he_alloc[f"a_eff_{p}"].round(1).tolist() for p in PRODS}
he_alloc_da   = {p: he_alloc[f"a_DA_{p}"].round(1).tolist() for p in PRODS}
he_alloc_rt   = {p: he_alloc[f"a_RT_{p}"].round(1).tolist() for p in PRODS}

# --- GKS actual AS revenue/MW comparison ---
gks_as = {
    "REGUP": float(df["GKS_DA_Reg_Up_Amt"].sum()),
    "REGDN": float(df["GKS_DA_Reg_Down_Amt"].sum()),
    "RRS":   float(df["GKS_DA_RRS_Amt"].sum()),
    "ECRS":  float(df["GKS_DA_ECRS_Amt"].sum()),
    "NSPIN": float(df["GKS_DA_NS_Amt"].sum()),
}
gks_as_total = sum(gks_as.values())

lp_as = {p: float((lp[f"aDA_{p}"] * lp[f"DAM_MCPC_{p}"]
                    + lp[f"aRT_{p}"] * lp[f"RT_MCPC_{p}"]).sum())
         for p in PRODS}
lp_as_total = sum(lp_as.values())

# Total LP / GKS total energy + AS (informational, AS focus)
gks_energy_da = float(df["GKS_DA_Energy_Amt"].sum())
gks_energy_rt = float(df["GKS_RT_Energy_Amt"].sum())
gks_total_all = gks_as_total + gks_energy_da + gks_energy_rt

data = {
    "window": {
        "start": "2026-01-01", "end": "2026-05-10",
        "n_days": int(df["date"].nunique()),
        "outage_days": cap_stats["outage_days"],
        "active_days": int(df["date"].nunique()) - cap_stats["outage_days"],
        "storm_fern_included": True,
    },
    "cap_stats": cap_stats,
    "coopt_lp": {
        "total":  coopt["total"],
        "energy": coopt["energy"],
        "as_total": coopt["as_total"],
        "per_product": {p: coopt[p] for p in PRODS},
    },
    "gks_actual": {
        "as_total": gks_as_total,
        "as_by_product": gks_as,
        "energy_da": gks_energy_da,
        "energy_rt": gks_energy_rt,
        "total_all": gks_total_all,
    },
    "lp_as_total": lp_as_total,
    "lp_as_by_product": lp_as,
    "gks_capture_as_pct": gks_as_total / lp_as_total if lp_as_total > 0 else None,
    "as_levels": levels,
    "dam_win_share_by_he": {
        "he": list(range(1, 25)),
        **dam_win_share,
    },
    "rt_gt_dam_summary": rt_gt_summary,
    "top_rt_dam_spikes": top_records,
    "corr_table": corr_table,
    "mean_mcpc_dam": {
        "he": list(range(1, 25)),
        **{p: mean_dam[f"AS_MCPC_{p}"].tolist() for p in PRODS},
    },
    "mean_mcpc_rt": {
        "he": list(range(1, 25)),
        **{p: mean_rt[f"RT_AS_MCPC_{p}"].tolist() for p in PRODS},
    },
    "lp_allocation_by_he": {
        "he": list(range(1, 25)),
        "a_eff": he_alloc_dict,
        "a_DA":  he_alloc_da,
        "a_RT":  he_alloc_rt,
    },
}

out = DERIVED / "dashboard_v5_data.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, default=str)
print(f"Saved -> {out.name}")
print(f"  Window: 130 days, {data['window']['outage_days']} outage / {data['window']['active_days']} active")
print(f"  LP total: ${coopt['total']:,.0f}  (Energy ${coopt['energy']:,.0f} + AS ${coopt['as_total']:,.0f})")
print(f"  GKS AS:   ${gks_as_total:,.0f}  ({gks_as_total/lp_as_total*100:.1f}% of LP AS)")
print(f"  Capability: discharge_mw mean {cap_stats['discharge_mw_mean']:.1f}, "
      f"soc_mwh_max mean {cap_stats['soc_mwh_max_mean']:.1f}")
