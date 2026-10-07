"""ITEM 6 / Deliverables 3-4 - pre-declared rule set backtested with a chronological train/test split, plus a
permutation null for the regime search (how large an in-sample t do you get from 1,224 cells of pure noise?).
Rules are fixed here BEFORE looking at test-window results (thresholds / hour sets fitted on train only where marked).
PnL = side * spread_rvn, 1 MW per traded hour, no clearing model / fees (same as item3a).
Windows: REAL (RVN_RN own prices 2026-06-04..09-13, train <08-01) and FULL (proxy+real 2023-12-02..2026-09-13, train <2025-09-01).
Outputs: derived/item6_rules_backtest.json, item6_rules_backtest.csv, item6_rules_by_year.csv, item6_permutation_null.json
"""
import json, numpy as np, pandas as pd
from item6_common import *

P = load_panel(); F = daily_features(P)
WINDOWS = {"REAL": (P.src == "RVN", REAL_SPLIT), "FULL": (P.FLOWDAY >= "2023-12-02", FULL_SPLIT)}
B0_HOURS = [3, 5, 7, 8, 9, 10, 11]          # item3a tradeable hours (all LONG) - fitted on the whole real window (in-sample there)
MORNING = [7, 8, 9, 10, 11]; AFTERNOON = [14, 15, 16, 17, 18]

def bind_day(W, c):
    return W.groupby("FLOWDAY")[f"da_{c}"].max()

def rules(W, split):
    """returns dict name -> (side Series aligned to W.index; 0 = no trade, +1 short, -1 long), meta"""
    days = np.sort(W.FLOWDAY.unique()); Ft = F.loc[days]; tr = Ft.index < split
    R, meta = {}, {}
    # --- baselines ---
    R["B0_item3a_long_HE3,5,7-11"] = pd.Series(np.where(W.HE.isin(B0_HOURS), -1.0, 0.0), index=W.index)
    # refit of item3a's rule on train only: hours with |t|>=1.5 on train, side = sign of train mean
    Wt = W[W.FLOWDAY < split]; g = Wt.groupby("HE").spread_rvn
    tt = g.mean() / (g.std() / np.sqrt(g.size())); sel = tt[tt.abs() >= 1.5]
    side_he = np.sign(sel).to_dict(); meta["B0refit_hours"] = {int(k): ("short" if v > 0 else "long") for k, v in side_he.items()}
    R["B0refit_best_side_train_|t|>=1.5"] = pd.Series(W.HE.map(side_he).fillna(0.0).values, index=W.index)
    R["B_always_long_all_HE"] = pd.Series(-1.0, index=W.index)
    R["B_long_HE7-11_static"] = pd.Series(np.where(W.HE.isin(MORNING), -1.0, 0.0), index=W.index)
    R["B_short_HE14-18_static"] = pd.Series(np.where(W.HE.isin(AFTERNOON), 1.0, 0.0), index=W.index)
    # --- persistence ---
    piv = W.pivot_table(index="FLOWDAY", columns="HE", values="spread_rvn")
    for lag, tag in ((1, "lag1_leaky"), (2, "lag2_strict")):
        s = np.sign(piv.shift(lag)).stack().rename("s").reset_index()
        m = W[["FLOWDAY", "HE"]].merge(s, on=["FLOWDAY", "HE"], how="left").s.fillna(0.0).values
        R[f"P_follow_yesterday_sign_perHE_{tag}"] = pd.Series(m, index=W.index)
        R[f"P_follow_yesterday_sign_HE9-20_{tag}"] = pd.Series(np.where(W.HE.between(9, 20), m, 0.0), index=W.index)
    # --- regime (thresholds from train terciles) ---
    for feat in ("rt_vol_lag2", "rt_max_lag2", "rt_vol_lag1"):
        q = np.nanquantile(Ft.loc[tr, feat].dropna(), 2 / 3); hi = (Ft[feat] > q).reindex(W.FLOWDAY).fillna(False).values
        R[f"R_long_HE7-11_if_{feat}_high"] = pd.Series(np.where(hi & W.HE.isin(MORNING), -1.0, 0.0), index=W.index); meta[f"thr_{feat}"] = round(float(q), 2)
    q = np.nanquantile(Ft.loc[tr, "wind_mean"].dropna(), 1 / 3); lo = (Ft["wind_mean"] < q).reindex(W.FLOWDAY).fillna(False).values
    R["R_long_HE7-11_if_wind_low_NEEDS_FC"] = pd.Series(np.where(lo & W.HE.isin(MORNING), -1.0, 0.0), index=W.index); meta["thr_wind_low"] = round(float(q), 0)
    # --- congestion (bind state of D-1 / D-2) ---
    for c, hrs, side in (("STPWAP39_1", AFTERNOON, 1.0), ("1715__B", [11, 16, 17, 18, 19], 1.0), ("E_PASP", [17, 18, 19, 20, 21, 22], -1.0), ("35055__A", [10, 11, 12, 13], -1.0)):
        if f"da_{c}" not in W: continue
        bd = bind_day(W, c)
        for lag in (1, 2):
            sig = (bd.shift(lag) == 1).reindex(W.FLOWDAY).fillna(False).values
            R[f"C_{'short' if side > 0 else 'long'}_HE{hrs[0]}-{hrs[-1]}_if_{c}_bound_lag{lag}"] = pd.Series(np.where(sig & W.HE.isin(hrs), side, 0.0), index=W.index)
    hou_imp = [c for c in ("STPWAP39_1", "1710__A", "SEA_AAT1") if f"da_{c}" in W]
    any_bd = pd.concat([bind_day(W, c) for c in hou_imp], axis=1).max(axis=1)
    for lag in (1, 2):
        sig = (any_bd.shift(lag) == 1).reindex(W.FLOWDAY).fillna(False).values
        R[f"C_short_HE14-18_if_any_HoustonImport_bound_lag{lag}"] = pd.Series(np.where(sig & W.HE.isin(AFTERNOON), 1.0, 0.0), index=W.index)
    # --- combined (strict ex-ante only) ---
    comb = R["B0_item3a_long_HE3,5,7-11"].copy()
    c1 = R.get("C_short_HE14-18_if_STPWAP39_1_bound_lag2"); comb = comb.where(comb != 0, c1)
    R["X_B0_long + STPWAP_lag2_short_HE14-18"] = comb
    comb2 = R["R_long_HE7-11_if_rt_vol_lag2_high"].where(R["R_long_HE7-11_if_rt_vol_lag2_high"] != 0, c1)
    R["X_regime_long_HE7-11 + STPWAP_lag2_short_HE14-18"] = comb2
    return R, meta

