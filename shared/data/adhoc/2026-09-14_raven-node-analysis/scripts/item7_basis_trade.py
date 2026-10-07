"""ITEM 7 PART B — GKS <-> Raven basis trade assessment (constraints, basis stats, virtual spread, dispatch, risk).
Inputs: derived/item7_basis_constraint_panel.parquet, derived/item7_price_panel.parquet (from item7_basis_panel.py).
Conventions: MCC = -SF x lambda; basis = RVN - GKS; spread = DA - RT (positive => short DA).
Basis virtual = short DA at RVN + long DA at GKS (1 MW each): PnL_h = spread_RVN - spread_GKS = basis_DA - basis_RT.
Outputs derived/item7_basis_constraints.csv, derived/item7_basis_trade.json. Real data only.
"""
import json
from pathlib import Path
import numpy as np, pandas as pd

R = Path(__file__).resolve().parents[1]; D = R / "derived"
B = pd.read_parquet(D / "item7_basis_constraint_panel.parquet")
P = pd.read_parquet(D / "item7_price_panel.parquet")
OVL0 = pd.Timestamp("2026-06-04")
TOP10 = ["WHARTN", "BLESSI_PAVLOV1_1", "E_PASP", "1710__C", "HARGRO_TWINBU1_1", "STPELM27_1", "630__B", "STPWAP39_1", "587__A", "50__A"]
out = {}

# ---------------- 1. constraints by basis impact ----------------
B["abs_basis"] = B.basis_h.abs()
B["year"] = B.hour.dt.year
last12 = B.hour.max() - pd.DateOffset(months=12)
rows = []
for cn, s in B.groupby("CONSTRAINTNAME"):
    da, rt = s[s.MARKET == "DA"], s[s.MARKET == "RT"]
    ov = s[s.hour >= OVL0]
    def sf(sub, col):
        v = sub[col].dropna(); return float(v.mean()) if len(v) else np.nan
    r = dict(constraint=cn, hours=len(s), da_hours=len(da), rt_hours_equiv=round(float(rt.bind_frac.sum()), 1),
             sf_gks_da=sf(da, "sf_gks"), sf_gks_rt=sf(rt, "sf_gks"),
             sf_loc_da=sf(da, "sf_loc"), sf_loc_rt=sf(rt, "sf_loc"),
             sf_rvn_real_da=sf(da[da.src == "RVN"], "sf_rvn_mean"), sf_rvn_real_rt=sf(rt[rt.src == "RVN"], "sf_rvn_mean"),
             sf_proxy_da=sf(da, "sf_proxy_mean"),
             cum_mcc_rvn=float(s.mcc_rvn.sum()), cum_mcc_gks=float(s.mcc_gks.sum()),
             cum_basis=float(s.basis_h.sum()), cum_basis_da=float(da.basis_h.sum()), cum_basis_rt=float(rt.basis_h.sum()),
             gross_basis=float(s.abs_basis.sum()), gross_basis_last12m=float(s[s.hour >= last12].abs_basis.sum()),
             gross_basis_overlap=float(ov.abs_basis.sum()), overlap_share_real=float((ov.src == "RVN").mean()) if len(ov) else np.nan,
             mean_lambda_da=float(da.lam_h.mean()) if len(da) else np.nan,
             first_bind=str(s.hour.min().date()), last_bind=str(s.hour.max().date()))
    # sign relation on DA SFs (RT as check); use real RVN SF when available else location SF
    a = r["sf_rvn_real_da"] if not np.isnan(r["sf_rvn_real_da"]) else r["sf_loc_da"]
    g = r["sf_gks_da"]
    if np.isnan(a) or np.isnan(g) or abs(a) < 0.005 or abs(g) < 0.005: rel = "one-sided/negligible"
    elif np.sign(a) != np.sign(g): rel = "OPPOSING"
    else: rel = "same-sign"
    r["sf_relation"] = rel; r["delta_sf_da"] = (a - g) if not (np.isnan(a) or np.isnan(g)) else np.nan
    r["basis_impact_index"] = abs(r["delta_sf_da"]) * r["mean_lambda_da"] * r["da_hours"] if not np.isnan(r["delta_sf_da"]) else np.nan
    rows.append(r)
