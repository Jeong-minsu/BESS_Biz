"""Diagnose GKS proxy candidates on what actually matters here: reproducing GKS's RT TB2 LEVEL.
For each candidate (and HB_SOUTH): TB2 mean vs GKS real over the overlap, bias %, MAE,
plus its own 2020 TB2 mean to spot nodes whose historical behaviour is nothing like GKS.
Real data only.
"""
import glob, sys
from pathlib import Path
import numpy as np, pandas as pd

BASE = Path(__file__).resolve().parents[1]; D = BASE / "derived"
sys.path.insert(0, str(BASE / "scripts")); import dl
GKS, HB_SOUTH, HB_BUSAVG = 10017907494, 10000697079, 10000698380

S = pd.read_csv(D / "gks_proxy_scan_top30.csv")
cands = [int(x) for x in S.id.head(20)] + [HB_SOUTH, HB_BUSAVG]
obj = dl.read_csv("ercot/metadata/objects/all.csv.gz")
nm = dict(zip(obj.OBJECTID, obj.OBJECTNAME)); zn = dict(zip(obj.OBJECTID, obj.ZONE))
sub = dict(zip(obj.OBJECTID, obj.SUBTYPE))

def tb2(s):
    g = pd.DataFrame({"p": s, "d": s.index.normalize()}).dropna()
    c = g.groupby("d").p.transform("size")
    g = g[c == 24]
    return g.groupby("d").p.apply(lambda v: v.nlargest(2).mean() - v.nsmallest(2).mean())

# overlap window from the panel
parts = []
for f in sorted(glob.glob(str(BASE / "raw/price_panel/*.parquet"))):
    if Path(f).stem < "202408":
        continue
    m = pd.read_parquet(f)
    parts.append(m[m.OBJECTID.isin(set(cands) | {GKS})][["OBJECTID", "DATETIME", "RTLMP"]])
p = pd.concat(parts, ignore_index=True)
p["dt"] = pd.to_datetime(p.DATETIME)
RT = p.pivot_table(index="dt", columns="OBJECTID", values="RTLMP")
t_gks = tb2(RT[GKS])

# 2020 behaviour from the cached 2020-2023 pull (only has proxy members + hubs) -> refetch per candidate is heavy,
# so use 2020 only for those present in the cache; otherwise mark n/a
cache = pd.read_parquet(BASE / "raw/gks_px_2020_2023.parquet")
cache["dt"] = pd.to_datetime(cache.DATETIME)
R20 = cache[pd.to_datetime(cache.day).dt.year == 2020].pivot_table(index="dt", columns="OBJECTID", values="RTLMP")

rows = []
for c in cands:
    if c not in RT.columns:
        continue
    t = tb2(RT[c])
    j = pd.DataFrame({"c": t, "g": t_gks}).dropna()
    if len(j) < 100:
        continue
    t20 = tb2(R20[c]).mean() if c in R20.columns else np.nan
    rows.append(dict(name=nm.get(c, c), zone=zn.get(c), subtype=sub.get(c),
                     tb2_cand=j.c.mean(), tb2_gks=j.g.mean(),
                     bias_pct=100 * (j.c.mean() / j.g.mean() - 1),
                     mae=(j.c - j.g).abs().mean(), corr=j.c.corr(j.g),
                     tb2_2020=t20, days=len(j)))
R = pd.DataFrame(rows).sort_values("mae")
pd.set_option("display.width", 220)
print("GKS 실측 RT TB2 재현력 (겹침 기간 2024-08 ~ 2026-09)")
print(R.round(2).to_string(index=False))
print(f"\nGKS 실측 평균 RT TB2: ${t_gks.mean():.1f} ({len(t_gks)}일)")
R.to_csv(D / "gks_proxy_diag.csv", index=False)