rows, byyear, allmeta = [], [], {}
for wname, (mask, split) in WINDOWS.items():
    W = P[mask].reset_index(drop=True); R, meta = rules(W, split); allmeta[wname] = meta
    for name, side in R.items():
        on = side != 0
        for part, m in (("all", on), ("train", on & (W.FLOWDAY < split)), ("test", on & (W.FLOWDAY >= split))):
            x = W[m]; pnl = side[m] * x.spread_rvn
            mt = rule_metrics(pnl, x.FLOWDAY)
            mt.update(ev_sys_part=round(float((side[m] * x.spread_sys).mean()), 3) if len(x) else None,
                      ev_basis_part=round(float((side[m] * x.basis_sys).mean()), 3) if len(x) else None,
                      days_in_part=int(W[(W.FLOWDAY < split) if part == "train" else (W.FLOWDAY >= split) if part == "test" else slice(None)].FLOWDAY.nunique()))
            rows.append(dict(window=wname, rule=name, part=part, family=name.split("_")[0], **mt))
        for (y, s), x in W[on].groupby([W.FLOWDAY.dt.year, W.season]):
            pnl = side[x.index] * x.spread_rvn
            byyear.append(dict(window=wname, rule=name, year=int(y), season=s, n_hours=len(x), ev_per_mwh=round(float(pnl.mean()), 3),
                               per_day_per_mw=round(float(pnl.groupby(x.FLOWDAY).sum().mean()), 2), hit_rate_hours=round(float((pnl > 0).mean()), 3), t=round(tstat(pnl)[0], 2)))
bt = pd.DataFrame(rows); by = pd.DataFrame(byyear)
bt.to_csv(D / "item6_rules_backtest.csv", index=False); by.to_csv(D / "item6_rules_by_year.csv", index=False)

