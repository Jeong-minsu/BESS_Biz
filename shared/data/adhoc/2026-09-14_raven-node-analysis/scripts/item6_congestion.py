"""ITEM 6 / Deliverable 2 - congestion-conditioned DART edge at RVN_RN.
Per tracked constraint C (item2 top-10 + real-window top-12 + next-in-rank):
  A. EX-POST: hours where C binds in DA (lambda>0) -> RVN spread, excess over the same-HE unconditional mean, basis (RVN-HB_HOUSTON
     and RVN-HB_BUSAVG spread components), n, t. Same for RT binding. Not tradeable - diagnostic.
  B. Basis share of spread variance on C-binding days vs other days.
  C. PERSISTENCE of bind state: P(bind D | bind D-1), P(bind D | bind D-2), base rate, lift; hour-level same-HE persistence.
  D. EX-ANTE rule: signal = C bound in DA on D-1 (lag1, item3a convention, mildly leaky) or D-2 (lag2, strict);
     hours = typical DA-binding HEs of C (top HEs covering 60% of train bind-hours); side = short if MCC at Raven > 0 (DA raised) else long.
     PnL vs the same hours unconditioned; PnL decomposition into system part and basis part. Train/test split.
Windows: REAL (2026-06-04.., split 08-01) and FULL (proxy+real, split 2025-09-01). BH per family.
Outputs: derived/item6_congestion_stats.json, item6_congestion_expost.csv, item6_congestion_persistence.csv, item6_congestion_exante.csv
"""
import json, numpy as np, pandas as pd
from scipy import stats
from item6_common import *

P = load_panel(); CONS = constraints()
WINDOWS = {"REAL": (P.src == "RVN", REAL_SPLIT), "FULL": (P.FLOWDAY >= "2023-12-02", FULL_SPLIT)}
expost, pers, exante, bshare = [], [], [], []

