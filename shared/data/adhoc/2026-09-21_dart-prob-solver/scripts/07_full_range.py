"""Corrected solver: BOTH thresholds swept over full 0.00-1.00 (earlier run truncated L at 0.50).

Rule (SHORT priority, per user):
    da_win >= S_hi          -> SHORT (+spread)
    elif rt_win >= L_hi     -> LONG  (-spread)
    else flat
Scenarios: full / ex-coldsnap (2026-01-23..31 제외) / ex-Jan
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

A = Path(__file__).resolve().parents[1]
m = pd.read_parquet(A / "derived" / "joined.parquet").sort_values("ft_utc").reset_index(drop=True)
m["ds"] = m.date.astype(str)
pd.set_option("display.width", 260, "display.max_columns", 60, "display.max_rows", 200)

SCEN = {
    "full":       m,
    "excold":     m[~m.ds.between("2026-01-23", "2026-01-31")],
    "exjan":      m[~m.ds.str.startswith("2026-01")],
}


def mdd(c):
    p = np.maximum.accumulate(np.concatenate([[0.0], c]))
    return float((p - np.concatenate([[0.0], c])).max())


def stats(pnl, mask):
    t = pnl[mask]
    if t.size == 0:
        return dict(n=0, cum=0.0, ev=np.nan, win=np.nan, pl=np.nan, mdd=np.nan)
    w, l = t[t > 0], t[t < 0]
    return dict(n=int(t.size), cum=float(t.sum()), ev=float(t.mean()), win=float((t > 0).mean()),
                pl=float(w.mean() / abs(l.mean())) if w.size and l.size else np.nan,
                mdd=mdd(np.cumsum(pnl)))


def grid(d, G):
    sp, dw, rw = d.spread.to_numpy(), d.da_win_probability.to_numpy(), d.rt_win_probability.to_numpy()
    rows = []
    for s in G:
        ms = dw >= s
        for l in G:
            ml = (rw >= l) & ~ms
            pnl = np.where(ms, sp, 0.0) + np.where(ml, -sp, 0.0)
            r = dict(S_hi=s, L_hi=l)
            r.update({f"all_{k}": v for k, v in stats(pnl, ms | ml).items()})
            r.update({f"sh_{k}": v for k, v in stats(np.where(ms, sp, 0.0), ms).items()})
            r.update({f"lg_{k}": v for k, v in stats(np.where(ml, -sp, 0.0), ml).items()})
            rows.append(r)
    g = pd.DataFrame(rows)
    g["all_trade_rate"] = g.all_n / len(d)
    return g


C = ["S_hi", "L_hi", "all_n", "all_trade_rate", "all_cum", "all_ev", "all_win", "all_pl", "all_mdd",
     "sh_n", "sh_cum", "sh_win", "sh_pl", "lg_n", "lg_cum", "lg_win", "lg_pl"]
FINE = np.round(np.arange(0.0, 1.001, 0.01), 2)
BIN = np.round(np.arange(0.0, 1.001, 0.1), 1)

for tag, d in SCEN.items():
    sp = d.spread.to_numpy()
    print(f"\n{'='*100}\n### {tag.upper()}  hours={len(d)}  days={d.date.nunique()}  "
          f"baseline short-all cum={sp.sum():,.0f} ev={sp.mean():.3f} win={(sp>0).mean():.3f}")
    gf = grid(d, FINE)
    gb = grid(d, BIN)
    gf.to_csv(A / "derived" / f"grid_fine_{tag}.csv", index=False)
    gb.to_csv(A / "derived" / f"grid_bin01_{tag}.csv", index=False)

    print(f"\n-- 0.1 bins: TOP 8 by cum PnL --")
    print(gb.nlargest(8, "all_cum")[C].round(3).to_string(index=False))
    print(f"\n-- 0.1 bins: TOP 8 by WIN RATE (trade rate >= 5%) --")
    fb = gb[gb.all_trade_rate >= 0.05]
    print(fb.nlargest(8, "all_win")[C].round(3).to_string(index=False))
    print(f"\n-- 0.01 fine: TOP 5 by cum PnL --")
    print(gf.nlargest(5, "all_cum")[C].round(3).to_string(index=False))
    print(f"-- 0.01 fine: TOP 5 by win rate (trade rate >= 5%) --")
    ff = gf[gf.all_trade_rate >= 0.05]
    print(ff.nlargest(5, "all_win")[C].round(3).to_string(index=False))
    print(f"-- 0.01 fine: TOP 5 by cum/MDD (trade rate >= 5%) --")
    ff = ff.assign(calmar=ff.all_cum / ff.all_mdd.replace(0, np.nan))
    print(ff.nlargest(5, "calmar")[C + ["calmar"]].round(3).to_string(index=False))
