"""Supplement: tail-event frequency both sides, block comparison, high-win-rate conditions."""
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]
d = pd.read_parquet(ROOT / "derived" / "hourly.parquet")
pd.set_option("display.width", 250, "display.float_format", "{:,.2f}".format)

# 1) tail frequency: |spread| thresholds, both sides, per year
rows = []
for y, g in d.groupby("period"):
    r = {"year": y, "hours": len(g)}
    for t in [100, 250, 500, 1000]:
        r[f"short_loss>{t}"] = (g.short < -t).sum(); r[f"short_win>{t}"] = (g.short > t).sum()
    rows.append(r)
print(pd.DataFrame(rows).to_string(index=False))

# 2) P&L concentration: top/bottom N hours contribution
s = d.short.sort_values()
for n in [1, 5, 10, 20, 50]:
    print(f"worst{n}: {s.head(n).sum():,.0f}  best{n}: {s.tail(n).sum():,.0f}  middle(total ex both): {s.iloc[n:-n].sum():,.0f}")
print("total", s.sum())

# 3) blocks: daily bet
def st(x):
    w, l = x[x > 0], x[x < 0]
    R = w.mean() / -l.mean()
    return dict(win=len(w)/len(x), payoff=R, be=1/(1+R), EV=x.mean(), median=x.median(), worst=x.min(), best=x.max(),
                total=x.sum(), total_ex_worst_day=x.sum()-x.min(), total_ex_best_day=x.sum()-x.max())
blocks = {"HE1-8": (1, 8), "HE9-16": (9, 16), "HE17-22": (17, 22), "HE23-24": (23, 24), "HE14-16": (14, 16)}
res = {k: st(d[d.he.between(a, b)].groupby("md").short.sum()) for k, (a, b) in blocks.items()}
print(pd.DataFrame(res).T.to_string())

# 4) conditions with >=80% hourly win rate (DA floor x HE block), n>=50
out = []
for k, (a, b) in blocks.items():
    for f in [30, 50, 75, 100, 150]:
        x = d[d.he.between(a, b) & (d.da >= f)].short
        if len(x) < 30: continue
        w, l = x[x > 0], x[x < 0]
        out.append(dict(block=k, floor=f, n=len(x), win=len(w)/len(x), avg_win=w.mean(), avg_loss=-l.mean(),
                        payoff=w.mean()/-l.mean(), EV=x.mean(), worst=x.min(), total=x.sum(), total_ex_worst=x.sum()-x.min()))
print(pd.DataFrame(out).to_string(index=False))

# 5) 2026-09-22 context
print(d[d.md == "2026-09-22"][["he", "da", "rt", "short"]].to_string(index=False))
