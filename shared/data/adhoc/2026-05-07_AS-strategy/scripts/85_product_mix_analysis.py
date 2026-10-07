"""
#85 — Product mix optimization verification (Q5).

Question (user 2026-05-18): Always 100% highest-spread product vs mixing — does mixing help?

Setup (per user assumptions):
- Day-Ahead AS sold ⇒ 100% Real-Time buyback. Net DA revenue per MW = spread.
- Battery HSL[t] = avail_discharge_mw (time-varying, avg 58 MW).
- Battery SoC[t] = soc_mwh_max (time-varying, avg 153 MWh).
- Per-product Real-Time cap = min(HSL[t], SoC[t] / SoC duration).
- ONE physical MW cannot be awarded to multiple products simultaneously.

Strategies compared:
  (A) Always 100% on a single product (3 variants: RRS / ECRS / NSPIN)
  (B) Oracle hour-by-hour SINGLE product pick (max spread per hour, all DA)
  (C) Oracle hour-by-hour pick over {DA, RT} × {3 products}
  (D) Oracle LP split (linear program per hour, can mix products & DA/RT)

If D > C: mixing has structural value (capacity sharing helps).
If D ≈ C and C > A_best: hour-by-hour product picking helps but no mixing.
If C ≈ A_best: just always pick the best avg-spread product.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linprog

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC = Path(__file__).resolve().parents[1]
DERIVED = ADHOC / "derived"

m = pd.read_parquet(DERIVED / "master_hourly.parquet")
m["datetime_ct"] = pd.to_datetime(m["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
m["month"] = m["datetime_ct"].dt.strftime("%Y-%m")

HSL_NAME = 100.0
SOC_NAME = 200.0
# Merge Tenaska Telemetered HSL (primary baseline per user 2026-05-18)
thsl_p = DERIVED / "tenaska_hsl_hourly.parquet"
if thsl_p.exists():
    thsl = pd.read_parquet(thsl_p)
    thsl["datetime_ct"] = pd.to_datetime(thsl["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
    m = m.merge(thsl, on="datetime_ct", how="left")
    hsl = m["tenaska_hsl_telemetered"].combine_first(m["avail_discharge_mw"]).fillna(HSL_NAME).values
    print(f"HSL source: Tenaska Telemetered (primary, mean {hsl.mean():.1f} MW)")
else:
    hsl = m["avail_discharge_mw"].fillna(HSL_NAME).values
    print(f"HSL source: Smartbidder fallback (mean {hsl.mean():.1f} MW)")
soc = m["soc_mwh_max"].fillna(SOC_NAME).values

PRODS = ["RRS", "ECRS", "NSPIN"]
SOC_DUR = {"RRS": 0.5, "ECRS": 1.0, "NSPIN": 4.0}

spreads = {p: m[f"AS_SPREAD_{p}"].values for p in PRODS}
rt_mcpc = {p: m[f"RT_AS_MCPC_{p}"].values for p in PRODS}
n = len(m)

print(f"Data window: {m['datetime_ct'].min()} ~ {m['datetime_ct'].max()}  ({n} hours)")
print(f"HSL avg = {hsl.mean():.1f} MW, SoC avg = {soc.mean():.1f} MWh")
print()

# ---------- Strategy A: always single product ----------
print("=" * 75)
print("STRATEGY A: Always 100% single product (Day-Ahead with full Real-Time buyback)")
print("=" * 75)
print(f"   per hour: HSL[t] x spread_p[t]")
print()
A_rev = {p: float((hsl * spreads[p]).sum()) for p in PRODS}
print(f"   {'Product':10s} {'Total revenue':>15s}  {'avg spread':>14s}")
for p in PRODS:
    print(f"   {p:10s} ${A_rev[p]:>13,.0f}  ${spreads[p].mean():>+10.3f}/MWh")
best_single = max(A_rev, key=lambda k: A_rev[k])
print()
print(f"   --> Best single-product: {best_single} = ${A_rev[best_single]:,.0f}")
print()

# ---------- Strategy B: Oracle per-hour pick (single product DA) ----------
print("=" * 75)
print("STRATEGY B: Oracle hour-by-hour SINGLE product pick (Day-Ahead only)")
print("=" * 75)
print(f"   per hour: HSL[t] x max(spread_RRS[t], spread_ECRS[t], spread_NSPIN[t])")
print()
spread_mat = np.stack([spreads[p] for p in PRODS], axis=1)
best_idx = np.argmax(spread_mat, axis=1)
best_sp  = spread_mat[np.arange(n), best_idx]
B_rev = float((hsl * best_sp).sum())
print(f"   Oracle B total = ${B_rev:,.0f}")
picks = {PRODS[i]: int((best_idx == i).sum()) for i in range(3)}
print(f"   Hour pick distribution:")
for p in PRODS:
    print(f"     {p:6s}: {picks[p]:>5d} hours ({picks[p]/n*100:>5.1f}%)")
print()
print(f"   B vs best-single ({best_single}): +${B_rev - A_rev[best_single]:,.0f}  ({(B_rev/A_rev[best_single]-1)*100:+.2f}%)")
print()

# ---------- Strategy C: Oracle per-hour, includes RT route ----------
print("=" * 75)
print("STRATEGY C: Oracle hour-by-hour pick over {DA, RT} x {RRS, ECRS, NSPIN}")
print("=" * 75)
all_revs = []; labels = []
for p in PRODS:
    da_r = hsl * spreads[p]
    rt_cap = np.minimum(hsl, soc / SOC_DUR[p])
    rt_r = rt_cap * rt_mcpc[p]
    all_revs.append(da_r); labels.append(f"{p}_DA")
    all_revs.append(rt_r); labels.append(f"{p}_RT")
all_mat = np.stack(all_revs, axis=1)
best_combo = np.argmax(all_mat, axis=1)
C_rev = float(all_mat[np.arange(n), best_combo].sum())
print(f"   Oracle C total = ${C_rev:,.0f}")
combo_counts = {labels[i]: int((best_combo == i).sum()) for i in range(6)}
print(f"   Combo pick distribution (sorted desc):")
for lbl, cnt in sorted(combo_counts.items(), key=lambda x: -x[1]):
    print(f"     {lbl:8s}: {cnt:>5d} hours ({cnt/n*100:>5.1f}%)")
print()
print(f"   C vs B (DA-only single): +${C_rev - B_rev:,.0f}  ({(C_rev/B_rev-1)*100:+.2f}%)")
print(f"   C vs best-single ({best_single}): +${C_rev - A_rev[best_single]:,.0f}  ({(C_rev/A_rev[best_single]-1)*100:+.2f}%)")
print()

# ---------- Strategy D: Oracle LP split ----------
print("=" * 75)
print("STRATEGY D: Oracle LP split (mix products & DA/RT, shared HSL & SoC)")
print("=" * 75)
print(f"   per hour: maximize sum(spread_p * a_DA_p) + sum(RT_MCPC_p * a_RT_p)")
print(f"   subject to: sum(a_DA_p + a_RT_p) <= HSL[t]   (power)")
print(f"               sum(a_RT_p * dur_p) <= SoC[t]    (energy)")
print(f"               a_RT_p <= min(HSL[t], SoC[t]/dur_p)")
print(f"   (DA has NO SoC restriction per user assumption #2)")
print()
D_total = 0.0
split_hours = 0
split_2plus = 0
n_skipped = 0
for t in range(n):
    hsl_t = float(hsl[t]); soc_t = float(soc[t])
    if hsl_t == 0:
        n_skipped += 1
        continue
    c = np.array([-spreads["RRS"][t], -spreads["ECRS"][t], -spreads["NSPIN"][t],
                  -rt_mcpc["RRS"][t], -rt_mcpc["ECRS"][t], -rt_mcpc["NSPIN"][t]])
    A_ub = np.array([
        [1, 1, 1, 1, 1, 1],
        [0, 0, 0, SOC_DUR["RRS"], SOC_DUR["ECRS"], SOC_DUR["NSPIN"]],
    ])
    b_ub = np.array([hsl_t, soc_t])
    bounds = [(0, hsl_t)] * 3 + [
        (0, min(hsl_t, soc_t / SOC_DUR["RRS"])),
        (0, min(hsl_t, soc_t / SOC_DUR["ECRS"])),
        (0, min(hsl_t, soc_t / SOC_DUR["NSPIN"])),
    ]
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
    if not res.success:
        continue
    D_total += -res.fun
    active = sum(1 for v in res.x if v > 0.01)
    if active >= 2:
        split_hours += 1
    if active >= 3:
        split_2plus += 1

print(f"   Oracle D total = ${D_total:,.0f}  (skipped {n_skipped} hrs with HSL=0)")
print(f"   Hours with 2+ active variables: {split_hours} / {n} ({split_hours/n*100:.1f}%)")
print(f"   Hours with 3+ active variables: {split_2plus} / {n} ({split_2plus/n*100:.1f}%)")
print()
print(f"   D vs C (single per hour): +${D_total - C_rev:,.0f}  ({(D_total/C_rev-1)*100:+.2f}%)")
print(f"   D vs B (DA single only): +${D_total - B_rev:,.0f}  ({(D_total/B_rev-1)*100:+.2f}%)")
print(f"   D vs A_best ({best_single}): +${D_total - A_rev[best_single]:,.0f}  ({(D_total/A_rev[best_single]-1)*100:+.2f}%)")
print()

# ---------- Summary ----------
print("=" * 75)
print("SUMMARY")
print("=" * 75)
print(f"  A1. Always 100% RRS   :     ${A_rev['RRS']:>12,.0f}")
print(f"  A2. Always 100% ECRS  :     ${A_rev['ECRS']:>12,.0f}")
print(f"  A3. Always 100% NSPIN :     ${A_rev['NSPIN']:>12,.0f}")
print(f"      --> Best single A: {best_single} = ${A_rev[best_single]:,.0f}")
print(f"  B.  Oracle DA pick   :     ${B_rev:>12,.0f}   (+{(B_rev/A_rev[best_single]-1)*100:.1f}% vs A_best)")
print(f"  C.  Oracle DA or RT  :     ${C_rev:>12,.0f}   (+{(C_rev/A_rev[best_single]-1)*100:.1f}% vs A_best)")
print(f"  D.  Oracle LP split  :     ${D_total:>12,.0f}   (+{(D_total/A_rev[best_single]-1)*100:.1f}% vs A_best)")
print()

# Verdict
gain_C_over_A = (C_rev / A_rev[best_single] - 1) * 100
gain_D_over_C = (D_total / C_rev - 1) * 100
print("VERDICT:")
if gain_C_over_A < 2:
    print(f"  - Hour-by-hour picking adds <2% vs always-best — single product is fine.")
else:
    print(f"  - Hour-by-hour picking adds +{gain_C_over_A:.1f}% — pick best product each hour matters.")
if gain_D_over_C < 1:
    print(f"  - LP split adds <1% vs picking single per hour — MIXING DOES NOT HELP.")
else:
    print(f"  - LP split adds +{gain_D_over_C:.1f}% — MIXING HAS REAL VALUE.")

# Save result
out = {
    "strategies": {
        "A_always_RRS":   round(A_rev["RRS"], 0),
        "A_always_ECRS":  round(A_rev["ECRS"], 0),
        "A_always_NSPIN": round(A_rev["NSPIN"], 0),
        "A_best_single":  best_single,
        "A_best_revenue": round(A_rev[best_single], 0),
        "B_oracle_pick_DA":      round(B_rev, 0),
        "C_oracle_pick_DAorRT":  round(C_rev, 0),
        "D_oracle_lp_split":     round(D_total, 0),
    },
    "picks_B": {p: int((best_idx == i).sum()) for i, p in enumerate(PRODS)},
    "picks_C": {labels[i]: int((best_combo == i).sum()) for i in range(6)},
    "split_hours_pct_D":      round(split_hours / n * 100, 2),
    "uplifts_vs_A_best": {
        "B_pct": round((B_rev / A_rev[best_single] - 1) * 100, 2),
        "C_pct": round((C_rev / A_rev[best_single] - 1) * 100, 2),
        "D_pct": round((D_total / A_rev[best_single] - 1) * 100, 2),
    },
    "uplift_D_over_C_pct":    round((D_total / C_rev - 1) * 100, 2),
}
(DERIVED / "q5_product_mix.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print()
print(f"   saved -> derived/q5_product_mix.json")
