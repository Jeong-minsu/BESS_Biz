"""
YoY comparison #20 — Build the final comparison Excel (3-category structure).

Input:  derived/daily_metrics_combined.parquet
Output: output/GKS_YoY_2025vs2026_Feb14_Apr30.xlsx

Sheets:
  1. Findings              — narrative summary
  2. Comparison_Summary    — hierarchical 3-category 2025 vs 2026 (Energy / AS / DART Virtual)
  3. Summary_Wide          — flat 41-metric 2025 vs 2026
  4. Regime_Split_RTC      — pre/post-RTC+B split (Feb14-Mar2 vs Mar3-Apr30)
  5. Notes                 — methodology & data sources
  6. YoY_SideBySide_mm_dd  — daily, paired by mm-dd
  7. Energy_2025_Daily / Energy_2026_Daily
  8. AS_2025_Daily / AS_2026_Daily
  9. DART_2025_Daily / DART_2026_Daily
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[5]
ADHOC = PROJECT_ROOT / "shared" / "data" / "adhoc" / "2026-05-11_yoy-comparison"
DERIVED = ADHOC / "derived"
OUTDIR = ADHOC / "output"
OUTDIR.mkdir(parents=True, exist_ok=True)


# ---- Sheet column lists ----
ENERGY_COLS = [
    "date", "Energy_Rev_$",
    "Discharge_Rev_$", "Charge_Cost_$",
    "Top2_RT_$", "Bot2_RT_$", "TB2_RT_$",
    "Top2_DA_$", "Bot2_DA_$", "TB2_DA_$",
    "Discharge_WAP_$", "Charge_WAP_$", "Actual_TB2_$",
    "HSL_avg_MW", "HSL_max_MW",
    "Discharge_MWh", "Charge_MWh", "Throughput_MWh", "Cycles",
]
AS_COLS = [
    "date", "AS_Rev_$",
    "AS_Rev_DA_GSD_$", "AS_Rev_RT_GSD_$",          # GSD breakdown
    "GSD_NSpin_DA_$", "GSD_NSpin_RT_Imb_$",
    "GSD_RRS_DA_$",   "GSD_RRS_RT_Imb_$",
    "GSD_ECRS_DA_$",  "GSD_ECRS_RT_Imb_$",
    "GSD_RegUp_DA_$", "GSD_RegDn_DA_$",
    "GSD_RT_RDAS_Imb_$", "GSD_RT_AS_Other_$",
    "AS_Rev_BSD_$",                                # original Battery view (for reference)
    "RRS_DA_avg_$",   "RRS_avg_award_MW",   "RRS_award_MWh",
    "ECRS_DA_avg_$",  "ECRS_avg_award_MW",  "ECRS_award_MWh",
    "NSPIN_DA_avg_$", "NSPIN_avg_award_MW", "NSPIN_award_MWh",
    "REGUP_DA_avg_$", "REGUP_avg_award_MW", "REGUP_award_MWh",
    "REGDN_DA_avg_$", "REGDN_avg_award_MW", "REGDN_award_MWh",
]
DART_COLS = [
    "date", "DART_Rev_$",
    "DART_Spread_avg_$", "P_DA_gt_RT", "P_DA_lt_RT",
    "DA_Sales_MWh", "DA_Purchases_MWh",
    "Net_DA_Award_MWh", "Gross_DA_Award_MWh",
]


def make_comparison_summary(d25: pd.DataFrame, d26: pd.DataFrame) -> pd.DataFrame:
    """3-category hierarchical summary table."""
    def pct(new, old):
        if old in (0, None) or np.isnan(old):
            return np.nan
        return (new - old) / abs(old) * 100

    rows = []
    def add(cat, metric, v25, v26, fmt="{:,.2f}"):
        try:
            delta = v26 - v25
        except Exception:
            delta = np.nan
        pchg = pct(v26, v25)
        rows.append({
            "Category":    cat,
            "Sub-metric":  metric,
            "2025":        v25,
            "2026":        v26,
            "Δ (26-25)":   delta,
            "% Change":    pchg,
        })

    # ---- Energy ----
    # Period-weighted WAPs (correct way): Σ(qty × price) / Σ qty
    # NOTE: previous version used mean of daily WAPs which over-weighted low-
    # volume days and inflated the YoY change in Actual_TB2.
    pw_disch_25 = d25["Discharge_Rev_$"].sum()  / d25["Discharge_MWh"].sum()
    pw_disch_26 = d26["Discharge_Rev_$"].sum()  / d26["Discharge_MWh"].sum()
    pw_charge_25 = d25["Charge_Cost_$"].sum()   / d25["Charge_MWh"].sum()
    pw_charge_26 = d26["Charge_Cost_$"].sum()   / d26["Charge_MWh"].sum()
    pw_tb2_25 = pw_disch_25 - pw_charge_25
    pw_tb2_26 = pw_disch_26 - pw_charge_26

    add("Energy", "Revenue ($, period sum, incl RT Reliability Deploy)",
        d25["Energy_Rev_$"].sum(),  d26["Energy_Rev_$"].sum())
    add("Energy", "  ├ Discharge revenue ($)",
        d25["Discharge_Rev_$"].sum(), d26["Discharge_Rev_$"].sum())
    add("Energy", "  ├ Charge cost ($)",
        d25["Charge_Cost_$"].sum(),   d26["Charge_Cost_$"].sum())
    add("Energy", "  ├ Energy at-RT (Discharge rev − Charge cost)",
        d25["Energy_Rev_pre_RDAS_$"].sum(),  d26["Energy_Rev_pre_RDAS_$"].sum())
    add("Energy", "  └ RT Reliability Deploy AS Imbalance (moved from AS)",
        d25["Energy_Adj_RDAS_$"].sum(),  d26["Energy_Adj_RDAS_$"].sum())
    add("Energy", "TB2 단가 — RT theoretical ($/MWh, daily mean)",
        d25["TB2_RT_$"].mean(),     d26["TB2_RT_$"].mean())
    add("Energy", "GKS 실제 충방 단가 (Actual TB2, $/MWh, period-weighted)",
        pw_tb2_25, pw_tb2_26)
    add("Energy", "  ├ Discharge WAP ($/MWh, period-weighted)",
        pw_disch_25, pw_disch_26)
    add("Energy", "  └ Charge WAP ($/MWh, period-weighted)",
        pw_charge_25, pw_charge_26)
    add("Energy", "HSL avg (MW, Telemetered)",
        d25["HSL_avg_MW"].mean(),      d26["HSL_avg_MW"].mean())
    add("Energy", "HSL max (MW, Telemetered)",
        d25["HSL_max_MW"].max(),       d26["HSL_max_MW"].max())
    # Cycles displayed as per-day average (e.g., 0.70) per user request
    add("Energy", "Cycles per day (avg)",
        d25["Cycles"].mean(),          d26["Cycles"].mean())
    add("Energy", "  └ Cycles period sum (reference)",
        d25["Cycles"].sum(),           d26["Cycles"].sum())
    add("Energy", "Throughput (MWh, period sum)",
        d25["Throughput_MWh"].sum(),   d26["Throughput_MWh"].sum())

    # ---- AS (corrected: Generator-Settlement-Data based) ----
    add("AS", "Revenue ($, period sum, GSD-corrected)", d25["AS_Rev_$"].sum(), d26["AS_Rev_$"].sum())
    add("AS", "  ├ DA AS rev ($, sum PCNS+RRS+ECRS+RU+RD AMT, sign-flipped)",
        d25["AS_Rev_DA_GSD_$"].sum(), d26["AS_Rev_DA_GSD_$"].sum())
    add("AS", "  └ RT AS rev ($, RT_AS_imbalance + reliability deploy)",
        d25["AS_Rev_RT_GSD_$"].sum(), d26["AS_Rev_RT_GSD_$"].sum())
    add("AS", "  (vs Battery-Settlement-Details AS — over-states 2026 by missing RT imb)",
        d25["AS_Rev_BSD_$"].sum(), d26["AS_Rev_BSD_$"].sum())
    for p, lbl in [("RRS", "RRS"), ("ECRS", "ECRS"), ("NSPIN", "NSpin"),
                   ("REGUP", "RegUp"), ("REGDN", "RegDn")]:
        add("AS", f"  ├ {lbl} DA 평균가 ($/MWh)",
            d25[f"{p}_DA_avg_$"].mean(), d26[f"{p}_DA_avg_$"].mean())
        add("AS", f"  └ {lbl} DA 평균 awarded Q (MW)",
            d25[f"{p}_avg_award_MW"].mean(), d26[f"{p}_avg_award_MW"].mean())

    # ---- DART Virtual ----
    add("DART Virtual", "Revenue ($, period sum)",  d25["DART_Rev_$"].sum(),  d26["DART_Rev_$"].sum())
    add("DART Virtual", "Avg DA-RT spread ($/MWh)", d25["DART_Spread_avg_$"].mean(), d26["DART_Spread_avg_$"].mean())
    add("DART Virtual", "Short prob — P(DA>RT)",    d25["P_DA_gt_RT"].mean(), d26["P_DA_gt_RT"].mean())
    add("DART Virtual", "  └ Long prob — P(DA<RT)", d25["P_DA_lt_RT"].mean(), d26["P_DA_lt_RT"].mean())
    add("DART Virtual", "Net DA awarded (MWh, period sum)", d25["Net_DA_Award_MWh"].sum(), d26["Net_DA_Award_MWh"].sum())
    add("DART Virtual", "  ├ DA Energy-only Offer awarded (MWh)", d25["DA_Sales_MWh"].sum(), d26["DA_Sales_MWh"].sum())
    add("DART Virtual", "  └ DA Energy Bid awarded (MWh)",        d25["DA_Purchases_MWh"].sum(), d26["DA_Purchases_MWh"].sum())

    # ---- Total ----
    add("[Total]", "Total Revenue ($, period sum)",  d25["Total_Rev_$"].sum(), d26["Total_Rev_$"].sum())
    add("[Total]", "  ├ Energy (incl RT Reliability Deploy)",
        d25["Energy_Rev_$"].sum(), d26["Energy_Rev_$"].sum())
    add("[Total]", "  ├ AS (ex-RT Reliability Deploy)",
        d25["AS_Rev_$"].sum(), d26["AS_Rev_$"].sum())
    add("[Total]", "  ├ DART Virtual",
        d25["DART_Rev_$"].sum(), d26["DART_Rev_$"].sum())
    add("[Total]", "  └ BP_Dev",
        d25["BP_Dev_$"].sum(), d26["BP_Dev_$"].sum())

    return pd.DataFrame(rows)


def make_findings(d25, d26) -> pd.DataFrame:
    e25, e26 = d25["Energy_Rev_$"].sum(),  d26["Energy_Rev_$"].sum()
    a25, a26 = d25["AS_Rev_$"].sum(),      d26["AS_Rev_$"].sum()
    a25_bsd, a26_bsd = d25["AS_Rev_BSD_$"].sum(), d26["AS_Rev_BSD_$"].sum()
    v25, v26 = d25["DART_Rev_$"].sum(),    d26["DART_Rev_$"].sum()
    t25, t26 = d25["Total_Rev_$"].sum(),   d26["Total_Rev_$"].sum()
    pre25  = d25[d25["date"] < pd.Timestamp("2025-03-03")]["Total_Rev_$"].sum()
    post25 = d25[d25["date"] >= pd.Timestamp("2025-03-03")]["Total_Rev_$"].sum()
    pre26  = d26[d26["date"] < pd.Timestamp("2026-03-03")]["Total_Rev_$"].sum()
    post26 = d26[d26["date"] >= pd.Timestamp("2026-03-03")]["Total_Rev_$"].sum()

    return pd.DataFrame({
        "Findings (GKS YoY, 2/14..4/30, 76 days each)": [
            "TOTAL REVENUE — 3-category split (AS now corrected via Generator-Settlement-Data):",
            f"  Energy           2025  ${e25:>10,.0f}   2026  ${e26:>10,.0f}   ({(e26/e25-1)*100:+.1f}%)",
            f"  AS (GSD)         2025  ${a25:>10,.0f}   2026  ${a26:>10,.0f}   ({(a26/a25-1)*100:+.1f}%)",
            f"  DART Virtual     2025  ${v25:>10,.0f}   2026  ${v26:>10,.0f}   ({(v26/v25-1)*100:+.1f}%)",
            f"  TOTAL            2025  ${t25:>10,.0f}   2026  ${t26:>10,.0f}   ({(t26/t25-1)*100:+.1f}%, delta ${t26-t25:,.0f})",
            "",
            f"AS CORRECTION (per user verification request):",
            f"  Old (Battery-Settlement-Details only):  2025 ${a25_bsd:>10,.0f}   2026 ${a26_bsd:>10,.0f}   ({(a26_bsd/a25_bsd-1)*100:+.1f}%)",
            f"  New (Generator-Settlement-Data, full):  2025 ${a25:>10,.0f}   2026 ${a26:>10,.0f}   ({(a26/a25-1)*100:+.1f}%)",
            f"  Delta:                                  2025 ${a25-a25_bsd:>+10,.0f}   2026 ${a26-a26_bsd:>+10,.0f}",
            "  Reason: BSD captures DA AS payments + RT_Anc_Imbalance_Amt + RT_Reliability_Deploy_Imb_Amt,",
            "  but for post-RTC+B ESR (UUID ef8d8d31) the RT_Anc_Imbalance_Amt = 0 even when granular",
            "  RTNSIMBAMT/RTRRIMBAMT/RTECRIMBAMT charges exist (≈$106k charge for GKS in 2026).",
            "  See sheet 'AS_Reconciliation_BSDvsGSD' for full breakdown.",
            "",
            "RTC+B regime split (cutoff: 2026-03-03):",
            f"  Feb14-Mar2 (17d, both pre-RTC+B):  2025 ${pre25:>10,.0f}   2026 ${pre26:>10,.0f}",
            f"  Mar3-Apr30 (59d, 2026 post-RTC+B): 2025 ${post25:>10,.0f}   2026 ${post26:>10,.0f}",
            f"  => Shortfall is concentrated post-RTC+B (delta ${post26-post25:,.0f}).",
            "",
            "WHY 2026 IS WORSE — 3-category attribution of the $-436,839 gap:",
            f"  1) DART Virtual:    -${v25-v26:,.0f}  ({(v26-v25)/(t25-t26)*100:+.0f}% of the gap)",
            "     • P(DA>RT) dropped 67% -> 52%; mean DART spread +$4.17 -> -$2.05.",
            "     • ESR slashed net DA position 58,769 -> 9,507 MWh (-84%).",
            "     • 2025 strategy = sell DA, buy back at lower RT — no longer reliable in 2026.",
            "",
            f"  2) Energy:          -${e25-e26:,.0f}  ({(e26-e25)/(t25-t26)*100:+.0f}% of the gap)",
            "     • Cycles 52.9 -> 30.7 (-42%), throughput 21,142 -> 12,292 MWh.",
            "     • ESR reserved more headroom for AS, reducing energy arbitrage volume.",
            "     • Period-weighted Actual_TB2 essentially flat: $36.41 -> $34.38 (-5.6%).",
            "       (Note: earlier 'TB2 +29%' figure was an artifact of averaging daily WAPs without",
            "        volume weighting; period-weighted WAP is the correct decomp for revenue.)",
            "     • Discharge $: $458,559 -> $251,179 (-45%);  Charge $ cost: $135,470 -> $72,475 (-47%).",
            "     • Both sides of the spread dropped proportionally — the volume collapse drove the revenue drop.",
            "",
            f"  3) AS (GSD-corrected):  {a26-a25:+,.0f}  ({(a26-a25)/(t25-t26)*100:+.0f}% of the gap)",
            "     • DA AS volumes UP huge: NSpin avg 3 -> 48 MW, ECRS 0.4 -> 3.2 MW, RRS 7.8 -> 11.7 MW.",
            "     • DA AS unit prices DOWN: RRS DA -56%, ECRS -54%, RegUp -46%, RegDn -38% (NSpin DA +14% only winner).",
            "     • DA AS payment gross: 2025 $125,942 -> 2026 $208,919 (+66%).",
            "     • BUT RT AS imbalance flipped: 2025 +$66k credit (RTRDASIAMT) -> 2026 -$106k charge (RTNSIMBAMT/RRR/ECRS).",
            "     • Net AS revenue: 2025 $192k -> 2026 $103k  (-47%) — large NEGATIVE contribution to the gap.",
            "",
            "READ ORDER:",
            "  Comparison_Summary  -- hierarchical metrics by category (your spec)",
            "  Regime_Split_RTC    -- where in time the gap opened",
            "  Energy/AS/DART_2025|2026_Daily -- daily raw for each year",
            "  YoY_SideBySide_mm_dd -- paired by mm-dd with daily deltas",
        ],
    })


def make_regime_split(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["period"] = df["year_tag"]
    df.loc[(df["year_tag"] == "2025") & (df["date"] < pd.Timestamp("2025-03-03")),  "period"] = "2025_Feb14_Mar2"
    df.loc[(df["year_tag"] == "2025") & (df["date"] >= pd.Timestamp("2025-03-03")), "period"] = "2025_Mar3_Apr30"
    df.loc[(df["year_tag"] == "2026") & (df["date"] < pd.Timestamp("2026-03-03")),  "period"] = "2026_Feb14_Mar2_preRTC"
    df.loc[(df["year_tag"] == "2026") & (df["date"] >= pd.Timestamp("2026-03-03")), "period"] = "2026_Mar3_Apr30_postRTC"
    r = df.groupby("period").agg(
        n_days=("date", "count"),
        Total_Rev=("Total_Rev_$", "sum"),
        Energy_Rev=("Energy_Rev_$", "sum"),
        AS_Rev=("AS_Rev_$", "sum"),
        DART_Rev=("DART_Rev_$", "sum"),
        Throughput_MWh=("Throughput_MWh", "sum"),
        Cycles=("Cycles", "sum"),
        Actual_TB2_avg=("Actual_TB2_$", "mean"),
        TB2_RT_avg=("TB2_RT_$", "mean"),
        DART_Spread_avg=("DART_Spread_avg_$", "mean"),
        P_DA_gt_RT_avg=("P_DA_gt_RT", "mean"),
        HSL_avg=("HSL_avg_MW", "mean"),
        RRS_DA_avg=("RRS_DA_avg_$", "mean"),
        ECRS_DA_avg=("ECRS_DA_avg_$", "mean"),
        NSPIN_DA_avg=("NSPIN_DA_avg_$", "mean"),
        NSPIN_avg_award_MW=("NSPIN_avg_award_MW", "mean"),
    ).round(2).reset_index()
    order = ["2025_Feb14_Mar2", "2026_Feb14_Mar2_preRTC",
             "2025_Mar3_Apr30", "2026_Mar3_Apr30_postRTC"]
    r["__order"] = r["period"].map({k: i for i, k in enumerate(order)})
    return r.sort_values("__order").drop(columns="__order").reset_index(drop=True)


def make_total_reconciliation() -> pd.DataFrame:
    """Cross-source reconciliation of Total Revenue 2025 vs 2026 from multiple
    Tenaska PTP endpoints. Read from per-day JSONs."""
    import json as _json
    from collections import defaultdict as _dd

    PNL = (PROJECT_ROOT / "shared" / "data" / "pnl" / "gks" / "hourly")

    def sum_ep(year: str, pattern: str):
        # year is like "2025" (no trailing dash)
        agg = _dd(float)
        for f in sorted(PNL.glob(f"{year}-*{pattern}")):
            if not (f"{year}-02-14" <= f.name[:10] <= f"{year}-04-30"):
                continue
            try:
                for r in _json.loads(f.read_text(encoding="utf-8")):
                    v = r.get("value")
                    if isinstance(v, (int, float)):
                        agg[r["datapoint"]] += v
            except Exception:
                pass
        return dict(agg)

    rows = []
    def add(src, m, v25, v26):
        rows.append({"Source": src, "Metric": m, "2025 ($)": v25, "2026 ($)": v26,
                       "Δ": v26 - v25})

    # --- Battery-Settlement-Details (BSD) — Tenaska's curated view ---
    bsd_25_v2 = sum_ep("2025", "_energy_as_detail_v2.json")
    bsd_25 = {k: v for k, v in bsd_25_v2.items()}    # contains Gen+LR; values identical so OK
    bsd_26 = sum_ep("2026", "_energy_as_detail.json")
    # halve 2025 (Gen+LR duplicates): they're double-recorded in v2
    bsd_25_half = {k: v / 2 for k, v in bsd_25.items()}

    bsd_total_25 = (bsd_25_half.get("DA_Energy_Amt", 0) + bsd_25_half.get("RT_Energy_Amt", 0)
                     + bsd_25_half.get("DA_RRS_Amt", 0) + bsd_25_half.get("DA_ECRS_Amt", 0)
                     + bsd_25_half.get("DA_NS_Amt", 0)  + bsd_25_half.get("DA_Reg_Up_Amt", 0)
                     + bsd_25_half.get("DA_Reg_Down_Amt", 0)
                     + bsd_25_half.get("RT_Ancillary_Imbalance_Amt", 0)
                     + bsd_25_half.get("RT_Reliability_Deployment_Imbalance_Amt", 0)
                     + bsd_25_half.get("BP_Dev_Amt", 0))
    bsd_total_26 = (bsd_26.get("DA_Energy_Amt", 0) + bsd_26.get("RT_Energy_Amt", 0)
                     + bsd_26.get("DA_RRS_Amt", 0) + bsd_26.get("DA_ECRS_Amt", 0)
                     + bsd_26.get("DA_NS_Amt", 0)  + bsd_26.get("DA_Reg_Up_Amt", 0)
                     + bsd_26.get("DA_Reg_Down_Amt", 0)
                     + bsd_26.get("RT_Ancillary_Imbalance_Amt", 0)
                     + bsd_26.get("RT_Reliability_Deployment_Imbalance_Amt", 0))
    add("Battery-Settlement-Details (BSD)", "Total Revenue ($, period sum)",
        bsd_total_25, bsd_total_26)

    # --- Settlement-Summary (ERCOT statement aggregator) ---
    # We queried each year with a single elementIdentifier, so files contain
    # only ONE entity per day → no halving needed.
    ss_25 = sum_ep("2025", "_settle_summary.json")
    ss_26 = sum_ep("2026", "_settle_summary.json")
    ss_total_25 = -(ss_25.get("DA_Energy_Charge", 0)
                     + ss_25.get("DA_Market_Charges", 0)
                     + ss_25.get("RT_Energy_Charge", 0)
                     + ss_25.get("RT_Market_Charges", 0))
    ss_total_26 = -(ss_26.get("DA_Energy_Charge", 0)
                     + ss_26.get("DA_Market_Charges", 0)
                     + ss_26.get("RT_Energy_Charge", 0)
                     + ss_26.get("RT_Market_Charges", 0))
    add("Settlement-Summary (ERCOT stmt agg)", "Total Revenue ($, period sum)",
        ss_total_25, ss_total_26)

    # --- Our 3-category total (current Excel) ---
    df = pd.read_parquet(DERIVED / "daily_metrics_combined.parquet")
    d25 = df[df["year_tag"] == "2025"]
    d26 = df[df["year_tag"] == "2026"]
    add("Our 3-category (Energy+AS_GSD+DART+BP)", "Total Revenue ($, period sum)",
        d25["Total_Rev_$"].sum(), d26["Total_Rev_$"].sum())
    add("  ├ Energy (incl RT Reliability Deploy)", "",
        d25["Energy_Rev_$"].sum(), d26["Energy_Rev_$"].sum())
    add("  ├ AS (ex-RDAS, GSD-corrected)",  "",
        d25["AS_Rev_$"].sum(), d26["AS_Rev_$"].sum())
    add("  ├ DART Virtual", "",
        d25["DART_Rev_$"].sum(), d26["DART_Rev_$"].sum())
    add("  └ BP_Dev", "",
        d25["BP_Dev_$"].sum(), d26["BP_Dev_$"].sum())

    return pd.DataFrame(rows)


def make_as_reconciliation(d25: pd.DataFrame, d26: pd.DataFrame) -> pd.DataFrame:
    """Side-by-side breakdown of BSD vs GSD AS revenue."""
    rows = [
        ("Source: Battery-Settlement-Details (BSD)", "", ""),
        ("  DA AS sum (DA_RRS + DA_ECRS + DA_NS + DA_RegUp + DA_RegDn)",
         d25["AS_Rev_DA_$"].sum(), d26["AS_Rev_DA_$"].sum()),
        ("  RT AS sum (RT_Anc_Imbalance + RT_Reliability_Deploy)",
         d25["AS_Rev_RT_$"].sum(), d26["AS_Rev_RT_$"].sum()),
        ("  AS Total (BSD)", d25["AS_Rev_BSD_$"].sum(), d26["AS_Rev_BSD_$"].sum()),
        ("", "", ""),
        ("Source: Generator-Settlement-Data (GSD, ERCOT statement-style)", "", ""),
        ("  DA NSpin (PCNSAMT, sign-flipped)",  d25["GSD_NSpin_DA_$"].sum(),  d26["GSD_NSpin_DA_$"].sum()),
        ("  DA RRS   (PCRRAMT, sign-flipped)",  d25["GSD_RRS_DA_$"].sum(),    d26["GSD_RRS_DA_$"].sum()),
        ("  DA ECRS  (PCECRAMT)",                d25["GSD_ECRS_DA_$"].sum(),   d26["GSD_ECRS_DA_$"].sum()),
        ("  DA RegUp (PCRUAMT)",                 d25["GSD_RegUp_DA_$"].sum(),  d26["GSD_RegUp_DA_$"].sum()),
        ("  DA RegDn (PCRDAMT)",                 d25["GSD_RegDn_DA_$"].sum(),  d26["GSD_RegDn_DA_$"].sum()),
        ("  RT NSpin Imbalance (RTNSIMBAMT)",    d25["GSD_NSpin_RT_Imb_$"].sum(),  d26["GSD_NSpin_RT_Imb_$"].sum()),
        ("  RT RRS Imbalance (RTRRIMBAMT)",      d25["GSD_RRS_RT_Imb_$"].sum(),    d26["GSD_RRS_RT_Imb_$"].sum()),
        ("  RT ECRS Imbalance (RTECRIMBAMT)",    d25["GSD_ECRS_RT_Imb_$"].sum(),   d26["GSD_ECRS_RT_Imb_$"].sum()),
        ("  RT AS Other (RTASIAMT)",             d25["GSD_RT_AS_Other_$"].sum(),   d26["GSD_RT_AS_Other_$"].sum()),
        ("  RT Reliability Deploy AS Imb (RTRDASIAMT)",
                                                  d25["GSD_RT_RDAS_Imb_$"].sum(),   d26["GSD_RT_RDAS_Imb_$"].sum()),
        ("  AS Total (GSD)", d25["AS_Rev_$"].sum(), d26["AS_Rev_$"].sum()),
        ("", "", ""),
        ("BSD vs GSD diff (correction needed)",
         d25["AS_Rev_$"].sum() - d25["AS_Rev_BSD_$"].sum(),
         d26["AS_Rev_$"].sum() - d26["AS_Rev_BSD_$"].sum()),
    ]
    df = pd.DataFrame(rows, columns=["Component", "2025 ($)", "2026 ($)"])
    df["Δ (26-25)"] = pd.to_numeric(df["2026 ($)"], errors="coerce") - pd.to_numeric(df["2025 ($)"], errors="coerce")
    return df


def make_notes():
    return pd.DataFrame({"Notes": [
        "Period: 2025-02-14..2025-04-30 vs 2026-02-14..2026-04-30 (76 days each).",
        "",
        "*** AS REVENUE METHODOLOGY UPDATE (per verification) ***",
        "AS revenue now sourced from Tenaska PTP Generator-Settlement-Data (UUID-based query),",
        "which matches ERCOT settlement statement convention and includes all RT AS imbalances.",
        "Battery-Settlement-Details (BSD) — our original source — omits the granular per-product",
        "RT AS imbalance fields (RTNSIMBAMT/RTRRIMBAMT/RTECRIMBAMT) for the post-RTC+B ESR,",
        "showing only the aggregated RT_Anc_Imbalance_Amt which is reported as $0 for 2026.",
        "Result: 2026 AS revenue corrected DOWN from $208,919 to $102,587 (−$106,332 charge).",
        "See sheet 'AS_Reconciliation_BSDvsGSD' for full BSD vs GSD breakdown.",
        "",
        "Settlement-point: GKS_BESS_RN (Yes Energy hourly DA/RT LMP).",
        "Max SoC: 200 MWh; Cycles = (Discharge + Charge MWh) / (2 × 200).",
        "",
        "REVENUE — 3-CATEGORY SPLIT (sums to PTP settlement exactly):",
        "  Energy ($)         = Σ_h (RT_Gen_h − RT_Cons_h) × RTSPP_h    (physical merchant at-RT)",
        "  DART Virtual ($)   = (PTP DA_Energy_Amt + PTP RT_Energy_Amt) − Energy",
        "                       Algebraically equals Σ_h (DA_Sales − DA_Purchases) × (DA − RT).",
        "  AS ($)             = DA AS amounts (RRS + ECRS + NSpin + RegUp + RegDn)",
        "                       + RT_Ancillary_Imbalance_Amt + RT_Reliability_Deployment_Imbalance_Amt",
        "  BP_Dev ($)         = Base-Point Deviation penalty (energy-direction, kept separate).",
        "  Total ($)          = Energy + DART + AS + BP_Dev",
        "",
        "ENERGY metrics:",
        "  TB2 단가 ($/MWh)            = mean(top2 RT − bot2 RT) per day (theoretical opportunity).",
        "  GKS 실제 충방 단가 ($/MWh)  = Discharge WAP − Charge WAP (achieved spread).",
        "  Discharge WAP               = Σ_h RT_Gen_h × RT_h / Σ_h RT_Gen_h",
        "  Charge WAP                  = Σ_h RT_Cons_h × RT_h / Σ_h RT_Cons_h",
        "  HSL avg (MW)                = mean(Telemetered_HSL_5_Min) per day (PTP Generator-Performance).",
        "  Cycles                      = (Discharge + Charge MWh) / 400  per day.",
        "",
        "AS metrics (per product):",
        "  DA 평균가격 ($/MWh)   = mean(DAM MCPC) over 24h.",
        "  DA 평균 awarded Q (MW) = mean hourly award MW.  Sum over 24h = MWh awarded.",
        "    2025 quantity source: derived as DA $ ÷ MCPC (pre-RTC PTP feed has no per-resource AS qty).",
        "    2026 quantity source: PTP Gen_<product>_Qty direct.",
        "  RT_AS_MCPC (RT AS price): NaN for pre-RTC+B (2025 entirely + 2026 before 2026-03-03).",
        "",
        "DART VIRTUAL metrics:",
        "  Avg DA-RT spread ($/MWh) = mean(DA_LMP − RT_LMP) per day at GKS_BESS_RN.",
        "  Short prob P(DA>RT)      = hours with DA > RT ÷ 24  (when a short DART would win).",
        "  Long prob P(DA<RT)       = hours with DA < RT ÷ 24.",
        "  Net DA awarded (MWh)     = sum(DA_Sales_Qty − DA_Purchases_Qty) over 24h.",
        "  DA Energy-only Offer awarded = DA_Sales_Qty sum (sell side).",
        "  DA Energy Bid awarded         = DA_Purchases_Qty sum (buy side).",
        "",
        "REGIME — RTC+B (Real-Time Co-optimization with Batteries) went live ERCOT-wide 2026-03-03.",
        "  • 2025 entire period = pre-RTC+B (Gen + Load settled as separate resources).",
        "  • 2026-02-14..03-02 (17 days) = pre-RTC+B in 2026 (same regime).",
        "  • 2026-03-03..04-30 (59 days) = post-RTC+B (single ESR settlement; RT AS market active).",
        "",
        "DATA SOURCES:",
        "  Yes Energy:   DA/RT LMP at GKS_BESS_RN and HB_HOUSTON.",
        "  ERCOT API:    DAM AS clearing prices (np4-188-cd).",
        "  Tenaska PTP:",
        "    • 2025 settlement: Battery-Settlement-Details, entity 'Great Kiskadee Storage, LLC Gen' (UUID 549e9554...).",
        "    • 2026 settlement: Battery-Settlement-Details, entity 'Great Kiskadee Storage - ESR' (UUID ef8d8d31...).",
        "    • HSL (both years): Generator-Performance, entity 'Great Kiskadee BESS' (UUID 565ab4f2...), Telemetered_HSL_5_Min.",
    ]})


def main():
    src = DERIVED / "daily_metrics_combined.parquet"
    print(f"reading {src} ...")
    df = pd.read_parquet(src)
    df["date"] = pd.to_datetime(df["date"])
    d25 = df[df["year_tag"] == "2025"].copy().sort_values("date").reset_index(drop=True)
    d26 = df[df["year_tag"] == "2026"].copy().sort_values("date").reset_index(drop=True)
    print(f"  2025 rows: {len(d25)}, 2026 rows: {len(d26)}")

    # YoY side-by-side
    d25["mm_dd"] = d25["date"].dt.strftime("%m-%d")
    d26["mm_dd"] = d26["date"].dt.strftime("%m-%d")
    keep = (ENERGY_COLS[1:] + AS_COLS[1:] + DART_COLS[1:] + ["Total_Rev_$"])
    side = d25[["mm_dd"] + keep].merge(
        d26[["mm_dd"] + keep],
        on="mm_dd", suffixes=("_25", "_26"), how="outer",
    ).sort_values("mm_dd")
    delta_targets = [
        "Energy_Rev_$", "TB2_RT_$", "Actual_TB2_$", "HSL_avg_MW", "Cycles",
        "AS_Rev_$", "DART_Rev_$",
        "DART_Spread_avg_$", "P_DA_gt_RT", "Net_DA_Award_MWh",
        "Total_Rev_$",
    ]
    for c in delta_targets:
        c25, c26 = f"{c}_25", f"{c}_26"
        if c25 in side.columns and c26 in side.columns:
            side[f"{c}_Δ"] = side[c26] - side[c25]

    # Subset sheets
    energy_25 = d25[ENERGY_COLS].copy()
    energy_26 = d26[ENERGY_COLS].copy()
    as_25 = d25[[c for c in AS_COLS if c in d25.columns]].copy()
    as_26 = d26[[c for c in AS_COLS if c in d26.columns]].copy()
    dart_25 = d25[DART_COLS].copy()
    dart_26 = d26[DART_COLS].copy()

    # Wide summary (1 row per year + delta + pct)
    def summary_row(df):
        return {c: df[c].sum() if c.endswith("_$") or c.endswith("MWh")
                                  or c in ("Cycles", "Throughput_MWh")
                else df[c].mean() for c in df.columns
                if c not in ("year_tag", "date", "mm_dd")}
    s25 = pd.Series(summary_row(d25))
    s26 = pd.Series(summary_row(d26))
    delta = s26 - s25
    pct = ((s26 / s25.replace(0, np.nan) - 1) * 100)
    wide = pd.DataFrame({"2025": s25, "2026": s26, "Δ(26-25)": delta, "% Change": pct}).round(2)

    cmp = make_comparison_summary(d25, d26)
    regime = make_regime_split(df)
    findings = make_findings(d25, d26)
    notes = make_notes()
    as_recon = make_as_reconciliation(d25, d26)
    total_recon = make_total_reconciliation()

    out = OUTDIR / "GKS_YoY_2025vs2026_Feb14_Apr30.xlsx"
    if out.exists():
        try:
            out.unlink()
        except PermissionError:
            from datetime import datetime as _dt
            stamp = _dt.now().strftime("%Y%m%d_%H%M%S")
            out = OUTDIR / f"GKS_YoY_2025vs2026_Feb14_Apr30_{stamp}.xlsx"
            print(f"  (target locked — writing to {out.name} instead)")
    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        findings.to_excel(xw, sheet_name="Findings",              index=False)
        cmp.to_excel(     xw, sheet_name="Comparison_Summary",    index=False)
        total_recon.to_excel(xw, sheet_name="Total_Revenue_CrossCheck", index=False)
        as_recon.to_excel(xw, sheet_name="AS_Reconciliation_BSDvsGSD", index=False)
        wide.to_excel(    xw, sheet_name="Summary_Wide",          index=True)
        regime.to_excel(  xw, sheet_name="Regime_Split_RTC",      index=False)
        notes.to_excel(   xw, sheet_name="Notes",                 index=False)
        side.to_excel(    xw, sheet_name="YoY_SideBySide_mm_dd",  index=False)
        energy_25.to_excel(xw, sheet_name="Energy_2025_Daily",    index=False)
        energy_26.to_excel(xw, sheet_name="Energy_2026_Daily",    index=False)
        as_25.to_excel(    xw, sheet_name="AS_2025_Daily",        index=False)
        as_26.to_excel(    xw, sheet_name="AS_2026_Daily",        index=False)
        dart_25.to_excel(  xw, sheet_name="DART_2025_Daily",      index=False)
        dart_26.to_excel(  xw, sheet_name="DART_2026_Daily",      index=False)

    print(f"\nSAVED → {out}")
    print("\nComparison_Summary preview:")
    print(cmp.to_string(index=False, max_colwidth=50))


if __name__ == "__main__":
    main()
