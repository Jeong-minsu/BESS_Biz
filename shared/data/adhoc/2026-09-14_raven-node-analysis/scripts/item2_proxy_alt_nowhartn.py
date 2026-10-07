"""WHARTN-free alternative proxy. WHARTN (station constraint, SF~1.0 at CBEC_ALL/TAV_RN/SBE_RN_1, ~0 at
RBN_BESS1/WGU_RN/WAL_RN) never bound while RVN_RN existed, so the price fit cannot tell whether Raven sits
behind it. This fits blends restricted to nodes with WHARTN SF ~ 0 and scores them on the same OOS window.
Also reports WHARTN SF for every scanned node. Output: derived/item2_proxy_alt_nowhartn.json"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import nnls

R = Path(__file__).resolve().parents[1]; D = R / "derived"
RVN = 10019925379
T0, T1, SPLIT = pd.Timestamp("2026-06-04"), pd.Timestamp("2026-09-13"), pd.Timestamp("2026-08-01")
obj = pd.read_parquet(R / "raw/objects_all.parquet"); name = obj.set_index("OBJECTID").OBJECTNAME.to_dict()

# WHARTN SF by node across all scanned nodes
parts = []
for f in sorted(glob.glob(str(R / "raw/msf_nodes/*.parquet"))):
    d = pd.read_parquet(f, columns=["PRICENODEID", "SHIFTFACTOR", "SHADOWPRICE", "CONSTRAINTNAME"])
    parts.append(d[(d.CONSTRAINTNAME == "WHARTN") & (d.SHADOWPRICE > 0)])
w = pd.concat(parts).groupby("PRICENODEID").SHIFTFACTOR.agg(["mean", "size"])
w.index = w.index.map(name); print("WHARTN SF by node:\n", w.round(4).to_string())
clean = [oid for oid, nm in name.items() if nm in w.index[w["mean"].abs() < 0.05] and oid != RVN]

df = pd.concat(pd.read_parquet(R / f"raw/price_panel/{m}.parquet") for m in ["202606", "202607", "202608", "202609"])
df = df[(df.FLOWDAY >= T0) & (df.FLOWDAY <= T1)]; df["dt"] = pd.to_datetime(df.DATETIME, format="%m/%d/%Y %H:%M:%S")
DA = df.pivot(index="dt", columns="OBJECTID", values="DALMP").astype(float); RT = df.pivot(index="dt", columns="OBJECTID", values="RTLMP").astype(float)
FD = df.drop_duplicates("dt").set_index("dt").FLOWDAY.sort_index()
y_da, y_rt = DA[RVN], RT[RVN]


def fit(cols, mask):
    X = pd.concat([DA.loc[mask, cols], RT.loc[mask, cols]]); y = pd.concat([y_da[mask], y_rt[mask]])
    m = X.notna().all(axis=1) & y.notna(); X, y = X[m].values, y[m].values
    wt, _ = nnls(X, y); wt = wt / wt.sum(); icpt = float((y - X @ wt).mean())
    return dict(nodes=[name[c] for c in cols], ids=[int(c) for c in cols], weights=[round(float(v), 4) for v in wt], intercept=round(icpt, 3))


def tb2(s):
    g = pd.DataFrame({"p": s, "fd": FD.reindex(s.index)}).dropna().groupby("fd").p
    return g.apply(lambda v: v.nlargest(2).mean() - v.nsmallest(2).mean() if len(v) >= 20 else np.nan).dropna()


def oos(spec, idx):
    pdx = pd.Series(spec["intercept"] + DA.loc[idx, spec["ids"]].values @ np.array(spec["weights"]), index=idx)
    prx = pd.Series(spec["intercept"] + RT.loc[idx, spec["ids"]].values @ np.array(spec["weights"]), index=idx)
    e_da = (tb2(pdx) - tb2(y_da[idx])); e_rt = (tb2(prx) - tb2(y_rt[idx]))
    sp = ((pdx - prx) - (y_da[idx] - y_rt[idx])).groupby(FD.reindex(idx)).mean()
    r = dict(tb2_da_mae=round(e_da.abs().mean(), 2), tb2_da_bias=round(e_da.mean(), 2), tb2_rt_mae=round(e_rt.abs().mean(), 2),
             tb2_rt_bias=round(e_rt.mean(), 2), spread_daily_mae=round(sp.abs().mean(), 2))
    r["score"] = round((r["tb2_da_mae"] + r["tb2_rt_mae"]) / 2 + r["spread_daily_mae"], 2); return r


fit_mask = (FD < SPLIT).reindex(DA.index).fillna(False).values
test_idx = DA.index[(FD >= SPLIT).reindex(DA.index).fillna(False).values]
RBN, WGU, WES, DAG, NCO, WAL = 10017290064, 10016239529, 10016920911, 10016986325, 10016736811, 10018682155
cands = {"RBN+WGU": [RBN, WGU], "RBN+WGU+WES": [RBN, WGU, WES], "WGU+WES+DAG (full-hist)": [WGU, WES, DAG],
         "WGU+NCO (full-hist)": [WGU, NCO], "RBN+WAL+WGU (2025-05+)": [RBN, WAL, WGU]}
out = {"wharton_sf_by_node": {k: {"sf": round(float(v["mean"]), 4), "n": int(v["size"])} for k, v in w.iterrows()}, "blends": {}}
for k, cols in cands.items():
    if not all(c in clean for c in cols): print("skip (WHARTN SF not ~0):", k); continue
    s = fit(cols, fit_mask); s["oos"] = oos(s, test_idx); s["full_refit"] = fit(cols, np.ones(len(DA), bool)); out["blends"][k] = s
    print(k, s["weights"], s["intercept"], s["oos"])
json.dump(out, open(D / "item2_proxy_alt_nowhartn.json", "w"), indent=2)
