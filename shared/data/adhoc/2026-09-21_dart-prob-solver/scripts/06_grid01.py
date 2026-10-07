"""Full 0.0-1.0 grid at 0.1 bins, SHORT-priority rule (user spec).

Rule:  if da_win >= S_hi          -> SHORT   pnl = +spread
       elif rt_win >= L_hi        -> LONG    pnl = -spread
       else                       -> flat
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

A = Path(__file__).resolve().parents[1]
m = pd.read_parquet(A / "derived" / "joined.parquet").sort_values("ft_utc").reset_index(drop=True)
m["month"] = pd.to_datetime(m.date).dt.to_period("M").astype(str)
pd.set_option("display.width", 260, "display.max_columns", 60, "display.max_rows", 300)


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


def run(d, tag):
    sp, dw, rw = d.spread.to_numpy(), d.da_win_probability.to_numpy(), d.rt_win_probability.to_numpy()
    G = np.round(np.arange(0.0, 1.01, 0.1), 1)
    rows = []
    for s in G:
        ms = dw >= s
        for l in G:
            ml = (rw >= l) & ~ms                       # SHORT priority
            pnl = np.where(ms, sp, 0.0) + np.where(ml, -sp, 0.0)
            r = dict(S_hi=s, L_hi=l)
            r.update({f"all_{k}": v for k, v in stats(pnl, ms | ml).items()})
            r.update({f"sh_{k}": v for k, v in stats(np.where(ms, sp, 0.0), ms).items()})
            r.update({f"lg_{k}": v for k, v in stats(np.where(ml, -sp, 0.0), ml).items()})
            rows.append(r)
    g = pd.DataFrame(rows)
    g["all_trade_rate"] = g.all_n / len(d)
    g.to_csv(A / "derived" / f"grid01_{tag}.csv", index=False)
    return g


C = ["S_hi", "L_hi", "all_n", "all_trade_rate", "all_cum", "all_ev", "all_win", "all_pl", "all_mdd",
     "sh_n", "sh_cum", "sh_win", "sh_pl", "lg_n", "lg_cum", "lg_win", "lg_pl"]

g = run(m, "full")
print(f"=== FULL PERIOD, 0.1 bins, SHORT-priority — all {len(g)} combos ===")
print(g[C].round(3).to_string(index=False))
print("\n=== TOP 8 by cumulative PnL ===")
print(g.nlargest(8, "all_cum")[C].round(3).to_string(index=False))
print("\n--- user's cell S_hi=0.9 / L_hi=0.1 ---")
print(g[(g.S_hi == 0.9) & (g.L_hi == 0.1)][C].round(3).to_string(index=False))
