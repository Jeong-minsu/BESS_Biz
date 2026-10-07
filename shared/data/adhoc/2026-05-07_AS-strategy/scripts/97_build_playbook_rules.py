"""
#97 — Build production-ready playbook rules JSON for as_playbook.py module.

Exports:
  shared/data/forecasts/as_playbook_rules.json
    {
      "trained_on":             {date_range, hsl_assumption, soc_assumption},
      "he_bucket_map":          {1: "Night", ..., 24: "LateEve"},
      "nl_quintile_thresholds": {he: [q20, q40, q60, q80]},   # 24 entries × 4 thresholds
      "solar_quintile_thresholds": {he: [q20, q40, q60, q80]},
      "medium_cohort_rules":    {"<bucket>|<nl_q>": "<PRODUCT>_<VENUE>"},   # 25 entries
      "fine_cohort_rules":      {"<bucket>|<nl_q>|<solar_q>": "..."},      # ~125 entries
      "default_combo":          "NSPIN_DA",   # fallback if cohort missing
    }

These rules are computed from in-sample data 2026-01-01 ~ 2026-05-17 under HSL=100 MW
flat + SoC=200 MWh nameplate (per user 2026-05-19). Operationally, this is the
"strategy rule" — bidding MW is determined separately by HSL/SoC at bid time.
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
PROJECT_ROOT = Path(__file__).resolve().parents[5]
OUT = PROJECT_ROOT / "shared" / "data" / "forecasts" / "as_playbook_rules.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

# Load master + HSL=100 flat
m = pd.read_parquet(DERIVED / "master_hourly.parquet")
m["datetime_ct"] = pd.to_datetime(m["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
m["he"] = m["datetime_ct"].dt.hour + 1
m["date"] = m["datetime_ct"].dt.date

HSL_FLAT = 100.0
SOC_FLAT = 200.0
m["hsl"] = HSL_FLAT
m["soc"] = SOC_FLAT

PRODS = ["RRS", "ECRS", "NSPIN"]
SOC_DUR = {"RRS": 0.5, "ECRS": 1.0, "NSPIN": 4.0}

def he_bucket(h: int) -> str:
    if 1 <= h <= 6:   return "Night"
    if 7 <= h <= 10:  return "Morning"
    if 11 <= h <= 17: return "Midday"
    if 18 <= h <= 22: return "Evening"
    return "LateEve"
m["he_bucket"] = m["he"].apply(he_bucket)

# Quintile thresholds per HE — saved so production module can map new value → quintile
nl_thr = {}
solar_thr = {}
for h in range(1, 25):
    sub = m[m["he"] == h]
    nl_vals = sub["NET_LOAD_FORECAST_BID_CLOSE"].dropna().values
    sol_vals = sub["SOLAR_COPHSL_BIDCLOSE"].dropna().values
    if len(nl_vals) >= 5:
        nl_thr[h] = [round(float(np.quantile(nl_vals, q)), 2) for q in [0.2, 0.4, 0.6, 0.8]]
    if len(sol_vals) >= 5:
        solar_thr[h] = [round(float(np.quantile(sol_vals, q)), 2) for q in [0.2, 0.4, 0.6, 0.8]]

def assign_quintile(value: float, thresholds: list) -> str:
    """thresholds = [q20, q40, q60, q80] → returns Q1..Q5"""
    if value <= thresholds[0]: return "Q1"
    if value <= thresholds[1]: return "Q2"
    if value <= thresholds[2]: return "Q3"
    if value <= thresholds[3]: return "Q4"
    return "Q5"

# Apply to historical data to compute cohort labels
m["nl_q"]    = m.apply(lambda r: assign_quintile(r["NET_LOAD_FORECAST_BID_CLOSE"], nl_thr[r["he"]]), axis=1)
m["solar_q"] = m.apply(lambda r: assign_quintile(r["SOLAR_COPHSL_BIDCLOSE"], solar_thr[r["he"]]), axis=1)

# Build combo revenues
hsl_arr = m["hsl"].values
soc_arr = m["soc"].values
n = len(m)
combo_revs = {}
for p in PRODS:
    combo_revs[f"{p}_DA"] = hsl_arr * m[f"AS_SPREAD_{p}"].values
    rt_cap = np.minimum(hsl_arr, soc_arr / SOC_DUR[p])
    combo_revs[f"{p}_RT"] = rt_cap * m[f"RT_AS_MCPC_{p}"].values
combos = list(combo_revs.keys())


def learn_rules(cohort_keys: list[str]) -> dict:
    """For each cohort, pick the combo that MAXIMIZES total revenue in that cohort."""
    grouper = m[cohort_keys].astype(str).agg("|".join, axis=1)
    rules = {}
    for c in grouper.unique():
        mask = (grouper == c).values
        best_combo, best_sum = None, -np.inf
        for combo in combos:
            s = float(combo_revs[combo][mask].sum())
            if s > best_sum:
                best_sum = s
                best_combo = combo
        rules[c] = {
            "combo": best_combo,
            "n_hours_trained": int(mask.sum()),
            "trained_revenue": round(best_sum, 0),
        }
    return rules

medium_rules = learn_rules(["he_bucket", "nl_q"])
fine_rules   = learn_rules(["he_bucket", "nl_q", "solar_q"])

print(f"Medium rules: {len(medium_rules)} cohorts")
print(f"Fine rules:   {len(fine_rules)} cohorts")
print()
print("Medium combo distribution:")
from collections import Counter
med_dist = Counter(r["combo"] for r in medium_rules.values())
for c, n_ in sorted(med_dist.items(), key=lambda x: -x[1]):
    print(f"  {c}: {n_} cohorts")
print()
print("Fine combo distribution:")
fine_dist = Counter(r["combo"] for r in fine_rules.values())
for c, n_ in sorted(fine_dist.items(), key=lambda x: -x[1]):
    print(f"  {c}: {n_} cohorts")

# Output
out = {
    "_doc": ("Production playbook rules for AS DA-RT product/venue selection. "
             "Trained on 2026-01-01~2026-05-17 with HSL=100MW flat, SoC=200MWh nameplate. "
             "Use as_playbook.py module to consume. Cohort key format: "
             "Medium='<bucket>|<nl_q>', Fine='<bucket>|<nl_q>|<solar_q>'. "
             "Combo format: '<PRODUCT>_<VENUE>' where PRODUCT in {RRS,ECRS,NSPIN}, VENUE in {DA,RT}."),
    "trained_on": {
        "date_range":     ["2026-01-01", "2026-05-17"],
        "n_hours":        n,
        "hsl_mw":         HSL_FLAT,
        "soc_mwh":        SOC_FLAT,
        "soc_duration_h": SOC_DUR,
    },
    "he_bucket_map": {h: he_bucket(h) for h in range(1, 25)},
    "nl_quintile_thresholds_per_he": {str(h): thr for h, thr in nl_thr.items()},
    "solar_quintile_thresholds_per_he": {str(h): thr for h, thr in solar_thr.items()},
    "medium_cohort_rules": {k: v["combo"] for k, v in medium_rules.items()},
    "medium_cohort_trained_revenue": {k: v for k, v in medium_rules.items()},
    "fine_cohort_rules":   {k: v["combo"] for k, v in fine_rules.items()},
    "fine_cohort_trained_revenue": {k: v for k, v in fine_rules.items()},
    "default_combo": "NSPIN_DA",
}
OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
print(f"\nsaved -> {OUT.relative_to(PROJECT_ROOT)}")
print(f"  size: {OUT.stat().st_size / 1024:.1f} KB")
