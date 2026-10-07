"""Robustness: baseline, monthly, IS/OOS split, tail dependence."""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

A = Path(__file__).resolve().parents[1]
m = pd.read_parquet(A / "derived" / "joined.parquet").sort_values("ft_utc").reset_index(drop=True)
m["month"] = pd.to_datetime(m.date).dt.to_period("M").astype(str)
sp, dw, rw = m.spread.to_numpy(), m.da_win_probability.to_numpy(), m.rt_win_probability.to_numpy()
pd.set_option("display.width", 220, "display.max_columns", 40)


def mdd(c):
    p = np.maximum.accumulate(np.concatenate([[0.0], c]))
    return float((p - np.concatenate([[0.0], c])).max())


def st(pnl, mask, tot):
    t = pnl[mask]
    if t.size == 0:
        return dict(n=0, cum=0.0, ev=np.nan, win=np.nan, pl=np.nan, mdd=np.nan, med=np.nan)
    w, l = t[t > 0], t[t < 0]
    return dict(n=t.size, cum=t.sum(), ev=t.mean(), med=np.median(t), win=(t > 0).mean(),
                pl=(w.mean() / abs(l.mean())) if w.size and l.size else np.nan,
                mdd=mdd(np.cumsum(pnl)))


print("=== BASELINE (no signal, 1MW x 1h) ===")
print(f"short-all-hours : n={len(sp)} cum={sp.sum():,.0f} ev={sp.mean():.3f} win={(sp>0).mean():.3f} mdd={mdd(np.cumsum(sp)):,.0f}")
print(f"long-all-hours  : n={len(sp)} cum={-sp.sum():,.0f} ev={-sp.mean():.3f} win={(sp<0).mean():.3f} mdd={mdd(np.cumsum(-sp)):,.0f}")

print("\n=== SHORT side, candidate thresholds, monthly cum PnL ===")
CAND = [0.50, 0.65, 0.73, 0.80, 0.87, 0.92, 0.98]
tab = {}
for s in CAND:
    pnl = np.where(dw >= s, sp, 0.0)
    tab[f"S>={s}"] = pd.Series(pnl, index=m.month).groupby(level=0).sum()
mt = pd.DataFrame(tab)
mt.loc["TOTAL"] = mt.sum()
print(mt.round(0).to_string())

print("\n=== SHORT side: months with positive PnL (of 9) ===")
print((mt.drop("TOTAL") > 0).sum().to_string())

print("\n=== IS (Jan-May) vs OOS (Jun-Sep) — SHORT ===")
is_m = m.month <= "2026-05"
for s in CAND:
    msk = dw >= s
    a = st(np.where(msk, sp, 0.0), msk & is_m.to_numpy(), None)
    b = st(np.where(msk, sp, 0.0), msk & ~is_m.to_numpy(), None)
    print(f"S>={s:.2f} | IS  n={a['n']:5d} cum={a['cum']:9,.0f} ev={a['ev']:7.2f} win={a['win']:.3f} pl={a['pl']:.2f}"
          f" || OOS n={b['n']:5d} cum={b['cum']:9,.0f} ev={b['ev']:7.2f} win={b['win']:.3f} pl={b['pl']:.2f}")

print("\n=== IS vs OOS — LONG ===")
for l in [0.50, 0.60, 0.70, 0.80, 0.90]:
    msk = rw >= l
    a = st(np.where(msk, -sp, 0.0), msk & is_m.to_numpy(), None)
    b = st(np.where(msk, -sp, 0.0), msk & ~is_m.to_numpy(), None)
    print(f"L>={l:.2f} | IS  n={a['n']:5d} cum={a['cum']:9,.0f} ev={a['ev']:7.2f} win={a['win']:.3f}"
          f" || OOS n={b['n']:5d} cum={b['cum']:9,.0f} ev={b['ev']:7.2f} win={b['win']:.3f}")

print("\n=== SHORT: tail dependence (drop top-N winning hours) ===")
for s in [0.73, 0.87, 0.98]:
    msk = dw >= s
    t = np.sort(sp[msk])[::-1]
    print(f"S>={s}: n={t.size} cum={t.sum():,.0f} | ex-top1={t[1:].sum():,.0f} "
          f"ex-top5={t[5:].sum():,.0f} ex-top10={t[10:].sum():,.0f} median={np.median(t):.2f}")

print("\n=== SHORT: hour-of-day profile at S>=0.87 ===")
msk = dw >= 0.87
h = m[msk].assign(pnl=sp[msk]).groupby("he").agg(n=("pnl", "size"), cum=("pnl", "sum"),
                                                 ev=("pnl", "mean"), win=("pnl", lambda x: (x > 0).mean()))
print(h.round(2).to_string())
