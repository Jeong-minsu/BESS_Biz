"""Max loss short/long, $100+ frequency by HE, tail-emphasis numbers."""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats as ss
ROOT = Path(__file__).resolve().parents[1]
d = pd.read_parquet(ROOT / "derived" / "hourly.parquet")
pd.set_option("display.width", 250, "display.float_format", "{:,.2f}".format)
s = d.short; yrs = d.md.nunique() / 365.25

# 1) max loss
for name, x in [("SHORT", s), ("LONG", -s)]:
    i = x.idxmin(); day = (x.groupby(d.md).sum()); j = day.idxmin()
    mon = x.groupby(d.md.dt.to_period("M")).sum()
    print(f"{name}: worst hour {x[i]:,.0f} ({d.md[i].date()} HE{d.he[i]}, DA {d.da[i]:.0f} RT {d.rt[i]:.0f}) | worst day {day[j]:,.0f} ({j.date()}) | worst month {mon.min():,.0f} ({mon.idxmin()})")
    for k in [1, 5, 10]:
        print(f"   top{k} worst hours sum {x.nsmallest(k).sum():,.0f}")

# 2) $100+ frequency by HE (per-year rate and % of days)
f = pd.DataFrame({
    "RT>=100 %days": d.groupby("he").rt.apply(lambda v: (v >= 100).mean() * 100),
    "DA>=100 %days": d.groupby("he").da.apply(lambda v: (v >= 100).mean() * 100),
    "SHORT loss>=100 %": d.groupby("he").short.apply(lambda v: (v <= -100).mean() * 100),
    "LONG loss>=100 %": d.groupby("he").short.apply(lambda v: (v >= 100).mean() * 100),
    "RT>=100 /yr": d.groupby("he").rt.apply(lambda v: (v >= 100).sum() / yrs),
    "SHORT loss>=100 /yr": d.groupby("he").short.apply(lambda v: (v <= -100).sum() / yrs),
    "LONG loss>=100 /yr": d.groupby("he").short.apply(lambda v: (v >= 100).sum() / yrs),
    "RT max": d.groupby("he").rt.max(),
})
print(f.to_string()); print("TOTAL per year:", (f[[c for c in f if "/yr" in c]].sum()).round(1).to_dict())
f.to_csv(ROOT / "derived" / "freq100_by_he.csv")
for y, g in d.groupby("period"):
    n = g.md.nunique()
    print(y, "days", n, "RT>=100 hrs", (g.rt >= 100).sum(), "DA>=100 hrs", (g.da >= 100).sum(),
          "short loss>=100", (g.short <= -100).sum(), "long loss>=100", (g.short >= 100).sum(),
          "days with any RT>=100", g[g.rt >= 100].md.nunique())

# 3) tail emphasis
mu, sd = s.mean(), s.std(); med = s.median(); mad = (s - med).abs().median() * 1.4826
print(f"\nmean {mu:.2f} sd {sd:.2f} median {med:.2f} robust-sd(MAD) {mad:.2f} kurtosis(excess) {s.kurt():,.0f} skew {s.skew():.1f}")
for t in [100, 250, 500, 1000]:
    act = (s <= -t).sum()
    exp_norm = len(s) * ss.norm.cdf((-t - med) / mad)
    print(f"short loss>={t}: actual {act}  normal(robust sd) expects {exp_norm:.2e}  -> every {1/max(exp_norm/len(s),1e-300)/8766:.1e} yrs")
print("worst hour in robust sigma:", (s.min() - med) / mad)
w = s[s > 0]
print("worst hour = avg winning hours:", -s.min() / w.mean(), " median winning hours:", -s.min() / w.median())
day = s.groupby(d.md).sum(); wd = day[day > 0]
print("9/22 day loss = median winning days:", -day.min() / wd.median(), " avg winning days:", -day.min() / wd.mean())
# share of |pnl| from top 1% / 0.1% hours
a = s.abs().sort_values(ascending=False)
for p in [0.001, 0.01, 0.05]:
    k = int(len(a) * p); print(f"top {p*100}% hours ({k}) = {a.head(k).sum()/a.sum()*100:.1f}% of gross |P&L|")
# recovery: after 9/22, how many days of median winning to recover; drawdown duration
cum = day.cumsum(); peak = cum.cummax(); dd = cum - peak
print("max DD", dd.min(), "at", dd.idxmin().date(), "peak date", cum[:dd.idxmin()].idxmax().date())
# time to earn back: 24h short avg daily EV ex-tail
print("days of avg ex-worst-day EV to recover 9/22:", -day.min() / (day.drop(day.idxmin()).mean()))
# evening HE17-22 per day
ev = d[d.he.between(17, 22)].groupby("md").short.sum()
print("HE17-22: win days", (ev > 0).sum(), "of", len(ev), "sum of all winning days", ev[ev > 0].sum(), "worst day", ev.min(),
      "worst 3 days", ev.nsmallest(3).sum(), "rest", ev.sum() - ev.nsmallest(3).sum())
# rolling: fraction of 30-day windows with worst hour > sum of rest
