"""
#99b — Medium / Fine playbook revenue broken down by Net-load quintile.

User question (2026-05-21): medium / fine 전략에서 net-load cohort 를 5분위로
나눴을 때 분위별 숫자가 어떻게 되나?

Reuses #95 logic (HSL=100 flat, in-sample best-combo per cohort) but instead of
reporting per-cohort, aggregates the resulting hourly revenue array by nl_q.

Output: stdout only (diagnostic — no JSON written).
"""
from __future__ import annotations
import sys
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

m["netload_pct"] = m.groupby("he")["NET_LOAD_FORECAST_BID_CLOSE"].rank(pct=True)
m["nl_q"] = pd.qcut(m["netload_pct"], 5, labels=["Q1","Q2","Q3","Q4","Q5"], duplicates="drop")
m["solar_pct"] = m.groupby("he")["SOLAR_COPHSL_BIDCLOSE"].rank(pct=True, method="first")
m["solar_q"] = pd.qcut(m["solar_pct"], 5, labels=["Q1","Q2","Q3","Q4","Q5"], duplicates="drop")

hsl = m["hsl"].values
soc = m["soc"].values
n = len(m)
spreads = {p: m[f"AS_SPREAD_{p}"].values for p in PRODS}
rt_mcpc = {p: m[f"RT_AS_MCPC_{p}"].values for p in PRODS}
combo_revs = {}
for p in PRODS:
    combo_revs[f"{p}_DA"] = hsl * spreads[p]
    rt_cap = np.minimum(hsl, soc / SOC_DUR[p])
    combo_revs[f"{p}_RT"] = rt_cap * rt_mcpc[p]
combos = list(combo_revs.keys())
all_mat = np.stack([combo_revs[c] for c in combos], axis=1)


def playbook_rev_array(cohort_keys):
    """Return per-hour revenue array for a playbook (best-combo per cohort, in-sample)."""
    grouper = m[cohort_keys].astype(str).agg("|".join, axis=1)
    rev = np.zeros(n)
    for c in grouper.unique():
        mask = (grouper == c).values
        best_combo, best_sum = None, -np.inf
        for combo in combos:
            s = float(combo_revs[combo][mask].sum())
            if s > best_sum:
                best_sum, best_combo = s, combo
        rev[mask] = combo_revs[best_combo][mask]
    return rev

rev_baseline = combo_revs["NSPIN_DA"]
rev_medium   = playbook_rev_array(["he_bucket", "nl_q"])
rev_fine     = playbook_rev_array(["he_bucket", "nl_q", "solar_q"])
rev_oracle   = all_mat.max(axis=1)

nlq = m["nl_q"].values

print("=" * 100)
print("NET-LOAD QUINTILE BREAKDOWN — Medium & Fine playbooks (HSL=100 flat, in-sample, 137 days / 3287h)")
print("Net-load quintile = D-1 bidclose NET_LOAD_FORECAST rank within each HE (Q1 lowest … Q5 highest)")
print("=" * 100)
hdr = (f"{'NL-Q':6s} {'Hours':>7s} | {'Baseline':>12s} {'Medium':>12s} {'Fine':>12s} {'Oracle':>12s} | "
       f"{'Med/h':>9s} {'Fine/h':>9s} | {'Med vs Base':>13s} {'Fine vs Base':>14s} {'Fine vs Med':>13s}")
print(hdr)
print("-" * len(hdr))
for q in ["Q1","Q2","Q3","Q4","Q5"]:
    mask = (nlq == q)
    h  = int(mask.sum())
    b  = rev_baseline[mask].sum()
    md = rev_medium[mask].sum()
    fn = rev_fine[mask].sum()
    orc= rev_oracle[mask].sum()
    print(f"{q:6s} {h:>7d} | ${b:>11,.0f} ${md:>11,.0f} ${fn:>11,.0f} ${orc:>11,.0f} | "
          f"${md/h:>8,.0f} ${fn/h:>8,.0f} | {(md/b-1)*100:>+11.1f}% {(fn/b-1)*100:>+12.1f}% {(fn/md-1)*100:>+11.1f}%")
print("-" * len(hdr))
b, md, fn, orc = rev_baseline.sum(), rev_medium.sum(), rev_fine.sum(), rev_oracle.sum()
print(f"{'TOTAL':6s} {n:>7d} | ${b:>11,.0f} ${md:>11,.0f} ${fn:>11,.0f} ${orc:>11,.0f} | "
      f"${md/n:>8,.0f} ${fn/n:>8,.0f} | {(md/b-1)*100:>+11.1f}% {(fn/b-1)*100:>+12.1f}% {(fn/md-1)*100:>+11.1f}%")

# Share of total revenue per quintile
print()
print("Revenue share by quintile (% of playbook total):")
print(f"{'NL-Q':6s} {'Baseline':>10s} {'Medium':>10s} {'Fine':>10s}")
for q in ["Q1","Q2","Q3","Q4","Q5"]:
    mask = (nlq == q)
    print(f"{q:6s} {rev_baseline[mask].sum()/b*100:>9.1f}% "
          f"{rev_medium[mask].sum()/md*100:>9.1f}% {rev_fine[mask].sum()/fn*100:>9.1f}%")

# Combo choice count per quintile (how many cohorts in each quintile pick which combo)
print()
print("Fine playbook — cohort count by quintile × chosen combo:")
grp_fine = m[["he_bucket","nl_q","solar_q"]].astype(str).agg("|".join, axis=1)
choice = {}
for c in grp_fine.unique():
    mask = (grp_fine == c).values
    best_combo, best_sum = None, -np.inf
    for combo in combos:
        s = float(combo_revs[combo][mask].sum())
        if s > best_sum:
            best_sum, best_combo = s, combo
    nlq_c = c.split("|")[1]
    choice.setdefault(nlq_c, {cc: 0 for cc in combos})
    choice[nlq_c][best_combo] += 1
print(f"{'NL-Q':6s} " + " ".join(f"{cc:>9s}" for cc in combos))
for q in ["Q1","Q2","Q3","Q4","Q5"]:
    row = choice.get(q, {cc: 0 for cc in combos})
    print(f"{q:6s} " + " ".join(f"{row[cc]:>9d}" for cc in combos))
