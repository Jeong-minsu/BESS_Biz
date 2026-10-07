"""Data for spread-distribution vs normal visualization."""
from pathlib import Path
import json, numpy as np, pandas as pd
from scipy import stats as ss
ROOT = Path(__file__).resolve().parents[1]
d = pd.read_parquet(ROOT / "derived" / "hourly.parquet")
s = d.short.to_numpy(); n = len(s)
mu, sd = s.mean(), s.std(ddof=1); med = np.median(s); rsd = np.median(np.abs(s - med)) * 1.4826
edges = np.arange(-80, 82, 2); cnt, _ = np.histogram(s, edges); mid = (edges[:-1] + edges[1:]) / 2
hist = [dict(x=float(m), p=float(c / n / 2), c=int(c)) for m, c in zip(mid, cnt)]
xs = np.linspace(-80, 80, 321)
pdf_full = [[float(x), float(ss.norm.pdf(x, mu, sd))] for x in xs]
pdf_rob = [[float(x), float(ss.norm.pdf(x, med, rsd))] for x in xs]
# tails
tx = np.unique(np.round(np.geomspace(10, 3100, 90), 1))
tail = []
for x in tx:
    tail.append(dict(x=float(x), lossS=float((s <= -x).mean()), cS=int((s <= -x).sum()),
                     lossL=float((s >= x).mean()), cL=int((s >= x).sum()),
                     nF=float(ss.norm.cdf(-x, mu, sd)), nR=float(ss.norm.cdf(-x, med, rsd))))
# QQ
srt = np.sort(s); pp = (np.arange(1, n + 1) - 0.5) / n; z = ss.norm.ppf(pp)
idx = np.unique(np.r_[np.arange(0, 60), np.linspace(0, n - 1, 700).astype(int), np.arange(n - 60, n)])
dd = d.sort_values("short").reset_index(drop=True)
qq = [dict(z=float(z[i]), v=float(srt[i]), md=str(dd.md[i].date()), he=int(dd.he[i]), da=float(dd.da[i]), rt=float(dd.rt[i])) for i in idx]
out = dict(n=n, mu=mu, sd=sd, med=med, rsd=rsd, kurt=float(pd.Series(s).kurt()), skew=float(pd.Series(s).skew()),
           outL=int((s < -80).sum()), outR=int((s > 80).sum()), hist=hist, pdf_full=pdf_full, pdf_rob=pdf_rob, tail=tail, qq=qq,
           within1=float((np.abs(s - mu) <= sd).mean()), within_r=float((np.abs(s - med) <= rsd).mean()),
           beyond3=int((np.abs(s - mu) > 3 * sd).sum()), exp3=float(n * 2 * ss.norm.sf(3)))
(ROOT / "derived" / "dist_viz.json").write_text(json.dumps(out, separators=(",", ":")))
print({k: v for k, v in out.items() if not isinstance(v, list)})
print([t for t in tail if t["x"] in (10.0,) or abs(t["x"]-100)<6 or abs(t["x"]-1000)<60])