for wname, (mask, split) in WINDOWS.items():
    W = P[mask].copy(); he_mean = W.groupby("HE").spread_rvn.transform("mean"); W["excess"] = W.spread_rvn - he_mean
    days = np.sort(W.FLOWDAY.unique()); ndays = len(days)
    for c in CONS:
        dcol, mda, mrt = f"da_{c}", f"mccda_{c}", f"mccrt_{c}"
        if dcol not in W: continue
        rtb = W[mrt].abs() > 1e-6
        for mk, sel in (("DA", W[dcol] == 1), ("RT", rtb)):
            x = W[sel]
            if len(x) < 10: continue
            t, p = tstat(x.excess)
            expost.append(dict(window=wname, constraint=c, market=mk, n_hours=len(x), n_days=x.FLOWDAY.nunique(), share_of_hours=round(len(x) / len(W), 4),
                               mcc_mean_at_raven=round(float(x[mda if mk == "DA" else mrt].mean()), 3),
                               spread_mean=round(float(x.spread_rvn.mean()), 2), excess_over_he_mean=round(float(x.excess.mean()), 2), t_excess=round(t, 2), p=p,
                               basis_hou_mean=round(float(x.basis_spread.mean()), 2), basis_sys_mean=round(float(x.basis_sys.mean()), 2),
                               sys_spread_mean=round(float(x.spread_sys.mean()), 2), p_short_win=round(float((x.spread_rvn > 0).mean()), 3),
                               top_HEs=x.HE.value_counts().head(5).index.tolist()))
        # B. basis variance share on binding days
        bind_days = set(W.loc[W[dcol] == 1, "FLOWDAY"].unique())
        if len(bind_days) >= 5 and ndays - len(bind_days) >= 5:
            on = W[W.FLOWDAY.isin(bind_days)]; off = W[~W.FLOWDAY.isin(bind_days)]
            bshare.append(dict(window=wname, constraint=c, n_bind_days=len(bind_days), basis_sys_var_share_bind_days=round(float(on.basis_sys.var() / on.spread_rvn.var()), 4),
                               basis_sys_var_share_other_days=round(float(off.basis_sys.var() / off.spread_rvn.var()), 4),
                               basis_hou_var_share_bind_days=round(float(on.basis_spread.var() / on.spread_rvn.var()), 4),
                               basis_hou_var_share_other_days=round(float(off.basis_spread.var() / off.spread_rvn.var()), 4)))
        # C. persistence (day level, DA binding any hour) and hour level
        db = W.groupby("FLOWDAY")[dcol].max().reindex(days).fillna(0).astype(int)
        base = db.mean()
        row = dict(window=wname, constraint=c, n_days=ndays, n_bind_days=int(db.sum()), p_bind_day=round(float(base), 3))
        for lag in (1, 2):
            prev = db.shift(lag); m = prev.notna()
            a = db[m & (prev == 1)]; b = db[m & (prev == 0)]
            row[f"p_bind_given_bind_lag{lag}"] = round(float(a.mean()), 3) if len(a) else None
            row[f"p_bind_given_nobind_lag{lag}"] = round(float(b.mean()), 3) if len(b) else None
            row[f"lift_lag{lag}"] = round(float(a.mean() / base), 2) if len(a) and base > 0 else None
            if len(a) >= 5 and len(b) >= 5:
                ct = [[int(a.sum()), int(len(a) - a.sum())], [int(b.sum()), int(len(b) - b.sum())]]
                row[f"p_fisher_lag{lag}"] = float(stats.fisher_exact(ct)[1])
        hp = W.pivot_table(index="FLOWDAY", columns="HE", values=dcol, aggfunc="max").reindex(days).fillna(0)
        prev = hp.shift(1)
        same = hp.values[1:][prev.values[1:] == 1]
        row["p_bind_he_given_bind_same_he_lag1"] = round(float(same.mean()), 3) if len(same) else None
        row["p_bind_he_base"] = round(float(hp.values.mean()), 4)
        row["hours_autocorr_lag1"] = round(float(W.groupby("FLOWDAY")[dcol].sum().reindex(days).fillna(0).autocorr(1)), 3)
        pers.append(row)
        # D. ex-ante rule
        Wt = W[W.FLOWDAY < split]
        hcount = Wt.groupby("HE")[dcol].sum().sort_values(ascending=False)
        if hcount.sum() < 20: continue
        cum = hcount.cumsum() / hcount.sum(); H = sorted(hcount.index[: int((cum < 0.60).sum()) + 1].tolist())
        sign_mcc = np.sign(Wt.loc[Wt[dcol] == 1, mda].mean()) if (Wt[dcol] == 1).any() else 0
        side = 1.0 if sign_mcc > 0 else -1.0   # +1 = short DA (pnl=+spread), -1 = long
        for lag in (1, 2):
            sig = db.shift(lag).reindex(W.FLOWDAY).values == 1
            inH = W.HE.isin(H).values
            on = W[sig & inH]; off = W[(~sig) & inH]
            if len(on) < 10: continue
            pnl = side * on.spread_rvn; pnl_off = side * off.spread_rvn
            mt = rule_metrics(pnl, on.FLOWDAY); tr = on[on.FLOWDAY < split]; te = on[on.FLOWDAY >= split]
            dt = stats.ttest_ind(pnl, pnl_off, equal_var=False) if len(off) > 5 else None
            exante.append(dict(window=wname, constraint=c, lag=lag, avail="ex_ante_lag1" if lag == 1 else "ex_ante_lag2", side="short" if side > 0 else "long",
                               typical_HEs=H, n_signal_days=int(on.FLOWDAY.nunique()), **mt,
                               ev_uncond_same_hours=round(float(pnl_off.mean()), 3), n_uncond=len(off), p_vs_uncond=float(dt.pvalue) if dt is not None else None,
                               ev_sys_part=round(float((side * on.spread_sys).mean()), 3), ev_basis_part=round(float((side * on.basis_sys).mean()), 3),
                               ev_train=round(float((side * tr.spread_rvn).mean()), 3) if len(tr) else None, n_train=len(tr),
                               ev_test=round(float((side * te.spread_rvn).mean()), 3) if len(te) else None, n_test=len(te),
                               t_test=round(tstat(side * te.spread_rvn)[0], 2) if len(te) > 3 else None, p_test=tstat(side * te.spread_rvn)[1] if len(te) > 3 else None,
                               p_ev=tstat(pnl)[1]))

