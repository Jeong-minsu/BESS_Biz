"""ITEM 6 / Deliverable 1 - regime-conditioned hourly DART edge at RVN_RN.
For each daily regime variable (terciles, thresholds fixed on the TRAIN window) x HE:
  (a) separation test: Kruskal-Wallis of spread across terciles (does the regime move the hourly spread at all?)
  (b) within-regime edge: one-sample t of mean spread per (regime level x HE), with short/long win rate, P/L, EV, loss p95/p99
  (c) block-level (4 HE blocks) versions of (a),(b) with lower multiplicity
Windows: REAL (RVN_RN own prices, 2026-06-04..09-13; train ..07-31 / test 08-01..) and FULL (proxy+real 2023-12..2026-09;
train ..2025-08-31 / test 2025-09-01..). All p-values BH-adjusted per family (FDR 10%). Hypothesis counts are recorded.
Outputs: derived/item6_regime_stats.json, derived/item6_regime_hourly.csv, derived/item6_regime_separation.csv
"""
import json, numpy as np, pandas as pd
from scipy import stats
from item6_common import *

P = load_panel(); F = daily_features(P)
BLOCKS = {"HE1-6": range(1, 7), "HE7-11": range(7, 12), "HE12-14": range(12, 15), "HE15-20": range(15, 21), "HE21-24": range(21, 25)}
P["block"] = P.HE.map({h: b for b, r in BLOCKS.items() for h in r})
WINDOWS = {"REAL": (P.src == "RVN", REAL_SPLIT), "FULL": (P.FLOWDAY >= "2023-12-02", FULL_SPLIT)}
sep_rows, hr_rows, tally = [], [], {}

for wname, (mask, split) in WINDOWS.items():
    W = P[mask].copy(); Fw = F.loc[W.FLOWDAY.unique()]
    train_days = Fw.index[Fw.index < split]
    for feat, avail in list(FEATURES.items()) + [("season", "known")]:
        if feat == "season":
            if wname == "REAL": continue
            lab = Fw.season; q = None
        else:
            lab, q = tercile_labels(Fw.loc[train_days, feat].dropna().values, Fw[feat].values); lab = pd.Series(np.asarray(lab, dtype=object), index=Fw.index)
        W["reg"] = W.FLOWDAY.map(lab)
        for grain, key in (("HE", "HE"), ("block", "block")):
            for h, g in W.dropna(subset=["reg"]).groupby(key):
                groups = [x.spread_rvn.values for _, x in g.groupby("reg") if len(x) >= 5]
                if len(groups) >= 2:
                    kw = stats.kruskal(*groups); sep_rows.append(dict(window=wname, grain=grain, feature=feat, avail=avail, unit=str(h), n=len(g),
                                                                   kw_stat=round(float(kw.statistic), 2), p=float(kw.pvalue),
                                                                   means={str(k): round(float(x.spread_rvn.mean()), 2) for k, x in g.groupby("reg")}))
                for lev, x in g.groupby("reg"):
                    if len(x) < 10: continue
                    t, p = tstat(x.spread_rvn); ss = side_stats(x.spread_rvn); best = "short" if x.spread_rvn.mean() > 0 else "long"
                    # test-window replication of the same cell (thresholds fixed from train)
                    xt = x[x.FLOWDAY >= split]; xtr = x[x.FLOWDAY < split]
                    hr_rows.append(dict(window=wname, grain=grain, feature=feat, avail=avail, unit=str(h), level=str(lev), n=len(x), n_days=x.FLOWDAY.nunique(),
                                        mean=round(float(x.spread_rvn.mean()), 2), t=round(t, 2), p=p, best_side=best,
                                        p_win_best=ss[best]["p_win"], pl_best=ss[best]["pl_ratio"], ev_best=ss[best]["ev"],
                                        loss_p95_best=ss[best]["loss_p95"], loss_p99_best=ss[best]["loss_p99"],
                                        mean_train=round(float(xtr.spread_rvn.mean()), 2) if len(xtr) else None, n_train=len(xtr),
                                        mean_test=round(float(xt.spread_rvn.mean()), 2) if len(xt) else None, n_test=len(xt),
                                        sign_replicates=bool(len(xt) and len(xtr) and np.sign(xt.spread_rvn.mean()) == np.sign(xtr.spread_rvn.mean())),
                                        thresholds=[round(float(v), 1) for v in q] if q is not None else None))

sep = pd.DataFrame(sep_rows); hr = pd.DataFrame(hr_rows)
for df, fam in ((sep, "separation"), (hr, "within_regime_edge")):
    df["bh_reject_q10"] = False
    for (w, gr), idx in df.groupby(["window", "grain"]).groups.items():
        df.loc[idx, "bh_reject_q10"] = bh(df.loc[idx, "p"].values, 0.10)
        df.loc[idx, "bonf_reject_05"] = df.loc[idx, "p"].values < 0.05 / len(idx)
        tally[f"{fam}|{w}|{gr}"] = dict(n_tests=int(len(idx)), n_p_lt_05=int((df.loc[idx, "p"] < 0.05).sum()),
                                        n_bh_q10=int(df.loc[idx, "bh_reject_q10"].sum()), n_bonf_05=int(df.loc[idx, "bonf_reject_05"].sum()))
sep["means"] = sep.means.apply(json.dumps)
sep.to_csv(D / "item6_regime_separation.csv", index=False); hr.to_csv(D / "item6_regime_hourly.csv", index=False)

# --- which features separate? per feature: share of HEs with BH-significant separation, and unconditional-vs-conditional spread ---
summ = []
for (w, gr, feat, avail), g in sep.groupby(["window", "grain", "feature", "avail"]):
    summ.append(dict(window=w, grain=gr, feature=feat, avail=avail, n_units=len(g), n_bh_sig=int(g.bh_reject_q10.sum()),
                     n_p05=int((g.p < 0.05).sum()), median_p=round(float(g.p.median()), 3),
                     sig_units=[r.unit for r in g.itertuples() if r.bh_reject_q10]))
summ = pd.DataFrame(summ).sort_values(["window", "grain", "n_bh_sig"], ascending=[True, True, False])
print(summ.to_string())
print("\nTALLY:", json.dumps(tally, indent=1))

# --- edge cells that are (i) BH-significant on the full window AND (ii) same sign in the held-out test part ---
surv = hr[hr.bh_reject_q10 & hr.sign_replicates & (hr.avail != "ex_post")].copy()
surv["oos_ev_best"] = np.where(surv.best_side == "short", surv.mean_test, -surv.mean_test)
print("\nBH-surviving, sign-replicating, non-ex-post cells:\n", surv.sort_values("p")[["window", "grain", "feature", "avail", "unit", "level", "n", "mean", "t", "best_side", "ev_best", "loss_p99_best", "mean_train", "mean_test", "n_test"]].to_string())

json.dump(dict(meta=dict(windows={k: dict(split=v[1]) for k, v in WINDOWS.items()}, features=FEATURES, blocks={k: list(v) for k, v in BLOCKS.items()},
                         convention="spread = DA - RT at RVN_RN (real from 2026-06-04, item2 NNLS proxy before); terciles fixed on train"),
               hypothesis_tally=tally, feature_separation=summ.to_dict(orient="records"),
               surviving_cells=surv.drop(columns=["thresholds"]).to_dict(orient="records"),
               hourly_cells=hr[hr.grain == "HE"].drop(columns=["thresholds"]).to_dict(orient="records")),
          open(D / "item6_regime_stats.json", "w"), indent=1, default=str)
