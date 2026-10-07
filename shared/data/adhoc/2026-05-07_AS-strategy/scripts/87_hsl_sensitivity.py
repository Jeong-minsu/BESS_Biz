"""
#87 — HSL Sensitivity Analysis (Q7)

User question (2026-05-18): Is Oracle's HSL cap apples-to-apples with what GKS actually bid?

Finding: GKS bid > Smartbidder forecast HSL in 69% of hours (avg over-bid +33 MW).
→ Current Oracle (using forecast HSL) UNDERSTATES potential.

This script recomputes all strategies under 3 HSL assumptions:
  (a) Smartbidder forecast HSL    — current baseline (conservative)
  (b) max(forecast, GKS actual bid) — proven-deliverable (GKS proved they could bid this much)
  (c) Nameplate 100 MW flat        — planning ceiling

Also computes GKS Total Actual capture % under each, and revenue diff per scenario.

Output:
  derived/q7_hsl_sensitivity.json
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC = Path(__file__).resolve().parents[1]
DERIVED = ADHOC / "derived"

m = pd.read_parquet(DERIVED / "master_hourly.parquet")
m["datetime_ct"] = pd.to_datetime(m["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")

PRODS = ["RRS", "ECRS", "NSPIN"]
SOC_DUR = {"RRS": 0.5, "ECRS": 1.0, "NSPIN": 4.0}
HSL_NAME = 100.0

# Get GKS actual max bid per hour across products
m["nspin_bid"] = m["GKS_Gen_NS_Qty"].fillna(0)
m["rrs_bid"]   = m["GKS_Gen_RRS_Qty"].fillna(0)
m["ecrs_bid"]  = m["GKS_Gen_ECRS_Qty"].fillna(0)
m["max_gks_bid"] = m[["nspin_bid","rrs_bid","ecrs_bid"]].max(axis=1)

# Merge Tenaska HSL
thsl_p = DERIVED / "tenaska_hsl_hourly.parquet"
hsl_tenaska = None
if thsl_p.exists():
    thsl = pd.read_parquet(thsl_p)
    thsl["datetime_ct"] = pd.to_datetime(thsl["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
    m = m.merge(thsl, on="datetime_ct", how="left")
    hsl_tenaska = m["tenaska_hsl_telemetered"].combine_first(m["avail_discharge_mw"]).fillna(HSL_NAME).values

# Define 4 HSL scenarios
hsl_smartbidder = m["avail_discharge_mw"].fillna(HSL_NAME).values
hsl_proven      = np.maximum(hsl_smartbidder, m["max_gks_bid"].values)
hsl_nameplate   = np.full(len(m), HSL_NAME)
soc = m["soc_mwh_max"].fillna(200.0).values

scenarios = {
    "a_smartbidder_forecast": ("(a) Smartbidder forecast", hsl_smartbidder),
    "b_tenaska_telemetered":  ("(b) Tenaska Telemetered HSL — TRUE apples-to-apples", hsl_tenaska if hsl_tenaska is not None else hsl_smartbidder),
    "c_max_forecast_or_bid":  ("(c) max(forecast, GKS actual bid) — proven-deliverable", hsl_proven),
    "d_nameplate_100":        ("(d) Nameplate 100 MW flat", hsl_nameplate),
}

spreads = {p: m[f"AS_SPREAD_{p}"].values for p in PRODS}
rt_mcpc = {p: m[f"RT_AS_MCPC_{p}"].values for p in PRODS}
n = len(m)

# Restrict GKS revenue calc to Tenaska window
gks_mask = m["GKS_DA_NS_Amt"].notna().values

# Get GKS revenue (sign-corrected, with RT imbalance subtraction)
# RT imbalance from rt_as_revenue_15min already merged in master? No — need to merge here
ri = pd.read_parquet(DERIVED / "rt_as_revenue_15min.parquet")
ri["datetime_ct"] = pd.to_datetime(ri["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
ri["hour_ct"] = ri["datetime_ct"].dt.floor("h")
code_map = {"RTRRIMBAMT":"RT_IMB_RRS","RTECRIMBAMT":"RT_IMB_ECRS","RTNSIMBAMT":"RT_IMB_NSPIN"}
ri = ri[ri["charge_code"].isin(code_map)].copy()
ri["product"] = ri["charge_code"].map(code_map)
hourly = ri.groupby(["hour_ct","product"])["value"].sum().unstack(fill_value=0.0).reset_index()
hourly = hourly.rename(columns={"hour_ct":"datetime_ct"})
m2 = m.merge(hourly, on="datetime_ct", how="left")
for c in ["RT_IMB_RRS","RT_IMB_ECRS","RT_IMB_NSPIN"]:
    m2[c] = m2.get(c, 0).fillna(0)

gks_total_gross_da = sum(float(m2[f].sum()) for f in ["GKS_DA_RRS_Amt","GKS_DA_ECRS_Amt","GKS_DA_NS_Amt"])
gks_total_imb_paid = sum(float(m2[f].sum()) for f in ["RT_IMB_RRS","RT_IMB_ECRS","RT_IMB_NSPIN"])
gks_total_actual   = gks_total_gross_da - gks_total_imb_paid


def compute_strategies(hsl: np.ndarray) -> dict:
    """Compute all 5 strategies for a given HSL array."""
    out = {}
    # A: always single product
    out["A_RRS"]   = float((hsl * spreads["RRS"]).sum())
    out["A_ECRS"]  = float((hsl * spreads["ECRS"]).sum())
    out["A_NSPIN"] = float((hsl * spreads["NSPIN"]).sum())
    out["A_best"]  = max(out["A_RRS"], out["A_ECRS"], out["A_NSPIN"])
    out["A_best_label"] = max(["RRS","ECRS","NSPIN"], key=lambda p: out[f"A_{p}"])

    # B: oracle per-hour pick (DA only)
    spread_mat = np.stack([spreads[p] for p in PRODS], axis=1)
    best_sp = spread_mat[np.arange(n), np.argmax(spread_mat, axis=1)]
    out["B_oracle_DA"] = float((hsl * best_sp).sum())

    # C: oracle per-hour pick (DA or RT, single product)
    all_revs = []
    for p in PRODS:
        all_revs.append(hsl * spreads[p])
        rt_cap = np.minimum(hsl, soc / SOC_DUR[p])
        all_revs.append(rt_cap * rt_mcpc[p])
    all_mat = np.stack(all_revs, axis=1)
    out["C_oracle_DAorRT"] = float(all_mat[np.arange(n), np.argmax(all_mat, axis=1)].sum())

    # D: LP split (per-hour)
    from scipy.optimize import linprog
    D = 0.0
    for t in range(n):
        h_t = float(hsl[t]); s_t = float(soc[t])
        if h_t == 0:
            continue
        c = np.array([-spreads["RRS"][t], -spreads["ECRS"][t], -spreads["NSPIN"][t],
                      -rt_mcpc["RRS"][t], -rt_mcpc["ECRS"][t], -rt_mcpc["NSPIN"][t]])
        A_ub = np.array([[1,1,1,1,1,1],
                         [0,0,0, SOC_DUR["RRS"], SOC_DUR["ECRS"], SOC_DUR["NSPIN"]]])
        b_ub = np.array([h_t, s_t])
        bounds = [(0, h_t)]*3 + [
            (0, min(h_t, s_t / SOC_DUR["RRS"])),
            (0, min(h_t, s_t / SOC_DUR["ECRS"])),
            (0, min(h_t, s_t / SOC_DUR["NSPIN"])),
        ]
        res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
        if res.success:
            D += -res.fun
    out["D_LP_split"] = float(D)
    return out


# Run for each scenario
results = {}
print("="*85)
print("HSL SENSITIVITY ANALYSIS")
print("="*85)
for key, (label, hsl) in scenarios.items():
    print(f"\nScenario: {label}")
    print(f"  HSL avg = {hsl.mean():.1f} MW, hours at 0 = {(hsl==0).sum()}")
    res = compute_strategies(hsl)
    res["label"] = label
    res["hsl_avg"] = round(float(hsl.mean()), 1)
    res["hsl_zero_hours"] = int((hsl==0).sum())
    res["gks_capture_pct"] = round(gks_total_actual / res["D_LP_split"] * 100, 2) if res["D_LP_split"] else None
    results[key] = res
    print(f"  A_best ({res['A_best_label']:6s}): ${res['A_best']:>11,.0f}")
    print(f"  B (DA only oracle):     ${res['B_oracle_DA']:>11,.0f}")
    print(f"  C (DA/RT oracle):       ${res['C_oracle_DAorRT']:>11,.0f}")
    print(f"  D (LP split oracle):    ${res['D_LP_split']:>11,.0f}")
    print(f"  GKS capture of D: {res['gks_capture_pct']}%")

# Compare scenarios
print()
print("="*85)
print("COMPARISON ACROSS HSL SCENARIOS")
print("="*85)
print(f"GKS Total Actual AS Revenue: ${gks_total_actual:,.0f}")
print()
print(f"{'Strategy':25s} {'(a) Smartbidder':>17s} {'(b) Tenaska':>13s} {'(c) Proven':>13s} {'(d) Nameplate':>15s}")
for s_key, s_label in [("A_best", "A. Always best single"),
                        ("B_oracle_DA", "B. Oracle DA pick"),
                        ("C_oracle_DAorRT", "C. Oracle DA/RT pick"),
                        ("D_LP_split", "D. Oracle LP split")]:
    a = results["a_smartbidder_forecast"][s_key]
    b = results["b_tenaska_telemetered"][s_key]
    c = results["c_max_forecast_or_bid"][s_key]
    d = results["d_nameplate_100"][s_key]
    print(f"  {s_label:23s} ${a:>14,.0f}  ${b:>11,.0f}  ${c:>11,.0f}  ${d:>13,.0f}")
print()
print(f"GKS Total Actual capture of Oracle D:")
for k in scenarios:
    print(f"  {results[k]['label']:55s}: {results[k]['gks_capture_pct']:>5.1f}%")

# Save
out = {
    "gks_total_actual_revenue":  round(gks_total_actual, 0),
    "gks_total_gross_da":        round(gks_total_gross_da, 0),
    "gks_total_imb_paid":        round(gks_total_imb_paid, 0),
    "scenarios": {k: {kk: (round(vv, 0) if isinstance(vv, float) and abs(vv)>10 else vv)
                       for kk, vv in v.items()}
                   for k, v in results.items()},
    "bid_vs_forecast_stats": {
        "smartbidder_forecast_hsl_avg":  round(float(hsl_smartbidder.mean()), 1),
        "gks_max_bid_avg":                round(float(m["max_gks_bid"].mean()), 1),
        "hours_bid_exceeds_forecast":    int((m["max_gks_bid"] > m["avail_discharge_mw"].fillna(100)).sum()),
        "pct_bid_exceeds_forecast":      round(float((m["max_gks_bid"] > m["avail_discharge_mw"].fillna(100)).mean()) * 100, 1),
        "avg_overbid_when_overbid":      round(float((m["max_gks_bid"] - m["avail_discharge_mw"].fillna(100))[m["max_gks_bid"] > m["avail_discharge_mw"].fillna(100)].mean()), 1),
    },
}
(DERIVED / "q7_hsl_sensitivity.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print()
print(f"saved -> derived/q7_hsl_sensitivity.json")
