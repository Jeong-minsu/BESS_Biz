"""Ex-January solver + calibration check + bootstrap significance."""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

A = Path(__file__).resolve().parents[1]
m = pd.read_parquet(A / "derived" / "joined.parquet").sort_values("ft_utc").reset_index(drop=True)
m["month"] = pd.to_datetime(m.date).dt.to_period("M").astype(str)
pd.set_option("display.width", 220, "display.max_columns", 40)


def mdd(c):
    p = np.maximum.accumulate(np.concatenate([[0.0], c]))
    return float((p - np.concatenate([[0.0], c])).max())


def sweep(d, label):
    sp, dw, rw = d.spread.to_numpy(), d.da_win_probability.to_numpy(), d.rt_win_probability.to_numpy()
    out = []
    for s in np.round(np.arange(0.50, 1.00, 0.02), 2):
        msk = dw >= s
        t = sp[msk]
        if t.size < 20:
            continue
        w, l = t[t > 0], t[t < 0]
        out.append(dict(thr=s, side="SHORT", n=t.size, cum=t.sum(), ev=t.mean(),
                        win=(t > 0).mean(), pl=w.mean() / abs(l.mean()) if w.size and l.size else np.nan,
                        mdd=mdd(np.cumsum(np.where(msk, sp, 0.0)))))
    for s in np.round(np.arange(0.50, 1.00, 0.02), 2):
        msk = rw >= s
        t = -sp[msk]
        if t.size < 20:
            continue
        w, l = t[t > 0], t[t < 0]
        out.append(dict(thr=s, side="LONG", n=t.size, cum=t.sum(), ev=t.mean(),
                        win=(t > 0).mean(), pl=w.mean() / abs(l.mean()) if w.size and l.size else np.nan,
                        mdd=mdd(np.cumsum(np.where(msk, -sp, 0.0)))))
    o = pd.DataFrame(out)
    print(f"\n=== {label} (n_hours={len(d)}) ===")
    print(f"baseline short-all: cum={sp.sum():,.0f} ev={sp.mean():.3f}")
    for side in ["SHORT", "LONG"]:
        print(f"-- {side} --")
        print(o[o.side == side].drop(columns="side").round(3).to_string(index=False))
    return o


ex = m[m.month != "2026-01"]
sweep(ex, "EX-JANUARY (Feb 2026 - Sep 2026)")

print("\n\n=== CALIBRATION: is da_win_probability calibrated to P(spread>0)? ===")
for d, lab in [(m, "ALL"), (ex, "EX-JAN")]:
    b = pd.cut(d.da_win_probability, [0, .2, .3, .4, .5, .6, .7, .8, .9, 1.0])
    t = d.groupby(b, observed=True).agg(n=("spread", "size"),
                                        stated=("da_win_probability", "mean"),
                                        realized=("spread", lambda s: (s > 0).mean()),
                                        ev=("spread", "mean")).round(3)
    print(f"\n-- {lab} --"); print(t.to_string())

print("\n\n=== BOOTSTRAP: block-bootstrap by DAY, SHORT S>=0.87, ex-Jan ===")
rng = np.random.default_rng(7)
for d, lab in [(m, "ALL"), (ex, "EX-JAN")]:
    dd = d[d.da_win_probability >= 0.87]
    daily = dd.groupby("date").spread.sum()
    days = daily.to_numpy()
    if days.size == 0:
        continue
    boot = rng.choice(days, size=(20000, days.size), replace=True).sum(axis=1)
    print(f"{lab}: trade-days={days.size} actual={days.sum():,.0f} "
          f"boot p5={np.percentile(boot,5):,.0f} p50={np.percentile(boot,50):,.0f} "
          f"p95={np.percentile(boot,95):,.0f} P(cum<=0)={(boot<=0).mean():.3f}")
