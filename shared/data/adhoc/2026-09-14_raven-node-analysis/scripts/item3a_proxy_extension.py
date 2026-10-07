"""ITEM 3a - multi-year seasonal DART picture for RVN_RN using item2's proxy blend.
Proxy (from derived/item2_proxy_definition.json): proxy_LMP = intercept + sum(w_i * LMP_i), same weights for DA and RT.
History limited by RBN_BESS1 (DA from 2023-12) -> proxy window 2023-12-01 .. 2026-09-13.
1) Validation: proxy-implied hourly stats vs RVN_RN actual over 2026-06-04..09-13.
2) Seasonal hourly win-rate / PL / EV tables (DJF, MAM, JJA, SON) + month x HE mean-spread grid.
3) Multi-year test of the persistence rules (follow yesterday's sign per HE) by year.
Outputs: derived/item3a_proxy_seasonal.json, derived/item3a_proxy_hourly_by_season.csv
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
W0, W1 = "2026-06-04", "2026-09-13"
pdef = json.loads((ROOT / "derived/item2_proxy_definition.json").read_text())
W = dict(zip(pdef["nodes"], pdef["weights"])); C = pdef["intercept"]

panel = pd.read_parquet(ROOT / "derived/item3a_node_panel.parquet")
panel = panel[panel.HE <= 24]                       # drop the 25th hour on fall-back DST days
wide = panel.pivot_table(index=["FLOWDAY", "HE"], columns="NODE", values=["DALMP", "RTLMP"]).astype("float64")
need = [("DALMP", n) for n in W] + [("RTLMP", n) for n in W]
px = wide.dropna(subset=need)
da = C + sum(W[n] * px[("DALMP", n)] for n in W)
rt = C + sum(W[n] * px[("RTLMP", n)] for n in W)
sysp = wide.loc[px.index, ("DALMP", "HB_BUSAVG")] - wide.loc[px.index, ("RTLMP", "HB_BUSAVG")]
p = pd.DataFrame(dict(spread=da - rt, sys_spread=sysp, hub_da=wide.loc[px.index, ("DALMP", "HB_BUSAVG")])).reset_index()
p["month"] = p.FLOWDAY.dt.month; p["year"] = p.FLOWDAY.dt.year
p["season"] = p.month.map({12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM", 6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"})
print("proxy window:", p.FLOWDAY.min().date(), "->", p.FLOWDAY.max().date(), "hours:", len(p))


def side_stats(pnl):
    n = len(pnl); w = pnl[pnl > 0]; l = -pnl[pnl < 0]
    p_win = len(w) / n; mw = w.mean() if len(w) else 0.0; ml = l.mean() if len(l) else 0.0
    b = mw / ml if ml > 0 else np.nan
    return dict(p_win=round(p_win, 3), mean_win=round(mw, 2), mean_loss=round(ml, 2), pl_ratio=round(b, 2) if np.isfinite(b) else None,
                ev_per_mwh=round(pnl.mean(), 2), loss_p95=round(float(np.percentile(l, 95)), 1) if len(l) else 0.0,
                loss_p99=round(float(np.percentile(l, 99)), 1) if len(l) else 0.0,
                kelly_f=round(float(p_win - (1 - p_win) / b), 3) if b and np.isfinite(b) and b > 0 else None)


def hourly(df):
    rows = []
    for he, s in df.groupby("HE").spread:
        t = s.mean() / (s.std() / np.sqrt(len(s)))
        rows.append(dict(HE=int(he), n=int(len(s)), spread_mean=round(s.mean(), 2), spread_std=round(s.std(), 2), t_stat=round(float(t), 2),
                         short=side_stats(s), long=side_stats(-s), best_side="short" if s.mean() > 0 else "long"))
    return rows


out = dict(meta=dict(proxy=pdef["proxy_name"], nodes=W, intercept=C, proxy_window=[str(p.FLOWDAY.min().date()), str(p.FLOWDAY.max().date())],
                     n_hours=int(len(p)), convention="spread = DA - RT; short PnL=+spread; long PnL=-spread; HE 1..24 (HE25 on DST fall-back dropped)",
                     caveat="proxy blend is 41% CBEC_ALL (SOUTH zone) - its congestion footprint is not Raven's; use for seasonal shape of the system-driven spread, not node-specific basis"))

# ---- 1) validation vs actual RVN_RN over the real window ----
act = json.loads((ROOT / "derived/item3a_dart_stats.json").read_text())["nodes"]["RVN_RN"]["hourly"]
pv_win = hourly(p[(p.FLOWDAY >= W0) & (p.FLOWDAY <= W1)])
val = pd.DataFrame([dict(HE=a["HE"], act_mean=a["spread_mean"], prx_mean=b["spread_mean"], act_pwin_short=a["short"]["p_win"], prx_pwin_short=b["short"]["p_win"],
                         act_best=a["best_side"], prx_best=b["best_side"], act_long_p99=a["long"]["loss_p99"], prx_long_p99=b["long"]["loss_p99"])
                    for a, b in zip(act, pv_win)])
out["validation_2026_window"] = dict(best_side_agreement=round(float((val.act_best == val.prx_best).mean()), 3),
                                     corr_hourly_mean_spread=round(float(val.act_mean.corr(val.prx_mean)), 3),
                                     mae_hourly_mean_spread=round(float((val.act_mean - val.prx_mean).abs().mean()), 2),
                                     mae_pwin_short=round(float((val.act_pwin_short - val.prx_pwin_short).abs().mean()), 3),
                                     table=val.to_dict(orient="records"))

# ---- 2) seasonal hourly tables + month x HE grid + JJA by year ----
out["by_season"] = {s: hourly(p[p.season == s]) for s in ["DJF", "MAM", "JJA", "SON"]}
out["season_summary"] = {}
for s, rows in out["by_season"].items():
    d = p[p.season == s]
    out["season_summary"][s] = dict(n_days=int(d.FLOWDAY.nunique()), mean_spread=round(d.spread.mean(), 2), spread_std=round(d.spread.std(), 2),
                                    p_short_win=round(float((d.spread > 0).mean()), 3),
                                    n_hours_abs_t_ge_1_5=int(sum(abs(r["t_stat"]) >= 1.5 for r in rows)),
                                    short_hours=int(sum(r["best_side"] == "short" for r in rows)),
                                    sum_ev_best_side_per_day=round(float(sum(r[r["best_side"]]["ev_per_mwh"] for r in rows)), 1),
                                    long_loss_p99_all_hours=round(float(np.percentile(np.maximum(d.spread, 0), 99)), 1),
                                    short_loss_p99_all_hours=round(float(np.percentile(np.maximum(-d.spread, 0), 99)), 1))
grid = p.groupby(["month", "HE"]).spread.mean().unstack().round(2)
out["month_x_HE_mean_spread"] = dict(months=grid.index.tolist(), HE=grid.columns.tolist(), values=grid.values.tolist())
gridp = p.groupby(["month", "HE"]).spread.apply(lambda s: (s > 0).mean()).unstack().round(3)
out["month_x_HE_p_short_win"] = dict(months=gridp.index.tolist(), HE=gridp.columns.tolist(), values=gridp.values.tolist())
out["by_year_month"] = p.groupby(["year", "month"]).spread.agg(mean="mean", p_short_win=lambda s: (s > 0).mean(), n="size").round(3).reset_index().to_dict(orient="records")
out["jja_by_year"] = {int(y): dict(mean_spread=round(d.spread.mean(), 2), p_short_win=round(float((d.spread > 0).mean()), 3),
                                   peak_HE16_20_mean=round(d[d.HE.between(16, 20)].spread.mean(), 2), morning_HE7_11_mean=round(d[d.HE.between(7, 11)].spread.mean(), 2),
                                   n_days=int(d.FLOWDAY.nunique())) for y, d in p[p.season == "JJA"].groupby("year")}
# congestion share of spread variance by season (proxy vs HB_BUSAVG)
out["basis_share_of_var_by_season"] = {s: round(float((d.spread - d.sys_spread).var() / d.spread.var()), 3) for s, d in p.groupby("season")}

# ---- 3) persistence rules by year (1 MW per HE) ----
pv = p.pivot(index="FLOWDAY", columns="HE", values="spread")


def bt(pos, mask=None):
    pnl = (pv * pos).sum(axis=1, min_count=1).dropna()
    if mask is not None: pnl = pnl[mask.reindex(pnl.index).fillna(False)]
    if len(pnl) < 2: return dict(mean_per_day=None, sharpe=None, win_rate_days=None, worst_day=None, n_days=int(len(pnl)))
    return dict(mean_per_day=round(float(pnl.mean()), 1), sharpe=round(float(pnl.mean() / pnl.std()), 3), win_rate_days=round(float((pnl > 0).mean()), 3),
                worst_day=round(float(pnl.min()), 0), n_days=int(len(pnl)))


follow = np.sign(pv.shift(1))
follow_920 = follow * [1.0 if 9 <= h <= 20 else 0.0 for h in follow.columns]   # per-column mask (HE 9-20 only)
rules = dict(always_short=lambda: 1.0, always_long=lambda: -1.0, follow_yesterday_all_HE=lambda: follow, follow_yesterday_HE9_20_only=lambda: follow_920,
             expanding_best_side_oos_after_60d=lambda: np.sign(pv.expanding(min_periods=60).mean().shift(1)))
out["rules_by_year"] = {}
yrs = pv.index.year
for name, f in rules.items():
    pos = f()
    out["rules_by_year"][name] = {"all": bt(pos)}
    for y in sorted(set(yrs)):
        out["rules_by_year"][name][str(y)] = bt(pos, pd.Series(yrs == y, index=pv.index))
    out["rules_by_year"][name]["by_season"] = {s: bt(pos, p.groupby("FLOWDAY").season.first() == s) for s in ["DJF", "MAM", "JJA", "SON"]}
out["per_HE_acf1_full_history"] = pv.apply(lambda c: c.autocorr(1)).round(3).to_dict()
out["per_HE_p_same_sign_full_history"] = (np.sign(pv) == np.sign(pv.shift(1))).iloc[1:].mean().round(3).to_dict()

(ROOT / "derived/item3a_proxy_seasonal.json").write_text(json.dumps(out, indent=1, default=str))
flat = pd.concat([pd.json_normalize(rows, sep="_").assign(season=s) for s, rows in out["by_season"].items()])
flat.to_csv(ROOT / "derived/item3a_proxy_hourly_by_season.csv", index=False)

print("\nVALIDATION", json.dumps({k: v for k, v in out["validation_2026_window"].items() if k != "table"}))
print(val.to_string(index=False))
print("\nSEASON SUMMARY"); print(pd.DataFrame(out["season_summary"]).T.to_string())
print("\nJJA by year", json.dumps(out["jja_by_year"]))
print("basis share of var by season", out["basis_share_of_var_by_season"])
print("\nMONTH x HE mean spread"); print(grid.to_string())
print("\nMONTH x HE p(short win)"); print(gridp.to_string())
for s in ["DJF", "MAM", "JJA", "SON"]:
    print(f"\n== {s}"); print(flat[flat.season == s][["HE", "n", "spread_mean", "t_stat", "short_p_win", "short_pl_ratio", "short_ev_per_mwh", "short_loss_p99", "long_p_win", "long_pl_ratio", "long_ev_per_mwh", "long_loss_p99", "best_side"]].to_string(index=False))
print("\nRULES BY YEAR")
for k, v in out["rules_by_year"].items(): print(k, json.dumps(v))
print("acf1 per HE", out["per_HE_acf1_full_history"])
print("p_same_sign per HE", out["per_HE_p_same_sign_full_history"])
