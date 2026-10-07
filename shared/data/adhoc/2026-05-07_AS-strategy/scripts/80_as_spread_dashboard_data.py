"""
#80 — Ancillary Service Day-Ahead vs Real-Time Spread Dashboard data compiler
       (Responsive Reserve Service / ERCOT Contingency Reserve Service / Non-Spinning Reserve)

Generates a single JSON consumed by the HTML dashboard.

Sections:
  Q1  Hourly Day-Ahead minus Real-Time spread series per product
      (daily mean, Hour-Ending × Day-of-Week heatmap, distribution histogram, percentiles)
  Q2  Negative-spread profile (probability by Hour-Ending / Day-of-Week / Month,
      top severe events with root-cause attribution)
  Q3  D-1 negative-spread flag — Logistic Regression model per product
      Features: net-load forecast percentile, wind forecast percentile,
      solar forecast percentile, Day-Ahead clearing price percentile, Hour-Ending sin/cos.
      Reports Area Under ROC Curve, top-decile lift, threshold at best F1 score, operating points.
  Q4  Optimal Day-Ahead vs Real-Time bid share — KEY ASSUMPTION (per user 2026-05-18):
      *Any Ancillary Service capacity sold in Day-Ahead is bought back 100% in Real-Time,*
      *because the BESS operates energy independently in Real-Time.*
      Net Day-Ahead AS revenue therefore equals:
          a_DA * (DAM_MCPC - RT_AS_MCPC) = a_DA * spread
      Real-Time AS sale (alternative) earns:
          a_RT * RT_AS_MCPC
      Reports strategies (Day-Ahead 100% with buyback / Real-Time 100% / Binary D-1 flag rule /
      3-tier heuristic / Ex-post Oracle) at the same MW base (LP a_eff per Hour-Ending).

Inputs:
  derived/master_hourly.parquet                 (full hourly grid)
  derived/q2_coopt_lp_summary.json              (per-product ex-post LP)
  derived/q2_coopt_lp_he_alloc.parquet          (Hour-Ending mean LP allocation)

Output:
  derived/as_spread_dashboard_data.json
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

PRODUCTS = ["RRS", "ECRS", "NSPIN"]
# severity thresholds (chosen on prior NSPIN analysis — DA<RT by more than $/MWh)
SEVERE = {"RRS": 3.0, "ECRS": 5.0, "NSPIN": 5.0}

# ----- Battery physical parameters (per user 2026-05-18) -----
HSL_MW          = 100.0    # High Sustained Limit (power rating)
SOC_MWH         = 200.0    # energy capacity
# Product-specific SoC duration multiplier — # hours the AS award must be deliverable for
SOC_DURATION_H = {"RRS": 0.5, "ECRS": 1.0, "NSPIN": 4.0}
# Effective max MW per product:
#   DA-side: HSL only (BESS can stage SoC over the day to meet hourly bids)
#   RT-side: HSL ∧ (SOC_MWH / SOC_DURATION_H)  — SoC must be physically held at decision time
RT_MAX_MW = {p: min(HSL_MW, SOC_MWH / SOC_DURATION_H[p]) for p in PRODUCTS}
DA_MAX_MW = {p: HSL_MW for p in PRODUCTS}
# → RRS=100, ECRS=100, NSPIN=50 (Non-Spinning Reserve is SoC-constrained)


def load_master() -> pd.DataFrame:
    df = pd.read_parquet(DERIVED / "master_hourly.parquet")
    df["datetime_ct"] = pd.to_datetime(df["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
    df["date"] = df["datetime_ct"].dt.date
    df["he"] = df["datetime_ct"].dt.hour + 1
    df["dow"] = df["datetime_ct"].dt.dayofweek
    df["month"] = df["datetime_ct"].dt.month
    df["is_wknd"] = df["dow"].isin([5, 6]).astype(int)
    # D-1 features percentiles within HE (rank pct so always 0..1)
    df["netload_fc_pct"] = df.groupby("he")["NET_LOAD_FORECAST_BID_CLOSE"].rank(pct=True)
    df["wind_fc_pct"]    = df.groupby("he")["WIND_STWPF_BIDCLOSE"].rank(pct=True)
    df["solar_fc_pct"]   = df.groupby("he")["SOLAR_COPHSL_BIDCLOSE"].rank(pct=True)
    for p in PRODUCTS:
        col = f"AS_MCPC_{p}"
        df[f"da_{p}_pct"] = df.groupby("he")[col].rank(pct=True)

    # ----- Merge Tenaska HSL (Generator-Performance) — true GKS HSL baseline -----
    # Tenaska Telemetered_HSL_5_Min aggregated to hourly = the actual operational HSL.
    # Use this instead of Smartbidder avail_discharge_mw (which is a forward forecast).
    thsl_path = DERIVED / "tenaska_hsl_hourly.parquet"
    if thsl_path.exists():
        thsl = pd.read_parquet(thsl_path)
        thsl["datetime_ct"] = pd.to_datetime(thsl["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
        df = df.merge(thsl, on="datetime_ct", how="left")
        # Where Tenaska HSL is missing, fall back to Smartbidder
        df["hsl_primary"] = df["tenaska_hsl_telemetered"].combine_first(df["avail_discharge_mw"])
    else:
        df["hsl_primary"] = df["avail_discharge_mw"]

    # ----- Merge RT AS imbalance amounts per product (from ERCOT 60-day disclosure) -----
    # Tenaska's "energy_as_detail" endpoint returns RT_Ancillary_Imbalance_Amt as a single bucket
    # and currently $0 for GKS — likely because the data feed is incomplete for this field.
    # Script #72 fetched per-product RT AS imbalance amounts. We sum to hourly and join here.
    rt_imb_path = DERIVED / "rt_as_revenue_15min.parquet"
    if rt_imb_path.exists():
        ri = pd.read_parquet(rt_imb_path)
        ri["datetime_ct"] = pd.to_datetime(ri["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
        ri["hour_ct"] = ri["datetime_ct"].dt.floor("h")
        code_map = {"RTRRIMBAMT": "RT_IMB_RRS", "RTECRIMBAMT": "RT_IMB_ECRS", "RTNSIMBAMT": "RT_IMB_NSPIN"}
        ri = ri[ri["charge_code"].isin(code_map)].copy()
        ri["product"] = ri["charge_code"].map(code_map)
        hourly = ri.groupby(["hour_ct", "product"])["value"].sum().unstack(fill_value=0.0).reset_index()
        hourly = hourly.rename(columns={"hour_ct": "datetime_ct"})
        df = df.merge(hourly, on="datetime_ct", how="left")
        for c in ["RT_IMB_RRS", "RT_IMB_ECRS", "RT_IMB_NSPIN"]:
            if c not in df.columns:
                df[c] = 0.0
            df[c] = df[c].fillna(0.0)
    else:
        for c in ["RT_IMB_RRS", "RT_IMB_ECRS", "RT_IMB_NSPIN"]:
            df[c] = 0.0
    return df


# -----------------------------------------------------------------------------
# Q1 spread time series + distribution
# -----------------------------------------------------------------------------
def section_q1(df: pd.DataFrame) -> dict:
    out: dict = {"products": {}}
    for p in PRODUCTS:
        d = df[f"AS_SPREAD_{p}"]
        da = df[f"AS_MCPC_{p}"]
        rt = df[f"RT_AS_MCPC_{p}"]
        # daily mean spread (and per HE heatmap)
        daily = df.groupby("date").agg(
            spread_mean=(f"AS_SPREAD_{p}", "mean"),
            da_mean=(f"AS_MCPC_{p}", "mean"),
            rt_mean=(f"RT_AS_MCPC_{p}", "mean"),
        ).reset_index()
        # HE heatmap (HE × DOW)  --> mean spread
        hod_dow = df.pivot_table(
            index="he", columns="dow", values=f"AS_SPREAD_{p}", aggfunc="mean"
        ).round(2)
        # day-of-week labels 0=Mon..6=Sun
        # percentile distribution (for histogram)
        bins = [-np.inf, -50, -20, -10, -5, -2, -1, 0, 1, 2, 5, 10, 20, 50, 100, np.inf]
        labels = ["< -50", "-50~-20", "-20~-10", "-10~-5", "-5~-2", "-2~-1",
                  "-1~0", "0~1", "1~2", "2~5", "5~10", "10~20", "20~50",
                  "50~100", "> 100"]
        cuts = pd.cut(d, bins=bins, labels=labels, include_lowest=True)
        hist = cuts.value_counts().reindex(labels, fill_value=0).astype(int).to_dict()
        out["products"][p] = {
            "hours":   int(len(d)),
            "da_mean": round(float(da.mean()), 3),
            "rt_mean": round(float(rt.mean()), 3),
            "spread_mean":   round(float(d.mean()), 3),
            "spread_median": round(float(d.median()), 3),
            "spread_p01":    round(float(d.quantile(0.01)), 3),
            "spread_p05":    round(float(d.quantile(0.05)), 3),
            "spread_p95":    round(float(d.quantile(0.95)), 3),
            "spread_p99":    round(float(d.quantile(0.99)), 3),
            "spread_min":    round(float(d.min()), 3),
            "spread_max":    round(float(d.max()), 3),
            "neg_share":     round(float((d < 0).mean()), 4),
            "sev_neg_share": round(float((d < -SEVERE[p]).mean()), 4),
            "daily_series": [
                {"date": str(r["date"]),
                 "spread": round(float(r["spread_mean"]), 3),
                 "da": round(float(r["da_mean"]), 3),
                 "rt": round(float(r["rt_mean"]), 3)}
                for _, r in daily.iterrows()
            ],
            "hod_dow_heatmap": [
                [None if pd.isna(hod_dow.loc[he, dw]) else float(hod_dow.loc[he, dw])
                 for dw in range(7)]
                for he in range(1, 25)
            ],
            "histogram": hist,
        }
    return out


# -----------------------------------------------------------------------------
# Q2 negative-spread profile
# -----------------------------------------------------------------------------
def section_q2(df: pd.DataFrame) -> dict:
    out: dict = {"products": {}}
    for p in PRODUCTS:
        spread = df[f"AS_SPREAD_{p}"]
        neg = spread < 0
        sev_thr = -SEVERE[p]
        sev = spread < sev_thr
        d2 = df.assign(neg=neg, sev=sev,
                       damage=-spread.clip(upper=0) * HSL_MW)  # $ damage if 100MW awarded

        # P(neg) by HE / DOW / month
        p_he   = d2.groupby("he")["neg"].mean().mul(100).round(1).to_dict()
        p_dow  = d2.groupby("dow")["neg"].mean().mul(100).round(1).to_dict()
        p_month= d2.groupby("month")["neg"].mean().mul(100).round(1).to_dict()

        # ─────────────────────────────────────────────────────────────────────
        # ROOT-CAUSE attribution (2026-05-19 user request: actual causes, not results)
        # ─────────────────────────────────────────────────────────────────────
        # SPIKE definitions:
        #   "RT spike"  = RT MCPC (energy or AS) above top-5% (p95) of distribution.
        #                 This is the RESULT, not cause — we report it for context only.
        # ROOT-CAUSE definitions (these explain WHY the RT spike happened):
        #   "Wind generation 부족":
        #     ((WIND_RTI − WIND_STWPF_BIDCLOSE) / WIND_STWPF_BIDCLOSE) < −10%
        #     = 실측 wind 가 D-1 bid-close forecast 대비 10% 이상 부족 (wind bust).
        #     ERCOT 의 RT 가격 spike 의 가장 흔한 root cause.
        #   "Load surge":
        #     ((RTLOAD − LOAD_FORECAST) / LOAD_FORECAST) > +3%
        #     = 실측 load 가 forecast 대비 3% 이상 초과 (heat wave, cold snap, 통계오차).
        #   "Net-load surprise":
        #     Wind 부족 + Load surge 동시 발생 — 가장 강한 scarcity 신호.
        #   "Storm/extreme weather":
        #     특정 known event 날짜 (Winter Storm Fern 2026-01-24~28 등).
        #   "Solar drop (proxy)":
        #     해당 HE 의 SOLAR_COPHSL_BIDCLOSE 가 그 HE 분포의 하위 20%
        #     = forecast 가 이미 낮음 → 일출/일몰 전후 또는 cloud event 가능성.
        #   "Day-Ahead mis-pricing":
        #     DA MCPC < $0.5/MWh — DA 시장이 풍족 가격으로 cleared 됐는데 RT 에서 scarcity.
        #     ERCOT DA AS 수요 모델의 forecast bust.
        #   "Multi-hour event":
        #     같은 day 에 3개 이상 시간이 모두 negative spread → 일시적 spike 가 아닌 systemic event.
        # ─────────────────────────────────────────────────────────────────────
        STORM_DATES = {  # known extreme-weather events (added per analysis)
            pd.Timestamp("2026-01-24").date(),
            pd.Timestamp("2026-01-25").date(),
            pd.Timestamp("2026-01-26").date(),
            pd.Timestamp("2026-01-27").date(),
            pd.Timestamp("2026-01-28").date(),
        }
        # Pre-compute multi-hour-event days (3+ neg hours for this product)
        neg_by_date = d2.groupby("date")["neg"].sum()
        multi_hour_days = set(neg_by_date[neg_by_date >= 3].index)
        # Pre-compute solar percentile within each HE
        solar_by_he = df.groupby("he")["SOLAR_COPHSL_BIDCLOSE"].rank(pct=True)
        solar_pct = solar_by_he.to_dict()

        # top severe events (single hours) — sorted by absolute spread magnitude
        sev_rows = d2[sev].copy()
        sev_rows["spread"] = sev_rows[f"AS_SPREAD_{p}"]
        sev_rows = sev_rows.sort_values("spread").head(20)

        def root_causes(row) -> tuple[list[str], str]:
            """Return (causes_list, primary_cause). Causes = WHY; not just RT-spike result."""
            causes = []
            # Wind generation bust
            wind_fc = row.get("WIND_STWPF_BIDCLOSE")
            wind_actual = row.get("WIND_RTI")
            wind_bust_pct = None
            if pd.notna(wind_fc) and wind_fc > 0 and pd.notna(wind_actual):
                wind_bust_pct = (wind_actual - wind_fc) / wind_fc * 100
                if wind_bust_pct < -10:
                    causes.append(f"Wind 부족 ({wind_bust_pct:+.0f}% vs FC)")
            # Load surge
            load_fc = row.get("LOAD_FORECAST")
            load_actual = row.get("RTLOAD")
            load_surge_pct = None
            if pd.notna(load_fc) and load_fc > 0 and pd.notna(load_actual):
                load_surge_pct = (load_actual - load_fc) / load_fc * 100
                if load_surge_pct > 3:
                    causes.append(f"Load surge ({load_surge_pct:+.1f}% vs FC)")
            # Storm date
            if row["date"] in STORM_DATES:
                causes.append("Winter Storm Fern (1/24-28)")
            # Solar drop proxy
            sp = solar_pct.get(row.name)
            if sp is not None and sp < 0.20:
                causes.append("Solar 낮음 (해당 HE 하위 20%)")
            # DA mis-pricing
            if row[f"AS_MCPC_{p}"] < 0.5:
                causes.append("DA MCPC < $0.5 (DA 시장 forecast bust)")
            # Multi-hour day
            if row["date"] in multi_hour_days:
                causes.append(f"Multi-hour event (이 날 음수 spread {int(neg_by_date.loc[row['date']])} 시간)")
            # Determine primary (most likely root)
            primary = "Unclassified"
            if wind_bust_pct is not None and load_surge_pct is not None and wind_bust_pct < -10 and load_surge_pct > 3:
                primary = "Net-load surprise (wind 부족 + load surge)"
            elif wind_bust_pct is not None and wind_bust_pct < -10:
                primary = "Wind 부족"
            elif load_surge_pct is not None and load_surge_pct > 3:
                primary = "Load surge"
            elif row["date"] in STORM_DATES:
                primary = "Winter Storm"
            elif row[f"AS_MCPC_{p}"] < 0.5:
                primary = "DA forecast bust (mis-pricing)"
            elif sp is not None and sp < 0.20:
                primary = "Solar 부족 시간대"
            return causes, primary

        events = []
        for _, r in sev_rows.iterrows():
            causes, primary = root_causes(r)
            # Wind / load forecast error values for table display
            wind_fc = r.get("WIND_STWPF_BIDCLOSE"); wind_actual = r.get("WIND_RTI")
            load_fc = r.get("LOAD_FORECAST"); load_actual = r.get("RTLOAD")
            wind_err_pct = ((wind_actual - wind_fc) / wind_fc * 100
                            if pd.notna(wind_fc) and wind_fc > 0 and pd.notna(wind_actual) else None)
            load_err_pct = ((load_actual - load_fc) / load_fc * 100
                            if pd.notna(load_fc) and load_fc > 0 and pd.notna(load_actual) else None)
            events.append({
                "datetime":       str(r["datetime_ct"]),
                "he":             int(r["he"]),
                "da":             round(float(r[f"AS_MCPC_{p}"]), 2),
                "rt":             round(float(r[f"RT_AS_MCPC_{p}"]), 2),
                "spread":         round(float(r["spread"]), 2),
                "damage_100mw":   round(float(r["damage"]), 0),
                "rt_lmp":         round(float(r["RTLMP_GKS_BESS_RN"]), 2)
                                  if pd.notna(r.get("RTLMP_GKS_BESS_RN")) else None,
                "wind_err_pct":   round(float(wind_err_pct), 1) if wind_err_pct is not None else None,
                "load_err_pct":   round(float(load_err_pct), 2) if load_err_pct is not None else None,
                "primary_cause":  primary,
                "causes":         causes,
            })

        # ALSO: aggregate root-cause attribution across ALL severe-neg hours (not just top 20)
        cause_summary = {"Wind 부족": 0, "Load surge": 0, "Net-load surprise": 0,
                         "Winter Storm": 0, "DA forecast bust (mis-pricing)": 0,
                         "Solar 부족 시간대": 0, "Unclassified": 0}
        for _, r in d2[d2["sev"]].iterrows():
            _, prim = root_causes(r)
            cause_summary[prim] = cause_summary.get(prim, 0) + 1
        total_sev = max(sum(cause_summary.values()), 1)
        cause_summary_pct = {k: round(v / total_sev * 100, 1) for k, v in cause_summary.items()}

        # damage day ranking — sum |neg spread| × 100MW per day
        d2["loss_dollar"] = -spread.clip(upper=0) * HSL_MW
        damage_by_day = d2.groupby("date")["loss_dollar"].sum().sort_values(ascending=False).head(15)
        damage_days = [
            {"date": str(dt),
             "loss": round(float(v), 0),
             "n_neg_hours": int(d2[(d2["date"] == dt) & (d2["neg"])].shape[0])}
            for dt, v in damage_by_day.items()
        ]

        out["products"][p] = {
            "p_neg_overall":  round(float(neg.mean()) * 100, 1),
            "p_sev_overall":  round(float(sev.mean()) * 100, 1),
            "total_damage_$": round(float(d2["loss_dollar"].sum()), 0),
            "p_neg_by_he":    p_he,
            "p_neg_by_dow":   p_dow,
            "p_neg_by_month": p_month,
            "severe_events":  events,
            "damage_days":    damage_days,
            "severity_threshold": SEVERE[p],
            "root_cause_summary":     cause_summary,
            "root_cause_summary_pct": cause_summary_pct,
            "n_severe_events_total":  int(d2["sev"].sum()),
        }
    return out


# -----------------------------------------------------------------------------
# Q3 D-1 negative flag logit
# -----------------------------------------------------------------------------
def section_q3(df: pd.DataFrame) -> dict:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score, confusion_matrix, precision_recall_curve

    out: dict = {"products": {}}
    for p in PRODUCTS:
        y = (df[f"AS_SPREAD_{p}"] < 0).astype(int).values
        feats = ["netload_fc_pct", "wind_fc_pct", "solar_fc_pct", f"da_{p}_pct"]
        X = df[feats].copy()
        X["he_sin"] = np.sin(2 * np.pi * df["he"] / 24)
        X["he_cos"] = np.cos(2 * np.pi * df["he"] / 24)
        X = X.fillna(X.median())

        m = LogisticRegression(max_iter=2000, class_weight="balanced").fit(X, y)
        prob = m.predict_proba(X)[:, 1]
        auc = float(roc_auc_score(y, prob))
        # top-decile lift
        dec = pd.qcut(prob, 10, labels=False, duplicates="drop")
        topdec = float(y[dec == dec.max()].mean())
        base = float(y.mean())
        # find best F1 threshold
        prec, rec, thr = precision_recall_curve(y, prob)
        f1 = 2 * prec * rec / (prec + rec + 1e-9)
        idx = int(np.nanargmax(f1[:-1])) if len(thr) else 0
        best_thr = float(thr[idx]) if len(thr) else 0.5
        yhat = (prob >= best_thr).astype(int)
        cm = confusion_matrix(y, yhat).tolist()  # [[TN,FP],[FN,TP]]
        # also evaluate at a "conservative" threshold (top-decile) and "aggressive" (top-quartile)
        thr_top10 = float(np.quantile(prob, 0.90))
        thr_top25 = float(np.quantile(prob, 0.75))
        def stats_at(t: float):
            yh = (prob >= t).astype(int)
            tp = int(((yh == 1) & (y == 1)).sum()); fp = int(((yh == 1) & (y == 0)).sum())
            fn = int(((yh == 0) & (y == 1)).sum()); tn = int(((yh == 0) & (y == 0)).sum())
            prec_ = tp / max(tp + fp, 1); rec_ = tp / max(tp + fn, 1)
            return {"threshold": round(t, 3),
                    "alarm_rate": round((tp + fp) / len(y), 3),
                    "precision":  round(prec_, 3),
                    "recall":     round(rec_, 3),
                    "f1":         round(2*prec_*rec_/max(prec_+rec_, 1e-9), 3)}

        # day-of-day prob series (max P(neg) within the day, for the dashboard time-series)
        df_tmp = df.assign(prob=prob)
        daily_prob = df_tmp.groupby("date")["prob"].max().reset_index()
        daily_prob_series = [{"date": str(r["date"]), "prob": round(float(r["prob"]), 3)}
                             for _, r in daily_prob.iterrows()]

        out["products"][p] = {
            "feature_list": list(X.columns),
            "coefficients": {c: round(float(v), 3) for c, v in zip(X.columns, m.coef_[0])},
            "intercept":    round(float(m.intercept_[0]), 3),
            "auc":          round(auc, 3),
            "base_rate":    round(base * 100, 1),
            "top_decile_hit": round(topdec * 100, 1),
            "top_decile_lift": round(topdec / max(base, 1e-9), 2),
            "best_f1_threshold": round(best_thr, 3),
            "best_f1_cm": cm,
            "operating_points": {
                "best_f1": stats_at(best_thr),
                "top10":   stats_at(thr_top10),
                "top25":   stats_at(thr_top25),
            },
            "daily_max_prob_series": daily_prob_series,
        }
    return out


# -----------------------------------------------------------------------------
# Q4 optimal DA/RT split — TIME-VARYING HSL (Smartbidder availability) +
#                          product-specific SoC duration cap for Real-Time
# -----------------------------------------------------------------------------
def section_q4(df: pd.DataFrame, q3: dict) -> dict:
    # Time-varying HSL — Tenaska Telemetered (primary) + SoC from Smartbidder
    hsl_arr_full = df["hsl_primary"].fillna(HSL_MW).values          # Tenaska > Smartbidder fallback
    soc_arr_full = df["soc_mwh_max"].fillna(SOC_MWH).values
    pct_hsl_full = float((hsl_arr_full >= HSL_MW * 0.99).mean()) * 100
    pct_hsl_zero = float((hsl_arr_full == 0).mean()) * 100
    avg_hsl      = float(hsl_arr_full.mean())

    # ----- Monthly GKS AS revenue breakdown (for verification) -----
    df_tk = df[df["GKS_DA_NS_Amt"].notna()].copy()
    df_tk["month"] = df_tk["datetime_ct"].dt.strftime("%Y-%m")
    products_monthly: list[dict] = []
    for month, g in df_tk.groupby("month"):
        row = {"month": month, "n_days": int(g["datetime_ct"].dt.date.nunique())}
        total_gross = total_imb = 0.0
        for p, amt_c, imb_c in [("RRS","GKS_DA_RRS_Amt","RT_IMB_RRS"),
                                ("ECRS","GKS_DA_ECRS_Amt","RT_IMB_ECRS"),
                                ("NSPIN","GKS_DA_NS_Amt","RT_IMB_NSPIN")]:
            gross = float(g[amt_c].sum()) if amt_c in g else 0.0
            imb_p = float(g[imb_c].sum()) if imb_c in g else 0.0
            row[f"{p}_gross"] = round(gross, 0)
            row[f"{p}_imb"]   = round(imb_p, 0)
            row[f"{p}_net"]   = round(gross - imb_p, 0)
            total_gross += gross; total_imb += imb_p
        row["TOTAL_gross"] = round(total_gross, 0)
        row["TOTAL_imb"]   = round(total_imb, 0)
        row["TOTAL_net"]   = round(total_gross - total_imb, 0)
        products_monthly.append(row)

    out: dict = {
        "products": {},
        "monthly_gks_revenue": products_monthly,
        "battery_assumption": {
            "hsl_nameplate_mw":      HSL_MW,
            "soc_nameplate_mwh":     SOC_MWH,
            "soc_duration_hours":    SOC_DURATION_H,
            "hsl_time_varying":      True,
            "hsl_avg_mw":            round(avg_hsl, 1),
            "hsl_full_pct_of_hours": round(pct_hsl_full, 1),
            "hsl_zero_pct_of_hours": round(pct_hsl_zero, 1),
            "explanation": (
                f"Battery nameplate = {HSL_MW:.0f} MW / {SOC_MWH:.0f} MWh. "
                f"HSL = Tenaska Telemetered_HSL_5_Min (시간별, primary), Smartbidder fallback. "
                f"평균 HSL {avg_hsl:.0f} MW, 100 MW 풀가용 {pct_hsl_full:.0f}%, 0 MW outage {pct_hsl_zero:.0f}%. "
                "Day-Ahead 참여 cap (시간별) = Tenaska HSL[t]. "
                "Real-Time 참여 cap = min(Tenaska HSL[t], soc_mwh_max[t] / SoC duration per product)."
            ),
        },
    }

    for p in PRODUCTS:
        # ---- GKS actual revenue ----
        gks_amt_col = {"RRS": "GKS_DA_RRS_Amt", "ECRS": "GKS_DA_ECRS_Amt", "NSPIN": "GKS_DA_NS_Amt"}[p]
        gks_qty_col = {"RRS": "GKS_Gen_RRS_Qty", "ECRS": "GKS_Gen_ECRS_Qty", "NSPIN": "GKS_Gen_NS_Qty"}[p]
        gks_imb_col = {"RRS": "RT_IMB_RRS",     "ECRS": "RT_IMB_ECRS",     "NSPIN": "RT_IMB_NSPIN"}[p]
        gks_da_qty_arr = df[gks_qty_col].fillna(0).values if gks_qty_col in df else np.zeros(len(df))
        gks_gross_da_revenue = float(df[gks_amt_col].sum()) if gks_amt_col in df else 0.0
        gks_net_da_revenue   = float((gks_da_qty_arr * df[f"AS_SPREAD_{p}"].values).sum())
        # NOTE (2026-05-18 user 검증): ERCOT charge code *IMBAMT 는 RT 부족 delivery 시 GKS 가
        # 지불하는 charge (debit). 데이터에선 양수로 잡혔지만 settlement 부호는 음수 → 매출에서 차감.
        gks_rt_as_imbalance_paid = float(df[gks_imb_col].sum()) if gks_imb_col in df else 0.0
        gks_total_actual_as_revenue = gks_gross_da_revenue - gks_rt_as_imbalance_paid
        gks_avg_bid_when_active = float(gks_da_qty_arr[gks_da_qty_arr > 0].mean()) \
                                  if (gks_da_qty_arr > 0).any() else 0.0
        gks_hours_with_bid = int((gks_da_qty_arr > 0).sum())
        gks_participation_pct = float((gks_da_qty_arr > 0).mean()) * 100

        # ---- D-1 logit probability ----
        from sklearn.linear_model import LogisticRegression
        feats = ["netload_fc_pct", "wind_fc_pct", "solar_fc_pct", f"da_{p}_pct"]
        X = df[feats].copy()
        X["he_sin"] = np.sin(2 * np.pi * df["he"] / 24)
        X["he_cos"] = np.cos(2 * np.pi * df["he"] / 24)
        X = X.fillna(X.median())
        y = (df[f"AS_SPREAD_{p}"] < 0).astype(int).values
        m = LogisticRegression(max_iter=2000, class_weight="balanced").fit(X, y)
        prob = m.predict_proba(X)[:, 1]
        thr = q3["products"][p]["best_f1_threshold"]

        # ---- TIME-VARYING MW caps ----
        da_cap_arr = hsl_arr_full                                          # = avail_discharge_mw[t]
        rt_cap_arr = np.minimum(hsl_arr_full, soc_arr_full / SOC_DURATION_H[p])
        avg_da_cap = float(da_cap_arr.mean())
        avg_rt_cap = float(rt_cap_arr.mean())
        # binding diagnostic: when avail SoC < HSL, SoC is binding for RT
        rt_soc_binding_share = float(((soc_arr_full / SOC_DURATION_H[p]) < hsl_arr_full).mean()) * 100

        spread_arr = df[f"AS_SPREAD_{p}"].values    # = DAM_MCPC − RT_AS_MCPC
        rt_as_arr  = df[f"RT_AS_MCPC_{p}"].values

        # ---- Strategy 1: Day-Ahead 100% (with full RT buyback), time-varying HSL ----
        naive_da100_net = float((da_cap_arr * spread_arr).sum())

        # ---- Strategy 2: Real-Time 100%, time-varying SoC-capped MW ----
        naive_rt100 = float((rt_cap_arr * rt_as_arr).sum())

        # ---- Strategy 3: Binary D-1 Flag Rule ----
        def rule_total(t: float) -> float:
            s = (prob < t).astype(float)
            return float((s * da_cap_arr * spread_arr).sum()
                       + ((1 - s) * rt_cap_arr * rt_as_arr).sum())
        ts = np.linspace(0.05, 0.99, 95)
        rev = np.array([rule_total(t) for t in ts])
        best_idx = int(np.argmax(rev))
        best_thr_rev = float(ts[best_idx])
        bin_total = float(rev[best_idx])
        bin_at_f1 = rule_total(thr)
        bin_da_share = float((prob < best_thr_rev).mean())

        # ---- Strategy 4: 3-tier Heuristic ----
        thr_low  = thr
        thr_high = max(thr * 1.5, float(np.quantile(prob, 0.85)))
        tier_share = np.where(prob >= thr_high, 0.0,
                      np.where(prob >= thr_low, 0.5, 1.0))
        tier_total = float((tier_share * da_cap_arr * spread_arr).sum()
                         + ((1 - tier_share) * rt_cap_arr * rt_as_arr).sum())
        tier_da_share = float(tier_share.mean())

        # ---- Strategy 5: Oracle ----
        da_revenue_arr = da_cap_arr * spread_arr
        rt_revenue_arr = rt_cap_arr * rt_as_arr
        oracle_take_da = da_revenue_arr > rt_revenue_arr
        oracle_total = float(np.where(oracle_take_da, da_revenue_arr, rt_revenue_arr).sum())
        oracle_da_share = float(oracle_take_da.mean())

        better_naive = max(naive_da100_net, naive_rt100)
        better_naive_label = ("Day-Ahead 100% (with buyback)"
                              if naive_da100_net >= naive_rt100 else "Real-Time 100%")

        out["products"][p] = {
            # GKS actual revenue (all components)
            "gks_gross_da_as_revenue":      round(gks_gross_da_revenue, 0),
            "gks_net_da_as_revenue":        round(gks_net_da_revenue, 0),
            "gks_rt_as_imbalance_paid":     round(gks_rt_as_imbalance_paid, 0),
            "gks_total_actual_as_revenue":  round(gks_total_actual_as_revenue, 0),
            "gks_avg_bid_mw_when_active":   round(gks_avg_bid_when_active, 1),
            "gks_hours_with_bid":           gks_hours_with_bid,
            "gks_participation_pct":        round(gks_participation_pct, 1),
            # MW base diagnostics (time-varying)
            "da_cap_avg_mw":                round(avg_da_cap, 1),
            "rt_cap_avg_mw":                round(avg_rt_cap, 1),
            "rt_soc_binding_pct_of_hours":  round(rt_soc_binding_share, 1),
            "soc_duration_h":               SOC_DURATION_H[p],
            "assumption_note": (
                "Day-Ahead 매도분 Real-Time 100% buyback 가정; 순 Day-Ahead 매출 = bid MW × spread. "
                "MW base = 시간변동 Smartbidder availability (DA cap = avail, RT cap = min(avail, soc/duration))."
            ),
            "strategies": {
                "naive_day_ahead_100pct_with_buyback": {
                    "description": (
                        f"매시간 가용 HSL 전량 (avail_discharge_mw[t], 평균 {avg_da_cap:.0f} MW) 을 Day-Ahead에 sell, "
                        f"Real-Time에서 100% buyback. 순매출 = MW[t] × spread[t]."
                    ),
                    "mw_per_hour_avg":     round(avg_da_cap, 1),
                    "revenue_usd":         round(naive_da100_net, 0),
                    "day_ahead_share_pct": 100.0,
                },
                "naive_real_time_100pct": {
                    "description": (
                        f"Day-Ahead에 입찰하지 않고 매시간 SoC-cap MW (평균 {avg_rt_cap:.0f} MW) 를 Real-Time에 sell. "
                        f"매출 = MW[t] × Real-Time MCPC[t]."
                    ),
                    "mw_per_hour_avg":     round(avg_rt_cap, 1),
                    "revenue_usd":         round(naive_rt100, 0),
                    "day_ahead_share_pct": 0.0,
                },
                "binary_d1_flag_rule": {
                    "description": (
                        f"D-1 Logistic Regression 의 P(negative spread) < τ* 일 때 Day-Ahead, "
                        f"그 외 Real-Time. τ*는 95개 threshold sweep 에서 매출 최대화점."
                    ),
                    "tau_star":               round(best_thr_rev, 3),
                    "revenue_usd":            round(bin_total, 0),
                    "revenue_at_best_f1_thr": round(bin_at_f1, 0),
                    "day_ahead_share_pct":    round(bin_da_share * 100, 1),
                },
                "three_tier_heuristic": {
                    "description": (
                        f"P(neg) < {thr_low:.2f} ⇒ 100% Day-Ahead · "
                        f"{thr_low:.2f} ≤ P(neg) < {thr_high:.2f} ⇒ 50%/50% mix · "
                        f"P(neg) ≥ {thr_high:.2f} ⇒ 100% Real-Time"
                    ),
                    "tau_low":             round(float(thr_low), 3),
                    "tau_high":            round(float(thr_high), 3),
                    "revenue_usd":         round(tier_total, 0),
                    "day_ahead_share_pct": round(tier_da_share * 100, 1),
                },
                "oracle_perfect_foresight": {
                    "description": (
                        "매시간 정답을 알 때 Day-Ahead (avail × spread) 와 Real-Time (SoC-cap × RT_MCPC) 중 큰 쪽 선택. "
                        "Binary rule family 의 이론 상한."
                    ),
                    "revenue_usd":         round(oracle_total, 0),
                    "day_ahead_share_pct": round(oracle_da_share * 100, 1),
                },
            },
            "capture_metrics": {
                "binary_capture_of_oracle_pct":    round(bin_total / oracle_total * 100, 1) if oracle_total else None,
                "three_tier_capture_of_oracle_pct":round(tier_total / oracle_total * 100, 1) if oracle_total else None,
                "da100_capture_of_oracle_pct":     round(naive_da100_net / oracle_total * 100, 1) if oracle_total else None,
                "rt100_capture_of_oracle_pct":     round(naive_rt100 / oracle_total * 100, 1) if oracle_total else None,
                "gks_net_da_capture_of_oracle_pct":     round(gks_net_da_revenue / oracle_total * 100, 1) if oracle_total else None,
                "gks_total_actual_capture_of_oracle_pct": round(gks_total_actual_as_revenue / oracle_total * 100, 1) if oracle_total else None,
                "binary_uplift_vs_better_naive_pct": round((bin_total / better_naive - 1) * 100, 2) if better_naive else None,
                "better_naive_label":              better_naive_label,
            },
        }
    return out


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main() -> None:
    print("[80_as_spread_dashboard_data]")
    df = load_master()
    print(f"  rows: {len(df)}, range {df['datetime_ct'].min()} ~ {df['datetime_ct'].max()}")

    print("  Q1 spread series ...")
    q1 = section_q1(df)
    print("  Q2 negative profile ...")
    q2 = section_q2(df)
    print("  Q3 D-1 flag logit ...")
    q3 = section_q3(df)
    print("  Q4 optimal split ...")
    q4 = section_q4(df, q3)

    q5_path = DERIVED / "q5_product_mix.json"
    q5 = json.loads(q5_path.read_text(encoding="utf-8")) if q5_path.exists() else {}
    q6_path = DERIVED / "q6_winner_characterization.json"
    q6 = json.loads(q6_path.read_text(encoding="utf-8")) if q6_path.exists() else {}
    q7_path = DERIVED / "q7_hsl_sensitivity.json"
    q7 = json.loads(q7_path.read_text(encoding="utf-8")) if q7_path.exists() else {}
    q8_path = DERIVED / "q8_gks_vs_optimal.json"
    q8 = json.loads(q8_path.read_text(encoding="utf-8")) if q8_path.exists() else {}
    q9_path = DERIVED / "q9_filtered_comparison.json"
    q9 = json.loads(q9_path.read_text(encoding="utf-8")) if q9_path.exists() else {}
    q10_path = DERIVED / "q10_situational_playbook.json"
    q10 = json.loads(q10_path.read_text(encoding="utf-8")) if q10_path.exists() else {}
    q11_path = DERIVED / "q11_playbook_upside.json"
    q11 = json.loads(q11_path.read_text(encoding="utf-8")) if q11_path.exists() else {}
    q12_path = DERIVED / "q12_daily_strategy_series.json"
    q12 = json.loads(q12_path.read_text(encoding="utf-8")) if q12_path.exists() else {}
    q13_path = DERIVED / "q13_playbook_hourly_mix.json"
    q13 = json.loads(q13_path.read_text(encoding="utf-8")) if q13_path.exists() else {}

    payload = {
        "generated_at": pd.Timestamp.now(tz="America/Chicago").isoformat(),
        "data_range": [str(df["datetime_ct"].min()), str(df["datetime_ct"].max())],
        "n_hours": int(len(df)),
        "n_days":  int(df["date"].nunique()),
        "products": PRODUCTS,
        "severity_threshold_$/mwh": SEVERE,
        "Q1_spread_series":      q1,
        "Q2_negative_profile":   q2,
        "Q3_flag_logit":         q3,
        "Q4_optimal_split":      q4,
        "Q5_product_mix":        q5,
        "Q6_winner_chars":       q6,
        "Q7_hsl_sensitivity":    q7,
        "Q8_gks_vs_optimal":     q8,
        "Q9_filtered_comparison":q9,
        "Q10_playbook":          q10,
        "Q11_playbook_upside":   q11,
        "Q12_daily_strategy":    q12,
        "Q13_playbook_mix":      q13,
    }
    out_path = DERIVED / "as_spread_dashboard_data.json"
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    sz_kb = out_path.stat().st_size / 1024
    print(f"  saved -> {out_path.name}  ({sz_kb:.1f} KB)")


if __name__ == "__main__":
    main()
