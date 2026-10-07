"""Threshold solver for Tyba da_win / rt_win DART signals on GKS_BESS_RN.

Position rule (1 MW x 1h, hourly, D-1 06:00 CT vintage => leakage-free vs 10:00 bid close):
    SHORT DA  if da_win >= S_hi        pnl = +spread = DA - RT
    LONG  DA  if rt_win >= L_hi        pnl = -spread = RT - DA
    else flat
NOTE: in this file rt_win == 1 - da_win exactly, so the user's third parameter
S_lo (da_win <= S_lo for long) is redundant: da_win <= 1 - L_hi already.
The reported S_lo column is therefore the implied 1 - L_hi.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

A = Path(__file__).resolve().parents[1]
m = pd.read_parquet(A / "derived" / "joined.parquet").sort_values("ft_utc").reset_index(drop=True)
sp = m.spread.to_numpy()
dw = m.da_win_probability.to_numpy()
rw = m.rt_win_probability.to_numpy()


def mdd(cum: np.ndarray) -> float:
    if cum.size == 0:
        return 0.0
    peak = np.maximum.accumulate(np.concatenate([[0.0], cum]))
    return float((peak - np.concatenate([[0.0], cum])).max())


def stats(pnl_full: np.ndarray, mask: np.ndarray) -> dict:
    """pnl_full aligned to all hours (0 where flat); mask = traded hours."""
    t = pnl_full[mask]
    n = t.size
    if n == 0:
        return dict(n=0, cum=0.0, ev=np.nan, win=np.nan, pl=np.nan, mdd=np.nan)
    wins, loss = t[t > 0], t[t < 0]
    cum_series = np.cumsum(pnl_full)          # chronological, flat hours carry 0
    return dict(
        n=n,
        cum=float(t.sum()),
        ev=float(t.mean()),
        win=float((t > 0).mean()),
        pl=float(wins.mean() / abs(loss.mean())) if loss.size and wins.size else np.nan,
        mdd=mdd(cum_series),
    )


GRID = np.round(np.arange(0.50, 1.00, 0.01), 2)
rows = []
for s_hi in GRID:
    ms = dw >= s_hi
    for l_hi in GRID:
        ml = rw >= l_hi
        pnl = np.where(ms, sp, 0.0) + np.where(ml, -sp, 0.0)
        both = ms | ml
        r = dict(S_hi=s_hi, L_hi=l_hi, S_lo_implied=round(1 - l_hi, 2))
        r.update({f"all_{k}": v for k, v in stats(pnl, both).items()})
        r.update({f"sh_{k}": v for k, v in stats(np.where(ms, sp, 0.0), ms).items()})
        r.update({f"lg_{k}": v for k, v in stats(np.where(ml, -sp, 0.0), ml).items()})
        rows.append(r)

g = pd.DataFrame(rows)
g["all_trade_rate"] = g.all_n / len(m)
g.to_csv(A / "derived" / "grid.csv", index=False)
print(f"grid {g.shape}  hours={len(m)}  days={m.date.nunique()}")

pd.set_option("display.width", 250, "display.max_columns", 60)
C = ["S_hi", "L_hi", "all_n", "all_trade_rate", "all_cum", "all_ev", "all_win", "all_pl", "all_mdd",
     "sh_n", "sh_cum", "sh_win", "sh_pl", "lg_n", "lg_cum", "lg_win", "lg_pl"]

print("\n=== TOP 10 by cumulative PnL (no constraint) ===")
print(g.nlargest(10, "all_cum")[C].round(3).to_string(index=False))

MIN = 0.05
f = g[g.all_trade_rate >= MIN]
print(f"\n=== TOP 10 by cum PnL, trade rate >= {MIN:.0%} ===")
print(f.nlargest(10, "all_cum")[C].round(3).to_string(index=False))

print("\n=== TOP 10 by return/MDD (trade rate >= 5%) ===")
f = f.assign(calmar=f.all_cum / f.all_mdd.replace(0, np.nan))
print(f.nlargest(10, "calmar")[C + ["calmar"]].round(3).to_string(index=False))

print("\n=== SHORT-ONLY sweep (L_hi=1.0 i.e. long disabled) ===")
so = []
for s_hi in GRID:
    ms = dw >= s_hi
    r = dict(S_hi=s_hi); r.update(stats(np.where(ms, sp, 0.0), ms)); so.append(r)
so = pd.DataFrame(so); so["rate"] = so.n / len(m)
print(so.round(3).to_string(index=False))

print("\n=== LONG-ONLY sweep ===")
lo = []
for l_hi in GRID:
    ml = rw >= l_hi
    r = dict(L_hi=l_hi); r.update(stats(np.where(ml, -sp, 0.0), ml)); lo.append(r)
lo = pd.DataFrame(lo); lo["rate"] = lo.n / len(m)
print(lo.round(3).to_string(index=False))
so.to_csv(A / "derived" / "short_sweep.csv", index=False)
lo.to_csv(A / "derived" / "long_sweep.csv", index=False)
