"""One-off P&L aggregation for GKS flowday 2026-05-03.

Reads Tenaska Battery-Settlement-Details rows, pivots to (HE_CPT × datapoint),
prints daily totals + hourly stack for the report.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz")
SRC = ROOT / "shared/data/pnl/gks/hourly/2026-05-03_energy_as_detail.json"
HSL_SRC = ROOT / "shared/data/pnl/gks/hourly/2026-05-03_hsl.json"

CPT = timezone(timedelta(hours=-5))  # ERCOT CPT (CST, no DST in this dataset assumption)


def utc_to_he_cpt(iso_end: str) -> int:
    """interval_end_utc -> HE in CPT (1..24)."""
    dt_utc = datetime.fromisoformat(iso_end.replace("Z", "+00:00"))
    dt_cpt = dt_utc.astimezone(CPT)
    he = dt_cpt.hour
    return 24 if he == 0 else he


def main():
    rows = json.loads(SRC.read_text())
    # pivot: he -> datapoint -> sum value
    by_he: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        he = utc_to_he_cpt(r["interval_end_utc"])
        by_he[he][r["datapoint"]] += float(r["value"] or 0.0)

    # daily totals
    totals: dict[str, float] = defaultdict(float)
    for he, dps in by_he.items():
        for k, v in dps.items():
            totals[k] += v

    # ---------- DAILY TOTALS ----------
    print("\n=== DAILY TOTALS ($) ===")
    cats = {
        "DA Energy": ["DA_Energy_Amt"],
        "RT Energy": ["RT_Energy_Amt"],
        "RT Reliability Deploy Imb": ["RT_Reliability_Deployment_Imbalance_Amt"],
        "RT Ancillary Imbalance": ["RT_Ancillary_Imbalance_Amt"],
        "DA RegUp": ["DA_Reg_Up_Amt"],
        "DA RegDown": ["DA_Reg_Down_Amt"],
        "DA RRS": ["DA_RRS_Amt"],
        "DA NonSpin": ["DA_NS_Amt"],
        "DA ECRS": ["DA_ECRS_Amt"],
        "RT RegUp": ["RT_Reg_Up_Amt"],
        "RT RegDown": ["RT_Reg_Down_Amt"],
        "RT RRS": ["RT_RRS_Amt"],
        "RT NonSpin": ["RT_NS_Amt"],
        "RT ECRS": ["RT_ECRS_Amt"],
        "BP Deviation": ["BP_Dev_Amt"],
    }
    sums: dict[str, float] = {}
    for label, keys in cats.items():
        sums[label] = sum(totals.get(k, 0.0) for k in keys)
        print(f"  {label:30s}  {sums[label]:>14,.2f}")

    da_energy = sums["DA Energy"]
    rt_energy = sums["RT Energy"] + sums["RT Reliability Deploy Imb"] + sums["RT Ancillary Imbalance"]
    da_as = sums["DA RegUp"] + sums["DA RegDown"] + sums["DA RRS"] + sums["DA NonSpin"] + sums["DA ECRS"]
    rt_as = sums["RT RegUp"] + sums["RT RegDown"] + sums["RT RRS"] + sums["RT NonSpin"] + sums["RT ECRS"]
    dev = sums["BP Deviation"]
    net = da_energy + rt_energy + da_as + rt_as + dev

    print(f"\n  DA Energy total:  {da_energy:>14,.2f}")
    print(f"  RT Energy total:  {rt_energy:>14,.2f}  (incl. imbalance)")
    print(f"  DA AS total:      {da_as:>14,.2f}")
    print(f"  RT AS total:      {rt_as:>14,.2f}")
    print(f"  Deviation:        {dev:>14,.2f}")
    print(f"  NET:              {net:>14,.2f}")

    # ---------- MWh totals ----------
    da_sales = totals.get("DA_Sales_Qty", 0.0)
    da_purch = totals.get("DA_Purchases_Qty", 0.0)
    rt_gen = totals.get("RT_Generation_Qty", 0.0)
    rt_con = totals.get("RT_Consumption_Qty", 0.0)
    print(f"\n  DA Sales MWh:     {da_sales:>14,.3f}")
    print(f"  DA Purch MWh:     {da_purch:>14,.3f}")
    print(f"  RT Gen MWh:       {rt_gen:>14,.3f}")
    print(f"  RT Con MWh:       {rt_con:>14,.3f}")

    # ---------- DASPP / RTSPP avg ----------
    daspp_vals = [by_he[h].get("DASPP", 0.0) for h in range(1, 25)]
    rtspp_vals = [by_he[h].get("RTSPP_Avg", 0.0) for h in range(1, 25)]
    daspp_avg = sum(daspp_vals) / 24
    rtspp_avg = sum(rtspp_vals) / 24
    print(f"\n  DASPP avg ($/MWh):  {daspp_avg:>10,.2f}")
    print(f"  RTSPP avg ($/MWh):  {rtspp_avg:>10,.2f}")

    # ---------- Hourly stack ----------
    print("\n=== HOURLY STACK ($) ===")
    print("HE | DA E | RT E | RegUp | RegDn | RRS | NS | ECRS | Dev | Total | DASPP | RTSPP | Gen | Con")
    hourly_rows = []
    for h in range(1, 25):
        d = by_he[h]
        da_e = d.get("DA_Energy_Amt", 0.0)
        rt_e = (
            d.get("RT_Energy_Amt", 0.0)
            + d.get("RT_Reliability_Deployment_Imbalance_Amt", 0.0)
            + d.get("RT_Ancillary_Imbalance_Amt", 0.0)
        )
        regup = d.get("DA_Reg_Up_Amt", 0.0) + d.get("RT_Reg_Up_Amt", 0.0)
        regdn = d.get("DA_Reg_Down_Amt", 0.0) + d.get("RT_Reg_Down_Amt", 0.0)
        rrs = d.get("DA_RRS_Amt", 0.0) + d.get("RT_RRS_Amt", 0.0)
        ns = d.get("DA_NS_Amt", 0.0) + d.get("RT_NS_Amt", 0.0)
        ecrs = d.get("DA_ECRS_Amt", 0.0) + d.get("RT_ECRS_Amt", 0.0)
        dev_h = d.get("BP_Dev_Amt", 0.0)
        tot = da_e + rt_e + regup + regdn + rrs + ns + ecrs + dev_h
        daspp = d.get("DASPP", 0.0)
        rtspp = d.get("RTSPP_Avg", 0.0)
        gen = d.get("RT_Generation_Qty", 0.0)
        con = d.get("RT_Consumption_Qty", 0.0)
        hourly_rows.append(
            (h, da_e, rt_e, regup, regdn, rrs, ns, ecrs, dev_h, tot, daspp, rtspp, gen, con)
        )
        print(
            f"{h:2d} | {da_e:8.2f} | {rt_e:8.2f} | {regup:7.2f} | {regdn:7.2f} | {rrs:7.2f} | "
            f"{ns:6.2f} | {ecrs:7.2f} | {dev_h:7.2f} | {tot:9.2f} | {daspp:6.2f} | {rtspp:6.2f} | "
            f"{gen:6.2f} | {con:6.2f}"
        )

    # ---------- Cleared MW totals (AS mix) ----------
    as_mw = {}
    for prod in ["Reg_Up", "Reg_Down", "RRS", "NS", "ECRS"]:
        gen_q = totals.get(f"Gen_{prod}_Qty", 0.0)
        clr_q = totals.get(f"CLR_{prod}_Qty", 0.0)
        as_mw[prod] = (gen_q, clr_q, gen_q + clr_q)
    print("\n=== AS Cleared MW (daily sum, hourly cleared awards summed across 24 HE) ===")
    for prod, (g, c, t) in as_mw.items():
        print(f"  {prod:10s}  Gen={g:8.2f} MW  CLR={c:8.2f} MW  Total={t:8.2f} MW")

    # ---------- HSL summary ----------
    hsl_rows = json.loads(HSL_SRC.read_text())
    hsl_vals = [float(r["value"]) for r in hsl_rows if r.get("datapoint") == "HSL" and r.get("value") is not None]
    if hsl_vals:
        print(f"\n  HSL: n={len(hsl_vals)}, mean={sum(hsl_vals)/len(hsl_vals):.2f}, max={max(hsl_vals):.2f}, min={min(hsl_vals):.2f}")
    # peak hour
    peak = max(hourly_rows, key=lambda r: r[9])
    print(f"\n  Peak revenue hour: HE{peak[0]}  total=${peak[9]:,.2f}")

    # ---------- emit JSON for downstream ----------
    out = {
        "flowday": "2026-05-03",
        "totals": {**sums, "DA_Energy_total": da_energy, "RT_Energy_total": rt_energy,
                   "DA_AS_total": da_as, "RT_AS_total": rt_as, "Net": net},
        "qty": {"da_sales_mwh": da_sales, "da_purchases_mwh": da_purch,
                "rt_gen_mwh": rt_gen, "rt_con_mwh": rt_con},
        "prices": {"daspp_avg": daspp_avg, "rtspp_avg": rtspp_avg,
                   "daspp_hourly": daspp_vals, "rtspp_hourly": rtspp_vals},
        "as_mw_daily": {k: {"gen": g, "clr": c, "total": t} for k, (g, c, t) in as_mw.items()},
        "hourly": [
            {"he": h, "da_energy": de, "rt_energy": re_, "regup": ru, "regdown": rd,
             "rrs": rrs_, "nonspin": ns_, "ecrs": ec, "deviation": dv, "total": tt,
             "daspp": ds, "rtspp": rs, "gen_mwh": gn, "con_mwh": cn}
            for (h, de, re_, ru, rd, rrs_, ns_, ec, dv, tt, ds, rs, gn, cn) in hourly_rows
        ],
    }
    out_path = ROOT / "shared/data/pnl/gks/hourly/2026-05-03_pivoted.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote pivot: {out_path}")


if __name__ == "__main__":
    main()