C = pd.DataFrame(rows).sort_values("gross_basis", ascending=False)
C.to_csv(D / "item7_basis_constraints.csv", index=False)
tot_gross = C.gross_basis.sum()
opp = C[C.sf_relation == "OPPOSING"]
print("constraints", len(C), "opposing", len(opp), "opposing share of gross basis", round(opp.gross_basis.sum() / tot_gross, 3))
print(C.head(25)[["constraint", "sf_relation", "sf_rvn_real_da", "sf_loc_da", "sf_gks_da", "cum_basis", "gross_basis", "gross_basis_last12m", "last_bind"]].round(3).to_string())
print("\nOPPOSING top 15:"); print(opp.head(15)[["constraint", "sf_rvn_real_da", "sf_loc_da", "sf_gks_da", "cum_basis_da", "cum_basis_rt", "gross_basis", "gross_basis_last12m", "last_bind"]].round(3).to_string())
out["constraints"] = {"n": len(C), "n_opposing": int(len(opp)), "gross_basis_total": tot_gross,
                      "opposing_share_gross": float(opp.gross_basis.sum() / tot_gross),
                      "same_sign_share_gross": float(C[C.sf_relation == "same-sign"].gross_basis.sum() / tot_gross),
                      "one_sided_share_gross": float(C[C.sf_relation == "one-sided/negligible"].gross_basis.sum() / tot_gross),
                      "top20_by_gross": C.head(20).round(4).to_dict("records"),
                      "top15_opposing": opp.head(15).round(4).to_dict("records"),
                      "top10_item2": C[C.constraint.isin(TOP10)].round(4).to_dict("records")}

# ---------------- 2. basis level / vol / profile ----------------
P["month"] = P.index.month; P["year"] = P.index.year
P["basis_DA"] = P.DA_RVN - P.DA_GKS_BESS_RN; P["basis_RT"] = P.RT_RVN - P.RT_GKS_BESS_RN
P["hub_basis_DA"] = P.DA_HB_HOUSTON - P.DA_HB_SOUTH; P["hub_basis_RT"] = P.RT_HB_HOUSTON - P.RT_HB_SOUTH
P["spread_RVN"] = P.DA_RVN - P.RT_RVN; P["spread_GKS"] = P.DA_GKS_BESS_RN - P.RT_GKS_BESS_RN
P["spread_pnl"] = P.spread_RVN - P.spread_GKS          # short RVN / long GKS basis virtual
ov = P[P.index >= OVL0]

def bstats(df, col):
    s = df[col]; return dict(mean=float(s.mean()), median=float(s.median()), std=float(s.std()), p5=float(s.quantile(.05)),
                             p95=float(s.quantile(.95)), min=float(s.min()), max=float(s.max()), share_pos=float((s > 0).mean()))
out["basis"] = {"window_full": [str(P.index.min()), str(P.index.max()), int(len(P))], "window_overlap": [str(ov.index.min()), str(ov.index.max()), int(len(ov))]}
for lab, df in (("full", P), ("overlap", ov)):
    out["basis"][lab] = {c: bstats(df, c) for c in ("basis_DA", "basis_RT", "hub_basis_DA", "hub_basis_RT")}
    out["basis"][lab]["by_HE"] = df.groupby("HE")[["basis_DA", "basis_RT"]].agg(["mean", "std"]).round(2).pipe(lambda t: t.set_axis([f"{a}_{b}" for a, b in t.columns], axis=1)).to_dict()
    out["basis"][lab]["by_month"] = df.groupby("month")[["basis_DA", "basis_RT"]].agg(["mean", "std"]).round(2).pipe(lambda t: t.set_axis([f"{a}_{b}" for a, b in t.columns], axis=1)).to_dict()
