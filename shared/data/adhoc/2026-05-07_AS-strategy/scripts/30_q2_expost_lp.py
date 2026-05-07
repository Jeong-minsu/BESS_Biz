"""
Q1 + Q2 — Ex-post optimal BESS dispatch (daily LP)

For each day, solve a 24-hour LP that jointly optimizes:
- Physical charge/discharge (subject to 100 MW power, 200 MWh energy, 85% rt eff)
- DA vs RT split for energy
- AS allocation across 5 products (RegUp, RegDn, RRS, ECRS, NSPIN)
- SOC dynamics + AS reservation headroom

Outputs the optimal stack and compares to GKS actual.

Variables per day (24 HE each):
   ds[h]    in [0, 100]   physical discharge MW
   ch[h]    in [0, 100]   physical charge MW
   ds_da[h] in [0, ds[h]] DA-sold portion of discharge
   ch_da[h] in [0, ch[h]] DA-bought portion of charge
   a_p[h]   in [0, 100]   AS award MW for product p in 5 products
   soc[h]   in [0, 200]   end-of-hour SoC

Constraints:
   ds[h] + ch[h] + a_RU[h] + a_RRS[h] + a_ECRS[h] + a_NSPIN[h] <= 100   (gen capacity)
   ch[h] + a_RD[h] <= 100                                                (load capacity for RegDn)
   soc[h] = soc[h-1] + eff*ch[h] - ds[h]/eff
   AS energy reservation (per user 2026-05-07 update: DAM AS는 SoC telemetry 검사 없음 →
   ERCOT는 RT only에서 SoC 기반 telemetry로 award 제한. 본 LP는 DAM AS commit만 모델링하므로
   SoC reservation 제약을 완전히 제거. RT AS는 별도 모델링 필요 (현재 미구현).)
   ds_da <= ds, ch_da <= ch
   soc[0] = 100 (init), soc[24] >= 50 (terminal — avoid emptying)

Objective:
   max sum_h [
       ds_da[h]*DA_LMP[h]  - ch_da[h]*DA_LMP[h]            (DA energy)
     + (ds[h]-ds_da[h])*RT_LMP[h] - (ch[h]-ch_da[h])*RT_LMP[h]  (RT energy)
     + a_RU[h]*MCPC_REGUP[h] + a_RD[h]*MCPC_REGDN[h]
     + a_RRS[h]*MCPC_RRS[h] + a_ECRS[h]*MCPC_ECRS[h] + a_NSPIN[h]*MCPC_NSPIN[h]
   ]

Output:
   derived/q2_lp_per_day.parquet     (HE-level optimal stack)
   derived/q2_lp_summary.json        (totals, comparison to GKS actual)
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

ADHOC_ROOT = Path(__file__).resolve().parents[1]
DERIVED = ADHOC_ROOT / "derived"

POWER_MW   = 100.0
ENERGY_MWH = 200.0
EFF        = 0.922  # one-way efficiency, sqrt(0.85)
SOC_INIT   = 100.0
SOC_FINAL_MIN = 50.0
AS_PRODS   = ["REGUP", "REGDN", "RRS", "ECRS", "NSPIN"]


def solve_day(day_df: pd.DataFrame) -> dict:
    """Solve LP for one operating day. day_df: 24 rows in HE order."""
    H = len(day_df)
    if H not in (23, 24, 25):  # 23 = spring DST, 25 = fall DST
        raise ValueError(f"Bad HE count: {H}")

    DA = day_df["DALMP_GKS_BESS_RN"].values
    RT = day_df["RTLMP_GKS_BESS_RN"].values
    MC = {p: day_df[f"AS_MCPC_{p}"].values for p in AS_PRODS}

    # Variable layout (all H-vectors stacked):
    # 0..H-1   ds[h]
    # H..2H-1  ch[h]
    # 2H..3H-1 ds_da[h]
    # 3H..4H-1 ch_da[h]
    # 4H..5H-1 a_RU[h]
    # 5H..6H-1 a_RD[h]
    # 6H..7H-1 a_RRS[h]
    # 7H..8H-1 a_ECRS[h]
    # 8H..9H-1 a_NSPIN[h]
    # 9H..10H-1 soc[h]   (end-of-hour SoC; soc[H-1] is final)
    n_blocks = 10
    N = n_blocks * H

    def idx(block: int, h: int) -> int:
        return block * H + h

    DS, CH, DSDA, CHDA, ARU, ARD, ARRS, AECRS, ANSPIN, SOC = range(n_blocks)

    # Objective: maximize -> minimize negative
    c = np.zeros(N)
    for h in range(H):
        c[idx(DSDA, h)]   = DA[h]                # DA energy revenue
        c[idx(CHDA, h)]   = -DA[h]               # DA charge cost
        c[idx(DS, h)]    +=  RT[h]               # discharge gross at RT (we'll subtract DSDA*RT)
        c[idx(DSDA, h)]  += -RT[h]               # net DA discharge: DSDA*(DA-RT) plus DS*RT
        c[idx(CH, h)]    += -RT[h]
        c[idx(CHDA, h)]  +=  RT[h]               # net DA charge: -CHDA*(DA-RT) - CH*RT
        c[idx(ARU, h)]    = MC["REGUP"][h]
        c[idx(ARD, h)]    = MC["REGDN"][h]
        c[idx(ARRS, h)]   = MC["RRS"][h]
        c[idx(AECRS, h)]  = MC["ECRS"][h]
        c[idx(ANSPIN, h)] = MC["NSPIN"][h]
    c_min = -c

    # Bounds
    bounds = [(0, None)] * N
    for h in range(H):
        bounds[idx(DS, h)]      = (0.0, POWER_MW)
        bounds[idx(CH, h)]      = (0.0, POWER_MW)
        bounds[idx(DSDA, h)]    = (0.0, POWER_MW)
        bounds[idx(CHDA, h)]    = (0.0, POWER_MW)
        for blk in (ARU, ARD, ARRS, AECRS, ANSPIN):
            bounds[idx(blk, h)] = (0.0, POWER_MW)
        bounds[idx(SOC, h)]     = (0.0, ENERGY_MWH)
    # Final SoC floor
    # Use linear constraint instead of bound modification for safety:
    # already bounded [0, 200]; add A_ub row enforcing -SOC[H-1] <= -SOC_FINAL_MIN

    A_ub_rows = []
    b_ub = []
    A_eq_rows = []
    b_eq = []

    for h in range(H):
        # Gen capacity: ds + a_RU + a_RRS + a_ECRS + a_NSPIN <= 100
        row = np.zeros(N)
        row[idx(DS, h)]      = 1
        row[idx(ARU, h)]     = 1
        row[idx(ARRS, h)]    = 1
        row[idx(AECRS, h)]   = 1
        row[idx(ANSPIN, h)]  = 1
        A_ub_rows.append(row); b_ub.append(POWER_MW)

        # Load capacity: ch + a_RD <= 100
        row = np.zeros(N)
        row[idx(CH, h)]   = 1
        row[idx(ARD, h)]  = 1
        A_ub_rows.append(row); b_ub.append(POWER_MW)

        # ds_da <= ds  ->  ds_da - ds <= 0
        row = np.zeros(N)
        row[idx(DSDA, h)] = 1
        row[idx(DS, h)]   = -1
        A_ub_rows.append(row); b_ub.append(0)

        # ch_da <= ch
        row = np.zeros(N)
        row[idx(CHDA, h)] = 1
        row[idx(CH, h)]   = -1
        A_ub_rows.append(row); b_ub.append(0)

        # SoC dynamics (equality):
        # soc[h] = soc[h-1] + eff*ch[h] - ds[h]/eff
        # soc[h] - soc[h-1] - eff*ch[h] + (1/eff)*ds[h] = 0
        row = np.zeros(N)
        row[idx(SOC, h)] = 1
        if h == 0:
            # soc[0] - SOC_INIT - eff*ch[0] + (1/eff)*ds[0] = 0
            row[idx(CH, h)] = -EFF
            row[idx(DS, h)] = 1.0/EFF
            A_eq_rows.append(row); b_eq.append(SOC_INIT)
        else:
            row[idx(SOC, h-1)] = -1
            row[idx(CH, h)] = -EFF
            row[idx(DS, h)] = 1.0/EFF
            A_eq_rows.append(row); b_eq.append(0.0)

        # AS reservation: DAM AS commit은 ERCOT가 SoC telemetry를 검사하지 않음
        # (RT only에서 검사 → RT AS award가 SoC에 의해 제한됨).
        # 본 LP는 DAM AS만 모델링하므로 SoC reservation 제약은 적용하지 않음.
        # 단 capacity constraints (gen/load side)는 그대로 유지 — 동시 commit 한도는 100 MW.

    # Final SoC floor: -soc[H-1] <= -SOC_FINAL_MIN
    row = np.zeros(N)
    row[idx(SOC, H-1)] = -1
    A_ub_rows.append(row); b_ub.append(-SOC_FINAL_MIN)

    A_ub = np.vstack(A_ub_rows)
    A_eq = np.vstack(A_eq_rows)
    b_ub = np.array(b_ub)
    b_eq = np.array(b_eq)

    res = linprog(c_min, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds,
                  method="highs")
    if not res.success:
        return {"status": "fail", "message": res.message}

    x = res.x
    block = lambda blk: x[blk*H:(blk+1)*H]
    out = pd.DataFrame({
        "datetime_ct":  day_df["datetime_ct"].values,
        "he":           day_df["he"].values,
        "DA_LMP":       DA,
        "RT_LMP":       RT,
        "ds":           block(DS),
        "ch":           block(CH),
        "ds_da":        block(DSDA),
        "ch_da":        block(CHDA),
        "ds_rt":        block(DS) - block(DSDA),
        "ch_rt":        block(CH) - block(CHDA),
        "a_REGUP":      block(ARU),
        "a_REGDN":      block(ARD),
        "a_RRS":        block(ARRS),
        "a_ECRS":       block(AECRS),
        "a_NSPIN":      block(ANSPIN),
        "soc":          block(SOC),
    })
    out["energy_rev"] = (
        out["ds_da"]*out["DA_LMP"] - out["ch_da"]*out["DA_LMP"]
      + out["ds_rt"]*out["RT_LMP"] - out["ch_rt"]*out["RT_LMP"]
    )
    for p in AS_PRODS:
        out[f"as_rev_{p}"] = out[f"a_{p}"] * day_df[f"AS_MCPC_{p}"].values
    out["as_rev_total"]  = sum(out[f"as_rev_{p}"] for p in AS_PRODS)
    out["total_rev"]     = out["energy_rev"] + out["as_rev_total"]
    return {"status": "ok", "df": out, "obj": -res.fun}


def main() -> None:
    df = pd.read_parquet(DERIVED / "master_hourly.parquet")
    print(f"Solving LP per day for {df['date'].nunique()} days...")
    daily_dfs = []
    daily_summary = []
    failed = []
    for d, g in df.groupby("date"):
        g = g.sort_values("he").reset_index(drop=True)
        if g[["DALMP_GKS_BESS_RN","RTLMP_GKS_BESS_RN"]+[f"AS_MCPC_{p}" for p in AS_PRODS]].isna().any().any():
            failed.append((d, "missing inputs"))
            continue
        sol = solve_day(g)
        if sol["status"] != "ok":
            failed.append((d, sol.get("message", "fail")))
            continue
        sol["df"]["date"] = d
        daily_dfs.append(sol["df"])
        daily_summary.append({
            "date": str(d),
            "total_rev": float(sol["df"]["total_rev"].sum()),
            "energy_rev": float(sol["df"]["energy_rev"].sum()),
            "as_rev_total": float(sol["df"]["as_rev_total"].sum()),
            **{f"as_rev_{p}": float(sol["df"][f"as_rev_{p}"].sum()) for p in AS_PRODS},
        })

    if failed:
        print(f"  FAILED days: {len(failed)} -> {failed[:5]}")

    full = pd.concat(daily_dfs, ignore_index=True)
    full.to_parquet(DERIVED / "q2_lp_per_day.parquet", index=False)

    daily_df = pd.DataFrame(daily_summary)
    expost = {
        "n_days":          int(len(daily_df)),
        "expost_total":    float(daily_df["total_rev"].sum()),
        "expost_energy":   float(daily_df["energy_rev"].sum()),
        "expost_as_total": float(daily_df["as_rev_total"].sum()),
        **{f"expost_as_{p}": float(daily_df[f"as_rev_{p}"].sum()) for p in AS_PRODS},
    }

    # Compare with GKS actual
    gks_da_energy = float(df["GKS_DA_Energy_Amt"].sum())
    gks_rt_energy = float(df["GKS_RT_Energy_Amt"].sum())
    gks_energy_total = gks_da_energy + gks_rt_energy
    gks_as = {
        "REGUP":  float(df["GKS_DA_Reg_Up_Amt"].sum()),
        "REGDN":  float(df["GKS_DA_Reg_Down_Amt"].sum()),
        "RRS":    float(df["GKS_DA_RRS_Amt"].sum()),
        "ECRS":   float(df["GKS_DA_ECRS_Amt"].sum()),
        "NSPIN":  float(df["GKS_DA_NS_Amt"].sum()),
    }
    gks_as_total = sum(gks_as.values())
    gks_total = gks_energy_total + gks_as_total

    actual = {
        "actual_total":      gks_total,
        "actual_da_energy":  gks_da_energy,
        "actual_rt_energy":  gks_rt_energy,
        "actual_as_total":   gks_as_total,
        **{f"actual_as_{p}": v for p, v in gks_as.items()},
    }

    gap = {
        "gap_total":      expost["expost_total"]    - gks_total,
        "gap_energy":     expost["expost_energy"]   - gks_energy_total,
        "gap_as":         expost["expost_as_total"] - gks_as_total,
        "gks_pct_of_expost":     gks_total / expost["expost_total"] if expost["expost_total"] else None,
        "gks_energy_pct_expost": gks_energy_total / expost["expost_energy"] if expost["expost_energy"] else None,
        "gks_as_pct_expost":     gks_as_total / expost["expost_as_total"] if expost["expost_as_total"] else None,
    }

    summary = {**expost, **actual, **gap}

    print(f"\n=== Ex-post optimal (LP) ===")
    print(f"  Total revenue: ${expost['expost_total']:>14,.0f}")
    print(f"    Energy:      ${expost['expost_energy']:>14,.0f}")
    print(f"    AS total:    ${expost['expost_as_total']:>14,.0f}")
    for p in AS_PRODS:
        print(f"      {p:6s}:    ${expost[f'expost_as_{p}']:>14,.0f}")

    print(f"\n=== GKS actual ===")
    print(f"  Total revenue: ${gks_total:>14,.0f}")
    print(f"    DA energy:   ${gks_da_energy:>14,.0f}")
    print(f"    RT energy:   ${gks_rt_energy:>14,.0f}")
    print(f"    AS total:    ${gks_as_total:>14,.0f}")
    for p, v in gks_as.items():
        print(f"      {p:6s}:    ${v:>14,.0f}")

    print(f"\n=== Gap (ex-post - actual) ===")
    print(f"  Total gap:   ${gap['gap_total']:>14,.0f}    GKS captured {gap['gks_pct_of_expost']:.1%} of optimum")
    print(f"  Energy gap:  ${gap['gap_energy']:>14,.0f}   GKS captured {gap['gks_energy_pct_expost']:.1%}")
    print(f"  AS gap:      ${gap['gap_as']:>14,.0f}      GKS captured {gap['gks_as_pct_expost']:.1%}")

    daily_df.to_parquet(DERIVED / "q2_daily_summary.parquet", index=False)
    with open(DERIVED / "q2_lp_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSaved -> q2_lp_per_day.parquet, q2_daily_summary.parquet, q2_lp_summary.json")


if __name__ == "__main__":
    main()
