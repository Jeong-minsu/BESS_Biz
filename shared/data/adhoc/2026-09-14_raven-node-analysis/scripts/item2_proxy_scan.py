"""ITEM 2 Part A — proxy selection for RVN_RN (Raven, HOUSTON).
Scans all ERCOT price_nodes in raw/price_panel over the overlap window (2026-06-04..2026-09-13),
ranks by level corr / first-diff corr / basis RMSE / DA-RT spread corr, fits OLS+NNLS blends,
validates out-of-sample on reconstructed daily TB2 (DA, RT) and daily DA-RT spread.
Real data only. Outputs derived/item2_proxy_*.{csv,json}, derived/item2_proxy_definition.json
"""
import json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import nnls

R = Path(__file__).resolve().parents[1]
D = R / "derived"; D.mkdir(exist_ok=True)
RVN = 10019925379
NOMINATED = {10001765766: "CBEC_ALL", 10017290064: "RBN_BESS1", 10016969364: "TAV_RN"}
T0, T1 = pd.Timestamp("2026-06-04"), pd.Timestamp("2026-09-13")
SPLIT = pd.Timestamp("2026-08-01")   # fit < SPLIT, test >= SPLIT

obj = pd.read_parquet(R / "raw/objects_all.parquet")
obj = obj[obj.OBJECTTYPE == "price_node"].set_index("OBJECTID")
name = obj.OBJECTNAME.to_dict(); zone = obj.ZONE.to_dict(); sub = obj.SUBTYPE.to_dict()

df = pd.concat(pd.read_parquet(R / f"raw/price_panel/{m}.parquet") for m in ["202606", "202607", "202608", "202609"])
df = df[(df.FLOWDAY >= T0) & (df.FLOWDAY <= T1)]
df["dt"] = pd.to_datetime(df.DATETIME, format="%m/%d/%Y %H:%M:%S")
DA = df.pivot(index="dt", columns="OBJECTID", values="DALMP").astype("float64")
RT = df.pivot(index="dt", columns="OBJECTID", values="RTLMP").astype("float64")
FD = df.drop_duplicates("dt").set_index("dt").FLOWDAY.sort_index()
print("hours", len(DA), "nodes", DA.shape[1])

ok = (DA.notna().mean() > 0.98) & (RT.notna().mean() > 0.98) & (DA.std() > 1) & (RT.std() > 1)
cands = [c for c in DA.columns[ok] if c != RVN]
y_da, y_rt = DA[RVN], RT[RVN]
y_sp = y_da - y_rt


def corr(a, b):
    m = a.notna() & b.notna()
    return float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 10 else np.nan


def rmse(a, b):
    m = a.notna() & b.notna()
    return float(np.sqrt(((a[m] - b[m]) ** 2).mean()))


rows = []
for c in cands:
    x_da, x_rt = DA[c], RT[c]
    rows.append(dict(OBJECTID=c, node=name.get(c), zone=zone.get(c), subtype=sub.get(c),
                     corr_da=corr(y_da, x_da), corr_rt=corr(y_rt, x_rt),
                     corr_dda=corr(y_da.diff(), x_da.diff()), corr_drt=corr(y_rt.diff(), x_rt.diff()),
                     rmse_da=rmse(y_da, x_da), rmse_rt=rmse(y_rt, x_rt),
                     corr_spread=corr(y_sp, x_da - x_rt), rmse_spread=rmse(y_sp, x_da - x_rt),
                     mean_basis_da=float((y_da - x_da).mean()), mean_basis_rt=float((y_rt - x_rt).mean())))
S = pd.DataFrame(rows)
rk = pd.DataFrame({k: S[k].rank(ascending=False) for k in ["corr_da", "corr_rt", "corr_dda", "corr_drt", "corr_spread"]})
for k in ["rmse_da", "rmse_rt"]:
    rk[k] = S[k].rank(ascending=True)
S["composite_rank"] = rk.mean(axis=1)
S["identical_flag"] = (S.rmse_da < 0.5) & (S.rmse_rt < 0.5)
# 3-year eligibility: node must already have DA prices in the first panel month (2023-09)
first = pd.read_parquet(R / "raw/price_panel/202309.parquet", columns=["OBJECTID", "DALMP"]).dropna()
S["eligible_3yr"] = S.OBJECTID.isin(set(first.OBJECTID))
S = S.sort_values("composite_rank").reset_index(drop=True)
S.to_csv(D / "item2_proxy_scan_all.csv", index=False)
top20 = S.head(20)
print("\nTOP-20 by composite rank"); print(top20.round(3).to_string())
print("\nNominated:"); print(S[S.OBJECTID.isin(NOMINATED)].round(3).to_string())
print("\nHOUSTON-zone share in top20:", (top20.zone == "HOUSTON").mean())


