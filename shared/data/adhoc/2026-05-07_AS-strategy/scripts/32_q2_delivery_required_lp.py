"""
Q2 (정정 v4-B) — Delivery-required version of split LP

Same as 31_q2_dam_rt_split_lp.py BUT enforces s_DA = 0 (no shortfall).
즉 BESS는 DA에 commit한 물량을 RT에서 100% 이행할 수 있어야 함.
This represents a compliance-realistic operating policy:
  a_DA_p + a_RT_p ≤ cap_RT_p   (deliverable)
  a_DA_p + a_RT_p ≤ 100        (physical)

Same RT capability per product as v4-A:
  NSpin:  cap = soc/4
  RRS:    cap = min(100, 2×soc)
  ECRS:   cap = min(100, soc)
  REGUP:  cap = min(100, soc)
  REGDN:  cap = min(100, 200−soc)

Output:
  derived/q2_delivery_lp_per_day.parquet
  derived/q2_delivery_lp_summary.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC = Path(__file__).resolve().parents[1]
DERIVED = ADHOC / "derived"

POWER_MW = 100.0
ENERGY_MWH = 200.0
EFF = 0.922
SOC_INIT = 100.0
SOC_FINAL_MIN = 50.0
DURATION = {"REGUP":1.0, "REGDN":1.0, "RRS":0.5, "ECRS":1.0, "NSPIN":4.0}
PRODS_GEN = ["REGUP", "RRS", "ECRS", "NSPIN"]
PRODS_LOAD = ["REGDN"]
PRODS = PRODS_GEN + PRODS_LOAD


def solve_day(day_df: pd.DataFrame) -> dict:
    H = len(day_df)
    DA = day_df["DALMP_GKS_BESS_RN"].values
    RT = day_df["RTLMP_GKS_BESS_RN"].values
    DAM_MCPC = {p: day_df[f"AS_MCPC_{p}"].values    for p in PRODS}
    RT_MCPC  = {p: day_df[f"RT_AS_MCPC_{p}"].values for p in PRODS}

    # Variable layout (no s_DA — delivery is required)
    blocks = ["ds","ch","ds_da","ch_da"] \
             + [f"aDA_{p}" for p in PRODS] \
             + [f"aRT_{p}" for p in PRODS] \
             + ["soc"]
    block_idx = {n:i for i,n in enumerate(blocks)}
    N = len(blocks) * H
    def idx(n,h): return block_idx[n]*H + h

    c = np.zeros(N)
    for h in range(H):
        c[idx("ds_da",h)]   += DA[h]
        c[idx("ch_da",h)]   += -DA[h]
        c[idx("ds",h)]      += RT[h]
        c[idx("ds_da",h)]   += -RT[h]
        c[idx("ch",h)]      += -RT[h]
        c[idx("ch_da",h)]   += RT[h]
        for p in PRODS:
            c[idx(f"aDA_{p}",h)] += DAM_MCPC[p][h]
            c[idx(f"aRT_{p}",h)] += RT_MCPC[p][h]
    c_min = -c

    bounds = []
    for blk in blocks:
        for h in range(H):
            if blk == "soc":
                bounds.append((0.0, ENERGY_MWH))
            else:
                bounds.append((0.0, POWER_MW))

    A_ub_rows, b_ub = [], []
    A_eq_rows, b_eq = [], []
    for h in range(H):
        # ds_da ≤ ds, ch_da ≤ ch
        row = np.zeros(N); row[idx("ds_da",h)] = 1; row[idx("ds",h)] = -1
        A_ub_rows.append(row); b_ub.append(0)
        row = np.zeros(N); row[idx("ch_da",h)] = 1; row[idx("ch",h)] = -1
        A_ub_rows.append(row); b_ub.append(0)

        # SoC dynamics (eq)
        row = np.zeros(N)
        row[idx("soc",h)] = 1
        row[idx("ch",h)] = -EFF
        row[idx("ds",h)] = 1.0/EFF
        if h == 0:
            A_eq_rows.append(row); b_eq.append(SOC_INIT)
        else:
            row[idx("soc",h-1)] = -1
            A_eq_rows.append(row); b_eq.append(0.0)

        # AS per product: a_DA + a_RT ≤ 100, a_DA + a_RT ≤ mult × soc
        for p in PRODS:
            mult = 1.0 / DURATION[p]
            is_load = p in PRODS_LOAD

            # a_DA + a_RT ≤ 100
            row = np.zeros(N)
            row[idx(f"aDA_{p}",h)] = 1
            row[idx(f"aRT_{p}",h)] = 1
            A_ub_rows.append(row); b_ub.append(POWER_MW)

            # a_DA + a_RT ≤ mult × soc[h-1] (or mult × (200-soc) for REGDN)
            row = np.zeros(N)
            row[idx(f"aDA_{p}",h)] = 1
            row[idx(f"aRT_{p}",h)] = 1
            if h == 0:
                if is_load:
                    A_ub_rows.append(row); b_ub.append(mult * (ENERGY_MWH - SOC_INIT))
                else:
                    A_ub_rows.append(row); b_ub.append(mult * SOC_INIT)
            else:
                if is_load:
                    row[idx("soc",h-1)] = mult
                    A_ub_rows.append(row); b_ub.append(mult * ENERGY_MWH)
                else:
                    row[idx("soc",h-1)] = -mult
                    A_ub_rows.append(row); b_ub.append(0)

        # Physical gen capacity
        row = np.zeros(N)
        row[idx("ds",h)] = 1
        for p in PRODS_GEN:
            row[idx(f"aDA_{p}",h)] = 1
            row[idx(f"aRT_{p}",h)] = 1
        A_ub_rows.append(row); b_ub.append(POWER_MW)

        # Physical load capacity
        row = np.zeros(N)
        row[idx("ch",h)] = 1
        row[idx("aDA_REGDN",h)] = 1
        row[idx("aRT_REGDN",h)] = 1
        A_ub_rows.append(row); b_ub.append(POWER_MW)

    # Final SoC floor
    row = np.zeros(N); row[idx("soc",H-1)] = -1
    A_ub_rows.append(row); b_ub.append(-SOC_FINAL_MIN)

    A_ub = np.vstack(A_ub_rows); A_eq = np.vstack(A_eq_rows)
    b_ub = np.array(b_ub); b_eq = np.array(b_eq)

    res = linprog(c_min, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")
    if not res.success:
        return {"status":"fail","message":res.message}
    x = res.x
    def block(name): return x[block_idx[name]*H:(block_idx[name]+1)*H]

    out = pd.DataFrame({
        "datetime_ct": day_df["datetime_ct"].values,
        "he":          day_df["he"].values,
        "DA_LMP":      DA, "RT_LMP": RT,
        "ds": block("ds"), "ch": block("ch"),
        "ds_da": block("ds_da"), "ch_da": block("ch_da"),
        "soc": block("soc"),
    })
    for p in PRODS:
        out[f"aDA_{p}"] = block(f"aDA_{p}")
        out[f"aRT_{p}"] = block(f"aRT_{p}")
        out[f"DAM_MCPC_{p}"] = DAM_MCPC[p]
        out[f"RT_MCPC_{p}"]  = RT_MCPC[p]
        out[f"net_AS_{p}"] = (out[f"aDA_{p}"]*out[f"DAM_MCPC_{p}"]
                              + out[f"aRT_{p}"]*out[f"RT_MCPC_{p}"])
    out["energy_rev"] = (
        out["ds_da"]*out["DA_LMP"] - out["ch_da"]*out["DA_LMP"]
      + (out["ds"]-out["ds_da"])*out["RT_LMP"] - (out["ch"]-out["ch_da"])*out["RT_LMP"]
    )
    out["as_rev_total"] = sum(out[f"net_AS_{p}"] for p in PRODS)
    out["total_rev"] = out["energy_rev"] + out["as_rev_total"]
    return {"status":"ok", "df":out}


def main():
    df = pd.read_parquet(DERIVED / "master_hourly.parquet")
    print(f"Solving delivery-required LP for {df['date'].nunique()} days...")
    daily_dfs = []; failed = []
    needed = (["DALMP_GKS_BESS_RN","RTLMP_GKS_BESS_RN"]
              + [f"AS_MCPC_{p}" for p in PRODS]
              + [f"RT_AS_MCPC_{p}" for p in PRODS])
    for d, g in df.groupby("date"):
        g = g.sort_values("he").reset_index(drop=True)
        if g[needed].isna().any().any():
            failed.append((d,"missing")); continue
        sol = solve_day(g)
        if sol["status"] != "ok":
            failed.append((d, sol.get("message"))); continue
        sol["df"]["date"] = d
        daily_dfs.append(sol["df"])
    if failed: print(f"  failed: {len(failed)}")

    full = pd.concat(daily_dfs, ignore_index=True)
    full.to_parquet(DERIVED / "q2_delivery_lp_per_day.parquet", index=False)

    total_rev = float(full["total_rev"].sum())
    energy_rev = float(full["energy_rev"].sum())
    as_rev = float(full["as_rev_total"].sum())
    print(f"\n=== Delivery-required LP (s_DA forced = 0) ===")
    print(f"  Total: ${total_rev:>14,.0f}")
    print(f"    Energy: ${energy_rev:>14,.0f}")
    print(f"    AS:     ${as_rev:>14,.0f}")

    summary = {"total":total_rev, "energy":energy_rev, "as_total":as_rev}
    print(f"\n  {'Product':6s} {'a_DA':>8s} {'a_RT':>8s} {'DA share':>10s} "
          f"{'DA Rev':>14s} {'RT Rev':>14s} {'Net':>14s}")
    for p in PRODS:
        ada = float(full[f"aDA_{p}"].mean())
        art = float(full[f"aRT_{p}"].mean())
        dr = float((full[f"aDA_{p}"]*full[f"DAM_MCPC_{p}"]).sum())
        rr = float((full[f"aRT_{p}"]*full[f"RT_MCPC_{p}"]).sum())
        net = dr + rr
        share = ada/(ada+art) if (ada+art)>0 else None
        share_s = f"{share*100:.1f}%" if share is not None else "n/a"
        print(f"  {p:6s} {ada:>8.2f} {art:>8.2f} {share_s:>10s} ${dr:>13,.0f} ${rr:>13,.0f} ${net:>13,.0f}")
        summary[p] = {"a_DA_mean":ada, "a_RT_mean":art,
                      "DA_share": float(share) if share is not None else None,
                      "da_revenue":dr, "rt_revenue":rr, "net_revenue":net}

    # GKS comparison
    gks_total_as = float(df["GKS_DA_NS_Amt"].sum() + df["GKS_DA_ECRS_Amt"].sum()
                          + df["GKS_DA_RRS_Amt"].sum() + df["GKS_DA_Reg_Up_Amt"].sum()
                          + df["GKS_DA_Reg_Down_Amt"].sum())
    gks_energy = float(df["GKS_DA_Energy_Amt"].sum() + df["GKS_RT_Energy_Amt"].sum())
    gks_total = gks_total_as + gks_energy
    summary["gks_capture"] = gks_total / total_rev
    summary["gks_as_capture"] = gks_total_as / as_rev
    print(f"\n  GKS total: ${gks_total:,.0f}  ({gks_total/total_rev*100:.1f}% of delivery-LP)")
    print(f"  GKS AS:    ${gks_total_as:,.0f}  ({gks_total_as/as_rev*100:.1f}% of LP AS)")

    with open(DERIVED / "q2_delivery_lp_summary.json","w",encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSaved -> q2_delivery_lp_per_day.parquet, q2_delivery_lp_summary.json")


if __name__ == "__main__":
    main()
