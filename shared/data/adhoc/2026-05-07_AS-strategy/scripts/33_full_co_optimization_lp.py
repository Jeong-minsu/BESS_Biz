"""
v5 Full co-optimization LP — energy + AS, DA + RT commit (physical),
time-varying power & MWh cap from Smartbidder.

Per user (2026-05-11):
  - 100 MW / 200 MWh nameplate, but cap by Smartbidder /power-availability
    (hourly MW) and /soc-detailed soc_mwh_max (hourly MWh ceiling).
  - SoC trajectory is decision (not bound to GKS actual).
  - DA + RT both active. AS per product: a_DA (paid DAM_MCPC) and a_RT
    (paid RT_MCPC). Total physical position a_DA + a_RT ≤ deliverable cap
    (SoC capability) AND ≤ POWER_CAP[h]. No strategic over-commit (no
    virtual buyback arbitrage); LP chooses physical optimal split.
  - Energy DA commit (ds_da/ch_da) settled at DA_LMP, residual physical
    (ds - ds_da, ch - ch_da) at RT_LMP. ds, ds_da ≥ 0 separately.
    ds_da can exceed ds → DA short physical, bought back at RT_LMP.
  - Window: 2026-01-01 ~ 2026-05-10 (130 days), Storm Fern included.

Output:
  derived/q2_coopt_lp_per_day.parquet
  derived/q2_coopt_lp_summary.json
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

NAMEPLATE_MW = 100.0
NAMEPLATE_MWH = 200.0
EFF = 0.922                  # one-way (RTE ~85%)
SOC_INIT_FRAC = 0.5          # 50% of avail MWh at day start
SOC_FINAL_FRAC = 0.25        # ≥ 25% at day end
DURATION = {"REGUP":1.0, "REGDN":1.0, "RRS":0.5, "ECRS":1.0, "NSPIN":4.0}
PRODS_GEN  = ["REGUP", "RRS", "ECRS", "NSPIN"]
PRODS_LOAD = ["REGDN"]
PRODS = PRODS_GEN + PRODS_LOAD


def solve_day(day_df: pd.DataFrame) -> dict:
    H = len(day_df)
    DA = day_df["DALMP_GKS_BESS_RN"].values
    RT = day_df["RTLMP_GKS_BESS_RN"].values
    DAM_MCPC = {p: day_df[f"AS_MCPC_{p}"].values    for p in PRODS}
    RT_MCPC  = {p: day_df[f"RT_AS_MCPC_{p}"].values for p in PRODS}
    cap_ds   = day_df["avail_discharge_mw"].values
    cap_ch   = day_df["avail_charge_mw"].values
    cap_soc  = day_df["soc_mwh_max"].values

    # Variables (per hour, then stacked):
    # 0: ds_da, 1: ds, 2: ch_da, 3: ch, 4: soc
    # 5..9:   aDA_p   (5 products, DA AS commit ≥ 0)
    # 10..14: aRT_p   (5 products, RT AS commit ≥ 0; only positive — no
    #                  strategic over-commit / virtual buyback arbitrage)
    blocks = ["ds_da", "ds", "ch_da", "ch", "soc"] \
             + [f"aDA_{p}" for p in PRODS] \
             + [f"aRT_{p}" for p in PRODS]
    block_idx = {n: i for i, n in enumerate(blocks)}
    nblk = len(blocks)
    N = nblk * H
    def idx(name, h): return block_idx[name] * H + h

    # Objective (maximize): we pass -c to linprog
    c = np.zeros(N)
    for h in range(H):
        # Energy: ds_da*DA + (ds-ds_da)*RT - ch_da*DA - (ch-ch_da)*RT
        # = ds_da*(DA-RT) + ds*RT - ch_da*(DA-RT) - ch*RT
        c[idx("ds_da", h)] += (DA[h] - RT[h])
        c[idx("ds",    h)] += RT[h]
        c[idx("ch_da", h)] += -(DA[h] - RT[h])
        c[idx("ch",    h)] += -RT[h]
        # AS: a_DA*DAM + a_RT*RT
        for p in PRODS:
            c[idx(f"aDA_{p}", h)] += DAM_MCPC[p][h]
            c[idx(f"aRT_{p}", h)] += RT_MCPC[p][h]
    c_min = -c

    # Per-variable bounds (lb=0, ub varies)
    bounds: list[tuple[float, float]] = []
    for blk in blocks:
        for h in range(H):
            if blk in ("ds_da", "ds"):
                bounds.append((0.0, float(cap_ds[h])))
            elif blk in ("ch_da", "ch"):
                bounds.append((0.0, float(cap_ch[h])))
            elif blk == "soc":
                bounds.append((0.0, float(cap_soc[h])))
            else:
                # AS components individually capped at hourly avail (loose; tighter combined caps below)
                cap = cap_ds[h] if (blk.endswith(p) for p in PRODS_GEN) else cap_ch[h]
                # use max possible to keep simple
                bounds.append((0.0, float(NAMEPLATE_MW)))

    A_ub_rows, b_ub = [], []
    A_eq_rows, b_eq = [], []

    for h in range(H):
        # ---------- SoC dynamics (equality) ----------
        # soc[h] - EFF*ch[h] + ds[h]/EFF - soc[h-1] = 0
        # h=0: soc[0] = SOC_INIT + EFF*ch[0] - ds[0]/EFF
        row = np.zeros(N)
        row[idx("soc", h)] = 1.0
        row[idx("ch",  h)] = -EFF
        row[idx("ds",  h)] = 1.0 / EFF
        if h == 0:
            soc_init = SOC_INIT_FRAC * cap_soc[0]
            A_eq_rows.append(row); b_eq.append(soc_init)
        else:
            row[idx("soc", h - 1)] = -1.0
            A_eq_rows.append(row); b_eq.append(0.0)

        # ---------- Combined capacity (gen side, load side) ----------
        # Physical position uses a_total = aDA + aRT (both ≥ 0).
        # ds[h] + Σ_p_gen (aDA_p + aRT_p) ≤ cap_ds[h]
        row = np.zeros(N)
        row[idx("ds", h)] = 1.0
        for p in PRODS_GEN:
            row[idx(f"aDA_{p}", h)] = 1.0
            row[idx(f"aRT_{p}", h)] = 1.0
        A_ub_rows.append(row); b_ub.append(float(cap_ds[h]))

        # ch[h] + (aDA_REGDN + aRT_REGDN) ≤ cap_ch[h]
        row = np.zeros(N)
        row[idx("ch", h)] = 1.0
        row[idx(f"aDA_REGDN", h)] = 1.0
        row[idx(f"aRT_REGDN", h)] = 1.0
        A_ub_rows.append(row); b_ub.append(float(cap_ch[h]))

        # ---------- Per-product effective AS deliverability ----------
        # a_total_p = aDA_p + aRT_p
        # a_total_p ≤ mult × soc[h-1]                 (gen products)
        # a_total_p ≤ mult × (cap_soc[h] - soc[h-1])  (load product REGDN)
        for p in PRODS:
            mult = 1.0 / DURATION[p]
            is_load = (p in PRODS_LOAD)

            row = np.zeros(N)
            row[idx(f"aDA_{p}", h)] = 1.0
            row[idx(f"aRT_{p}", h)] = 1.0
            if h == 0:
                soc_prev = SOC_INIT_FRAC * cap_soc[0]
                rhs = mult * (cap_soc[h] - soc_prev) if is_load else mult * soc_prev
                A_ub_rows.append(row); b_ub.append(rhs)
            else:
                if is_load:
                    row[idx("soc", h - 1)] = mult
                    A_ub_rows.append(row); b_ub.append(mult * float(cap_soc[h]))
                else:
                    row[idx("soc", h - 1)] = -mult
                    A_ub_rows.append(row); b_ub.append(0.0)

            # a_total_p ≤ cap_ds[h] or cap_ch[h]  (per-side physical cap)
            row = np.zeros(N)
            row[idx(f"aDA_{p}", h)] = 1.0
            row[idx(f"aRT_{p}", h)] = 1.0
            A_ub_rows.append(row)
            b_ub.append(float(cap_ch[h] if is_load else cap_ds[h]))

        # ---------- DA commits bounded by physical AS-aware capacity ----------
        # ds_da[h] + Σ_p_gen aDA_p ≤ cap_ds[h]
        row = np.zeros(N)
        row[idx("ds_da", h)] = 1.0
        for p in PRODS_GEN:
            row[idx(f"aDA_{p}", h)] = 1.0
        A_ub_rows.append(row); b_ub.append(float(cap_ds[h]))
        # ch_da[h] + aDA_REGDN ≤ cap_ch[h]
        row = np.zeros(N)
        row[idx("ch_da", h)] = 1.0
        row[idx(f"aDA_REGDN", h)] = 1.0
        A_ub_rows.append(row); b_ub.append(float(cap_ch[h]))

    # ---------- Terminal SoC floor (skip if EOD MWh cap is ~0) ----------
    if cap_soc[H - 1] > 1.0:
        row = np.zeros(N); row[idx("soc", H - 1)] = -1.0
        A_ub_rows.append(row); b_ub.append(-SOC_FINAL_FRAC * cap_soc[H - 1])

    A_ub = np.vstack(A_ub_rows); A_eq = np.vstack(A_eq_rows)
    b_ub = np.array(b_ub);       b_eq = np.array(b_eq)

    res = linprog(c_min, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")
    if not res.success:
        return {"status": "fail", "message": res.message}
    x = res.x
    def block(name): return x[block_idx[name] * H:(block_idx[name] + 1) * H]

    out = pd.DataFrame({
        "datetime_ct": day_df["datetime_ct"].values,
        "he": day_df["he"].values,
        "DA_LMP": DA, "RT_LMP": RT,
        "cap_ds": cap_ds, "cap_ch": cap_ch, "cap_soc": cap_soc,
        "ds_da": block("ds_da"), "ds": block("ds"),
        "ch_da": block("ch_da"), "ch": block("ch"),
        "soc": block("soc"),
    })
    for p in PRODS:
        out[f"aDA_{p}"] = block(f"aDA_{p}")
        out[f"aRT_{p}"] = block(f"aRT_{p}")
        out[f"aEff_{p}"] = out[f"aDA_{p}"] + out[f"aRT_{p}"]
        out[f"DAM_MCPC_{p}"] = DAM_MCPC[p]
        out[f"RT_MCPC_{p}"]  = RT_MCPC[p]
        out[f"net_AS_{p}"] = (out[f"aDA_{p}"] * out[f"DAM_MCPC_{p}"]
                              + out[f"aRT_{p}"] * out[f"RT_MCPC_{p}"])

    out["energy_rev"] = (
        out["ds_da"] * out["DA_LMP"]
        + (out["ds"] - out["ds_da"]) * out["RT_LMP"]
        - out["ch_da"] * out["DA_LMP"]
        - (out["ch"] - out["ch_da"]) * out["RT_LMP"]
    )
    out["as_rev_total"] = sum(out[f"net_AS_{p}"] for p in PRODS)
    out["total_rev"] = out["energy_rev"] + out["as_rev_total"]
    return {"status": "ok", "df": out}


def main():
    df = pd.read_parquet(DERIVED / "master_hourly.parquet")
    print(f"v5 Full co-optimization LP: {df['date'].nunique()} days, {len(df)} hours")

    needed = (["DALMP_GKS_BESS_RN", "RTLMP_GKS_BESS_RN",
               "avail_discharge_mw", "avail_charge_mw", "soc_mwh_max"]
              + [f"AS_MCPC_{p}" for p in PRODS]
              + [f"RT_AS_MCPC_{p}" for p in PRODS])
    miss = [c for c in needed if c not in df.columns]
    if miss:
        sys.exit(f"missing columns: {miss}")

    daily_dfs, failed, outage_days = [], [], []
    for d, g in df.groupby("date"):
        g = g.sort_values("he").reset_index(drop=True)
        if g[needed].isna().any().any():
            failed.append((d, "missing data"))
            continue
        # Skip full-outage days (max discharge = 0 across all hours)
        if g["avail_discharge_mw"].max() <= 0.5 and g["avail_charge_mw"].max() <= 0.5:
            outage_days.append(d)
            zero_df = pd.DataFrame({
                "datetime_ct": g["datetime_ct"].values,
                "he": g["he"].values,
                "DA_LMP": g["DALMP_GKS_BESS_RN"].values,
                "RT_LMP": g["RTLMP_GKS_BESS_RN"].values,
                "cap_ds": g["avail_discharge_mw"].values,
                "cap_ch": g["avail_charge_mw"].values,
                "cap_soc": g["soc_mwh_max"].values,
                "ds_da": 0.0, "ds": 0.0, "ch_da": 0.0, "ch": 0.0, "soc": 0.0,
                "energy_rev": 0.0, "as_rev_total": 0.0, "total_rev": 0.0,
                "date": d,
            })
            for p in PRODS:
                zero_df[f"aDA_{p}"] = 0.0
                zero_df[f"aRT_{p}"] = 0.0
                zero_df[f"aEff_{p}"] = 0.0
                zero_df[f"DAM_MCPC_{p}"] = g[f"AS_MCPC_{p}"].values
                zero_df[f"RT_MCPC_{p}"]  = g[f"RT_AS_MCPC_{p}"].values
                zero_df[f"net_AS_{p}"]   = 0.0
            daily_dfs.append(zero_df)
            continue
        sol = solve_day(g)
        if sol["status"] != "ok":
            failed.append((d, sol.get("message", "?")))
            continue
        sol["df"]["date"] = d
        daily_dfs.append(sol["df"])
    if outage_days:
        print(f"  full-outage days (zero rev): {len(outage_days)} ({outage_days[:3]} ...)")
    if failed:
        print(f"  failed: {len(failed)} days  (first 3: {failed[:3]})")

    full = pd.concat(daily_dfs, ignore_index=True)
    out_path = DERIVED / "q2_coopt_lp_per_day.parquet"
    full.to_parquet(out_path, index=False)
    print(f"  saved -> {out_path.name}  ({len(full)} rows)")

    total_rev   = float(full["total_rev"].sum())
    energy_rev  = float(full["energy_rev"].sum())
    as_rev      = float(full["as_rev_total"].sum())
    print(f"\n=== Co-optimization LP (DA+RT both, full bidirectional) ===")
    print(f"  Total: ${total_rev:>14,.0f}")
    print(f"    Energy: ${energy_rev:>14,.0f}")
    print(f"    AS:     ${as_rev:>14,.0f}")

    summary: dict = {"total": total_rev, "energy": energy_rev, "as_total": as_rev,
                     "days": int(full["date"].nunique()),
                     "hours": int(len(full))}
    print(f"\n  {'Product':6s} {'a_DA':>8s} {'a_RT':>8s} {'a_Eff':>8s} "
          f"{'DA share':>10s} {'DA Rev':>14s} {'RT Rev':>14s} {'Total':>14s}")
    for p in PRODS:
        ada  = float(full[f"aDA_{p}"].mean())
        art  = float(full[f"aRT_{p}"].mean())
        aeff = float(full[f"aEff_{p}"].mean())
        dr   = float((full[f"aDA_{p}"] * full[f"DAM_MCPC_{p}"]).sum())
        rr   = float((full[f"aRT_{p}"] * full[f"RT_MCPC_{p}"]).sum())
        net  = dr + rr
        share = ada / aeff if aeff > 0 else None
        share_s = f"{share*100:.1f}%" if share is not None else "n/a"
        print(f"  {p:6s} {ada:>8.2f} {art:>8.2f} {aeff:>8.2f} "
              f"{share_s:>10s} ${dr:>13,.0f} ${rr:>13,.0f} ${net:>13,.0f}")
        summary[p] = {"a_DA_mean": ada, "a_RT_mean": art, "a_eff_mean": aeff,
                      "DA_share": float(share) if share is not None else None,
                      "da_revenue": dr, "rt_revenue": rr, "net_revenue": net}

    # ----- HE × product mean for the dashboard -----
    he_alloc = full.groupby("he").agg(
        **{f"a_eff_{p}": (f"aEff_{p}", "mean") for p in PRODS},
        **{f"a_DA_{p}":  (f"aDA_{p}",  "mean") for p in PRODS},
        **{f"a_RT_{p}":  (f"aRT_{p}",  "mean") for p in PRODS},
    ).reset_index()
    he_alloc.to_parquet(DERIVED / "q2_coopt_lp_he_alloc.parquet", index=False)

    with open(DERIVED / "q2_coopt_lp_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n  summary -> q2_coopt_lp_summary.json")


if __name__ == "__main__":
    main()
