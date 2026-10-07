"""
#93 — Filtered comparison: GKS Actual vs Optimal — only on GKS-participated periods.

User concern (2026-05-18): GKS may have strategically skipped DA AS on extreme-volatility
days (Storm Fern Jan 24-28). Including those days in the gap analysis is unfair —
Optimal would have huge revenue while GKS shows $0.

Three filter levels:
  (A) UNFILTERED (current Q8): all 130 days where Tenaska data exists
  (B) DAY-FILTERED: only days where GKS bid at least one AS product (any of RRS/ECRS/NSPIN)
  (C) PRODUCT-HOUR-FILTERED: per product, only hours where GKS bid that specific product

Output:
  derived/q9_filtered_comparison.json
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
m["date"] = m["datetime_ct"].dt.date

# Tenaska HSL
thsl = pd.read_parquet(DERIVED / "tenaska_hsl_hourly.parquet")
thsl["datetime_ct"] = pd.to_datetime(thsl["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
m = m.merge(thsl, on="datetime_ct", how="left")
m["hsl"] = m["tenaska_hsl_telemetered"].combine_first(m["avail_discharge_mw"]).fillna(100)
m["soc"] = m["soc_mwh_max"].fillna(200)

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

# Restrict to Tenaska window (only days where GKS data exists)
m = m[m["GKS_DA_NS_Amt"].notna()].copy()
print(f"Tenaska window hours: {len(m)} ({m['date'].nunique()} days)")

PRODS = ["RRS", "ECRS", "NSPIN"]
SOC_DUR = {"RRS": 0.5, "ECRS": 1.0, "NSPIN": 4.0}
PROD_QTY = {"RRS":"GKS_Gen_RRS_Qty","ECRS":"GKS_Gen_ECRS_Qty","NSPIN":"GKS_Gen_NS_Qty"}
PROD_AMT = {"RRS":"GKS_DA_RRS_Amt","ECRS":"GKS_DA_ECRS_Amt","NSPIN":"GKS_DA_NS_Amt"}
PROD_IMB = {"RRS":"RT_IMB_RRS","ECRS":"RT_IMB_ECRS","NSPIN":"RT_IMB_NSPIN"}

# Build per-hour optimal revenue (Strategy C — Oracle DA-or-RT, per product per hour)
hsl = m["hsl"].values
soc = m["soc"].values
spreads = {p: m[f"AS_SPREAD_{p}"].values for p in PRODS}
rt_mcpc = {p: m[f"RT_AS_MCPC_{p}"].values for p in PRODS}
n = len(m)

# For each hour, compute the BEST revenue for each product (DA or RT, whichever larger)
per_prod_best = {}
for p in PRODS:
    da_r = hsl * spreads[p]
    rt_cap = np.minimum(hsl, soc / SOC_DUR[p])
    rt_r = rt_cap * rt_mcpc[p]
    per_prod_best[p] = np.maximum(da_r, rt_r)

# Strategy C — pick GLOBAL best each hour
combo_revs = []
for p in PRODS:
    da_r = hsl * spreads[p]
    rt_cap = np.minimum(hsl, soc / SOC_DUR[p])
    rt_r = rt_cap * rt_mcpc[p]
    combo_revs.append(da_r); combo_revs.append(rt_r)
all_mat = np.stack(combo_revs, axis=1)
strategy_c_hourly = all_mat.max(axis=1)

# GKS daily aggregates
m["gks_total_net"] = sum(m[PROD_AMT[p]].fillna(0) - m[PROD_IMB[p]] for p in PRODS)
m["gks_bid_any"]   = (sum(m[PROD_QTY[p]].fillna(0) for p in PRODS) > 0).astype(int)
m["strategy_c_hourly"] = strategy_c_hourly
per_prod_gks_bid_mask = {p: (m[PROD_QTY[p]].fillna(0) > 0) for p in PRODS}


def compute_filter_summary(label: str, mask: np.ndarray) -> dict:
    """Compute GKS vs Optimal totals under a filter mask (rows-level)."""
    sub = m[mask].copy()
    gks_gross_da = sum(float(sub[PROD_AMT[p]].sum()) for p in PRODS)
    gks_imb_paid = sum(float(sub[PROD_IMB[p]].sum()) for p in PRODS)
    gks_net = gks_gross_da - gks_imb_paid
    # Optimal: Strategy C revenue summed over filtered hours
    optimal_C = float(sub["strategy_c_hourly"].sum())
    # Per product (Strategy C per-product best — separate product perspectives)
    per_prod = {}
    sub_idx = sub.index
    pos = m.index.get_indexer(sub_idx)
    for p in PRODS:
        # GKS net for this product (in filtered window)
        ggross = float(sub[PROD_AMT[p]].sum())
        gimb   = float(sub[PROD_IMB[p]].sum())
        gnet   = ggross - gimb
        # Best per-product revenue (DA or RT) summed over filter
        per_prod[p] = {
            "gks_gross_da":     round(ggross, 0),
            "gks_imb_paid":     round(gimb, 0),
            "gks_net":          round(gnet, 0),
            "optimal_best_pp":  round(float(per_prod_best[p][pos].sum()), 0),
        }
    return {
        "label":               label,
        "n_hours":             int(mask.sum()),
        "n_days":              int(sub["date"].nunique()),
        "gks_gross_da":        round(gks_gross_da, 0),
        "gks_imb_paid":        round(gks_imb_paid, 0),
        "gks_net":             round(gks_net, 0),
        "optimal_strategy_C":  round(optimal_C, 0),
        "gks_capture_pct":     round(gks_net / optimal_C * 100, 1) if optimal_C else None,
        "uplift_x":            round(optimal_C / gks_net, 1) if gks_net else None,
        "per_product":         per_prod,
    }


# Filter A: UNFILTERED (full Tenaska window)
mask_A = np.ones(n, dtype=bool)
summary_A = compute_filter_summary("A. UNFILTERED (full Tenaska window)", mask_A)

# Filter B: DAY-filtered (only days GKS bid at least one AS product)
days_with_bid = m.groupby("date")["gks_bid_any"].max()
day_set = set(days_with_bid[days_with_bid == 1].index)
mask_B = m["date"].isin(day_set).values
summary_B = compute_filter_summary("B. DAY-FILTERED (only days GKS bid any AS)", mask_B)

# Filter C: PRODUCT-HOUR-filtered (per-product, only GKS-bid hours)
# This is per-product specific, so handle separately
print()
print("=" * 90)
print("FILTERED COMPARISON — three filter levels")
print("=" * 90)
print()
for name, s in [("(A) UNFILTERED", summary_A), ("(B) DAY-FILTERED", summary_B)]:
    print(f"{name}:  hours={s['n_hours']:,}, days={s['n_days']}")
    print(f"   GKS Net = ${s['gks_net']:>10,.0f}  ·  Optimal (Strategy C) = ${s['optimal_strategy_C']:>10,.0f}  "
          f"·  GKS capture = {s['gks_capture_pct']}%  ·  uplift = {s['uplift_x']}x")
    print(f"   Per-product GKS Net vs Optimal best-per-product:")
    for p in PRODS:
        pp = s["per_product"][p]
        cap = pp["gks_net"] / pp["optimal_best_pp"] * 100 if pp["optimal_best_pp"] else None
        upl = pp["optimal_best_pp"] / pp["gks_net"] if pp["gks_net"] > 0 else None
        cap_s = f"{cap:.1f}%" if cap is not None else "—"
        upl_s = f"{upl:.1f}x" if upl is not None else "—"
        print(f"     {p:6s}: GKS Net = ${pp['gks_net']:>8,.0f}  Opt-best = ${pp['optimal_best_pp']:>9,.0f}  capture {cap_s}  uplift {upl_s}")
    print()

# Filter C (per-product separately)
print("(C) PRODUCT-HOUR-FILTERED (per-product, only hours GKS bid THAT product):")
filter_C = {}
for p in PRODS:
    mask_p = per_prod_gks_bid_mask[p].values
    sub = m[mask_p].copy()
    n_hr = int(mask_p.sum())
    n_dy = int(sub["date"].nunique()) if n_hr else 0
    gnet = float(sub[PROD_AMT[p]].sum() - sub[PROD_IMB[p]].sum())
    pos = m.index.get_indexer(sub.index)
    opt = float(per_prod_best[p][pos].sum())
    cap = gnet / opt * 100 if opt else None
    upl = opt / gnet if gnet > 0 else None
    filter_C[p] = {
        "n_hours":          n_hr,
        "n_days":           n_dy,
        "gks_net":          round(gnet, 0),
        "optimal_best_pp":  round(opt, 0),
        "capture_pct":      round(cap, 1) if cap is not None else None,
        "uplift_x":         round(upl, 1) if upl is not None else None,
    }
    cap_s = f"{cap:.1f}%" if cap is not None else "—"
    upl_s = f"{upl:.1f}x" if upl is not None else "—"
    print(f"   {p:6s}: hrs={n_hr:>4d} ({n_dy:>3d} days)  GKS Net = ${gnet:>8,.0f}  "
          f"Opt-best = ${opt:>9,.0f}  capture {cap_s}  uplift {upl_s}")

# What's the day count that gets excluded under filter B?
all_days = set(m["date"].unique())
excluded_days = sorted(all_days - day_set)
print()
print(f"Days WITH GKS AS bid (any product): {len(day_set)}")
print(f"Days WITHOUT GKS AS bid (excluded under filter B): {len(excluded_days)}")
if excluded_days:
    print(f"  Sample excluded days: {[str(d) for d in excluded_days[:10]]}")

# Save
out = {
    "filter_A_unfiltered":    summary_A,
    "filter_B_day_filtered":  summary_B,
    "filter_C_product_hour":  filter_C,
    "excluded_days_count":    len(excluded_days),
    "excluded_days_sample":   [str(d) for d in excluded_days[:30]],
}
(DERIVED / "q9_filtered_comparison.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print()
print("saved -> derived/q9_filtered_comparison.json")
