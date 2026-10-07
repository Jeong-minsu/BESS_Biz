"""Item 1 add-on: yearly TB2 of Raven vs the ERCOT-wide node average and vs GKS, in %.

Raven pre-2026-06 uses the item2 NNLS proxy; 2026 rows also carry the REAL RVN_RN series
so the two can be compared. GKS_BESS_RN only exists from 2024-08 (COD 2024-07).
"ERCOT average TB2" = cross-sectional mean/median of per-node daily TB2 over all ERCOT
price_nodes with full coverage that day. Real data only.
"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd

BASE = Path(__file__).resolve().parents[1]; D = BASE / "derived"
NODES = {"RVN_RN": 10019925379, "GKS_BESS_RN": 10017907494,
         "CBEC_ALL": 10001765766, "RBN_BESS1": 10017290064, "TAV_RN": 10016969364,
         "HB_HOUSTON": 10000697077, "HB_SOUTH": 10000697079, "HB_BUSAVG": 10000698380}
W, B = {"CBEC_ALL": 0.4148, "RBN_BESS1": 0.5407, "TAV_RN": 0.0445}, -0.065


def tb2_all_nodes(df, col):
    """Vectorised TB2 per (OBJECTID, FLOWDAY): mean(top2) - mean(bottom2), 24h days only."""
    d = df[["OBJECTID", "FLOWDAY", col]].dropna()
    n = d.groupby(["OBJECTID", "FLOWDAY"])[col].transform("size")
    d = d[n == 24]
    if d.empty:
        return pd.DataFrame(columns=["OBJECTID", "FLOWDAY", "tb2"])
    d = d.sort_values(["OBJECTID", "FLOWDAY", col])
    r = d.groupby(["OBJECTID", "FLOWDAY"]).cumcount()
    bot = d[r <= 1].groupby(["OBJECTID", "FLOWDAY"])[col].mean()
    top = d[r >= 22].groupby(["OBJECTID", "FLOWDAY"])[col].mean()
    return (top - bot).rename("tb2").reset_index()


rows_sys, rows_node = [], []
for fp in sorted(glob.glob(str(BASE / "raw/price_panel/*.parquet"))):
    m = pd.read_parquet(fp)
    for col, mkt in [("DALMP", "DA"), ("RTLMP", "RT")]:
        t = tb2_all_nodes(m, col)
        if t.empty:
            continue
        t["mkt"] = mkt
        # system-wide cross-sectional stats per day
        s = t.groupby("FLOWDAY").tb2.agg(["mean", "median", "count"]).reset_index()
        s["mkt"] = mkt
        rows_sys.append(s)
        # our nodes of interest
        rows_node.append(t[t.OBJECTID.isin(NODES.values())])
    print("done", Path(fp).stem, flush=True)

sysd = pd.concat(rows_sys, ignore_index=True)
nod = pd.concat(rows_node, ignore_index=True)
inv = {v: k for k, v in NODES.items()}
nod["node"] = nod.OBJECTID.map(inv)

# proxy TB2 must be built from proxy PRICES, not from blending TB2s.
parts = []
for fp in sorted(glob.glob(str(BASE / "raw/price_panel/*.parquet"))):
    m = pd.read_parquet(fp)
    parts.append(m[m.OBJECTID.isin(NODES.values())])
px = pd.concat(parts, ignore_index=True)
px["node"] = px.OBJECTID.map(inv)
px["dt"] = pd.to_datetime(px.DATETIME)
proxy_rows = []
for col, mkt in [("DALMP", "DA"), ("RTLMP", "RT")]:
    p = px.pivot_table(index="dt", columns="node", values=col)
    have = [k for k in W if k in p.columns]
    ok = p[have].notna().all(axis=1)
    p["PROXY"] = np.nan
    p.loc[ok, "PROXY"] = B + sum(W[k] * p.loc[ok, k] for k in have)
    fb = (~ok) & p["TAV_RN"].notna()
    p.loc[fb, "PROXY"] = p.loc[fb, "TAV_RN"]
    q = p[["PROXY"]].dropna().reset_index()
    q["FLOWDAY"] = q.dt.dt.normalize()
    cnt = q.groupby("FLOWDAY").PROXY.transform("size")
    q = q[cnt == 24].sort_values(["FLOWDAY", "PROXY"])
    r = q.groupby("FLOWDAY").cumcount()
    bot = q[r <= 1].groupby("FLOWDAY").PROXY.mean()
    top = q[r >= 22].groupby("FLOWDAY").PROXY.mean()
    pr = (top - bot).rename("tb2").reset_index()
    pr["node"] = "RAVEN_proxy"; pr["mkt"] = mkt
    proxy_rows.append(pr)
nod = pd.concat([nod.drop(columns=["OBJECTID"]), pd.concat(proxy_rows, ignore_index=True)],
                ignore_index=True)
nod["year"] = pd.to_datetime(nod.FLOWDAY).dt.year
sysd["year"] = pd.to_datetime(sysd.FLOWDAY).dt.year

# Raven composite: real RVN_RN where it exists, proxy before that
real = nod[nod.node == "RVN_RN"][["FLOWDAY", "mkt", "tb2"]].rename(columns={"tb2": "real"})
prx = nod[nod.node == "RAVEN_proxy"][["FLOWDAY", "mkt", "tb2"]].rename(columns={"tb2": "proxy"})
rav = prx.merge(real, on=["FLOWDAY", "mkt"], how="left")
rav["tb2"] = rav.real.fillna(rav.proxy)
rav["node"] = "RAVEN"; rav["year"] = pd.to_datetime(rav.FLOWDAY).dt.year

out = {}
print("\n" + "=" * 96)
for mkt in ["DA", "RT"]:
    sy = sysd[sysd.mkt == mkt].groupby("year")[["mean", "median"]].mean()
    tbl = []
    for y in sorted(sy.index):
        sysmean, sysmed = sy.loc[y, "mean"], sy.loc[y, "median"]
        rv = rav[(rav.mkt == mkt) & (rav.year == y)]
        gk = nod[(nod.node == "GKS_BESS_RN") & (nod.mkt == mkt) & (nod.year == y)]
        rvv = rv.tb2.mean() if len(rv) else np.nan
        gkv = gk.tb2.mean() if len(gk) else np.nan
        src = "real" if rv.real.notna().all() and len(rv) else ("mixed" if rv.real.notna().any() else "proxy")
        # like-for-like GKS comparison on common days only
        cm = rv.merge(gk[["FLOWDAY", "tb2"]].rename(columns={"tb2": "gks"}), on="FLOWDAY", how="inner")
        tbl.append(dict(year=int(y), n_days=len(rv), src=src,
                        raven=rvv, gks=gkv, sys_mean=sysmean, sys_median=sysmed,
                        vs_sys_mean_pct=100 * (rvv / sysmean - 1) if sysmean else np.nan,
                        vs_sys_median_pct=100 * (rvv / sysmed - 1) if sysmed else np.nan,
                        gks_vs_sys_mean_pct=100 * (gkv / sysmean - 1) if (sysmean and not np.isnan(gkv)) else np.nan,
                        vs_gks_pct=100 * (cm.tb2.mean() / cm.gks.mean() - 1) if len(cm) else np.nan,
                        common_days=len(cm)))
    t = pd.DataFrame(tbl)
    out[mkt] = t.to_dict(orient="records")
    print(f"\n### {mkt} — daily TB2 ($/MWh), yearly means")
    print(t.to_string(index=False, float_format=lambda x: f"{x:,.1f}"))

json.dump(out, open(D / "rev_item1_yearly_relative.json", "w"), indent=1, default=str)
pd.concat([pd.DataFrame(v).assign(mkt=k) for k, v in out.items()]).to_csv(
    D / "rev_item1_yearly_relative.csv", index=False)
print("\nwrote rev_item1_yearly_relative.{json,csv}")
