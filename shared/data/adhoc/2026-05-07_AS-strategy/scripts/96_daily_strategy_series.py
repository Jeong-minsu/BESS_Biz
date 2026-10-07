"""
#96 — Daily revenue series: Fine playbook vs Medium playbook vs NSPIN-100% baseline.

Per-hour strategy revenue → groupby date → daily totals → JSON for dashboard chart.

Output:
  derived/q12_daily_strategy_series.json
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
# Removes the HSL availability artifact (Storm Fern damped 1/28 loss because actual
# HSL collapsed to 28 MW). With HSL=100 flat, daily comparison shows the pure
# "rule quality" signal — what each strategy would have earned at full capacity.
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
m["netload_pct"] = m.groupby("he")["NET_LOAD_FORECAST_BID_CLOSE"].rank(pct=True)
m["nl_q"] = pd.qcut(m["netload_pct"], 5, labels=["Q1","Q2","Q3","Q4","Q5"])
m["solar_pct"] = m.groupby("he")["SOLAR_COPHSL_BIDCLOSE"].rank(pct=True, method="first")
m["solar_q"] = pd.qcut(m["solar_pct"], 5, labels=["Q1","Q2","Q3","Q4","Q5"])

# Build combo revenues
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
all_mat = np.stack([combo_revs[c] for c in combos], axis=1)

# Baseline: 100% NSPIN_DA every hour
hourly_baseline = combo_revs["NSPIN_DA"].copy()


def playbook_hourly(cohort_keys: list[str]) -> np.ndarray:
    """Compute hourly revenue under playbook (best-revenue combo per cohort, in-sample)."""
    grouper = m[cohort_keys].astype(str).agg("|".join, axis=1)
    rev = np.zeros(n)
    for c in grouper.unique():
        mask = (grouper == c).values
        best_combo, best_sum = None, -np.inf
        for combo in combos:
            s = float(combo_revs[combo][mask].sum())
            if s > best_sum:
                best_sum = s; best_combo = combo
        rev[mask] = combo_revs[best_combo][mask]
    return rev

hourly_medium = playbook_hourly(["he_bucket", "nl_q"])
hourly_fine   = playbook_hourly(["he_bucket", "nl_q", "solar_q"])
hourly_oracle = all_mat.max(axis=1)

# Aggregate to daily
df = pd.DataFrame({
    "date":     m["date"].values,
    "baseline": hourly_baseline,
    "medium":   hourly_medium,
    "fine":     hourly_fine,
    "oracle":   hourly_oracle,
})
daily = df.groupby("date").sum().reset_index().sort_values("date")
daily["baseline_cumsum"] = daily["baseline"].cumsum()
daily["medium_cumsum"]   = daily["medium"].cumsum()
daily["fine_cumsum"]     = daily["fine"].cumsum()
daily["oracle_cumsum"]   = daily["oracle"].cumsum()

print(f"Daily series: {len(daily)} days  ({daily['date'].min()} ~ {daily['date'].max()})")
print()
print("Daily revenue summary stats:")
for col in ["baseline", "medium", "fine", "oracle"]:
    s = daily[col]
    print(f"  {col:10s}: total ${s.sum():>10,.0f} · mean ${s.mean():>6,.0f}/day · max ${s.max():>8,.0f} (on {daily.loc[s.idxmax(), 'date']})")
print()

# Top 10 days for each strategy (where playbook outperforms baseline most)
daily["medium_vs_baseline"] = daily["medium"] - daily["baseline"]
daily["fine_vs_medium"]      = daily["fine"]   - daily["medium"]
print("Top 10 days where Medium playbook >> Baseline (largest gap):")
top_med = daily.nlargest(10, "medium_vs_baseline")[["date","baseline","medium","fine","medium_vs_baseline"]]
print(top_med.to_string(index=False))
print()
print("Top 10 days where Fine > Medium (Fine playbook extra):")
top_fine = daily.nlargest(10, "fine_vs_medium")[["date","medium","fine","fine_vs_medium"]]
print(top_fine.to_string(index=False))

# Save JSON
series = [{
    "date":     str(r["date"]),
    "baseline": round(float(r["baseline"]), 0),
    "medium":   round(float(r["medium"]),   0),
    "fine":     round(float(r["fine"]),     0),
    "oracle":   round(float(r["oracle"]),   0),
    "baseline_cumsum": round(float(r["baseline_cumsum"]), 0),
    "medium_cumsum":   round(float(r["medium_cumsum"]),   0),
    "fine_cumsum":     round(float(r["fine_cumsum"]),     0),
    "oracle_cumsum":   round(float(r["oracle_cumsum"]),   0),
} for _, r in daily.iterrows()]

out = {
    "n_days":  len(daily),
    "date_range": [str(daily['date'].min()), str(daily['date'].max())],
    "totals": {
        "baseline": round(float(daily["baseline"].sum()), 0),
        "medium":   round(float(daily["medium"].sum()),   0),
        "fine":     round(float(daily["fine"].sum()),     0),
        "oracle":   round(float(daily["oracle"].sum()),   0),
    },
    "daily_series": series,
    "top_days_medium_vs_baseline": [
        {"date": str(r["date"]),
         "baseline": round(float(r["baseline"]), 0),
         "medium":   round(float(r["medium"]),   0),
         "fine":     round(float(r["fine"]),     0),
         "uplift":   round(float(r["medium"]-r["baseline"]), 0)}
        for _, r in top_med.iterrows()
    ],
}
(DERIVED / "q12_daily_strategy_series.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print()
print(f"saved -> derived/q12_daily_strategy_series.json")
