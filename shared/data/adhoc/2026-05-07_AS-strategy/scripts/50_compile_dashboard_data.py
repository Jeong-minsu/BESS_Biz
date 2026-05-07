"""Compile all analysis outputs into a single JSON for the dashboard."""
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

df = pd.read_parquet(DERIVED / "master_hourly.parquet")
lp = pd.read_parquet(DERIVED / "q2_lp_per_day.parquet")
top = pd.read_parquet(DERIVED / "q1_top_as_per_he.parquet")
with open(DERIVED / "q2_lp_summary.json") as f:
    q2 = json.load(f)
with open(DERIVED / "q2_q3_as_summary.json") as f:
    asq = json.load(f)
with open(DERIVED / "q2_split_lp_summary.json") as f:
    split_lp = json.load(f)
with open(DERIVED / "q2_delivery_lp_summary.json") as f:
    deliv_lp = json.load(f)

PRODS = ["REGUP", "REGDN", "RRS", "ECRS", "NSPIN"]
data = {}

# === KPIs (from LP — Energy + AS combined) ===
data["expost_total"]    = q2["expost_total"]
data["expost_energy"]   = q2["expost_energy"]
data["expost_as_total"] = q2["expost_as_total"]
data["actual_total"]    = q2["actual_total"]
data["actual_energy"]   = q2["actual_da_energy"] + q2["actual_rt_energy"]
data["actual_as_total"] = q2["actual_as_total"]
data["gks_pct"]         = q2["gks_pct_of_expost"]
data["gap_total"]       = q2["gap_total"]
data["actual_da_energy"] = q2["actual_da_energy"]
data["actual_rt_energy"] = q2["actual_rt_energy"]

# === DAM vs RT level (Q2 new) ===
data["as_levels"] = asq["levels"]
data["as_strategies"] = asq["strategies"]
data["as_totals"]  = asq["totals"]
data["dam_win_share_by_he"] = asq["dam_win_share_by_he"]

# === Q3 new: RT > DAM characterization ===
data["rt_gt_dam_summary"] = asq["rt_gt_dam_summary"]
data["top_rt_dam_spikes"] = asq["top_rt_spikes"]
data["corr_table"] = asq["corr_table"]

# === Mean MCPC by HE x product (DAM) ===
mean_mcpc = df.groupby("he")[[f"AS_MCPC_{p}" for p in PRODS]].mean().round(2)
data["mean_mcpc_dam_by_he"] = {
    "he":    list(range(1, 25)),
    **{p: mean_mcpc[f"AS_MCPC_{p}"].tolist() for p in PRODS},
}
mean_mcpc_rt = df.groupby("he")[[f"RT_AS_MCPC_{p}" for p in PRODS]].mean().round(2)
data["mean_mcpc_rt_by_he"] = {
    "he":    list(range(1, 25)),
    **{p: mean_mcpc_rt[f"RT_AS_MCPC_{p}"].tolist() for p in PRODS},
}

# === LP AS allocation by HE (with new SoC factors) ===
as_alloc = lp.groupby("he")[["a_REGUP", "a_REGDN", "a_RRS", "a_ECRS", "a_NSPIN"]].mean().round(1)
data["lp_as_alloc"] = {
    "he":    list(range(1, 25)),
    **{p: as_alloc[f"a_{p}"].tolist() for p in PRODS},
}
data["expost_as_by_product"] = {p: q2[f"expost_as_{p}"] for p in PRODS}
data["actual_as_by_product"] = {p: q2[f"actual_as_{p}"] for p in PRODS}

# === GKS award activity ===
data["gks_award_hrs"] = {
    "REGUP": int((df["GKS_DA_Reg_Up_Amt"] != 0).sum()),
    "REGDN": int((df["GKS_DA_Reg_Down_Amt"] != 0).sum()),
    "RRS":   int((df.get("GKS_Gen_RRS_Qty", pd.Series(0, index=df.index)).fillna(0) > 0).sum()),
    "ECRS":  int((df.get("GKS_Gen_ECRS_Qty", pd.Series(0, index=df.index)).fillna(0) > 0).sum()),
    "NSPIN": int((df.get("GKS_Gen_NS_Qty", pd.Series(0, index=df.index)).fillna(0) > 0).sum()),
}

