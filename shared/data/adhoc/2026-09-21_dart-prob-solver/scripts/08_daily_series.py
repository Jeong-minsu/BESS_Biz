"""Daily + cumulative PnL series for the two optimal parameter sets."""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np, pandas as pd
import sys
if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(encoding="utf-8")

A = Path(__file__).resolve().parents[1]
m = pd.read_parquet(A / "derived" / "joined.parquet").sort_values("ft_utc").reset_index(drop=True)
m["ds"] = m.date.astype(str)
COLD = ("2026-01-23", "2026-01-31")
is_cold = m.ds.between(*COLD)


def series(d, s_hi, l_hi):
    sp = d.spread.to_numpy(); dw = d.da_win_probability.to_numpy(); rw = d.rt_win_probability.to_numpy()
    ms = dw >= s_hi
    ml = (rw >= l_hi) & ~ms
    pnl = np.where(ms, sp, 0.0) + np.where(ml, -sp, 0.0)
    g = pd.DataFrame({"ds": d.ds.values, "pnl": pnl,
                      "sh": np.where(ms, sp, 0.0), "lg": np.where(ml, -sp, 0.0),
                      "n_sh": ms.astype(int), "n_lg": ml.astype(int)}).groupby("ds").sum()
    g["cum"] = g.pnl.cumsum()
    g["base_cum"] = (-d.groupby("ds").spread.sum()).cumsum()   # signal-free always-LONG
    return g.reset_index()


def summarise(g, label, s_hi, l_hi):
    p = g.pnl.to_numpy()
    w, l = p[p > 0], p[p < 0]
    peak = np.maximum.accumulate(np.concatenate([[0.0], g.cum.to_numpy()]))
    dd = peak - np.concatenate([[0.0], g.cum.to_numpy()])
    return dict(label=label, S_hi=s_hi, L_hi=l_hi, days=int(len(g)),
                cum=round(float(g.cum.iloc[-1]), 1),
                day_win=round(float((p > 0).mean()), 3),
                day_pl=round(float(w.mean() / abs(l.mean())), 3),
                mdd_daily=round(float(dd.max()), 1),
                best_day=round(float(p.max()), 1), worst_day=round(float(p.min()), 1),
                base_cum=round(float(g.base_cum.iloc[-1]), 1))


OUT = {}
cases = [
    ("with_cold", m, 0.73, 0.00, "한파 포함 · 전기간 최적 S≥0.73"),
    ("ex_cold", m[~is_cold], 0.92, 0.00, "한파 제외 · 최적 S≥0.92"),
]
meta = []
for key, d, s, l, lab in cases:
    g = series(d, s, l)
    OUT[key] = dict(
        dates=g.ds.tolist(),
        daily=[round(float(x), 2) for x in g.pnl],
        cum=[round(float(x), 2) for x in g.cum],
        base_cum=[round(float(x), 2) for x in g.base_cum],
        n_short=[int(x) for x in g.n_sh],
        n_long=[int(x) for x in g.n_lg],
    )
    st = summarise(g, lab, s, l); meta.append(st)
    print(json.dumps(st, ensure_ascii=False))

OUT["meta"] = meta
OUT["cold_window"] = list(COLD)
(A / "derived" / "daily_series.json").write_text(json.dumps(OUT, ensure_ascii=False), encoding="utf-8")
for key, d, s, l, lab in cases:
    series(d, s, l).to_csv(A / "derived" / f"daily_{key}.csv", index=False)
print("\nsaved daily_series.json + daily_*.csv")
