"""ITEM 6 shared loaders: panel, daily regime features (with availability class), splits, stats helpers.
Availability classes (relative to DAM bid cutoff 10:00 CT on D-1):
  ex_ante_lag2 : built from D-2 (fully known at bid time)
  ex_ante_lag1 : built from D-1 full day (item3a convention; D-1 HE11-24 are NOT yet known at 10:00 -> mildly leaky, upper bound)
  needs_fc     : same-day DA price / load / wind / solar (DA clears ~13:30 D-1, after cutoff; usable only via a forecast -> upper bound)
  ex_post      : same-day RT quantities (diagnostic only, never tradeable)
"""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]; D = ROOT / "derived"
REAL0, REAL_SPLIT, END = "2026-06-04", "2026-08-01", "2026-09-13"
FULL_SPLIT = "2025-09-01"
SEASON = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM", 6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"}

def load_panel():
    P = pd.read_parquet(D / "item6_panel.parquet")
    P["basis_sys"] = P.spread_rvn - P.spread_sys      # node spread minus system spread (item3a definition)
    P["season"] = P.FLOWDAY.dt.month.map(SEASON)
    return P

def constraints():
    import json
    return json.load(open(D / "item6_panel_meta.json"))["constraints"]

def daily_features(P):
    g = P.groupby("FLOWDAY")
    f = pd.DataFrame(index=g.size().index)
    pk = P.HE.between(15, 20); op = P.HE.between(1, 6)
    f["da_level"] = g.da_sys.mean()
    f["da_shape"] = P[pk].groupby("FLOWDAY").da_sys.mean() - P[op].groupby("FLOWDAY").da_sys.mean()
    f["load_max"] = g.load_mw.max(); f["wind_mean"] = g.wind_mw.mean(); f["solar_max"] = g.solar_mw.max()
    f["netload_max"] = g.netload_mw.max()
    f["rt_level"] = g.rt_sys.mean(); f["rt_vol"] = g.rt_sys.std(); f["rt_max"] = g.rt_sys.max()
    f["spread_mean"] = g.spread_rvn.mean()
    f["mcc_abs"] = (P.mcc_da.abs() + P.mcc_rt.abs()).groupby(P.FLOWDAY).sum()
    for lag in (1, 2):
        for c in ("rt_vol", "rt_max", "rt_level", "spread_mean", "mcc_abs"):
            f[f"{c}_lag{lag}"] = f[c].shift(lag)
    f["season"] = f.index.month.map(SEASON)
    return f

FEATURES = {  # name -> availability class
    "da_level": "needs_fc", "da_shape": "needs_fc", "load_max": "needs_fc", "wind_mean": "needs_fc", "solar_max": "needs_fc", "netload_max": "needs_fc",
    "rt_vol_lag1": "ex_ante_lag1", "rt_max_lag1": "ex_ante_lag1", "spread_mean_lag1": "ex_ante_lag1", "mcc_abs_lag1": "ex_ante_lag1",
    "rt_vol_lag2": "ex_ante_lag2", "rt_max_lag2": "ex_ante_lag2", "spread_mean_lag2": "ex_ante_lag2",
    "rt_level": "ex_post", "rt_vol": "ex_post", "rt_max": "ex_post", "mcc_abs": "ex_post",
}

def tercile_labels(train_vals, vals):
    q = np.nanquantile(train_vals, [1 / 3, 2 / 3])
    return pd.cut(vals, [-np.inf, q[0], q[1], np.inf], labels=["low", "mid", "high"]), q

def side_stats(s):
    """s = spread series. Returns dict for short (pnl=+s) and long (pnl=-s)."""
    out = {}
    for side, pnl in (("short", s), ("long", -s)):
        w = pnl[pnl > 0]; l = -pnl[pnl < 0]
        out[side] = dict(p_win=round(float((pnl > 0).mean()), 3), pl_ratio=round(float(w.mean() / l.mean()), 2) if len(l) and len(w) else None,
                         ev=round(float(pnl.mean()), 2), loss_p95=round(float(np.percentile(l, 95)), 1) if len(l) else 0.0,
                         loss_p99=round(float(np.percentile(l, 99)), 1) if len(l) else 0.0)
    return out

def tstat(s):
    s = pd.Series(s).dropna()
    if len(s) < 3 or s.std(ddof=1) == 0: return 0.0, 1.0
    t, p = stats.ttest_1samp(s, 0.0); return float(t), float(p)

def bh(pvals, q=0.10):
    """Benjamini-Hochberg: returns boolean array of rejections at FDR q."""
    p = np.asarray(pvals, float); n = len(p); order = np.argsort(p); ranked = p[order]
    thresh = q * (np.arange(1, n + 1) / n); ok = ranked <= thresh
    k = np.max(np.where(ok)[0]) + 1 if ok.any() else 0
    rej = np.zeros(n, bool); rej[order[:k]] = True; return rej

def rule_metrics(pnl_hourly: pd.Series, flowdays: pd.Series):
    """pnl per MWh per traded hour (1 MW). Returns EV/MWh, hit rate, daily Sharpe, max drawdown, worst hour, n."""
    pnl_hourly = pd.Series(pnl_hourly.values, index=flowdays.values).dropna()
    if len(pnl_hourly) == 0: return dict(n_hours=0)
    daily = pnl_hourly.groupby(level=0).sum()
    cum = daily.cumsum(); dd = (cum - cum.cummax()).min()
    return dict(n_hours=int(len(pnl_hourly)), n_days=int(len(daily)), ev_per_mwh=round(float(pnl_hourly.mean()), 3),
                total_per_mw=round(float(pnl_hourly.sum()), 1), per_day_per_mw=round(float(daily.mean()), 2),
                hit_rate_hours=round(float((pnl_hourly > 0).mean()), 3), hit_rate_days=round(float((daily > 0).mean()), 3),
                sharpe_daily=round(float(daily.mean() / daily.std(ddof=1)), 3) if daily.std(ddof=1) > 0 else None,
                sharpe_annualised=round(float(daily.mean() / daily.std(ddof=1) * np.sqrt(365)), 2) if daily.std(ddof=1) > 0 else None,
                max_drawdown_per_mw=round(float(dd), 1), worst_hour=round(float(pnl_hourly.min()), 1), worst_day=round(float(daily.min()), 1),
                t_stat=round(tstat(pnl_hourly)[0], 2))
