"""ITEM 3a - DART virtual at RVN_RN: hourly win prob, P/L ratio, EV, tail, Kelly; vs GKS and system hub.
Convention: spread = DA - RT. Short PnL = +spread, Long PnL = -spread (per MWh).
Window: RVN_RN real DA data 2026-06-04 .. 2026-09-13 (hour-ending 1..24, America/Chicago).
System reference = HB_BUSAVG (bus-average hub ~ energy-only, congestion-free system price).
HB_HOUSTON kept as the Raven zonal hub for congestion-basis conditioning.
Outputs: derived/item3a_dart_stats.json, derived/item3a_hourly_<node>.csv
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
W0, W1 = "2026-06-04", "2026-09-13"
NODES = ["RVN_RN", "GKS_BESS_RN", "HB_BUSAVG", "HB_HOUSTON"]
T_TRADEABLE = 1.5          # |t-stat| of mean spread required to call an hour tradeable
TAIL_MULT = 20.0           # p99 loss > TAIL_MULT x EV  => flag as catastrophic tail

panel = pd.read_parquet(ROOT / "derived/item3a_node_panel.parquet")
panel = panel[(panel.FLOWDAY >= W0) & (panel.FLOWDAY <= W1)]
wide = panel.pivot_table(index=["FLOWDAY", "HE"], columns="NODE", values=["DALMP", "RTLMP", "SPREAD"])
wide = wide.dropna(subset=[("SPREAD", n) for n in NODES]).astype("float64")   # identical hours for all nodes; float64 so json sees python floats
print("hours in window:", len(wide), "days:", wide.index.get_level_values(0).nunique())


def side_stats(pnl: pd.Series) -> dict:
    """pnl per MWh for one side. win = pnl>0, loss = pnl<0 (ties ignored for sizes)."""
    n = len(pnl); w = pnl[pnl > 0]; l = -pnl[pnl < 0]
    p_win = len(w) / n; p_loss = len(l) / n
    mw = w.mean() if len(w) else 0.0; ml = l.mean() if len(l) else 0.0
    ev = pnl.mean()
    b = mw / ml if ml > 0 else np.inf
    kelly = (p_win - p_loss / b) if np.isfinite(b) and b > 0 else (1.0 if p_win > 0 else 0.0)
    return dict(n=n, p_win=round(p_win, 3), mean_win=round(mw, 2), mean_loss=round(ml, 2),
                pl_ratio=round(b, 2) if np.isfinite(b) else None, ev_per_mwh=round(ev, 2),
                loss_p95=round(float(np.percentile(l, 95)), 1) if len(l) else 0.0,
                loss_p99=round(float(np.percentile(l, 99)), 1) if len(l) else 0.0,
                loss_max=round(float(l.max()), 1) if len(l) else 0.0,
                kelly_f=round(float(kelly), 3))


def hourly_table(spread: pd.Series) -> list:
    rows = []
    for he, s in spread.groupby(level="HE"):
        s = s.dropna()
        sh, lo = side_stats(s), side_stats(-s)
        t = s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if s.std() > 0 else 0.0
        best = "short" if s.mean() > 0 else "long"
        bs = sh if best == "short" else lo
        trimmed = s[(s > s.quantile(0.01)) & (s < s.quantile(0.99))].mean()
        tail_flag = bs["loss_p99"] > TAIL_MULT * max(bs["ev_per_mwh"], 0.01)
        rows.append(dict(HE=int(he), spread_mean=round(s.mean(), 2), spread_std=round(s.std(), 2),
                         spread_mean_trim1pct=round(trimmed, 2), t_stat=round(float(t), 2),
                         short=sh, long=lo, best_side=best,
                         tradeable=bool(abs(t) >= T_TRADEABLE and bs["ev_per_mwh"] > 0 and bs["kelly_f"] > 0 and not tail_flag),
                         tail_flag=bool(tail_flag)))
    return rows


def node_summary(rows, spread):
    best_ev = np.array([r[r["best_side"]]["ev_per_mwh"] for r in rows])
    ts = np.array([r["t_stat"] for r in rows])
    days = spread.index.get_level_values(0).unique().sort_values(); mid = days[len(days) // 2]
    h1 = spread[spread.index.get_level_values(0) < mid].groupby(level="HE").mean()
    h2 = spread[spread.index.get_level_values(0) >= mid].groupby(level="HE").mean()
    stable = float((np.sign(h1) == np.sign(h2)).mean())
    best = pd.Series({r["HE"]: 1 if r["best_side"] == "short" else -1 for r in rows})
    pnl_d = (spread * spread.index.get_level_values("HE").map(best).values).groupby(level=0).sum()
    return dict(n_hours_tradeable=int(sum(r["tradeable"] for r in rows)),
                n_hours_tail_flag=int(sum(r["tail_flag"] for r in rows)),
                n_hours_abs_t_ge_1_5=int((abs(ts) >= 1.5).sum()),
                mean_abs_ev_best_side=round(float(best_ev.mean()), 2),
                sum_ev_best_side_per_day=round(float(best_ev.sum()), 1),
                mean_spread=round(float(spread.mean()), 2), spread_std=round(float(spread.std()), 2),
                edge_to_vol=round(float(abs(spread.mean()) / spread.std()), 4),
                best_side_half_split_stability=round(stable, 3),
                short_hours=int((best > 0).sum()), long_hours=int((best < 0).sum()),
                p_win_short_all=round(float((spread > 0).mean()), 3),
                p_win_long_all=round(float((spread < 0).mean()), 3),
                insample_best_daily_pnl_mean_1mw=round(float(pnl_d.mean()), 1),
                insample_best_daily_pnl_std_1mw=round(float(pnl_d.std()), 1),
                insample_best_daily_sharpe=round(float(pnl_d.mean() / pnl_d.std()), 3),
                insample_best_daily_win_rate=round(float((pnl_d > 0).mean()), 3))


out = dict(meta=dict(window=[W0, W1], n_hours=int(len(wide)), n_days=int(wide.index.get_level_values(0).nunique()),
                     convention="spread = DA - RT; short PnL = +spread, long PnL = -spread; $/MWh; HE 1..24 period-ending America/Chicago",
                     system_reference="HB_BUSAVG (ERCOT bus-average hub) as congestion-free system price proxy; HB_HOUSTON = Raven zonal hub",
                     tradeable_rule=f"|t| >= {T_TRADEABLE} and EV>0 and Kelly f>0 and loss_p99 <= {TAIL_MULT}x EV",
                     data="real Yes Energy datalake prices via raw/price_panel (no mock)"),
           nodes={}, patterns={}, ranking={})
for n in NODES:
    sp = wide[("SPREAD", n)]
    rows = hourly_table(sp)
    out["nodes"][n] = dict(hourly=rows, summary=node_summary(rows, sp))
    pd.json_normalize(rows, sep="_").to_csv(ROOT / f"derived/item3a_hourly_{n}.csv", index=False)

# ---- Difficulty ranking (RVN vs GKS vs system) ----
crit = ["n_hours_tradeable", "mean_abs_ev_best_side", "edge_to_vol", "best_side_half_split_stability", "insample_best_daily_sharpe"]
tbl = pd.DataFrame({n: {c: out["nodes"][n]["summary"][c] for c in crit} for n in ["RVN_RN", "GKS_BESS_RN", "HB_BUSAVG"]}).T
tbl["rank_score"] = tbl.rank(ascending=False).mean(axis=1)  # lower = easier
out["ranking"] = dict(criteria=crit, table=tbl.reset_index().rename(columns={"index": "node"}).to_dict(orient="records"),
                      order_easiest_first=tbl.rank_score.sort_values().index.tolist())

# ---- Patterns at RVN_RN ----
r = wide[("SPREAD", "RVN_RN")].rename("spread").reset_index()
r["dow"] = r.FLOWDAY.dt.dayofweek; r["weekend"] = r.dow >= 5; r["month"] = r.FLOWDAY.dt.month
r["block"] = pd.cut(r.HE, [0, 6, 14, 20, 24], labels=["HE1-6 overnight", "HE7-14 morning/midday", "HE15-20 evening peak", "HE21-24 late"])
r["sys_spread"] = wide[("SPREAD", "HB_BUSAVG")].values
r["da_basis_hou"] = (wide[("DALMP", "RVN_RN")] - wide[("DALMP", "HB_HOUSTON")]).values   # RVN vs Houston hub (intra-zone)
r["rt_basis_hou"] = (wide[("RTLMP", "RVN_RN")] - wide[("RTLMP", "HB_HOUSTON")]).values
r["da_basis_sys"] = (wide[("DALMP", "RVN_RN")] - wide[("DALMP", "HB_BUSAVG")]).values
r["rt_basis_sys"] = (wide[("RTLMP", "RVN_RN")] - wide[("RTLMP", "HB_BUSAVG")]).values
r["basis_spread"] = r.spread - r.sys_spread     # congestion contribution to the node DART spread
r["hub_rt"] = wide[("RTLMP", "HB_BUSAVG")].values; r["hub_da"] = wide[("DALMP", "HB_BUSAVG")].values


def grp(df, key):
    g = df.groupby(key, observed=True).spread
    o = pd.DataFrame(dict(n=g.size(), mean=g.mean().round(2), p_short_win=(g.apply(lambda s: (s > 0).mean())).round(3),
                          p_long_win=(g.apply(lambda s: (s < 0).mean())).round(3),
                          t=(g.mean() / (g.std() / np.sqrt(g.size()))).round(2)))
    return o.reset_index().astype({key: str}).to_dict(orient="records")


P = out["patterns"]
P["by_block"] = grp(r, "block")
P["by_dow"] = grp(r, "dow")
P["by_weekend"] = grp(r, "weekend")
P["by_month"] = grp(r, "month")
P["by_block_x_month"] = r.groupby(["month", "block"], observed=True).spread.agg(["mean", "size"]).round(2).reset_index().astype({"block": str}).to_dict(orient="records")
P["by_block_x_weekend"] = r.groupby(["weekend", "block"], observed=True).spread.agg(["mean", "size"]).round(2).reset_index().astype({"block": str}).to_dict(orient="records")

cov = r[["spread", "sys_spread", "basis_spread"]].cov()
P["decomposition"] = dict(var_spread=round(cov.loc["spread", "spread"], 1), var_sys=round(cov.loc["sys_spread", "sys_spread"], 1),
                          var_basis=round(cov.loc["basis_spread", "basis_spread"], 1),
                          cov_sys_basis=round(cov.loc["sys_spread", "basis_spread"], 1),
                          mean_spread=round(r.spread.mean(), 2), mean_sys=round(r.sys_spread.mean(), 2), mean_basis=round(r.basis_spread.mean(), 2),
                          corr_spread_sys=round(r.spread.corr(r.sys_spread), 3), corr_spread_basis=round(r.spread.corr(r.basis_spread), 3),
                          mean_da_basis_vs_houston=round(r.da_basis_hou.mean(), 2), mean_rt_basis_vs_houston=round(r.rt_basis_hou.mean(), 2),
                          mean_da_basis_vs_busavg=round(r.da_basis_sys.mean(), 2), mean_rt_basis_vs_busavg=round(r.rt_basis_sys.mean(), 2))
# cross-node: how much of each node's spread is basis (vs HB_BUSAVG) and how correlated the nodes are
P["cross_node"] = {n: dict(var_spread=round(float(wide[("SPREAD", n)].var()), 1),
                          var_basis=round(float((wide[("SPREAD", n)] - wide[("SPREAD", "HB_BUSAVG")]).var()), 1),
                          basis_var_share=round(float((wide[("SPREAD", n)] - wide[("SPREAD", "HB_BUSAVG")]).var() / wide[("SPREAD", n)].var()), 3),
                          corr_with_system=round(float(wide[("SPREAD", n)].corr(wide[("SPREAD", "HB_BUSAVG")])), 3))
                   for n in ["RVN_RN", "GKS_BESS_RN", "HB_HOUSTON"]}
P["cross_node"]["corr_RVN_GKS"] = round(float(wide[("SPREAD", "RVN_RN")].corr(wide[("SPREAD", "GKS_BESS_RN")])), 3)
# congestion-sign conditioning (same hour - diagnostic, not known ex-ante)
r["da_basis_sign"] = np.where(r.da_basis_hou > 0.5, "DA basis > +0.5", np.where(r.da_basis_hou < -0.5, "DA basis < -0.5", "|DA basis| <= 0.5"))
r["rt_basis_sign"] = np.where(r.rt_basis_hou > 0.5, "RT basis > +0.5", np.where(r.rt_basis_hou < -0.5, "RT basis < -0.5", "|RT basis| <= 0.5"))
P["by_da_basis_sign_same_hour"] = grp(r, "da_basis_sign")
P["by_rt_basis_sign_same_hour"] = grp(r, "rt_basis_sign")
# tradeable version: previous flowday's mean basis vs Houston hub (known before today's bid)
dmean = r.groupby("FLOWDAY").agg(da_b=("da_basis_hou", "mean"), rt_b=("rt_basis_hou", "mean"), sp=("spread", "mean"), sys=("sys_spread", "mean"))
dmean["prev_da_b"] = dmean.da_b.shift(1); dmean["prev_rt_b"] = dmean.rt_b.shift(1)
r = r.merge(dmean[["prev_da_b", "prev_rt_b"]], left_on="FLOWDAY", right_index=True)
r["prev_day_da_basis_sign"] = np.where(r.prev_da_b > 0.5, "prev-day DA basis > +0.5", np.where(r.prev_da_b < -0.5, "prev-day DA basis < -0.5", "neutral"))
r["prev_day_rt_basis_sign"] = np.where(r.prev_rt_b > 0.5, "prev-day RT basis > +0.5", np.where(r.prev_rt_b < -0.5, "prev-day RT basis < -0.5", "neutral"))
P["by_prev_day_da_basis_sign"] = grp(r.dropna(subset=["prev_da_b"]), "prev_day_da_basis_sign")
P["by_prev_day_rt_basis_sign"] = grp(r.dropna(subset=["prev_rt_b"]), "prev_day_rt_basis_sign")
P["by_prev_day_rt_basis_sign_x_block"] = r.dropna(subset=["prev_rt_b"]).groupby(["prev_day_rt_basis_sign", "block"], observed=True).spread.agg(["mean", "size"]).round(2).reset_index().astype({"block": str}).to_dict(orient="records")
# system tightness: hub DA price percentile bucket (forecastable) and RT bucket (diagnostic)
for col in ["hub_da", "hub_rt"]:
    q = r[col].quantile([0.5, 0.9, 0.99])
    r[col + "_bkt"] = pd.cut(r[col], [-np.inf, q[0.5], q[0.9], q[0.99], np.inf], labels=["<p50", "p50-90", "p90-99", ">p99"])
    P[f"by_{col}_pctile"] = [dict(d, thresholds=[round(q[0.5], 1), round(q[0.9], 1), round(q[0.99], 1)]) for d in grp(r, col + "_bkt")]

# ---- persistence / autocorrelation ----
dsign = np.sign(dmean.sp)
P["persistence"] = dict(
    daily_mean_spread_sign_pos_rate=round(float((dsign > 0).mean()), 3),
    p_same_sign_as_yesterday=round(float((dsign == dsign.shift(1)).dropna().mean()), 3),
    p_same_sign_expected_if_iid=round(float((dsign > 0).mean() ** 2 + (dsign < 0).mean() ** 2), 3),
    daily_mean_spread_acf_lag1=round(float(dmean.sp.autocorr(1)), 3),
    daily_mean_spread_acf_lag7=round(float(dmean.sp.autocorr(7)), 3),
    daily_sys_spread_acf_lag1=round(float(dmean.sys.autocorr(1)), 3),
    daily_da_basis_acf_lag1=round(float(dmean.da_b.autocorr(1)), 3),
    daily_rt_basis_acf_lag1=round(float(dmean.rt_b.autocorr(1)), 3))
pv = r.pivot(index="FLOWDAY", columns="HE", values="spread")
he_pers = pd.DataFrame(dict(
    p_same_sign=(np.sign(pv) == np.sign(pv.shift(1))).iloc[1:].mean().round(3),
    acf1=pv.apply(lambda c: c.autocorr(1)).round(3),
    p_pos=(pv > 0).mean().round(3)))
he_pers["p_same_sign_iid"] = (he_pers.p_pos ** 2 + (1 - he_pers.p_pos) ** 2).round(3)
P["persistence"]["per_HE"] = he_pers.reset_index().to_dict(orient="records")


def bt(pvx, pos):
    pnl = (pvx * pos).sum(axis=1, min_count=1).dropna()
    return dict(mean_per_day=round(float(pnl.mean()), 1), std=round(float(pnl.std()), 1), sharpe=round(float(pnl.mean() / pnl.std()), 3),
                win_rate_days=round(float((pnl > 0).mean()), 3), total=round(float(pnl.sum()), 0), worst_day=round(float(pnl.min()), 0), n_days=int(len(pnl)))


def rules(pvx):
    insamp = pd.DataFrame(np.sign(pvx.mean()).values[None, :].repeat(len(pvx), 0), index=pvx.index, columns=pvx.columns)
    return dict(always_short=bt(pvx, 1.0), always_long=bt(pvx, -1.0),
                follow_yesterday_sign_per_HE=bt(pvx, np.sign(pvx.shift(1)).iloc[1:]),
                insample_best_side_per_HE=bt(pvx, insamp),
                expanding_best_side_per_HE_oos_after_21d=bt(pvx, np.sign(pvx.expanding(min_periods=21).mean().shift(1)).dropna(how="all")))


P["rule_backtests_1mw_per_HE"] = {"RVN_RN": rules(pv)}
for n in ["GKS_BESS_RN", "HB_BUSAVG"]:
    pvn = wide[("SPREAD", n)].rename("SPREAD").reset_index().pivot(index="FLOWDAY", columns="HE", values="SPREAD")
    P["rule_backtests_1mw_per_HE"][n] = rules(pvn)

# ---- Sanity: top spike hours driving the tails ----
top = r.reindex(r.spread.abs().sort_values(ascending=False).index).head(12)[["FLOWDAY", "HE", "spread", "sys_spread", "basis_spread", "hub_rt"]].copy()
top["FLOWDAY"] = top.FLOWDAY.dt.strftime("%Y-%m-%d")
P["largest_abs_spread_hours"] = top.round(1).to_dict(orient="records")
P["share_of_total_abs_pnl_from_top1pct_hours"] = round(float(r.spread.abs().nlargest(int(len(r) * 0.01)).sum() / r.spread.abs().sum()), 3)

# ---- Sizing input for dart-virtual-trader (RVN_RN) ----
sizing = []
for rr in out["nodes"]["RVN_RN"]["hourly"]:
    side = rr["best_side"]; bs = rr[side]
    mw_quarter_kelly = round(max(bs["kelly_f"], 0) * 0.25 * 100, 1)        # fraction of a nominal 100 MW cap
    mw_p99_budget = round(min(100.0, 5000.0 / bs["loss_p99"]), 1) if bs["loss_p99"] > 0 else 100.0   # p99 hourly loss <= $5k
    sizing.append(dict(HE=rr["HE"], side=side, ev_per_mwh=bs["ev_per_mwh"], p_win=bs["p_win"], pl_ratio=bs["pl_ratio"],
                       loss_p99=bs["loss_p99"], kelly_f=bs["kelly_f"], mw_quarter_kelly_of_100=mw_quarter_kelly,
                       mw_for_p99_loss_le_5k=mw_p99_budget, suggested_mw=round(min(mw_quarter_kelly, mw_p99_budget), 1) if rr["tradeable"] else 0.0,
                       trade=rr["tradeable"]))
out["sizing_rvn"] = dict(basis="quarter-Kelly of a nominal 100 MW cap, capped by MW such that p99 hourly loss <= $5,000; 0 MW where not tradeable", hours=sizing)

(ROOT / "derived/item3a_dart_stats.json").write_text(json.dumps(out, indent=1, default=str))
# console digest
cols = ["HE", "spread_mean", "spread_mean_trim1pct", "t_stat", "short_p_win", "short_pl_ratio", "short_ev_per_mwh", "short_loss_p99",
        "long_p_win", "long_pl_ratio", "long_ev_per_mwh", "long_loss_p99", "best_side", "tradeable", "tail_flag"]
for n in NODES:
    print("\n==", n, json.dumps(out["nodes"][n]["summary"]))
    print(pd.json_normalize(out["nodes"][n]["hourly"], sep="_")[cols].to_string(index=False))
print("\nRANKING", json.dumps(out["ranking"], indent=1))
for k, v in P.items():
    print("\n--", k); print(json.dumps(v, default=str)[:3500])
print("\nSIZING"); print(pd.DataFrame(out["sizing_rvn"]["hours"]).to_string(index=False))