# === Energy LP DA share (kept for reference) ===
lp["ds_da_share"] = np.where(lp["ds"] > 0.01, lp["ds_da"] / lp["ds"], np.nan)
lp["ch_da_share"] = np.where(lp["ch"] > 0.01, lp["ch_da"] / lp["ch"], np.nan)
ds_share = lp.groupby("he")["ds_da_share"].mean()
ch_share = lp.groupby("he")["ch_da_share"].mean()
data["energy_da_share_by_he"] = {
    "he":              list(range(1, 25)),
    "discharge_da":    [round(float(ds_share.get(h, 0.5)), 3) for h in range(1, 25)],
    "charge_da":       [round(float(ch_share.get(h, 0.5)), 3) for h in range(1, 25)],
}

# === Daily P&L: LP vs Actual ===
daily_lp = lp.groupby("date").apply(lambda g: pd.Series({
    "lp_total": float((g["energy_rev"]
                       + g["as_rev_REGUP"] + g["as_rev_REGDN"]
                       + g["as_rev_RRS"] + g["as_rev_ECRS"] + g["as_rev_NSPIN"]).sum()),
}), include_groups=False).reset_index()
daily_lp["date"] = pd.to_datetime(daily_lp["date"])

daily_actual = df.groupby("date").apply(lambda g: pd.Series({
    "actual_total": float((g["GKS_DA_Energy_Amt"] + g["GKS_RT_Energy_Amt"]
                           + g["GKS_DA_NS_Amt"] + g["GKS_DA_ECRS_Amt"] + g["GKS_DA_RRS_Amt"]
                           + g["GKS_DA_Reg_Up_Amt"] + g["GKS_DA_Reg_Down_Amt"]).sum()),
}), include_groups=False).reset_index()
daily_actual["date"] = pd.to_datetime(daily_actual["date"])

merged = daily_lp.merge(daily_actual, on="date")
merged["gap"] = merged["lp_total"] - merged["actual_total"]
data["daily_pnl"] = {
    "date":         merged["date"].dt.strftime("%Y-%m-%d").tolist(),
    "lp_total":     merged["lp_total"].round(0).tolist(),
    "actual_total": merged["actual_total"].round(0).tolist(),
}

worst = merged.nlargest(10, "gap")[["date", "lp_total", "actual_total", "gap"]].copy()
worst["date"] = worst["date"].dt.strftime("%Y-%m-%d")
data["worst_gap_days"] = worst.round(0).to_dict("records")

# Annualized
N_DAYS = 60
data["annualized_lp"]     = q2["expost_total"]    / N_DAYS * 365
data["annualized_actual"] = q2["actual_total"]    / N_DAYS * 365
data["annualized_gap"]    = data["annualized_lp"] - data["annualized_actual"]

# === Q2 v4: DA/RT split LP results ===
data["split_lp"] = {
    "total_rev":  split_lp["total"],
    "energy_rev": split_lp["energy"],
    "as_rev":     split_lp["as_total"],
    "per_product": {p: split_lp[p] for p in PRODS},
}
data["deliv_lp"] = {
    "total_rev":  deliv_lp["total"],
    "energy_rev": deliv_lp["energy"],
    "as_rev":     deliv_lp["as_total"],
    "gks_capture":     deliv_lp["gks_capture"],
    "gks_as_capture":  deliv_lp["gks_as_capture"],
    "per_product": {p: deliv_lp[p] for p in PRODS},
}

# === Save
out = DERIVED / "dashboard_data.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, default=str)
print(f"Saved -> {out.name}")
print(f"  LP total:       ${data['expost_total']:,.0f}")
print(f"  Actual total:   ${data['actual_total']:,.0f}  ({data['gks_pct']:.1%})")
print(f"  AS optimal sum: ${asq['totals']['optimal']:,.0f}")
print(f"  Always-DAM AS:  ${asq['totals']['always_dam']:,.0f}  ({asq['totals']['always_dam']/asq['totals']['optimal']:.1%})")
