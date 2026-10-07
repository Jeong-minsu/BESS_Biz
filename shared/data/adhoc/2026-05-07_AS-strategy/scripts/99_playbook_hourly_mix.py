"""
#99 — Compute HE × combo product mix for Medium and Fine playbooks.

For each playbook (Medium / Fine), apply the cohort rules across 137 days and
aggregate the chosen combo per HE. Output for stacked bar chart.

Output:
  derived/q13_playbook_hourly_mix.json
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
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "scripts"))
from as_playbook import ASPlaybook   # noqa

# Load master data
m = pd.read_parquet(DERIVED / "master_hourly.parquet")
m["datetime_ct"] = pd.to_datetime(m["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
m["he"] = m["datetime_ct"].dt.hour + 1

pb = ASPlaybook()
print(f"Playbook loaded — trained {pb.trained_meta()['date_range']}")
print(f"  Medium rules: {len(pb.medium_rules)} cohorts")
print(f"  Fine rules:   {len(pb.fine_rules)} cohorts")

# Apply each playbook to every hour
def apply_playbook(level: str) -> list[str]:
    """Return per-hour combo string (e.g. 'NSPIN_DA') under the playbook."""
    combos = []
    for _, r in m.iterrows():
        nl_fc = r["NET_LOAD_FORECAST_BID_CLOSE"]
        sol_fc = r["SOLAR_COPHSL_BIDCLOSE"] or 0.0
        if pd.isna(nl_fc):
            combos.append("NSPIN_DA")  # default
            continue
        rec = pb.recommend(int(r["he"]), float(nl_fc), float(sol_fc), level=level)
        combos.append(rec["combo"])
    return combos

m["combo_medium"] = apply_playbook("medium")
m["combo_fine"]   = apply_playbook("fine")

# Aggregate by HE × combo (count of hours)
COMBO_ORDER = ["RRS_DA", "RRS_RT", "ECRS_DA", "ECRS_RT", "NSPIN_DA", "NSPIN_RT"]

def he_combo_matrix(level_col: str) -> dict:
    """Return {HE: {combo: hours}}."""
    ct = pd.crosstab(m["he"], m[level_col]).reindex(columns=COMBO_ORDER, fill_value=0)
    # Pct also
    pct = (ct.div(ct.sum(axis=1), axis=0) * 100).round(1)
    return {
        "hours": {int(he): {c: int(ct.loc[he, c]) for c in COMBO_ORDER} for he in ct.index},
        "pct":   {int(he): {c: float(pct.loc[he, c]) for c in COMBO_ORDER} for he in pct.index},
    }

med_data  = he_combo_matrix("combo_medium")
fine_data = he_combo_matrix("combo_fine")

print()
print("MEDIUM playbook — HE × combo (hours):")
print(f"  {'HE':>3s} " + " ".join(f"{c:>9s}" for c in COMBO_ORDER) + "  Total")
for he in range(1, 25):
    row = med_data["hours"][he]
    total = sum(row.values())
    print(f"  {he:>3d} " + " ".join(f"{row[c]:>9d}" for c in COMBO_ORDER) + f"  {total}")

print()
print("FINE playbook — HE × combo (hours):")
print(f"  {'HE':>3s} " + " ".join(f"{c:>9s}" for c in COMBO_ORDER) + "  Total")
for he in range(1, 25):
    row = fine_data["hours"][he]
    total = sum(row.values())
    print(f"  {he:>3d} " + " ".join(f"{row[c]:>9d}" for c in COMBO_ORDER) + f"  {total}")

# Save
out = {
    "combo_order":  COMBO_ORDER,
    "n_hours":      len(m),
    "n_days":       int(m["datetime_ct"].dt.date.nunique()),
    "date_range":   [str(m["datetime_ct"].min()), str(m["datetime_ct"].max())],
    "medium":       med_data,
    "fine":         fine_data,
}
(DERIVED / "q13_playbook_hourly_mix.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\nsaved -> derived/q13_playbook_hourly_mix.json")
