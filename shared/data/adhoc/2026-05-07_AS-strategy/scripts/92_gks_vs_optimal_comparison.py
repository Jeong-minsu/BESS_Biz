"""
#92 — GKS Actual vs Optimal (per product): MW / Revenue Share / DA-RT Mix.

For each product (RRS / ECRS / NSPIN):
  1. 평균 참여 용량 (Avg participation MW)
     - GKS:     avg(bid MW) over hours bid > 0
     - Optimal: avg(HSL or RT cap) over hours product is Strategy-C winner
  2. 수익 비중 (Revenue share %) — share of total AS revenue
  3. DA/RT 비중 (DA share %)
     - GKS:     100% DA (only DA bidding in Tenaska data)
     - Optimal: from Strategy C picks per product

Output:
  derived/q8_gks_vs_optimal.json
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

# Tenaska HSL (primary)
thsl = pd.read_parquet(DERIVED / "tenaska_hsl_hourly.parquet")
thsl["datetime_ct"] = pd.to_datetime(thsl["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
m = m.merge(thsl, on="datetime_ct", how="left")
hsl = m["tenaska_hsl_telemetered"].combine_first(m["avail_discharge_mw"]).fillna(100).values
soc = m["soc_mwh_max"].fillna(200).values

# RT AS Imbalance merge
ri = pd.read_parquet(DERIVED / "rt_as_revenue_15min.parquet")
ri["datetime_ct"] = pd.to_datetime(ri["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
ri["hour_ct"] = ri["datetime_ct"].dt.floor("h")
code_map = {"RTRRIMBAMT":"RT_IMB_RRS","RTECRIMBAMT":"RT_IMB_ECRS","RTNSIMBAMT":"RT_IMB_NSPIN"}
ri = ri[ri["charge_code"].isin(code_map)].copy()
ri["product"] = ri["charge_code"].map(code_map)
hourly = ri.groupby(["hour_ct","product"])["value"].sum().unstack(fill_value=0.0).reset_index()
hourly = hourly.rename(columns={"hour_ct":"datetime_ct"})
m = m.merge(hourly, on="datetime_ct", how="left")
for c in ["RT_IMB_RRS","RT_IMB_ECRS","RT_IMB_NSPIN"]:
    m[c] = m.get(c, 0).fillna(0)

PRODS = ["RRS", "ECRS", "NSPIN"]
SOC_DUR = {"RRS": 0.5, "ECRS": 1.0, "NSPIN": 4.0}
n = len(m)

# =============================================================================
# GKS Actual per product
# =============================================================================
print("=" * 80)
print("PART A: GKS ACTUAL — per product")
print("=" * 80)
gks_actual = {}
for p in PRODS:
    bid_col = {"RRS":"GKS_Gen_RRS_Qty","ECRS":"GKS_Gen_ECRS_Qty","NSPIN":"GKS_Gen_NS_Qty"}[p]
    rev_col = {"RRS":"GKS_DA_RRS_Amt","ECRS":"GKS_DA_ECRS_Amt","NSPIN":"GKS_DA_NS_Amt"}[p]
    imb_col = {"RRS":"RT_IMB_RRS","ECRS":"RT_IMB_ECRS","NSPIN":"RT_IMB_NSPIN"}[p]
    bid = m[bid_col].fillna(0).values
    gross = float(m[rev_col].sum())
    imb = float(m[imb_col].sum())
    net = gross - imb
    n_hrs_bid = int((bid > 0).sum())
    avg_bid_when_active = float(bid[bid > 0].mean()) if n_hrs_bid else 0.0
    gks_actual[p] = {
        "avg_bid_mw_when_active":    round(avg_bid_when_active, 1),
        "n_hours_bid":               n_hrs_bid,
        "participation_pct":         round(n_hrs_bid / n * 100, 1),
        "gross_da_revenue":          round(gross, 0),
        "rt_imb_paid":               round(imb, 0),
        "net_revenue":               round(net, 0),
        "da_share_pct":              100.0,   # GKS only bids in DA
        "rt_share_pct":              0.0,
    }

total_net = sum(g["net_revenue"] for g in gks_actual.values())
for p in PRODS:
    gks_actual[p]["revenue_share_pct"] = round(gks_actual[p]["net_revenue"] / total_net * 100, 1) if total_net else 0
    g = gks_actual[p]
    print(f"  {p:6s}: avg bid {g['avg_bid_mw_when_active']:>5.1f} MW, "
          f"part {g['participation_pct']:>4.0f}%, "
          f"net ${g['net_revenue']:>9,.0f}, "
          f"rev share {g['revenue_share_pct']:>4.1f}%, "
          f"DA/RT {g['da_share_pct']:>3.0f}/{g['rt_share_pct']:.0f}%")

# =============================================================================
# Optimal (Strategy C — Oracle DA-or-RT per product per hour)
# =============================================================================
print()
print("=" * 80)
print("PART B: OPTIMAL (Strategy C — Oracle DA-or-RT per product) — per product")
print("=" * 80)

spreads = {p: m[f"AS_SPREAD_{p}"].values for p in PRODS}
rt_mcpc = {p: m[f"RT_AS_MCPC_{p}"].values for p in PRODS}

# Compute per-hour revenue for each (product, venue) combo
combo_rev = {}
combo_mw  = {}
for p in PRODS:
    combo_rev[f"{p}_DA"] = hsl * spreads[p]
    combo_mw [f"{p}_DA"] = hsl
    rt_cap = np.minimum(hsl, soc / SOC_DUR[p])
    combo_rev[f"{p}_RT"] = rt_cap * rt_mcpc[p]
    combo_mw [f"{p}_RT"] = rt_cap

combos = [f"{p}_{v}" for p in PRODS for v in ["DA","RT"]]
rev_mat = np.stack([combo_rev[c] for c in combos], axis=1)
mw_mat  = np.stack([combo_mw [c] for c in combos], axis=1)
winner_idx = np.argmax(rev_mat, axis=1)

oracle = {p: {"da_hours": 0, "rt_hours": 0,
              "da_revenue": 0.0, "rt_revenue": 0.0,
              "da_mw_sum": 0.0, "rt_mw_sum": 0.0}
          for p in PRODS}
winning_rev = rev_mat[np.arange(n), winner_idx]
for i in range(n):
    # Skip hours where winning revenue is 0 (HSL=0 outage or all-zero prices)
    # — those don't represent "active" participation for any product.
    if winning_rev[i] <= 0:
        continue
    combo = combos[winner_idx[i]]
    p, v = combo.rsplit("_", 1)
    oracle[p][f"{v.lower()}_hours"] += 1
    oracle[p][f"{v.lower()}_revenue"] += float(winning_rev[i])
    oracle[p][f"{v.lower()}_mw_sum"]  += float(mw_mat[i, winner_idx[i]])

optimal = {}
oracle_total_rev = sum(o["da_revenue"] + o["rt_revenue"] for o in oracle.values())
for p in PRODS:
    o = oracle[p]
    total_hrs = o["da_hours"] + o["rt_hours"]
    total_rev = o["da_revenue"] + o["rt_revenue"]
    avg_mw = (o["da_mw_sum"] + o["rt_mw_sum"]) / total_hrs if total_hrs else 0
    da_pct = o["da_hours"] / total_hrs * 100 if total_hrs else 0
    rt_pct = 100 - da_pct
    optimal[p] = {
        "avg_active_mw":          round(avg_mw, 1),
        "n_hours_active":         total_hrs,
        "active_pct":             round(total_hrs / n * 100, 1),
        "total_revenue":          round(total_rev, 0),
        "revenue_share_pct":      round(total_rev / oracle_total_rev * 100, 1) if oracle_total_rev else 0,
        "da_revenue":             round(o["da_revenue"], 0),
        "rt_revenue":             round(o["rt_revenue"], 0),
        "da_hours":               o["da_hours"],
        "rt_hours":               o["rt_hours"],
        "da_share_pct":           round(da_pct, 1),
        "rt_share_pct":           round(rt_pct, 1),
    }
    print(f"  {p:6s}: avg active {optimal[p]['avg_active_mw']:>5.1f} MW, "
          f"active {optimal[p]['active_pct']:>4.0f}%, "
          f"rev ${optimal[p]['total_revenue']:>9,.0f}, "
          f"rev share {optimal[p]['revenue_share_pct']:>4.1f}%, "
          f"DA/RT {optimal[p]['da_share_pct']:>4.1f}/{optimal[p]['rt_share_pct']:.1f}%")

# =============================================================================
# Side-by-side comparison
# =============================================================================
print()
print("=" * 80)
print("PART C: GKS Actual vs Optimal — side by side")
print("=" * 80)
print(f"{'':10s}{'GKS Actual':>30s}    {'Optimal (Oracle C)':>30s}")
print(f"{'':10s}{'─'*30}    {'─'*30}")
for p in PRODS:
    g = gks_actual[p]
    o = optimal[p]
    print(f"  {p}")
    print(f"    {'평균 참여 MW':17s}  {g['avg_bid_mw_when_active']:>5.1f} MW (참여{g['participation_pct']:>3.0f}%)    {o['avg_active_mw']:>5.1f} MW (활성{o['active_pct']:>3.0f}%)")
    print(f"    {'수익 비중':17s}  {g['revenue_share_pct']:>5.1f}%                       {o['revenue_share_pct']:>5.1f}%")
    print(f"    {'DA/RT 비중':17s}  {g['da_share_pct']:>5.0f}% / {g['rt_share_pct']:>3.0f}%               {o['da_share_pct']:>5.1f}% / {o['rt_share_pct']:>3.1f}%")
    print()

# Save
out = {"gks_actual": gks_actual, "optimal_oracle_c": optimal}
(DERIVED / "q8_gks_vs_optimal.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"saved -> derived/q8_gks_vs_optimal.json")
