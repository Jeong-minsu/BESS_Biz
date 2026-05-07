"""
Q2 (재정의) — AS 상품별 DAM vs RT 시장 어디에 capacity offer해야 유리한가
Q3 (재정의) — RT AS price > DAM AS price 시간대의 특성 + 사전 예측 가능성

For each AS product, compute:
- Mean DAM vs RT MCPC (level comparison)
- DAM > RT vs RT > DAM hours
- Per-HE pattern of DAM/RT split optimal
- Conditions when RT > DAM (driver analysis)
- Per-product spread vs forecast error correlations

Output:
  derived/q2_as_market_split.parquet  (HE-level optimal DAM vs RT)
  derived/q2_q3_summary.json
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC = Path(__file__).resolve().parents[1]
DERIVED = ADHOC / "derived"

PRODS = ["REGUP", "REGDN", "RRS", "ECRS", "NSPIN"]


def main():
    df = pd.read_parquet(DERIVED / "master_hourly.parquet")
    df["date"] = pd.to_datetime(df["date"])
    print(f"Master: {df.shape}, days: {df['date'].nunique()}")

    out = {}

    # === 1. Level comparison: DAM vs RT mean ===
    print("\n=== 1. Level comparison ===")
    levels = []
    for p in PRODS:
        d = df[f"AS_MCPC_{p}"]
        r = df[f"RT_AS_MCPC_{p}"]
        levels.append({
            "product": p,
            "dam_mean": float(d.mean()), "rt_mean": float(r.mean()),
            "dam_median": float(d.median()), "rt_median": float(r.median()),
            "dam_p95": float(d.quantile(0.95)), "rt_p95": float(r.quantile(0.95)),
            "spread_mean": float((d-r).mean()),
            "n_dam_gt_rt": int((d > r).sum()),
            "n_rt_gt_dam": int((r > d).sum()),
            "n_equal":     int((d == r).sum()),
        })
    levels_df = pd.DataFrame(levels)
    print(levels_df.round(2).to_string(index=False))
    out["levels"] = levels_df.to_dict("records")

    # === 2. Per-HE optimal split (DAM-share if DAM > RT, else RT) ===
    print("\n=== 2. Optimal market by HE x product (% time DAM is winner) ===")
    hod = {}
    for p in PRODS:
        df[f"_dam_win_{p}"] = df[f"AS_MCPC_{p}"] > df[f"RT_AS_MCPC_{p}"]
        share = df.groupby("he")[f"_dam_win_{p}"].mean().round(3)
        hod[p] = share.tolist()
    hod_df = pd.DataFrame(hod, index=range(1,25))
    print(hod_df)
    out["dam_win_share_by_he"] = {"he": list(range(1,25)), **hod}

    # === 3. Optimal capacity-weighted DAM/RT mix per product (ex-post) ===
    # Strategy: for each HE, commit MW to whichever clears higher.
    # Compare to:
    #   - Always DAM (current GKS approach)
    #   - Always RT
    #   - Optimal (max of two)
    print("\n=== 3. Per-product strategy revenue comparison (per 100 MW assumption) ===")
    strategies = []
    for p in PRODS:
        d = df[f"AS_MCPC_{p}"]
        r = df[f"RT_AS_MCPC_{p}"]
        always_dam = (d * 100).sum()
        always_rt  = (r * 100).sum()
        optimal    = (np.maximum(d, r) * 100).sum()
        strategies.append({
            "product": p,
            "always_dam_revenue": float(always_dam),
            "always_rt_revenue":  float(always_rt),
            "optimal_revenue":    float(optimal),
            "dam_pct_of_optimal": float(always_dam/optimal) if optimal else None,
            "rt_pct_of_optimal":  float(always_rt/optimal)  if optimal else None,
        })
    strat_df = pd.DataFrame(strategies)
    print(strat_df.round(0).to_string(index=False))
    out["strategies"] = strat_df.to_dict("records")

    # === 4. RT > DAM hours: characterize ===
    print("\n=== 4. RT > DAM hours per product (descriptive) ===")
    rt_gt_dam_summary = []
    for p in PRODS:
        sub = df[df[f"_dam_win_{p}"] == False].copy()  # RT >= DAM
        if len(sub) == 0:
            continue
        spike = sub[sub[f"RT_AS_MCPC_{p}"] - sub[f"AS_MCPC_{p}"] > 5]  # RT-DAM > $5
        rt_gt_dam_summary.append({
            "product": p,
            "n_rt_ge_dam": int(len(sub)),
            "n_rt_spike_5plus": int(len(spike)),
            "mean_rt_minus_dam_when_rt_wins": float(
                (sub[f"RT_AS_MCPC_{p}"] - sub[f"AS_MCPC_{p}"]).mean()
            ),
            "mean_load_fc_err_in_spike": float(spike["load_fc_err"].mean()) if len(spike) else None,
            "mean_wind_fc_err_in_spike": float(spike["wind_fc_err"].mean()) if len(spike) else None,
        })
    rgd = pd.DataFrame(rt_gt_dam_summary)
    print(rgd.round(2).to_string(index=False))
    out["rt_gt_dam_summary"] = rgd.to_dict("records")

    # === 5. Top-10 RT > DAM events per product (for case study) ===
    print("\n=== 5. Top RT > DAM spike hours (any product) ===")
    df["max_rt_minus_dam"] = pd.concat([
        df[f"RT_AS_MCPC_{p}"] - df[f"AS_MCPC_{p}"] for p in PRODS
    ], axis=1).max(axis=1)
    df["max_rt_minus_dam_product"] = pd.concat([
        df[f"RT_AS_MCPC_{p}"] - df[f"AS_MCPC_{p}"] for p in PRODS
    ], axis=1).idxmax(axis=1).map(lambda c: PRODS[c] if isinstance(c, int) else None)
    # Better: pick by name
    spread_cols = pd.DataFrame({p: df[f"RT_AS_MCPC_{p}"] - df[f"AS_MCPC_{p}"] for p in PRODS})
    df["max_spread"] = spread_cols.max(axis=1)
    df["max_spread_prod"] = spread_cols.idxmax(axis=1)

    top = df.nlargest(15, "max_spread")[
        ["date","he","max_spread_prod","max_spread",
         "DALMP_GKS_BESS_RN","RTLMP_GKS_BESS_RN",
         "load_fc_err","wind_fc_err"]
    ].copy()
    for p in PRODS:
        top[f"DAM_{p}"] = df.loc[top.index, f"AS_MCPC_{p}"]
        top[f"RT_{p}"] = df.loc[top.index, f"RT_AS_MCPC_{p}"]
    top["date"] = top["date"].astype(str)
    print(top[["date","he","max_spread_prod","max_spread","load_fc_err","wind_fc_err"]].round(1).to_string(index=False))
    out["top_rt_spikes"] = top.round(2).to_dict("records")

    # === 6. Correlation: per-product spread vs forecast errors ===
    print("\n=== 6. Pearson corr (RT - DAM per product vs features) ===")
    feat_cols = ["load_fc_err", "wind_fc_err", "RTLMP_GKS_BESS_RN", "DALMP_GKS_BESS_RN",
                 "RTLOAD", "WIND_RTI"]
    corr_table = {}
    for p in PRODS:
        gap = df[f"RT_AS_MCPC_{p}"] - df[f"AS_MCPC_{p}"]
        corr_table[p] = {f: float(df[[f]].assign(g=gap)[[f,"g"]].corr().iloc[0,1])
                          for f in feat_cols}
    print(pd.DataFrame(corr_table).round(3))
    out["corr_table"] = corr_table

    # === 7. Capture-weighted: what if BESS commits to highest-(DAM,RT) per HE? ===
    # Total revenue across all 5 products with single-product strategy
    print("\n=== 7. Total AS revenue if pick best (DAM or RT) per product per HE, 100 MW ===")
    total_optimal = sum(strat_df["optimal_revenue"])
    total_dam = sum(strat_df["always_dam_revenue"])
    total_rt  = sum(strat_df["always_rt_revenue"])
    print(f"  Sum optimal:   ${total_optimal:>12,.0f}")
    print(f"  Sum always-DAM: ${total_dam:>12,.0f}  ({total_dam/total_optimal:.1%})")
    print(f"  Sum always-RT:  ${total_rt:>12,.0f}  ({total_rt/total_optimal:.1%})")
    out["totals"] = {"optimal": total_optimal, "always_dam": total_dam, "always_rt": total_rt}

    # Save
    with open(DERIVED / "q2_q3_as_summary.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved -> q2_q3_as_summary.json")


if __name__ == "__main__":
    main()
