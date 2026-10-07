"""
#77 — NonSpin DA<RT negative-spread hours: profile, D-1 detectability, optimal choice.

spread = AS_MCPC_NSPIN - RT_AS_MCPC_NSPIN  (>0 = DA rich, normal; <0 = RT rich, abnormal)

Q1 common characteristics of negative-spread hours
Q2 can we see it coming at D-1 bid close (only forecast / DAM-cleared features)
Q3 what was the optimal action in those hours
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ADHOC = Path(__file__).resolve().parents[1]
DERIVED = ADHOC / "derived"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 220)

df = pd.read_parquet(DERIVED / "master_hourly.parquet").copy()
df["hour_ct"] = pd.to_datetime(df["datetime_ct"], utc=True).dt.tz_convert("America/Chicago").dt.floor("h")
df["neg"] = df["AS_SPREAD_NSPIN"] < 0
df["sev_neg"] = df["AS_SPREAD_NSPIN"] < -3.0          # materially negative
# derived forecast features known at D-1 bid close
df["net_load_fc"] = df["NET_LOAD_FORECAST_BID_CLOSE"]
df["wind_fc"] = df["WIND_STWPF_BIDCLOSE"]
df["solar_fc"] = df["SOLAR_COPHSL_BIDCLOSE"]
# net-load forecast percentile within its own hour-of-day (captures "tight day for this HE")
df["netload_fc_pct"] = df.groupby("he")["net_load_fc"].rank(pct=True)
df["wind_fc_pct"] = df.groupby("he")["wind_fc"].rank(pct=True)
df["da_nspin_pct"] = df.groupby("he")["AS_MCPC_NSPIN"].rank(pct=True)   # DAM-cleared, known D-1 PM
df["da_nspin_low"] = df["AS_MCPC_NSPIN"] < 0.5

H = len(df)
N = df["neg"].sum()
print(f"=== NSPIN negative-spread (DA<RT)  —  {N}/{H} hours ({N/H*100:.1f}%) ===\n")

# ---------- Q1: common characteristics ----------
print("--- Q1. profile: negative vs positive hours ---")
feat = ["AS_MCPC_NSPIN", "RT_AS_MCPC_NSPIN", "net_load_fc", "wind_fc", "solar_fc",
        "RTLOAD", "WIND_RTI", "load_fc_err", "wind_fc_err",
        "RTLMP_GKS_BESS_RN", "DALMP_GKS_BESS_RN", "spread_gks", "GKS_RTSPP_Avg"]
prof = df.groupby("neg")[feat].mean().T
prof.columns = ["pos(DA>RT)", "neg(DA<RT)"]
prof["ratio_neg/pos"] = prof["neg(DA<RT)"] / prof["pos(DA>RT)"]
print(prof.round(2).to_string())
print()

# HE / dow / month concentration
for dim in ["he", "dow", "month"]:
    t = df.groupby(dim)["neg"].agg(["mean", "sum"])
    t["lift"] = t["mean"] / df["neg"].mean()
    top = t.sort_values("mean", ascending=False).head(6)
    print(f"  {dim:6s} most negative-prone:  " +
          "  ".join(f"{idx}={r['mean']*100:.0f}%(x{r['lift']:.1f},n={int(r['sum'])})"
                    for idx, r in top.iterrows()))
print()

# how often is a negative-spread hour also an RT energy / RT-AS spike hour
df["rt_lmp_spike"] = df["RTLMP_GKS_BESS_RN"] > df["RTLMP_GKS_BESS_RN"].quantile(0.90)
df["rt_nspin_spike"] = df["RT_AS_MCPC_NSPIN"] > df["RT_AS_MCPC_NSPIN"].quantile(0.90)
for f in ["rt_lmp_spike", "rt_nspin_spike", "da_nspin_low"]:
    p_neg_given_f = df.loc[df[f], "neg"].mean()
    p_f_given_neg = df.loc[df["neg"], f].mean()
    print(f"  P(neg | {f:14s})={p_neg_given_f*100:5.1f}%   P({f:14s} | neg)={p_f_given_neg*100:5.1f}%")
print()

# ---------- Q2: D-1 detectability ----------
print("--- Q2. D-1 detectability (features knowable before the operating day) ---")
d1_feats = ["netload_fc_pct", "wind_fc_pct", "da_nspin_pct", "he"]
# conditional probability of negative spread by D-1 feature buckets
for f in ["netload_fc_pct", "wind_fc_pct", "da_nspin_pct"]:
    q = pd.qcut(df[f], 5, labels=["Q1","Q2","Q3","Q4","Q5"], duplicates="drop")
    t = df.groupby(q, observed=True)["neg"].mean() * 100
    print(f"  P(neg) by {f:16s} quintile:  " + "  ".join(f"{k}={v:4.1f}%" for k, v in t.items()))
print()

# simple logistic regression: D-1 features only, AUC + lift in top decile
try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    X = df[["netload_fc_pct", "wind_fc_pct", "da_nspin_pct"]].copy()
    X["he_sin"] = np.sin(2*np.pi*df["he"]/24); X["he_cos"] = np.cos(2*np.pi*df["he"]/24)
    X = X.fillna(X.median())
    for tgt, lbl in [("neg", "any DA<RT"), ("sev_neg", "DA<RT by >$3")]:
        y = df[tgt].astype(int)
        m = LogisticRegression(max_iter=1000, class_weight="balanced").fit(X, y)
        p = m.predict_proba(X)[:, 1]
        auc = roc_auc_score(y, p)
        # top-decile lift
        dec = pd.qcut(p, 10, labels=False, duplicates="drop")
        topdec = y[dec == dec.max()].mean()
        base = y.mean()
        print(f"  logit [{lbl:12s}]  AUC={auc:.3f}   top-decile hit-rate={topdec*100:.1f}%  (base {base*100:.1f}%, lift x{topdec/base:.1f})")
        coefs = dict(zip(X.columns, m.coef_[0].round(2)))
        print(f"                     coefs={coefs}")
except ImportError:
    print("  (sklearn not available — skipping logit)")
print()

# ---------- Q3: optimal action in negative-spread hours ----------
print("--- Q3. optimal action in the 250 negative-spread hours ---")
hr = pd.read_parquet(DERIVED / "gks_as_hourly_full.parquet")
ns = hr[hr["product"] == "NSPIN"].merge(
    df[["hour_ct", "neg", "AS_MCPC_NSPIN", "RT_AS_MCPC_NSPIN", "AS_SPREAD_NSPIN",
        "RTLMP_GKS_BESS_RN", "DALMP_GKS_BESS_RN", "spread_gks", "he"]],
    on="hour_ct", how="inner")
negh = ns[ns["neg"]].copy()
print(f"  hours: {len(negh)}   GKS avg DA award={negh['da_qty'].mean():.1f}MW  "
      f"avg buyback={negh['buyback_qty'].mean():.1f}MW  buyback rate={negh['buyback_qty'].sum()/negh['da_qty'].sum()*100:.0f}%")
# what GKS actually paid to buy back in these hours (RT > DA -> expensive buyback)
actual_cost = negh["imb_amt"].sum()
# spread P&L on the bought-back MW (negative here, since DA<RT)
negh["spread_pnl"] = (negh["AS_MCPC_NSPIN"] - negh["RT_AS_MCPC_NSPIN"]) * negh["buyback_qty"]
print(f"  GKS actual: RT buyback cost in these hrs = ${actual_cost:,.0f}; "
      f"spread P&L on bought-back MW = ${negh['spread_pnl'].sum():,.0f}  (negative = lost vs holding)")
# alternatives per hour, on the buyback_qty MW:
#  A. hold/deliver DA NSPIN -> AS$ = DA_MCPC*qty, battery committed, no buyback cost
#  B. what GKS did: buy back -> AS$ = (DA-RT)*qty, battery freed for energy
#  C. sell extra NSPIN in RT instead -> earn +RT_MCPC*qty (RT is rich here)
negh["optA_hold"]   = negh["AS_MCPC_NSPIN"]    * negh["buyback_qty"]
negh["optB_buyback"]= (negh["AS_MCPC_NSPIN"] - negh["RT_AS_MCPC_NSPIN"]) * negh["buyback_qty"]
negh["optC_rtsell"] = negh["RT_AS_MCPC_NSPIN"] * negh["buyback_qty"]   # incremental RT AS sale value
# energy alternative: RT energy value of freeing the qty ~ |spread_gks| (RT-DA) per MWh, rough
negh["energy_proxy"] = negh["spread_gks"].abs() * negh["buyback_qty"]
print(f"  AS-$ on the bought-back MW under each choice:")
print(f"     A hold/deliver        = ${negh['optA_hold'].sum():>11,.0f}")
print(f"     B buy back (GKS did)  = ${negh['optB_buyback'].sum():>11,.0f}")
print(f"     C sell that MW in RT  = ${negh['optC_rtsell'].sum():>11,.0f}")
print(f"     (RT energy value proxy on freed MW = ${negh['energy_proxy'].sum():>11,.0f})")
print()
# split: mild vs severe negative
for lbl, mask in [("mild  (-3<=spread<0)", negh["AS_SPREAD_NSPIN"] >= -3),
                  ("severe (spread<-3)",   negh["AS_SPREAD_NSPIN"] < -3)]:
    s = negh[mask]
    print(f"  {lbl}: {len(s):3d} hrs  buyback={s['buyback_qty'].mean():4.1f}MW  "
          f"hold=${s['optA_hold'].sum():>9,.0f}  buyback=${s['optB_buyback'].sum():>9,.0f}  "
          f"rtsell=${s['optC_rtsell'].sum():>9,.0f}  energy_proxy=${s['energy_proxy'].sum():>9,.0f}")

negh.to_parquet(DERIVED / "nspin_negative_spread_hours.parquet", index=False)
print(f"\nsaved -> derived/nspin_negative_spread_hours.parquet")