out["basis"]["by_year"] = P.groupby("year")[["basis_DA", "basis_RT"]].agg(["mean", "std"]).round(2).pipe(lambda t: t.set_axis([f"{a}_{b}" for a, b in t.columns], axis=1)).to_dict()
print("\nbasis full:", {k: round(v["mean"], 2) for k, v in out["basis"]["full"].items() if isinstance(v, dict) and "mean" in v})
print("basis overlap:", {k: round(v["mean"], 2) for k, v in out["basis"]["overlap"].items() if isinstance(v, dict) and "mean" in v})
print(P.groupby("HE")[["basis_DA", "basis_RT"]].mean().round(2).T.to_string())

# ---------------- 3. variance explained by constraints ----------------
def hourly_sum(mask_fn=None):
    s = B if mask_fn is None else B[mask_fn(B)]
    return s.pivot_table(index="hour", columns="MARKET", values="basis_h", aggfunc="sum").reindex(P.index).fillna(0.0)
allc = hourly_sum(); oppc = hourly_sum(lambda b: b.CONSTRAINTNAME.isin(set(opp.constraint)))
top10c = hourly_sum(lambda b: b.CONSTRAINTNAME.isin(TOP10))
def r2(y, x):
    m = y.notna() & x.notna(); y, x = y[m], x[m]
    if len(y) < 10: return None
    beta = np.cov(x, y)[0, 1] / x.var(); return dict(r2=float(np.corrcoef(x, y)[0, 1] ** 2), beta=float(beta), n=int(len(y)))
out["variance_explained"] = {}
for lab, df in (("full", P), ("overlap", ov)):
    idx = df.index
    out["variance_explained"][lab] = {
        "DA": {"all_constraints": r2(df.basis_DA, allc["DA"].reindex(idx)), "opposing_only": r2(df.basis_DA, oppc["DA"].reindex(idx)), "item2_top10": r2(df.basis_DA, top10c["DA"].reindex(idx))},
        "RT": {"all_constraints": r2(df.basis_RT, allc["RT"].reindex(idx)), "opposing_only": r2(df.basis_RT, oppc["RT"].reindex(idx)), "item2_top10": r2(df.basis_RT, top10c["RT"].reindex(idx))}}
print("\nvariance explained:", json.dumps(out["variance_explained"], indent=0)[:1500])

# ---------------- 4. DA basis virtual vs legs ----------------
def trade_stats(pnl):
    w = pnl[pnl > 0]; l = pnl[pnl < 0]
    return dict(n=int(len(pnl)), ev=float(pnl.mean()), std=float(pnl.std()), win=float((pnl > 0).mean()),
                pl_ratio=float(w.mean() / -l.mean()) if len(w) and len(l) else None,
                p1=float(pnl.quantile(.01)), p99=float(pnl.quantile(.99)), min=float(pnl.min()), max=float(pnl.max()),
                t=float(pnl.mean() / pnl.std() * np.sqrt(len(pnl))) if pnl.std() > 0 else None)

def daily_sharpe(pnl_h):
    d = pnl_h.groupby(pnl_h.index.normalize()).sum(); return float(d.mean() / d.std() * np.sqrt(365)) if d.std() > 0 else None