# overfitting: IS vs OOS shrinkage per rule
piv = bt.pivot_table(index=["window", "rule"], columns="part", values="ev_per_mwh")
piv["shrink_train_to_test"] = 1 - piv.test / piv.train.replace(0, np.nan)
pd.set_option("display.width", 320); pd.set_option("display.max_rows", 300); pd.set_option("display.max_colwidth", 60)
cols = ["rule", "part", "n_hours", "n_days", "ev_per_mwh", "per_day_per_mw", "hit_rate_hours", "hit_rate_days", "sharpe_daily", "sharpe_annualised", "max_drawdown_per_mw", "worst_hour", "t_stat", "ev_sys_part", "ev_basis_part"]
for w in WINDOWS:
    print(f"\n===== {w} =====")
    print(bt[(bt.window == w) & (bt.part == "test")].sort_values("ev_per_mwh", ascending=False)[cols].to_string())
    print("\n-- train vs test EV --"); print(piv.loc[w].round(3).to_string())
print("\n-- FULL by year x season, selected rules --")
sel = by[(by.window == "FULL") & by.rule.isin(["B0_item3a_long_HE3,5,7-11", "R_long_HE7-11_if_rt_vol_lag2_high", "C_short_HE14-18_if_STPWAP39_1_bound_lag2", "C_short_HE14-18_if_any_HoustonImport_bound_lag2", "P_follow_yesterday_sign_perHE_lag2_strict", "P_follow_yesterday_sign_perHE_lag1_leaky", "X_B0_long + STPWAP_lag2_short_HE14-18"])]
print(sel.pivot_table(index=["rule", "season"], columns="year", values="ev_per_mwh").round(2).to_string())
print(sel.pivot_table(index=["rule", "season"], columns="year", values="n_hours").to_string())

# ---- permutation null for the REAL-window regime search (HE grain): shuffle day->feature assignment, keep hours intact ----
rng = np.random.default_rng(0)
W = P[P.src == "RVN"].reset_index(drop=True); days = np.sort(W.FLOWDAY.unique()); Fr = F.loc[days]
feats = [f for f, a in FEATURES.items() if a != "ex_post"]
def max_abs_t(W, labels_by_feat):
    best = 0.0
    for feat, lab in labels_by_feat.items():
        W["reg"] = W.FLOWDAY.map(lab)
        g = W.groupby(["reg", "HE"], observed=True).spread_rvn
        t = (g.mean() / (g.std() / np.sqrt(g.size()))).abs(); t = t[g.size() >= 10]
        best = max(best, float(t.max()))
    return best
obs_labels = {}
for feat in feats:
    lab, _ = tercile_labels(Fr.loc[Fr.index < REAL_SPLIT, feat].dropna().values, Fr[feat].values); obs_labels[feat] = pd.Series(np.asarray(lab, dtype=object), index=Fr.index)
t_obs = max_abs_t(W.copy(), obs_labels)
null = []
for i in range(300):
    perm = rng.permutation(len(days)); labs = {f: pd.Series(obs_labels[f].values[perm], index=days) for f in feats}
    null.append(max_abs_t(W.copy(), labs))
null = np.array(null)
perm_out = dict(n_features=len(feats), n_cells_approx=len(feats) * 3 * 24, observed_max_abs_t=round(t_obs, 2), null_max_abs_t_p50=round(float(np.median(null)), 2),
                null_max_abs_t_p90=round(float(np.percentile(null, 90)), 2), null_max_abs_t_p95=round(float(np.percentile(null, 95)), 2),
                p_value_family=round(float((null >= t_obs).mean()), 3), n_perm=300,
                note="day labels of every regime feature permuted jointly across days (hour structure and spread autocorrelation within day preserved); tests whether the largest in-sample |t| across all regime x HE cells exceeds what selection from noise gives")
print("\nPERMUTATION NULL (REAL, regime x HE search):", json.dumps(perm_out, indent=1))
json.dump(perm_out, open(D / "item6_permutation_null.json", "w"), indent=1)
json.dump(dict(meta=dict(windows={k: dict(split=v[1]) for k, v in WINDOWS.items()}, rule_meta=allmeta,
                         convention="spread=DA-RT; side +1 short/-1 long; PnL per MWh at 1 MW per traded hour; no clearing model or fees",
                         availability=dict(B="static/no info", P_lag1="leaky (uses D-1 HE11-24 not known at 10:00 D-1)", P_lag2="strict ex-ante", R_lag1="leaky", R_lag2="strict ex-ante",
                                           R_wind="needs D+1 wind forecast (upper bound)", C_lag1="leaky", C_lag2="strict ex-ante", X="strict ex-ante")),
               backtest=bt.to_dict(orient="records"), by_year_season=by.to_dict(orient="records"),
               train_vs_test=piv.reset_index().to_dict(orient="records"), permutation_null=perm_out),
          open(D / "item6_rules_backtest.json", "w"), indent=1, default=str)