# ---------------- regression blends ----------------
def fit(cols, kind, mask):
    """joint fit on stacked DA+RT hourly (one weight set for both markets)."""
    X = pd.concat([DA.loc[mask, cols], RT.loc[mask, cols]]); y = pd.concat([y_da[mask], y_rt[mask]])
    m = X.notna().all(axis=1) & y.notna(); X, y = X[m].values, y[m].values
    if kind == "ols":
        A = np.c_[np.ones(len(X)), X]; b, *_ = np.linalg.lstsq(A, y, rcond=None); icpt, w = b[0], b[1:]
    else:
        w, _ = nnls(X, y); icpt = 0.0
        if w.sum() > 0:
            w = w / w.sum(); icpt = float((y - X @ w).mean())
    yhat = icpt + X @ w; r2 = 1 - ((y - yhat) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return dict(nodes=[name[c] for c in cols], ids=[int(c) for c in cols], weights=[round(float(v), 4) for v in w],
                intercept=round(float(icpt), 3), r2_fit=round(float(r2), 4), kind=kind)


def predict(spec, P, idx):
    X = P.loc[idx, spec["ids"]].values
    return pd.Series(spec["intercept"] + X @ np.array(spec["weights"]), index=idx)


def tb2(s, fd):
    g = pd.DataFrame({"p": s, "fd": fd.reindex(s.index)}).dropna().groupby("fd").p
    return g.apply(lambda v: v.nlargest(2).mean() - v.nsmallest(2).mean() if len(v) >= 20 else np.nan).dropna()


def oos_eval(spec, test):
    pd_, pr_ = predict(spec, DA, test), predict(spec, RT, test)
    tb_da_t, tb_rt_t = tb2(y_da[test], FD), tb2(y_rt[test], FD)
    tb_da_p, tb_rt_p = tb2(pd_, FD), tb2(pr_, FD)
    sp_t = (y_da[test] - y_rt[test]).groupby(FD.reindex(test)).mean()
    sp_p = (pd_ - pr_).groupby(FD.reindex(test)).mean()
    hsp_t, hsp_p = y_da[test] - y_rt[test], pd_ - pr_
    big = hsp_t.abs() > 1
    return dict(
        tb2_da_true_mean=round(tb_da_t.mean(), 2), tb2_da_proxy_mean=round(tb_da_p.mean(), 2),
        tb2_da_mae=round((tb_da_p - tb_da_t).abs().mean(), 2), tb2_da_bias=round((tb_da_p - tb_da_t).mean(), 2),
        tb2_rt_true_mean=round(tb_rt_t.mean(), 2), tb2_rt_proxy_mean=round(tb_rt_p.mean(), 2),
        tb2_rt_mae=round((tb_rt_p - tb_rt_t).abs().mean(), 2), tb2_rt_bias=round((tb_rt_p - tb_rt_t).mean(), 2),
        spread_daily_mae=round((sp_p - sp_t).abs().mean(), 2), spread_daily_bias=round((sp_p - sp_t).mean(), 2),
        spread_hourly_corr=round(corr(hsp_t, hsp_p), 3),
        spread_hourly_sign_agree=round(float((np.sign(hsp_t[big]) == np.sign(hsp_p[big])).mean()), 3),
        rmse_da_hourly=round(rmse(y_da[test], pd_), 2), rmse_rt_hourly=round(rmse(y_rt[test], pr_), 2),
        n_days=int(len(tb_da_t)))


fit_mask = (FD < SPLIT).reindex(DA.index).fillna(False).values
test_idx = DA.index[(FD >= SPLIT).reindex(DA.index).fillna(False).values]
nonid = S.loc[~S.identical_flag & S.eligible_3yr, "OBJECTID"]   # blend members must have full 3-yr history
best1 = int(nonid.iloc[0])
kept = []
for c in [int(x) for x in nonid.head(8)]:
    if all(rmse(DA[c], DA[k]) > 1.0 for k in kept):
        kept.append(c)
    if len(kept) == 3:
        break

specs = {
    "single_best": dict(nodes=[name[best1]], ids=[best1], weights=[1.0], intercept=0.0, r2_fit=None, kind="single"),
    "single_TAV_RN": dict(nodes=["TAV_RN"], ids=[10016969364], weights=[1.0], intercept=0.0, r2_fit=None, kind="single"),
    "nominated_ols": fit(list(NOMINATED), "ols", fit_mask),
    "nominated_nnls": fit(list(NOMINATED), "nnls", fit_mask),
    "nominated_houston_only_ols": fit([10017290064, 10016969364], "ols", fit_mask),
    "scan_ols": fit(kept, "ols", fit_mask),
    "scan_nnls": fit(kept, "nnls", fit_mask),
}
for k, v in specs.items():
    v["oos"] = oos_eval(v, test_idx); v["insample"] = oos_eval(v, DA.index[fit_mask])
print("\n=== OOS (fit Jun4-Jul31, test Aug1-Sep13) ===")
cols = ["tb2_da_mae", "tb2_da_bias", "tb2_rt_mae", "tb2_rt_bias", "spread_daily_mae", "spread_hourly_corr",
        "spread_hourly_sign_agree", "rmse_da_hourly", "rmse_rt_hourly"]
tab = pd.DataFrame({k: {**{"nodes": "+".join(v["nodes"]), "w": v["weights"], "icpt": v["intercept"], "r2_fit": v["r2_fit"]},
                        **{c: v["oos"][c] for c in cols}} for k, v in specs.items()}).T
print(tab.to_string())
print("\ntrue OOS daily means: TB2_DA", specs["single_best"]["oos"]["tb2_da_true_mean"],
      "TB2_RT", specs["single_best"]["oos"]["tb2_rt_true_mean"])

score = {k: (v["oos"]["tb2_da_mae"] + v["oos"]["tb2_rt_mae"]) / 2 + v["oos"]["spread_daily_mae"] for k, v in specs.items()}
winner = min(score, key=score.get)
print("\nscores:", {k: round(v, 2) for k, v in score.items()}, "-> winner:", winner)
json.dump(specs, open(D / "item2_proxy_candidates.json", "w"), indent=2)
json.dump(score, open(D / "item2_proxy_scores.json", "w"), indent=2)

w = specs[winner]
full = w if w["kind"] == "single" else fit(w["ids"], w["kind"], np.ones(len(DA), bool))
definition = dict(
    target="RVN_RN", target_objectid=RVN, proxy_name=winner, nodes=full["nodes"], objectids=full["ids"],
    weights=full["weights"], intercept=full["intercept"],
    formula="proxy_LMP = intercept + sum(w_i * LMP_i), same weights applied to DA and to RT",
    fit_window="2026-06-04..2026-09-13 (refit on full overlap after OOS selection)",
    selected_by="min over OOS(Aug1-Sep13; fit Jun4-Jul31) of mean(TB2_DA_MAE,TB2_RT_MAE)+daily_spread_MAE",
    oos_metrics=w["oos"], r2_fit_full=full["r2_fit"],
    fallback=dict(applies_to="flowdays before 2023-12-01 (RBN_BESS1 has no prices before 2023-12)",
                  nodes=["TAV_RN"], objectids=[10016969364], weights=[1.0], intercept=0.0,
                  oos_metrics=specs["single_TAV_RN"]["oos"],
                  note="TAV_RN = best full-history single node by OOS score (1.08 vs winner 0.94); use alone for 2023-09..2023-11"),
    eligibility_rule="blend members restricted to nodes with DA prices already in 2023-09 (full 3-yr history); WAL_RN (best raw match, online 2025-05) excluded for that reason",
    limitations=["overlap window is ~100 summer days (2026-06-04..09-13); proxy untested in winter/shoulder",
                 "RVN_RN online only since 2026-06; its own congestion footprint may still be settling"],
    alternatives={k: dict(nodes=v["nodes"], weights=v["weights"], intercept=v["intercept"], oos=v["oos"])
                  for k, v in specs.items() if k != winner})
json.dump(definition, open(D / "item2_proxy_definition.json", "w"), indent=2)
print("\nwrote", D / "item2_proxy_definition.json")
print(json.dumps({k: definition[k] for k in ["nodes", "weights", "intercept", "r2_fit_full"]}))