def walk_forward(df, col):
    """direction per HE chosen on first half by sign of mean, applied to second half; Sharpe of daily PnL (1 MW/HE)."""
    cut = df.index[len(df) // 2]; a, b = df[df.index < cut], df[df.index >= cut]
    sgn = np.sign(a.groupby("HE")[col].mean()).replace(0, 1)
    pnl = b[col] * b.HE.map(sgn).values
    return dict(sharpe_oos=daily_sharpe(pnl), ev_oos=float(pnl.mean()), win_oos=float((pnl > 0).mean()), split=str(cut.date()))

out["virtual"] = {}
for lab, df in (("full", P), ("overlap", ov)):
    sec = {"by_HE": {}}
    for he, g in df.groupby("HE"):
        sec["by_HE"][int(he)] = {"spread_shortRVN_longGKS": trade_stats(g.spread_pnl), "leg_RVN_short": trade_stats(g.spread_RVN), "leg_GKS_short": trade_stats(g.spread_GKS)}
    sec["all_hours"] = {"spread_shortRVN_longGKS": trade_stats(df.spread_pnl), "leg_RVN_short": trade_stats(df.spread_RVN), "leg_GKS_short": trade_stats(df.spread_GKS)}
    sec["daily_sharpe_fixed_side"] = {"spread_short_RVN_long_GKS": daily_sharpe(df.spread_pnl), "spread_long_RVN_short_GKS": daily_sharpe(-df.spread_pnl),
                                      "RVN_short": daily_sharpe(df.spread_RVN), "RVN_long": daily_sharpe(-df.spread_RVN),
                                      "GKS_short": daily_sharpe(df.spread_GKS), "GKS_long": daily_sharpe(-df.spread_GKS)}
    sec["walk_forward_per_HE"] = {"spread": walk_forward(df, "spread_pnl"), "leg_RVN": walk_forward(df, "spread_RVN"), "leg_GKS": walk_forward(df, "spread_GKS")}
    # evening band where GKS discount lives (HE19-22): spread = long RVN DA / short GKS DA? sign by data
    ev = df[df.HE.between(19, 22)]
    sec["HE19_22"] = {"spread_shortRVN_longGKS": trade_stats(ev.spread_pnl), "leg_RVN_short": trade_stats(ev.spread_RVN), "leg_GKS_short": trade_stats(ev.spread_GKS)}
    sec["corr_spreads"] = float(df.spread_RVN.corr(df.spread_GKS))
    out["virtual"][lab] = sec
    print(f"\n[{lab}] spread all-hours", {k: round(v, 3) if isinstance(v, float) else v for k, v in sec["all_hours"]["spread_shortRVN_longGKS"].items()})
    print(f"[{lab}] sharpe fixed side", {k: round(v, 2) if v else v for k, v in sec["daily_sharpe_fixed_side"].items()})
    print(f"[{lab}] walk-forward", sec["walk_forward_per_HE"])
    print(f"[{lab}] corr spreads", round(sec["corr_spreads"], 3))
    tab = pd.DataFrame({he: {"ev_spread": v["spread_shortRVN_longGKS"]["ev"], "win_spread": v["spread_shortRVN_longGKS"]["win"], "p1_spread": v["spread_shortRVN_longGKS"]["p1"], "p99_spread": v["spread_shortRVN_longGKS"]["p99"],
                             "ev_RVNshort": v["leg_RVN_short"]["ev"], "ev_GKSshort": v["leg_GKS_short"]["ev"]} for he, v in sec["by_HE"].items()}).T
    print(tab.round(2).to_string())

# ---------------- 5. dispatch complementarity ----------------
def tb2(s):
    if len(s) < 24: return np.nan
    v = np.sort(s.values); return (v[-1] + v[-2]) / 2 - (v[0] + v[1]) / 2
def common_tb2(a, b):
    v = np.sort((a + b).values); return ((v[-1] + v[-2]) / 2 - (v[0] + v[1]) / 2)   # same hours for both, on summed price
out["dispatch"] = {}
for lab, df in (("full", P), ("overlap", ov)):
    rec = {}
    for mk in ("DA", "RT"):
        g = df.groupby("FLOWDAY"); res = []
        for fd, x in g:
            if len(x) != 24: continue
            a, b = x[f"{mk}_RVN"], x[f"{mk}_GKS_BESS_RN"]
            ind = tb2(a) + tb2(b); com = common_tb2(a, b)
            top_a = set(x.nlargest(2, f"{mk}_RVN").HE); top_b = set(x.nlargest(2, f"{mk}_GKS_BESS_RN").HE)
            bot_a = set(x.nsmallest(2, f"{mk}_RVN").HE); bot_b = set(x.nsmallest(2, f"{mk}_GKS_BESS_RN").HE)
            res.append(dict(fd=fd, ind=ind, com=com, dis_same=len(top_a & top_b), chg_same=len(bot_a & bot_b),
                            top_rvn=sorted(top_a), top_gks=sorted(top_b)))
        r = pd.DataFrame(res); days = len(r); yrs = days / 365.25
        rec[mk] = dict(days=days, tb2_sum_independent=float(r.ind.mean()), tb2_common=float(r.com.mean()),
                       uplift_per_day_per_mwh=float((r.ind - r.com).mean()), uplift_pct=float((r.ind - r.com).sum() / r.com.sum()),
                       uplift_usd_per_year_200MWh_each=float((r.ind - r.com).sum() * 200 / yrs),
                       share_days_same_2_discharge_hours=float((r.dis_same == 2).mean()), share_days_no_common_discharge_hour=float((r.dis_same == 0).mean()),
                       share_days_same_2_charge_hours=float((r.chg_same == 2).mean()),
                       mean_top_he_rvn=float(np.mean([np.mean(t) for t in r.top_rvn])), mean_top_he_gks=float(np.mean([np.mean(t) for t in r.top_gks])))
    out["dispatch"][lab] = rec
    print(f"\n[{lab}] dispatch", json.dumps(rec, indent=0)[:900])

# ---------------- 6. risk ----------------
def corr_block(df):
    return dict(da_price=float(df.DA_RVN.corr(df.DA_GKS_BESS_RN)), rt_price=float(df.RT_RVN.corr(df.RT_GKS_BESS_RN)),
                dart_spread=float(df.spread_RVN.corr(df.spread_GKS)),
                daily_tb2_da=float(df.groupby("FLOWDAY").DA_RVN.apply(tb2).corr(df.groupby("FLOWDAY").DA_GKS_BESS_RN.apply(tb2))),
                daily_tb2_rt=float(df.groupby("FLOWDAY").RT_RVN.apply(tb2).corr(df.groupby("FLOWDAY").RT_GKS_BESS_RN.apply(tb2))))
out["risk"] = {"corr_full": corr_block(P), "corr_overlap": corr_block(ov)}
sc = P[P.RT_HB_BUSAVG > 500]; nm = P[P.RT_HB_BUSAVG <= 500]
out["risk"]["scarcity_RT_busavg_gt_500"] = {"hours": int(len(sc)), "basis_RT_mean": float(sc.basis_RT.mean()), "basis_RT_std": float(sc.basis_RT.std()),
    "basis_RT_min": float(sc.basis_RT.min()), "basis_RT_max": float(sc.basis_RT.max()), "basis_DA_mean": float(sc.basis_DA.mean()),
    "spread_pnl_mean": float(sc.spread_pnl.mean()), "spread_pnl_min": float(sc.spread_pnl.min()), "spread_pnl_max": float(sc.spread_pnl.max()),
    "corr_rt_price_in_scarcity": float(sc.RT_RVN.corr(sc.RT_GKS_BESS_RN)), "normal_basis_RT_std": float(nm.basis_RT.std()),
    "share_of_gross_spread_pnl": float(sc.spread_pnl.abs().sum() / P.spread_pnl.abs().sum())}
top = P.reindex(P.spread_pnl.abs().sort_values(ascending=False).index).head(12)
out["risk"]["largest_spread_pnl_hours"] = [dict(dt=str(i), spread_pnl=round(r.spread_pnl, 1), basis_DA=round(r.basis_DA, 1), basis_RT=round(r.basis_RT, 1),
                                                 rt_busavg=round(r.RT_HB_BUSAVG, 1), src=r.DA_RVN_src) for i, r in top.iterrows()]
# constraint-retirement exposure: gross basis by forward status
C["status"] = np.where(pd.to_datetime(C.last_bind) < pd.Timestamp("2026-03-01"), "no bind since Mar-2026",
              np.where(C.gross_basis_last12m / C.gross_basis < 0.25, "faded (<25% in last 12m)", "live"))
out["risk"]["gross_basis_by_status"] = C.groupby("status").gross_basis.sum().div(tot_gross).round(3).to_dict()
out["risk"]["opposing_gross_basis_by_status"] = opp.assign(status=C.loc[opp.index, "status"]).groupby("status").gross_basis.sum().div(opp.gross_basis.sum()).round(3).to_dict()
print("\nrisk", json.dumps(out["risk"], indent=0)[:2500])
C.to_csv(D / "item7_basis_constraints.csv", index=False)
json.dump(out, open(D / "item7_basis_trade.json", "w"), indent=1, default=str)
print("\nsaved item7_basis_trade.json")
