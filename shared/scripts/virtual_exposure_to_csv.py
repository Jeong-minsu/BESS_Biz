"""Export daily virtual exposure to CSV from the cached JSON."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "shared/data/pnl/gks/adhoc/virtual_exposure_2026-01-01_2026-05-05.json"
OUT = SRC.with_suffix(".csv")

j = json.loads(SRC.read_text(encoding="utf-8"))

cols = [
    "date",
    "energy_virtual_mwh_perleg",   # primary energy virtual
    "energy_virtual_mwh_net",      # reference energy virtual
    "da_sales_mwh", "da_purchases_mwh",
    "rt_gen_mwh", "rt_consumption_mwh",
    # DA AS award MW per product (= Gen_*_Qty; max possible AS virtual)
    "da_award_rrs_mwh", "da_award_ecrs_mwh", "da_award_ns_mwh",
    "da_award_as_total_mwh",
    # DA AS revenue $ (= Award_MW * MCPC; was previously mis-labeled da_*_mw)
    "da_revenue_rrs_usd", "da_revenue_ecrs_usd", "da_revenue_ns_usd",
    "da_revenue_regup_usd", "da_revenue_regdn_usd",
    # RT AS settlement (financial AS-virtual proxy; pooled all-product)
    "rt_as_imbalance_usd", "rt_reldepl_imbalance_usd",
    "hours_with_data",
]

with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(cols)
    for d, row in sorted(j["daily"].items()):
        w.writerow([d] + [row.get(c, "") for c in cols[1:]])

print(f"✅ {OUT.relative_to(PROJECT_ROOT)}  ({len(j['daily'])} rows)")