expost = pd.DataFrame(expost); pers = pd.DataFrame(pers); exante = pd.DataFrame(exante); bshare = pd.DataFrame(bshare)
tally = {}
for df, fam, pcol in ((expost, "expost_bind_excess", "p"), (exante, "exante_rule_ev", "p_ev"), (exante, "exante_rule_test_window", "p_test")):
    df[f"bh_{fam}"] = False
    for w, idx in df.groupby("window").groups.items():
        pv = df.loc[idx, pcol].fillna(1.0).values
        df.loc[idx, f"bh_{fam}"] = bh(pv, 0.10)
        tally[f"{fam}|{w}"] = dict(n_tests=int(len(idx)), n_p_lt_05=int((pv < 0.05).sum()), n_bh_q10=int(bh(pv, 0.10).sum()), n_bonf_05=int((pv < 0.05 / len(idx)).sum()))
for lag in (1, 2):
    pv = pers[f"p_fisher_lag{lag}"].fillna(1.0).values
    tally[f"persistence_fisher_lag{lag}"] = dict(n_tests=int(len(pv)), n_p_lt_05=int((pv < 0.05).sum()), n_bh_q10=int(bh(pv, 0.10).sum()))
expost.to_csv(D / "item6_congestion_expost.csv", index=False); pers.to_csv(D / "item6_congestion_persistence.csv", index=False)
exante.to_csv(D / "item6_congestion_exante.csv", index=False); bshare.to_csv(D / "item6_congestion_basis_share.csv", index=False)

pd.set_option("display.width", 300); pd.set_option("display.max_rows", 300); pd.set_option("display.max_columns", 40)
print("== EX-POST (REAL, DA bind) ==")
print(expost[(expost.window == "REAL")].sort_values("p")[["constraint", "market", "n_hours", "n_days", "mcc_mean_at_raven", "spread_mean", "excess_over_he_mean", "t_excess", "p", "basis_hou_mean", "basis_sys_mean", "p_short_win", "bh_expost_bind_excess"]].to_string())
print("\n== EX-POST (FULL) BH survivors ==")
print(expost[(expost.window == "FULL") & expost.bh_expost_bind_excess].sort_values("p")[["constraint", "market", "n_hours", "n_days", "mcc_mean_at_raven", "spread_mean", "excess_over_he_mean", "t_excess", "basis_sys_mean", "p_short_win"]].to_string())
print("\n== BASIS SHARE (REAL) ==")
print(bshare[bshare.window == "REAL"].to_string())
print("\n== PERSISTENCE ==")
print(pers[["window", "constraint", "n_bind_days", "p_bind_day", "p_bind_given_bind_lag1", "p_bind_given_nobind_lag1", "lift_lag1", "p_fisher_lag1", "p_bind_given_bind_lag2", "lift_lag2", "p_fisher_lag2", "p_bind_he_given_bind_same_he_lag1", "p_bind_he_base", "hours_autocorr_lag1"]].to_string())
print("\n== EX-ANTE RULES ==")
print(exante.sort_values(["window", "p_ev"])[["window", "constraint", "lag", "side", "typical_HEs", "n_signal_days", "n_hours", "ev_per_mwh", "t_stat", "hit_rate_hours", "sharpe_daily", "worst_hour", "max_drawdown_per_mw", "ev_uncond_same_hours", "p_vs_uncond", "ev_sys_part", "ev_basis_part", "ev_train", "ev_test", "n_test", "t_test", "bh_exante_rule_ev", "bh_exante_rule_test_window"]].to_string())
print("\nTALLY", json.dumps(tally, indent=1))
json.dump(dict(meta=dict(constraints=CONS, windows={k: dict(split=v[1]) for k, v in WINDOWS.items()},
                         note="pre-2026-06 MCC at Raven uses proxy-blend shift factors (item2); WHARTN is a likely proxy artifact; RT bind = lambda>0 in any SCED interval"),
               hypothesis_tally=tally, expost=expost.to_dict(orient="records"), persistence=pers.to_dict(orient="records"),
               exante_rules=exante.to_dict(orient="records"), basis_share=bshare.to_dict(orient="records")),
          open(D / "item6_congestion_stats.json", "w"), indent=1, default=str)
