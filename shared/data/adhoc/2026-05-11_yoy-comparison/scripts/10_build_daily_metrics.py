"""
YoY comparison #10 — Build daily metrics for 2025 & 2026 (2/14..4/30 each year).

Revenue split into THREE categories:
  • Energy revenue          = Σ_h (Phys_Gen_h − Phys_Cons_h) × RTLMP_h
                              (physical merchant at-RT value of cycling).
  • DART Virtual revenue    = Σ_h (DA_Sales_Qty − DA_Purchases_Qty) × (DA − RT)
                              (financial DA-RT arbitrage layer).
  • AS revenue              = Σ_h DA_<product>_Amt
                              + RT_Ancillary_Imbalance_Amt
                              + RT_Reliability_Deployment_Imbalance_Amt
Identity: Energy + DART  ≡  DA_Energy_Amt + RT_Energy_Amt  (settlement totals).

Reads:
  2026: shared/data/adhoc/2026-05-07_AS-strategy/derived/master_hourly.parquet
  2025: derived/lmp_hourly_2025.parquet (Yes Energy)
        derived/as_dam_mcpc_hourly_2025.parquet (ERCOT)
        shared/data/pnl/gks/hourly/<YYYY-MM-DD>_energy_as_detail_v2.json (PTP, Gen entity)
        shared/data/pnl/gks/hourly/<YYYY-MM-DD>_hsl.json (PTP Telemetered_HSL_5_Min)
  HSL 2026: shared/data/pnl/gks/hourly/<YYYY-MM-DD>_hsl.json (PTP) when present,
            else fallback to master_hourly avail_discharge_mw (SmartBidder).

Writes:
  derived/daily_metrics_combined.parquet
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[5]
ADHOC = PROJECT_ROOT / "shared" / "data" / "adhoc" / "2026-05-11_yoy-comparison"
DERIVED = ADHOC / "derived"
PTP_DIR = PROJECT_ROOT / "shared" / "data" / "pnl" / "gks" / "hourly"
MASTER_2026 = (PROJECT_ROOT / "shared" / "data" / "adhoc"
               / "2026-05-07_AS-strategy" / "derived" / "master_hourly.parquet")

MAX_SOC_MWH = 200.0
AS_PRODUCTS = ["RRS", "ECRS", "NSPIN", "REGUP", "REGDN"]


# ---- Generator-Settlement-Data per-day loader (authoritative AS settlement) ----
# Sign convention: stmt fields are NEGATIVE when ERCOT pays the resource (credit
# to revenue), POSITIVE when the resource pays ERCOT (charge against revenue).
GSD_FIELDS_DA_AS = ["PCNSAMT", "PCRRAMT", "PCECRAMT", "PCRUAMT", "PCRDAMT"]
GSD_FIELDS_RT_AS = ["RTNSIMBAMT", "RTRRIMBAMT", "RTECRIMBAMT",
                     "RTRUIMBAMT", "RTRDIMBAMT",
                     "RTASIAMT", "LAASIRNAMT"]
# RTRDASIAMT (RT Reliability Deployment AS Imbalance) is classified as Energy
# revenue per user request (since it's the imbalance payment from delivering
# energy when AS is deployed by ERCOT).
GSD_FIELDS_RT_ENERGY_ADJ = ["RTRDASIAMT"]


def load_gsd_daily(year_prefix: str) -> pd.DataFrame:
    """Return DataFrame [date, AS_Rev_DA_GSD_$, AS_Rev_RT_GSD_$, AS_Rev_GSD_$,
    plus per-product DA $ from GSD] from per-day Generator-Settlement-Data files."""
    rows = []
    for f in sorted(PTP_DIR.glob(f"{year_prefix}*_gen_settle.json")):
        d = f.name[:10]
        try:
            arr = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  gsd read err: {f.name}: {e}")
            continue
        agg = {}
        for r in arr:
            v = r.get("value")
            if isinstance(v, (int, float)):
                k = r.get("datapoint")
                agg[k] = agg.get(k, 0.0) + v
        da_as_rev = -sum(agg.get(k, 0.0) for k in GSD_FIELDS_DA_AS)
        rt_as_rev = -sum(agg.get(k, 0.0) for k in GSD_FIELDS_RT_AS)
        # RTRDASIAMT moved to Energy (per user, point #1)
        rt_energy_adj = -sum(agg.get(k, 0.0) for k in GSD_FIELDS_RT_ENERGY_ADJ)
        rows.append({
            "date":             pd.to_datetime(d).date(),
            "AS_Rev_DA_GSD_$":  da_as_rev,
            "AS_Rev_RT_GSD_$":  rt_as_rev,
            "AS_Rev_GSD_$":     da_as_rev + rt_as_rev,
            "Energy_Adj_RDAS_$": rt_energy_adj,
            "GSD_RT_RDAS_Imb_$": rt_energy_adj,    # kept for reconciliation sheet
            "GSD_RT_AS_Other_$": -agg.get("RTASIAMT", 0.0),
            # Per-product DA ($)
            "GSD_NSpin_DA_$":   -agg.get("PCNSAMT", 0.0),
            "GSD_RRS_DA_$":     -agg.get("PCRRAMT", 0.0),
            "GSD_ECRS_DA_$":    -agg.get("PCECRAMT", 0.0),
            "GSD_RegUp_DA_$":   -agg.get("PCRUAMT", 0.0),
            "GSD_RegDn_DA_$":   -agg.get("PCRDAMT", 0.0),
            # Per-product RT imbalance ($)
            "GSD_NSpin_RT_Imb_$":  -agg.get("RTNSIMBAMT", 0.0),
            "GSD_RRS_RT_Imb_$":    -agg.get("RTRRIMBAMT", 0.0),
            "GSD_ECRS_RT_Imb_$":   -agg.get("RTECRIMBAMT", 0.0),
        })
    return pd.DataFrame(rows)


# ---- HSL loader ----
def load_hourly_hsl(year_prefix: str) -> pd.DataFrame:
    """Return DataFrame [date, he, hsl_mw] from PTP per-day HSL JSONs.
    Telemetered_HSL_5_Min is 5-min granularity → average to hour-ending."""
    rows = []
    for f in sorted(PTP_DIR.glob(f"{year_prefix}*_hsl.json")):
        try:
            arr = json.loads(f.read_text(encoding="utf-8"))
            for r in arr:
                if r.get("datapoint") != "Telemetered_HSL_5_Min":
                    continue
                rows.append({
                    "interval_start_utc": r.get("interval_start_utc"),
                    "hsl_mw": r.get("value"),
                })
        except Exception as e:
            print(f"  hsl read err: {f.name}: {e}")
    if not rows:
        return pd.DataFrame(columns=["date", "he", "hsl_mw"])
    df = pd.DataFrame(rows)
    df["interval_start_utc"] = pd.to_datetime(df["interval_start_utc"], utc=True)
    df["dt_ct"] = df["interval_start_utc"].dt.tz_convert("America/Chicago")
    df["date"] = df["dt_ct"].dt.date
    df["he"]   = df["dt_ct"].dt.hour + 1
    df["hsl_mw"] = pd.to_numeric(df["hsl_mw"], errors="coerce")
    g = df.groupby(["date", "he"], as_index=False)["hsl_mw"].mean()
    return g


# ---- 2026 hourly frame ----
def load_2026_hourly() -> pd.DataFrame:
    m = pd.read_parquet(MASTER_2026)
    m["datetime_ct"] = pd.to_datetime(m["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
    m["date"] = m["datetime_ct"].dt.date
    # Override HSL from PTP files when available (more accurate physical limit)
    hsl = load_hourly_hsl("2026-")
    if not hsl.empty:
        m = m.merge(hsl.rename(columns={"hsl_mw": "ptp_hsl_mw"}),
                     on=["date", "he"], how="left")
        # Prefer PTP HSL; fall back to SmartBidder avail_discharge_mw if PTP missing
        m["hsl_mw"] = m["ptp_hsl_mw"].fillna(m["avail_discharge_mw"])
    else:
        m["hsl_mw"] = m["avail_discharge_mw"]
    return m


# ---- 2025 hourly frame ----
def load_2025_hourly() -> pd.DataFrame:
    # 1) LMP wide
    lmp = pd.read_parquet(DERIVED / "lmp_hourly_2025.parquet")
    lmp["datetime_ct"] = pd.to_datetime(lmp["datetime_ct"])
    lmp["key"] = lmp["data_type"] + "_" + lmp["node"]
    wide = lmp.pivot_table(index=["datetime_ct", "he"], columns="key",
                            values="price", aggfunc="first").reset_index()
    wide["date"] = wide["datetime_ct"].dt.date

    # 2) AS DA MCPC
    asdf = pd.read_parquet(DERIVED / "as_dam_mcpc_hourly_2025.parquet")
    asdf["deliveryDate"] = pd.to_datetime(asdf["deliveryDate"]).dt.date
    asdf["hourEnding"]   = asdf["hourEnding"].astype(str).str.split(":").str[0].astype(int)
    asdf["MCPC"] = pd.to_numeric(asdf["MCPC"], errors="coerce")
    as_wide = asdf.pivot_table(index=["deliveryDate", "hourEnding"], columns="ancillaryType",
                                 values="MCPC", aggfunc="first").reset_index()
    rename = {}
    for c in as_wide.columns:
        if c in ("deliveryDate", "hourEnding"):
            continue
        cu = str(c).upper()
        if cu in ("REGUP", "REG-UP", "REGULATION UP"):
            rename[c] = "AS_MCPC_REGUP"
        elif cu in ("REGDN", "REGDOWN", "REG-DOWN", "REGULATION DOWN"):
            rename[c] = "AS_MCPC_REGDN"
        elif "ECRS" in cu:
            rename[c] = "AS_MCPC_ECRS"
        elif "NSPIN" in cu or "NONSPIN" in cu or "NON-SPIN" in cu:
            rename[c] = "AS_MCPC_NSPIN"
        elif "RRS" in cu:
            rename[c] = "AS_MCPC_RRS"
    as_wide = as_wide.rename(columns=rename)
    as_wide = as_wide[["deliveryDate", "hourEnding"] +
                       [c for c in ["AS_MCPC_REGUP", "AS_MCPC_REGDN",
                                    "AS_MCPC_ECRS", "AS_MCPC_NSPIN", "AS_MCPC_RRS"]
                        if c in as_wide.columns]]
    wide = wide.merge(as_wide.rename(columns={"deliveryDate": "date",
                                                "hourEnding": "he"}),
                       on=["date", "he"], how="left")

    # 3) PTP energy_as_detail v2 (Gen entity only — LR has duplicate values)
    rows = []
    v2 = sorted(PTP_DIR.glob("2025-*_energy_as_detail_v2.json"))
    if v2:
        for f in v2:
            try:
                arr = json.loads(f.read_text(encoding="utf-8"))
                for r in arr:
                    if r.get("element") != "Great Kiskadee Storage, LLC Gen":
                        continue
                    rows.append({"interval_start_utc": r.get("interval_start_utc"),
                                  "datapoint": r.get("datapoint"),
                                  "value": r.get("value")})
            except Exception as e:
                print(f"  {f.name}: {e}")
    if rows:
        ptp = pd.DataFrame(rows)
        ptp["interval_start_utc"] = pd.to_datetime(ptp["interval_start_utc"], utc=True)
        ptp["dt_ct"] = ptp["interval_start_utc"].dt.tz_convert("America/Chicago")
        ptp["date"] = ptp["dt_ct"].dt.date
        ptp["he"]   = ptp["dt_ct"].dt.hour + 1
        ptp["value"] = pd.to_numeric(ptp["value"], errors="coerce")
        ptp_w = ptp.pivot_table(index=["date", "he"], columns="datapoint",
                                 values="value", aggfunc="sum").reset_index()
        ptp_w.columns = [c if c in ("date", "he") else f"GKS_{c}"
                          for c in ptp_w.columns]
        wide = wide.merge(ptp_w, on=["date", "he"], how="left")

    # 4) PTP HSL (Telemetered_HSL_5_Min averaged to hour)
    hsl = load_hourly_hsl("2025-")
    if not hsl.empty:
        wide = wide.merge(hsl.rename(columns={"hsl_mw": "hsl_mw"}),
                           on=["date", "he"], how="left")
    else:
        wide["hsl_mw"] = np.nan

    return wide


# ---- daily aggregation ----
def daily_metrics(hourly: pd.DataFrame, label: str) -> pd.DataFrame:
    rows = []
    for d, sub in hourly.groupby("date"):
        if len(sub) < 23:
            continue
        s = sub.sort_values("he")
        da = s["DALMP_GKS_BESS_RN"].astype(float)
        rt = s["RTLMP_GKS_BESS_RN"].astype(float)

        # ---- price benchmarks ----
        top2_da, bot2_da = da.nlargest(2).mean(), da.nsmallest(2).mean()
        top2_rt, bot2_rt = rt.nlargest(2).mean(), rt.nsmallest(2).mean()
        tb2_da = top2_da - bot2_da
        tb2_rt = top2_rt - bot2_rt

        spread = da - rt                       # spread = DA − RT
        p_da_gt_rt = float((spread > 0).mean())
        p_da_lt_rt = float((spread < 0).mean())
        avg_spread = float(spread.mean())

        # ---- physical quantities ----
        gen_q  = s.get("GKS_RT_Generation_Qty",
                       pd.Series(np.nan, index=s.index)).astype(float).fillna(0)
        cons_q = s.get("GKS_RT_Consumption_Qty",
                       pd.Series(np.nan, index=s.index)).astype(float).fillna(0)
        da_sales = s.get("GKS_DA_Sales_Qty",
                          pd.Series(np.nan, index=s.index)).astype(float).fillna(0)
        da_purch = s.get("GKS_DA_Purchases_Qty",
                          pd.Series(np.nan, index=s.index)).astype(float).fillna(0)

        disch_mwh  = float(gen_q.sum())
        charge_mwh = float(cons_q.sum())
        throughput = disch_mwh + charge_mwh
        cycles     = throughput / (2 * MAX_SOC_MWH)

        def wap(qty, price):
            qf = qty.clip(lower=0)
            tot = qf.sum()
            return float((qf * price).sum() / tot) if tot > 0 else np.nan

        # Pre-compute settlement-basis price (RTSPP if available, fallback YE)
        # so WAPs use the SAME price source as Energy_Rev_$ below.
        _rtspp_pre = s.get("GKS_RTSPP_Avg",
                            pd.Series(np.nan, index=s.index)).astype(float)
        _rt_settle = _rtspp_pre.where(_rtspp_pre.notna(), rt)
        wap_discharge = wap(gen_q,  _rt_settle)
        wap_charge    = wap(cons_q, _rt_settle)
        actual_tb2 = ((wap_discharge - wap_charge)
                      if pd.notna(wap_discharge) and pd.notna(wap_charge) else np.nan)
        # Discharge $ revenue and Charge $ cost (period-aggregable building blocks)
        disch_dollar_rev   = float((gen_q  * _rt_settle).sum())
        charge_dollar_cost = float((cons_q * _rt_settle).sum())

        # ---- HSL ----
        hsl = s.get("hsl_mw", pd.Series(np.nan, index=s.index)).astype(float)
        hsl_avg = float(hsl.mean()) if hsl.notna().any() else np.nan
        hsl_max = float(hsl.max())  if hsl.notna().any() else np.nan

        # ---- 3-category revenue ----
        # PTP DA+RT settlement (authoritative).
        def safe_sum_local(col):
            return (float(s[col].astype(float).fillna(0).sum())
                    if col in s.columns else 0.0)
        ptp_da_e_local = safe_sum_local("GKS_DA_Energy_Amt")
        ptp_rt_e_local = safe_sum_local("GKS_RT_Energy_Amt")

        # Energy = Σ Phys_Net × RT_settlement_price  (physical merchant at-RT).
        #   Prefer GKS_RTSPP_Avg (PTP settlement basis) when available; fall back to YE RT LMP.
        rtspp = s.get("GKS_RTSPP_Avg",
                       pd.Series(np.nan, index=s.index)).astype(float)
        rt_for_energy = rtspp.where(rtspp.notna(), rt)
        phys_net  = (gen_q - cons_q)
        energy_rev = float((phys_net * rt_for_energy).sum())

        # DART = residual = PTP_DA + PTP_RT − Energy  (so 3 buckets exactly reconcile).
        # When physical fields are well-populated this equals Σ Net_DA × (DA − RT).
        net_da = (da_sales - da_purch)
        dart_rev = ptp_da_e_local + ptp_rt_e_local - energy_rev

        # AS = DA AS amts + RT AS imbalance + reliability deploy
        safe_sum = safe_sum_local
        as_rev_da = sum(safe_sum(c) for c in
                          ["GKS_DA_RRS_Amt", "GKS_DA_ECRS_Amt", "GKS_DA_NS_Amt",
                           "GKS_DA_Reg_Up_Amt", "GKS_DA_Reg_Down_Amt"])
        as_rev_rt = (safe_sum("GKS_RT_Ancillary_Imbalance_Amt")
                     + safe_sum("GKS_RT_Reliability_Deployment_Imbalance_Amt"))
        as_rev = as_rev_da + as_rev_rt

        # Misc / BP_Dev (energy direction, lump separately for QC)
        bp_dev = safe_sum("GKS_BP_Dev_Amt")

        # Sanity tag (Energy + DART now exactly = PTP DA + RT energy by construction)
        ptp_da_e = ptp_da_e_local
        ptp_rt_e = ptp_rt_e_local

        total_rev = energy_rev + dart_rev + as_rev + bp_dev

        # ---- AS prices/quantities by product ----
        as_da_prices, as_rt_prices, as_qty_mwh, as_qty_avg_mw = {}, {}, {}, {}
        as_qty_col_map = {
            "RRS":   "GKS_Gen_RRS_Qty",
            "ECRS":  "GKS_Gen_ECRS_Qty",
            "NSPIN": "GKS_Gen_NS_Qty",
            "REGUP": None,
            "REGDN": None,
        }
        as_amt_col_map = {
            "RRS":   "GKS_DA_RRS_Amt",
            "ECRS":  "GKS_DA_ECRS_Amt",
            "NSPIN": "GKS_DA_NS_Amt",
            "REGUP": "GKS_DA_Reg_Up_Amt",
            "REGDN": "GKS_DA_Reg_Down_Amt",
        }
        for p in AS_PRODUCTS:
            da_col = f"AS_MCPC_{p}"
            rt_col = f"RT_AS_MCPC_{p}"
            as_da_prices[f"{p}_DA_avg_$"] = (float(s[da_col].astype(float).mean())
                if da_col in s.columns and s[da_col].notna().any() else np.nan)
            as_rt_prices[f"{p}_RT_avg_$"] = (float(s[rt_col].astype(float).mean())
                if rt_col in s.columns and s[rt_col].notna().any() else np.nan)

            qcol = as_qty_col_map.get(p)
            if qcol and qcol in s.columns and s[qcol].notna().any():
                q_hourly = s[qcol].astype(float).fillna(0)
            else:
                # Pre-RTC fallback: derive from DA $ ÷ MCPC
                acol = as_amt_col_map.get(p)
                if acol and acol in s.columns and da_col in s.columns:
                    amt = s[acol].astype(float)
                    prc = s[da_col].astype(float).replace(0, np.nan)
                    with np.errstate(divide="ignore", invalid="ignore"):
                        q_hourly = (amt / prc).fillna(0)
                else:
                    q_hourly = pd.Series(0.0, index=s.index)
            as_qty_mwh[f"{p}_award_MWh"] = float(q_hourly.sum())
            as_qty_avg_mw[f"{p}_avg_award_MW"] = float(q_hourly.mean())

        rows.append({
            "year_tag": label,
            "date": d,
            # ---- Energy category ----
            "Energy_Rev_$":       energy_rev,
            "TB2_RT_$":           tb2_rt,
            "Actual_TB2_$":       actual_tb2,
            "Discharge_WAP_$":    wap_discharge,
            "Charge_WAP_$":       wap_charge,
            "Discharge_Rev_$":    disch_dollar_rev,
            "Charge_Cost_$":      charge_dollar_cost,
            "Top2_RT_$":          top2_rt, "Bot2_RT_$": bot2_rt,
            "Top2_DA_$":          top2_da, "Bot2_DA_$": bot2_da, "TB2_DA_$": tb2_da,
            "HSL_avg_MW":         hsl_avg, "HSL_max_MW": hsl_max,
            "Discharge_MWh":      disch_mwh, "Charge_MWh": charge_mwh,
            "Throughput_MWh":     throughput, "Cycles": cycles,
            # ---- AS category ----
            "AS_Rev_$":           as_rev,
            "AS_Rev_DA_$":        as_rev_da,
            "AS_Rev_RT_$":        as_rev_rt,
            **as_da_prices, **as_rt_prices, **as_qty_mwh, **as_qty_avg_mw,
            # ---- DART Virtual category ----
            "DART_Rev_$":         dart_rev,
            "DART_Spread_avg_$":  avg_spread,
            "P_DA_gt_RT":         p_da_gt_rt,
            "P_DA_lt_RT":         p_da_lt_rt,
            "DA_Sales_MWh":       float(da_sales.sum()),
            "DA_Purchases_MWh":   float(da_purch.sum()),
            "Net_DA_Award_MWh":   float(net_da.sum()),
            "Gross_DA_Award_MWh": float(da_sales.sum() + da_purch.sum()),
            # ---- Misc ----
            "BP_Dev_$":           bp_dev,
            "Total_Rev_$":        total_rev,
            # ---- Sanity check ----
            "PTP_DA_Energy_$":    ptp_da_e,
            "PTP_RT_Energy_$":    ptp_rt_e,
            "Energy_plus_DART_$": energy_rev + dart_rev,
        })

    return pd.DataFrame(rows)


def main():
    print("[10_build_daily_metrics] start")
    h26 = load_2026_hourly()
    h26_f = h26[(h26["date"] >= date(2026, 2, 14)) & (h26["date"] <= date(2026, 4, 30))]
    print(f"  2026 hours: {len(h26_f)}")
    d26 = daily_metrics(h26_f, "2026")
    print(f"  2026 daily rows: {len(d26)}")

    h25 = load_2025_hourly()
    h25_f = h25[(h25["date"] >= date(2025, 2, 14)) & (h25["date"] <= date(2025, 4, 30))]
    print(f"  2025 hours: {len(h25_f)}")
    d25 = daily_metrics(h25_f, "2025")
    print(f"  2025 daily rows: {len(d25)}")

    # ---- Overlay Generator-Settlement-Data AS revenue (authoritative) ----
    # Battery-Settlement-Details misses RT AS imbalance for post-RTC+B ESR.
    gsd25 = load_gsd_daily("2025-")
    gsd26 = load_gsd_daily("2026-")
    if not gsd25.empty:
        d25 = d25.merge(gsd25, on="date", how="left")
    if not gsd26.empty:
        d26 = d26.merge(gsd26, on="date", how="left")
    # Replace AS_Rev_$ with GSD-based value when present;
    # add RT Reliability Deployment to Energy bucket (per user, point #1).
    for d_ in (d25, d26):
        if "AS_Rev_GSD_$" in d_.columns:
            d_["AS_Rev_BSD_$"]      = d_["AS_Rev_$"]            # keep BSD view
            d_["Energy_Rev_pre_RDAS_$"] = d_["Energy_Rev_$"]    # pre-RDAS energy
            d_["AS_Rev_$"]          = d_["AS_Rev_GSD_$"].fillna(d_["AS_Rev_$"])
            # Move RTRDASIAMT into Energy bucket
            d_["Energy_Rev_$"]      = (d_["Energy_Rev_$"]
                                        + d_["Energy_Adj_RDAS_$"].fillna(0.0))
            # Total now reflects: Energy (incl. RTRDASIAMT) + DART + AS (GSD, ex-RDAS) + BP_Dev
            d_["Total_Rev_$"]       = (d_["Energy_Rev_$"] + d_["DART_Rev_$"]
                                        + d_["AS_Rev_$"] + d_["BP_Dev_$"])

    combined = pd.concat([d25, d26], ignore_index=True)
    out = DERIVED / "daily_metrics_combined.parquet"
    combined.to_parquet(out, index=False)
    combined.to_csv(DERIVED / "daily_metrics_combined.csv", index=False)
    print(f"  saved -> {out.name}  ({len(combined)} rows, {len(combined.columns)} cols)")

    # Sanity check
    for yr in ["2025", "2026"]:
        sub = combined[combined["year_tag"] == yr]
        e_plus_d  = sub["Energy_plus_DART_$"].sum()
        settle    = sub["PTP_DA_Energy_$"].sum() + sub["PTP_RT_Energy_$"].sum()
        print(f"  [{yr}] identity check: Energy+DART = ${e_plus_d:>12,.0f}   PTP DA+RT energy = ${settle:>12,.0f}   diff = ${e_plus_d-settle:>10,.0f}")
        if "AS_Rev_BSD_$" in sub.columns:
            bsd = sub["AS_Rev_BSD_$"].sum()
            gsd = sub["AS_Rev_$"].sum()
            print(f"  [{yr}] AS revenue: Battery-Settlement-Details = ${bsd:>10,.0f}   Generator-Settlement-Data = ${gsd:>10,.0f}   diff = ${gsd-bsd:>+10,.0f}")


if __name__ == "__main__":
    main()
