"""
Q1 — Hourly optimal AS product (ex-post)

For each HE, compare AS MCPC (5 products) and find the highest-paying product
that the BESS could realistically offer 100 MW capacity into.

Core simplification (ex-post, ignoring multi-period SOC):
  - For a 100 MW / 200 MWh BESS, on a per-HE basis the opportunity cost of
    1 MW capacity offered into AS = (DA energy revenue if used for arb).
  - For 2-hr BESS, top-2 hours go to discharge, bottom-2 to charge -> only
    those 4 hrs face arb opportunity cost. Other 20 hrs: AS dominates whenever MCPC>0.
  - For top-discharge hour, compare AS_MCPC vs DA_LMP (per-MW revenue).

Output:
  derived/q1_top_as_per_he.parquet         (HE, top product, MCPC, vs DA arb)
  derived/q1_summary.json                  (counts, ceiling vs GKS actual)

Notes:
  - AS product duration:
    * RegUp/Dn   -> 1 hour, but fast (≤4s)
    * RRS        -> 1 hour
    * ECRS       -> 2 hour sustained -> matches 2hr BESS
    * NonSpin    -> 1 hour but 30 min ramp
  - All 5 products are accessible to a 100MW/2hr BESS in principle.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC_ROOT = Path(__file__).resolve().parents[1]
DERIVED = ADHOC_ROOT / "derived"

AS_PRODUCTS = ["AS_MCPC_REGUP", "AS_MCPC_REGDN", "AS_MCPC_RRS", "AS_MCPC_ECRS", "AS_MCPC_NSPIN"]
GKS_AS_AWARD = {  # Tenaska columns (MW awarded)
    "REGUP":  None,  # not in Tenaska current pivot — GKS=0
    "REGDN":  None,
    "RRS":    "GKS_Gen_RRS_Qty",
    "ECRS":   "GKS_Gen_ECRS_Qty",
    "NSPIN":  "GKS_Gen_NS_Qty",
}
GKS_AS_REVENUE = {  # Tenaska revenue columns ($)
    "REGUP":  "GKS_DA_Reg_Up_Amt",
    "REGDN":  "GKS_DA_Reg_Down_Amt",
    "RRS":    "GKS_DA_RRS_Amt",
    "ECRS":   "GKS_DA_ECRS_Amt",
    "NSPIN":  "GKS_DA_NS_Amt",
}


def main() -> None:
    df = pd.read_parquet(DERIVED / "master_hourly.parquet")
    print(f"Master rows: {len(df)} | columns: {len([c for c in df.columns if c.startswith('AS_') or c.startswith('GKS_')])} AS+GKS")

    # ============================================================
    # 1. Per-HE top AS product (raw MCPC ranking)
    # ============================================================
    as_df = df[["datetime_ct", "he", "date", "month"] + AS_PRODUCTS].copy()
    as_long = as_df.melt(id_vars=["datetime_ct", "he", "date", "month"],
                         value_vars=AS_PRODUCTS,
                         var_name="product", value_name="mcpc")
    as_long["product"] = as_long["product"].str.replace("AS_MCPC_", "", regex=False)
    # rank by MCPC within each hour
    as_long["rank"] = as_long.groupby("datetime_ct")["mcpc"].rank(method="first", ascending=False).astype(int)
    top = as_long[as_long["rank"] == 1].copy()
    print(f"\n[Q1.1] Top AS product per HE — count distribution:")
    print(top["product"].value_counts())

    # ============================================================
    # 2. Hour-of-day pattern: which product dominates each HE?
    # ============================================================
    hod = (top.groupby(["he", "product"]).size()
              .unstack(fill_value=0))
    hod = hod.div(hod.sum(axis=1), axis=0).round(3)
    print(f"\n[Q1.2] Top AS product share by HE (rows = HE 1-24):")
    print(hod)

    # ============================================================
    # 3. Mean MCPC per HE per product
    # ============================================================
    mean_mcpc = as_long.groupby(["he", "product"])["mcpc"].mean().unstack().round(2)
    print(f"\n[Q1.3] Mean MCPC by HE x product:")
    print(mean_mcpc)

    # ============================================================
    # 4. Ex-post ceiling — assume 100 MW into best AS each HE
    # ============================================================
    # Best per HE
    top["best_mcpc_revenue"] = top["mcpc"] * 100  # $/HE if 100 MW
    ceiling_total = top["best_mcpc_revenue"].sum()
    ceiling_by_product = top.groupby("product")["best_mcpc_revenue"].sum().sort_values(ascending=False)
    print(f"\n[Q1.4] Ex-post AS-only ceiling (100 MW always to best product):")
    print(f"   Total: ${ceiling_total:,.0f} over {top['date'].nunique()} days")
    print(f"   by product:\n{ceiling_by_product.round(0)}")

    # ============================================================
    # 5. Alternative: 100 MW into single product all hours (compare)
    # ============================================================
    fixed_strats = {}
    for p in ["REGUP", "REGDN", "RRS", "ECRS", "NSPIN"]:
        col = f"AS_MCPC_{p}"
        fixed_strats[p] = (df[col].sum() * 100)
    print(f"\n[Q1.5] If always 100 MW into ONE product (all 1560 HE):")
    for k, v in sorted(fixed_strats.items(), key=lambda x: -x[1]):
        print(f"   {k:6s}: ${v:>12,.0f}  ({v/ceiling_total:.1%} of ceiling)")

    # ============================================================
    # 6. GKS actual AS revenue & implied performance
    # ============================================================
    gks_actual_total = 0.0
    gks_actual_by_product = {}
    for p, col in GKS_AS_REVENUE.items():
        if col in df.columns:
            v = df[col].sum()
            gks_actual_by_product[p] = v
            gks_actual_total += v
    print(f"\n[Q1.6] GKS actual AS revenue (Tenaska, Jan 1 - Mar 6):")
    for p, v in sorted(gks_actual_by_product.items(), key=lambda x: -x[1]):
        print(f"   {p:6s}: ${v:>12,.0f}")
    print(f"   TOTAL: ${gks_actual_total:,.0f}  ({gks_actual_total/ceiling_total:.1%} of 100MW-always-best ceiling)")

    # ============================================================
    # 7. Compare GKS AS award MW to ceiling allocation
    # ============================================================
    print(f"\n[Q1.7] GKS actual AS award MW (mean / max):")
    for p, col in GKS_AS_AWARD.items():
        if col and col in df.columns:
            print(f"   {p:6s}: mean={df[col].mean():.1f} MW | max={df[col].max():.0f} MW | hrs_active={(df[col]>0).sum()}")
        else:
            print(f"   {p:6s}: 0 (not awarded)")

    # ============================================================
    # 8. Save outputs
    # ============================================================
    top.to_parquet(DERIVED / "q1_top_as_per_he.parquet", index=False)
    summary = {
        "n_days": int(top["date"].nunique()),
        "n_hours": int(len(top)),
        "ceiling_total_usd": float(ceiling_total),
        "ceiling_by_product": {k: float(v) for k, v in ceiling_by_product.to_dict().items()},
        "fixed_one_product_100mw_strats": {k: float(v) for k, v in fixed_strats.items()},
        "gks_actual_total_as_usd": float(gks_actual_total),
        "gks_actual_by_product": {k: float(v) for k, v in gks_actual_by_product.items()},
        "gks_pct_of_ceiling": float(gks_actual_total / ceiling_total) if ceiling_total else None,
        "top_product_count": top["product"].value_counts().to_dict(),
        "mean_mcpc_per_he_per_product": mean_mcpc.to_dict(),
        "hourly_top_share": hod.to_dict(),
    }
    with open(DERIVED / "q1_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSaved -> q1_top_as_per_he.parquet, q1_summary.json")


if __name__ == "__main__":
    main()
