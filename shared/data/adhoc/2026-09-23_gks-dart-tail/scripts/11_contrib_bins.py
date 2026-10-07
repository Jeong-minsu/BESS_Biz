"""Spread x frequency = $ contribution by spread bin (GKS SHORT), vs normal expectation. Adds 'contrib' to dist_viz.json."""
from pathlib import Path
import json, numpy as np, pandas as pd
from scipy import stats as ss
ROOT = Path(__file__).resolve().parents[1]
s = pd.read_parquet(ROOT / "derived" / "hourly.parquet").short.to_numpy(); n = len(s)
J = json.loads((ROOT / "derived" / "dist_viz.json").read_text())
edges_pos = [0, 5, 10, 20, 50, 100, 250, 500, 1000, 3200]
edges = [-e for e in edges_pos[::-1]] + edges_pos[1:]
def norm_part(a, b, mu, sd):  # expected count and sum of x over [a,b)
    za, zb = (a - mu) / sd, (b - mu) / sd
    p = ss.norm.cdf(zb) - ss.norm.cdf(za)
    ex = mu * p + sd * (ss.norm.pdf(za) - ss.norm.pdf(zb))
    return n * p, n * ex
rows = []
for a, b in zip(edges[:-1], edges[1:]):
    m = (s >= a) & (s < b)
    cF, sF = norm_part(a, b, J["mu"], J["sd"]); cR, sR = norm_part(a, b, J["med"], J["rsd"])
    rows.append(dict(a=a, b=b, c=int(m.sum()), s=float(s[m].sum()), cF=cF, sF=sF, cR=cR, sR=sR))
J["contrib"] = rows
(ROOT / "derived" / "dist_viz.json").write_text(json.dumps(J, separators=(",", ":")))
pd.set_option("display.width", 200, "display.float_format", "{:,.1f}".format)
print(pd.DataFrame(rows).to_string(index=False))
