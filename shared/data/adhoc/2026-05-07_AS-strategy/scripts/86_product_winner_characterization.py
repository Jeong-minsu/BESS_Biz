"""
#86 — When does RRS or ECRS beat NSPIN? (Q6 follow-up to Q5)

For each hour categorize by spread winner (max of spread_RRS / spread_ECRS / spread_NSPIN).
Profile each cohort by HE, DOW, month, net-load FC, wind FC, solar FC, DA MCPC.
Build D-1 multinomial logit predicting winner.

Outputs:
  derived/q6_winner_characterization.json
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
m["he"]    = m["datetime_ct"].dt.hour + 1
m["dow"]   = m["datetime_ct"].dt.dayofweek
m["month"] = m["datetime_ct"].dt.month
m["date"]  = m["datetime_ct"].dt.date

PRODS = ["RRS", "ECRS", "NSPIN"]

# Winner per hour (max spread)
spread_mat = m[[f"AS_SPREAD_{p}" for p in PRODS]].values
winner_idx = np.argmax(spread_mat, axis=1)
m["winner"] = [PRODS[i] for i in winner_idx]
m["winning_spread"]   = spread_mat[np.arange(len(m)), winner_idx]
m["nspin_spread"]     = m["AS_SPREAD_NSPIN"]
m["rrs_spread"]       = m["AS_SPREAD_RRS"]
m["ecrs_spread"]      = m["AS_SPREAD_ECRS"]
m["nspin_lead"]       = m["nspin_spread"] - np.maximum(m["rrs_spread"], m["ecrs_spread"])  # +ve = NSPIN won
m["rrs_lead"]         = m["rrs_spread"]   - np.maximum(m["nspin_spread"], m["ecrs_spread"])
m["ecrs_lead"]        = m["ecrs_spread"]  - np.maximum(m["nspin_spread"], m["rrs_spread"])

n = len(m)
print(f"Total hours: {n}")
print()
print("Winner distribution:")
for p in PRODS:
    cnt = (m["winner"] == p).sum()
    avg_lead = m.loc[m["winner"] == p, f"{p.lower()}_lead"].mean()
    print(f"  {p:6s}: {cnt:>5d} ({cnt/n*100:>4.1f}%)   avg winning margin = ${avg_lead:>5.2f}/MWh")
print()

# =============================================================================
# Profile each cohort
# =============================================================================
print("=" * 75)
print("COHORT PROFILES — descriptive stats per winner cohort")
print("=" * 75)

cohort_features = ["LOAD_FORECAST", "NET_LOAD_FORECAST_BID_CLOSE",
                   "WIND_STWPF_BIDCLOSE", "SOLAR_COPHSL_BIDCLOSE",
                   "AS_MCPC_RRS", "AS_MCPC_ECRS", "AS_MCPC_NSPIN",
                   "RT_AS_MCPC_RRS", "RT_AS_MCPC_ECRS", "RT_AS_MCPC_NSPIN",
                   "DALMP_GKS_BESS_RN", "RTLMP_GKS_BESS_RN", "spread_gks",
                   "load_fc_err", "wind_fc_err",
                   "he"]
prof = m.groupby("winner")[cohort_features].mean().T
prof = prof[PRODS]  # column order
prof["RRS_vs_NSPIN"] = prof["RRS"] - prof["NSPIN"]
prof["ECRS_vs_NSPIN"] = prof["ECRS"] - prof["NSPIN"]
print(prof.round(2).to_string())
print()

# HE distribution per winner — TWO views (user 2026-05-19 fix)
print("=" * 75)
print("Hour-Ending distribution — TWO views")
print("=" * 75)
# View 1: COLUMN-normalize → "Of all NSPIN winner hours, X% are at HE 22"
he_dist_col = pd.crosstab(m["he"], m["winner"], normalize="columns") * 100
he_dist_col = he_dist_col[PRODS].round(1)
print("\nView 1 — Column-normalize: of each winner's hours, % distribution across HE")
print(he_dist_col.to_string())

# View 2: ROW-normalize → "At HE 22, X% of hours had NSPIN as winner" (사용자가 기대한 것)
he_dist_row = pd.crosstab(m["he"], m["winner"], normalize="index") * 100
he_dist_row = he_dist_row[PRODS].round(1)
print("\nView 2 — Row-normalize: within each HE, % of hours each product was winner (sums to 100% per HE)")
print(he_dist_row.to_string())

# View 3: Absolute count
he_dist_abs = pd.crosstab(m["he"], m["winner"])
he_dist_abs = he_dist_abs[PRODS]
print("\nView 3 — Absolute counts: # hours each product was winner at each HE")
print(he_dist_abs.to_string())

# Use row-normalize for main display
he_dist = he_dist_col   # keep backward-compat name but expose all 3 via JSON below
print()

# Find HE where each product MOST DOMINANT (using row normalize)
print("Top HE for each winner (where it dominates the most — row-normalize % within HE):")
for p in PRODS:
    top_he = he_dist_row[p].sort_values(ascending=False).head(5)
    print(f"  {p:6s} top HE: " + ", ".join(f"HE{int(h)}({v:.0f}%)" for h, v in top_he.items()))
print()

# DOW
print("=" * 75)
print("Day-of-week distribution (% of cohort hours)")
print("=" * 75)
dow_dist = pd.crosstab(m["dow"], m["winner"], normalize="columns") * 100
dow_dist = dow_dist[PRODS].round(1)
dow_labels = ["월", "화", "수", "목", "금", "토", "일"]
dow_dist.index = [dow_labels[i] for i in dow_dist.index]
print(dow_dist.to_string())
print()

# Month
print("Month distribution (% of cohort hours):")
mo_dist = pd.crosstab(m["month"], m["winner"], normalize="columns") * 100
mo_dist = mo_dist[PRODS].round(1)
print(mo_dist.to_string())
print()

# =============================================================================
# Conditional probabilities — P(winner | feature quintile)
# =============================================================================
print("=" * 75)
print("CONDITIONAL P(winner) BY FEATURE QUINTILE")
print("=" * 75)
key_feats = ["LOAD_FORECAST", "NET_LOAD_FORECAST_BID_CLOSE",
             "WIND_STWPF_BIDCLOSE", "SOLAR_COPHSL_BIDCLOSE",
             "AS_MCPC_RRS", "AS_MCPC_NSPIN"]
for f in key_feats:
    try:
        q = pd.qcut(m[f], 5, labels=["Q1(low)","Q2","Q3","Q4","Q5(high)"], duplicates="drop")
    except ValueError:
        # too many duplicate values (e.g., solar at night) — fall back to rank-based binning
        ranks = m[f].rank(method="first")
        q = pd.qcut(ranks, 5, labels=["Q1(low)","Q2","Q3","Q4","Q5(high)"])
    ct = pd.crosstab(q, m["winner"], normalize="index") * 100
    ct = ct[PRODS].round(1)
    print(f"\n  By {f}:")
    print(ct.to_string())

# =============================================================================
# Multinomial logit — D-1 winner prediction
# =============================================================================
print()
print("=" * 75)
print("MULTINOMIAL LOGIT — D-1 winner prediction")
print("=" * 75)
print("Features: net-load FC pct (within HE), wind FC pct, solar FC pct,")
print("          DA MCPC pct per product, HE sin/cos")
print()

# Build D-1 feature percentiles per HE
m["netload_fc_pct"] = m.groupby("he")["NET_LOAD_FORECAST_BID_CLOSE"].rank(pct=True)
m["wind_fc_pct"]    = m.groupby("he")["WIND_STWPF_BIDCLOSE"].rank(pct=True)
m["solar_fc_pct"]   = m.groupby("he")["SOLAR_COPHSL_BIDCLOSE"].rank(pct=True)
for p in PRODS:
    m[f"da_{p.lower()}_pct"] = m.groupby("he")[f"AS_MCPC_{p}"].rank(pct=True)

X = m[["netload_fc_pct", "wind_fc_pct", "solar_fc_pct",
       "da_rrs_pct", "da_ecrs_pct", "da_nspin_pct"]].copy()
X["he_sin"] = np.sin(2 * np.pi * m["he"] / 24)
X["he_cos"] = np.cos(2 * np.pi * m["he"] / 24)
X = X.fillna(X.median())
y = m["winner"].values

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

clf = LogisticRegression(max_iter=2000, C=1.0, class_weight="balanced")
clf.fit(X, y)
yhat = clf.predict(X)
acc = accuracy_score(y, yhat)
print(f"In-sample accuracy: {acc*100:.1f}%   (base rate of mode {'NSPIN'}: {(y=='NSPIN').mean()*100:.1f}%)")
print()
print("Class-by-class report:")
print(classification_report(y, yhat, digits=3))
print("Confusion matrix (rows=true, cols=pred):")
cm = confusion_matrix(y, yhat, labels=PRODS)
print("              " + "  ".join(f"{p:>7s}" for p in PRODS))
for i, p in enumerate(PRODS):
    print(f"  true {p:6s}: " + "  ".join(f"{cm[i,j]:>7d}" for j in range(3)))
print()

# Coefficient summary
print("Logit coefficients (per class — positive = increases that class probability):")
class_order = clf.classes_
print(f"               {'   '.join(f'{c:>9s}' for c in class_order)}")
for j, f in enumerate(X.columns):
    coefs = clf.coef_[:, j]
    print(f"  {f:18s} " + "  ".join(f"{v:>+9.2f}" for v in coefs))
print()

# Top-K accuracy + per-class precision/recall at threshold
print("Top-3 D-1 features for predicting each winner (by |coef|):")
for i, c in enumerate(class_order):
    impt = sorted(zip(X.columns, clf.coef_[i]), key=lambda x: -abs(x[1]))[:4]
    parts = [f"{f}({v:+.2f})" for f, v in impt]
    print(f"  {c:6s}: " + " · ".join(parts))
print()

# Save
out = {
    "n_hours":         int(n),
    "winner_dist":     {p: {"hours": int((m["winner"]==p).sum()),
                            "pct": round((m["winner"]==p).mean()*100, 1),
                            "avg_winning_margin_usd_per_mwh": round(float(m.loc[m["winner"]==p, f"{p.lower()}_lead"].mean()), 3)}
                        for p in PRODS},
    # 3 views of HE × winner relationship
    "he_dist_col_pct": {p: he_dist_col[p].to_dict() for p in PRODS},   # of winner's hours, % at each HE
    "he_dist_row_pct": {p: he_dist_row[p].to_dict() for p in PRODS},   # within each HE, % each product was winner
    "he_dist_abs_count": {p: he_dist_abs[p].astype(int).to_dict() for p in PRODS},  # # hours per (HE, winner)
    # backward compat — keep he_dist_pct but mark deprecated
    "he_dist_pct":     {p: he_dist_col[p].to_dict() for p in PRODS},
    "_he_dist_pct_NOTE": "DEPRECATED — column-normalize. Use he_dist_row_pct (intuitive) or he_dist_abs_count.",
    "dow_dist_pct":    {p: dow_dist[p].to_dict() for p in PRODS},
    "month_dist_pct":  {p: mo_dist[p].to_dict() for p in PRODS},
    "cohort_means":    {p: prof[p].to_dict() for p in PRODS},
    "logit_accuracy":  round(float(acc)*100, 1),
    "logit_base_rate": round((y=="NSPIN").mean()*100, 1),
    "logit_coefficients": {
        c: {f: round(float(v), 3) for f, v in zip(X.columns, clf.coef_[i])}
        for i, c in enumerate(class_order)
    },
    "confusion_matrix": {
        f"true_{PRODS[i]}": {f"pred_{PRODS[j]}": int(cm[i,j]) for j in range(3)} for i in range(3)
    },
}
(DERIVED / "q6_winner_characterization.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"saved -> derived/q6_winner_characterization.json")
