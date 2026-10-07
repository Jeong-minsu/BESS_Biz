"""
#95 — Playbook upside vs Always-NSPIN-DA baseline (Q11).

User question (2026-05-19): 시황별 playbook 적용 시 매출 vs 전시간 100% NSPIN-DA
(with RT buyback) 매출 — upside 얼마나?

Strategies compared:
  (1) BASELINE — Always 100% NSPIN Day-Ahead (with RT buyback)
      매시간 HSL[t] × spread_NSPIN[t]
  (2) PLAYBOOK-coarse — 5 HE bucket only (5 cohorts)
  (3) PLAYBOOK-medium — HE bucket × Net-load quintile (25 cohorts)
  (4) PLAYBOOK-fine   — HE bucket × Net-load quintile × Solar quintile (~125 cohorts)
  (5) ORACLE per-hour — Strategy C ceiling (in-sample hour-level optimal)

Each playbook rule (per cohort): pick the (product, venue) combo that MAXIMIZES
total revenue across the cohort's training hours. Apply that combo to each hour
in the cohort.

NOTE: In-sample evaluation (no holdout) — this is the BEST playbook could do given
the data we have. Realistic OOS performance would be ~70-90% of this.

Output:
  derived/q11_playbook_upside.json
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
m["he"] = m["datetime_ct"].dt.hour + 1
m["date"] = m["datetime_ct"].dt.date

# ──────────────────────────────────────────────────────────────────────────
# HSL ASSUMPTION (user 2026-05-19): use 100 MW flat for clean strategy comparison.
# This isolates strategy quality from HSL availability artifacts (Storm Fern damped
# 1/28 loss because actual HSL collapsed to 28 MW). With HSL=100 flat the relative
# strategy upside is the pure "rule quality" signal.
# ──────────────────────────────────────────────────────────────────────────
m["hsl"] = 100.0
m["soc"] = 200.0

PRODS = ["RRS", "ECRS", "NSPIN"]
SOC_DUR = {"RRS": 0.5, "ECRS": 1.0, "NSPIN": 4.0}

def he_bucket(h: int) -> str:
    if 1 <= h <= 6:   return "Night"
    if 7 <= h <= 10:  return "Morning"
    if 11 <= h <= 17: return "Midday"
    if 18 <= h <= 22: return "Evening"
    return "LateEve"
m["he_bucket"] = m["he"].apply(he_bucket)

# Compute Net-load quintile within HE (D-1 information only)
m["netload_pct"] = m.groupby("he")["NET_LOAD_FORECAST_BID_CLOSE"].rank(pct=True)
m["nl_q"] = pd.qcut(m["netload_pct"], 5,
                    labels=["Q1","Q2","Q3","Q4","Q5"], duplicates="drop")
# Solar quintile within HE (D-1 information only). Handle ties (lots of zeros at night).
m["solar_pct"] = m.groupby("he")["SOLAR_COPHSL_BIDCLOSE"].rank(pct=True, method="first")
m["solar_q"] = pd.qcut(m["solar_pct"], 5,
                       labels=["Q1","Q2","Q3","Q4","Q5"], duplicates="drop")

# 6 combos: 3 products × 2 venues
hsl = m["hsl"].values
soc = m["soc"].values
n = len(m)
spreads = {p: m[f"AS_SPREAD_{p}"].values for p in PRODS}
rt_mcpc = {p: m[f"RT_AS_MCPC_{p}"].values for p in PRODS}
combo_revs: dict[str, np.ndarray] = {}
for p in PRODS:
    combo_revs[f"{p}_DA"] = hsl * spreads[p]
    rt_cap = np.minimum(hsl, soc / SOC_DUR[p])
    combo_revs[f"{p}_RT"] = rt_cap * rt_mcpc[p]
combos = list(combo_revs.keys())

# Baseline: always NSPIN_DA (with RT buyback) every hour
baseline_NSPIN_DA = float(combo_revs["NSPIN_DA"].sum())
print(f"Baseline (Always 100% NSPIN Day-Ahead with buyback) = ${baseline_NSPIN_DA:,.0f}")
print(f"  Avg HSL = {hsl.mean():.1f} MW · n hours = {n:,}")
print()

# Oracle (Strategy C — hour-level pick)
all_mat = np.stack([combo_revs[c] for c in combos], axis=1)
oracle_C = float(all_mat.max(axis=1).sum())
print(f"Oracle Strategy C (in-sample hour-level optimal) = ${oracle_C:,.0f}")
print()


def playbook_revenue(cohort_keys: list[str], label: str) -> dict:
    """Group by cohort_keys, pick best-revenue combo per cohort, apply to each hour."""
    grouper = m[cohort_keys].astype(str).agg("|".join, axis=1)
    unique_cohorts = grouper.unique()
    # For each cohort, pick the combo with max total revenue in this cohort
    cohort_choice = {}
    revenue = np.zeros(n)
    for c in unique_cohorts:
        mask = (grouper == c).values
        # For each combo, compute total revenue across cohort hours
        best_combo = None
        best_sum = -np.inf
        for combo in combos:
            s = float(combo_revs[combo][mask].sum())
            if s > best_sum:
                best_sum = s
                best_combo = combo
        cohort_choice[c] = {"combo": best_combo, "hours": int(mask.sum()),
                            "total_revenue": round(best_sum, 0)}
        revenue[mask] = combo_revs[best_combo][mask]
    total = float(revenue.sum())
    n_cohorts = len(unique_cohorts)
    # Cohort-choice distribution (count of cohorts → each combo)
    combo_dist = {c: 0 for c in combos}
    for k, v in cohort_choice.items():
        combo_dist[v["combo"]] += 1
    return {
        "label":          label,
        "cohort_keys":    cohort_keys,
        "n_cohorts":      n_cohorts,
        "total_revenue":  round(total, 0),
        "uplift_vs_baseline_usd":  round(total - baseline_NSPIN_DA, 0),
        "uplift_vs_baseline_pct":  round((total / baseline_NSPIN_DA - 1) * 100, 2),
        "capture_of_oracle_pct":   round(total / oracle_C * 100, 1),
        "combo_dist_across_cohorts": combo_dist,
        "cohort_choices":         cohort_choice,
    }


# Playbook variants
playbooks = {
    "coarse_5":   playbook_revenue(["he_bucket"], "Coarse — 5 HE buckets only"),
    "medium_25":  playbook_revenue(["he_bucket", "nl_q"], "Medium — HE bucket × Net-load quintile"),
    "fine_125":   playbook_revenue(["he_bucket", "nl_q", "solar_q"], "Fine — HE bucket × NL quintile × Solar quintile"),
}

print("=" * 90)
print("PLAYBOOK STRATEGY UPSIDE (vs Always-NSPIN-DA baseline)")
print("=" * 90)
print()
print(f"{'Strategy':50s} {'Revenue':>14s}  {'vs Baseline':>14s}  {'Oracle Capture':>14s}")
print(f"{'─'*50:50s} {'─'*14:>14s}  {'─'*14:>14s}  {'─'*14:>14s}")
print(f"{'(0) Baseline — Always 100% NSPIN-DA':50s} ${baseline_NSPIN_DA:>12,.0f}  {'—':>13s}  {baseline_NSPIN_DA/oracle_C*100:>13.1f}%")
for key, pb in playbooks.items():
    print(f"{'(' + key[0].upper() + ') ' + pb['label']:50s} ${pb['total_revenue']:>12,.0f}  {pb['uplift_vs_baseline_pct']:>+12.2f}%  {pb['capture_of_oracle_pct']:>13.1f}%")
print(f"{'(O) Oracle Strategy C — in-sample hour-level':50s} ${oracle_C:>12,.0f}  {(oracle_C/baseline_NSPIN_DA-1)*100:>+12.2f}%  {'100.0%':>14s}")
print()

# Detail: per-cohort choices for medium playbook
print("=" * 90)
print("MEDIUM PLAYBOOK (25 cohorts) — chosen combo per cohort")
print("=" * 90)
print(f"{'HE Bucket':12s} {'NL Quintile':12s} {'Combo':12s} {'Hours':>6s} {'$ revenue':>12s}")
for k, v in sorted(playbooks["medium_25"]["cohort_choices"].items(),
                   key=lambda x: x[0]):
    hb, nl = k.split("|")
    print(f"{hb:12s} {nl:12s} {v['combo']:12s} {v['hours']:>6d} ${v['total_revenue']:>10,.0f}")
print()
print(f"Combo distribution across 25 cohorts: {playbooks['medium_25']['combo_dist_across_cohorts']}")
print()

# Filter B variant — only GKS-participated days
print("=" * 90)
print("FILTER B — restrict to days GKS participated in any AS (104 of 130 days)")
print("=" * 90)
m_filtered = m[m["GKS_DA_NS_Amt"].notna()].copy()
nspin_bid = m_filtered["GKS_Gen_NS_Qty"].fillna(0)
rrs_bid   = m_filtered["GKS_Gen_RRS_Qty"].fillna(0)
ecrs_bid  = m_filtered["GKS_Gen_ECRS_Qty"].fillna(0)
m_filtered["gks_bid_any"] = (nspin_bid + rrs_bid + ecrs_bid) > 0
days_with_bid = set(m_filtered[m_filtered["gks_bid_any"]]["date"].unique())
mask_B = m["date"].isin(days_with_bid).values
nB = int(mask_B.sum())
baseline_B = float(combo_revs["NSPIN_DA"][mask_B].sum())
oracle_B   = float(all_mat[mask_B].max(axis=1).sum())
# Re-evaluate playbook on filter B (in-sample, just sum revenue on filter B hours)
pb_med_B = float(np.where(mask_B, playbooks["medium_25"]["total_revenue"] / n, 0).sum())
# Actually need to recompute: the medium playbook revenue array
def playbook_apply_to_mask(cohort_keys: list[str], mask: np.ndarray) -> float:
    """Apply trained-on-all playbook to subset (in-sample, single cohort lookup)."""
    grouper = m[cohort_keys].astype(str).agg("|".join, axis=1)
    rev = np.zeros(n)
    for c in grouper.unique():
        mask_c = (grouper == c).values
        # find best combo in this cohort
        best_combo, best_sum = None, -np.inf
        for combo in combos:
            s = float(combo_revs[combo][mask_c].sum())
            if s > best_sum:
                best_sum = s
                best_combo = combo
        rev[mask_c] = combo_revs[best_combo][mask_c]
    return float(rev[mask].sum())
pb_coarse_B = playbook_apply_to_mask(["he_bucket"], mask_B)
pb_medium_B = playbook_apply_to_mask(["he_bucket", "nl_q"], mask_B)
pb_fine_B   = playbook_apply_to_mask(["he_bucket", "nl_q", "solar_q"], mask_B)

# GKS actual on filter B
gks_gross = float(m_filtered[["GKS_DA_RRS_Amt","GKS_DA_ECRS_Amt","GKS_DA_NS_Amt"]].sum().sum())
# RT IMB merge
ri = pd.read_parquet(DERIVED / "rt_as_revenue_15min.parquet")
ri["datetime_ct"] = pd.to_datetime(ri["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
ri["hour_ct"] = ri["datetime_ct"].dt.floor("h")
code_map = {"RTRRIMBAMT":"RT_IMB_RRS","RTECRIMBAMT":"RT_IMB_ECRS","RTNSIMBAMT":"RT_IMB_NSPIN"}
ri = ri[ri["charge_code"].isin(code_map)].copy()
ri["product"] = ri["charge_code"].map(code_map)
hourly = ri.groupby(["hour_ct","product"])["value"].sum().unstack(fill_value=0).reset_index()
hourly = hourly.rename(columns={"hour_ct":"datetime_ct"})
m_fb = m_filtered.merge(hourly, on="datetime_ct", how="left")
for c in ["RT_IMB_RRS","RT_IMB_ECRS","RT_IMB_NSPIN"]:
    m_fb[c] = m_fb.get(c, 0).fillna(0)
gks_imb = float(m_fb[["RT_IMB_RRS","RT_IMB_ECRS","RT_IMB_NSPIN"]].sum().sum())
gks_net = gks_gross - gks_imb

print(f"  Filter B hours: {nB:,} (104 days)")
print(f"  GKS Actual Net (on filter B): ${gks_net:,.0f}")
print(f"  Baseline (Always 100% NSPIN-DA on filter B): ${baseline_B:,.0f}")
print(f"  Playbook coarse (5 cohorts):    ${pb_coarse_B:,.0f}  (+{(pb_coarse_B/baseline_B-1)*100:+.2f}% vs baseline)")
print(f"  Playbook medium (25 cohorts):   ${pb_medium_B:,.0f}  (+{(pb_medium_B/baseline_B-1)*100:+.2f}% vs baseline)")
print(f"  Playbook fine (125 cohorts):    ${pb_fine_B:,.0f}  (+{(pb_fine_B/baseline_B-1)*100:+.2f}% vs baseline)")
print(f"  Oracle Strategy C (on filter B): ${oracle_B:,.0f}")
print()
print(f"  Medium playbook vs GKS Actual: +${pb_medium_B - gks_net:,.0f} ({(pb_medium_B/gks_net-1)*100:+.1f}%)")

# Save
out = {
    "all_days": {
        "n_hours":                n,
        "baseline_always_nspin_da":     round(baseline_NSPIN_DA, 0),
        "oracle_strategy_c":            round(oracle_C, 0),
        "playbooks":                    {k: {kk: vv for kk, vv in v.items() if kk != "cohort_choices"}
                                          for k, v in playbooks.items()},
    },
    "filter_B_gks_days": {
        "n_hours":                 nB,
        "n_days":                  len(days_with_bid),
        "gks_actual_net":          round(gks_net, 0),
        "baseline_always_nspin_da": round(baseline_B, 0),
        "playbook_coarse":         round(pb_coarse_B, 0),
        "playbook_medium":         round(pb_medium_B, 0),
        "playbook_fine":           round(pb_fine_B, 0),
        "oracle_strategy_c":       round(oracle_B, 0),
    },
    "medium_playbook_cohort_rules": playbooks["medium_25"]["cohort_choices"],
}
(DERIVED / "q11_playbook_upside.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
print()
print("saved -> derived/q11_playbook_upside.json")
