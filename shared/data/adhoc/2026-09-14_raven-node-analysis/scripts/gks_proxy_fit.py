"""Build a GKS_BESS_RN proxy from nodes that already had prices in 2020, so GKS can be
reconstructed back to 2020-2023 (GKS's own node only starts 2024-08).

Same method as the Raven proxy: scan candidates, fit NNLS on stacked DA+RT hourly, select by
out-of-sample TB2 error. Train 2024-08-01..2025-12-31, test 2026-01-01..2026-09-13.
Real data only.
"""
import glob, json, pickle
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import nnls

BASE = Path(__file__).resolve().parents[1]; D = BASE / "derived"
GKS = 10017907494
ids2020 = pickle.load(open(BASE / "raw/ids_2020.pkl", "rb"))
KEEP = (ids2020 | {GKS})

parts = []
for f in sorted(glob.glob(str(BASE / "raw/price_panel/*.parquet"))):
    if Path(f).stem < "202408":
        continue
    m = pd.read_parquet(f)
    parts.append(m[m.OBJECTID.isin(KEEP)])
px = pd.concat(parts, ignore_index=True)
px["dt"] = pd.to_datetime(px.DATETIME)
DA = px.pivot_table(index="dt", columns="OBJECTID", values="DALMP")
RT = px.pivot_table(index="dt", columns="OBJECTID", values="RTLMP")
ix = DA.index.intersection(RT.index)
DA, RT = DA.loc[ix], RT.loc[ix]
y_da, y_rt = DA[GKS], RT[GKS]
ok = y_da.notna() & y_rt.notna()
DA, RT, y_da, y_rt = DA[ok], RT[ok], y_da[ok], y_rt[ok]
cand = [c for c in DA.columns if c != GKS and DA[c].notna().mean() > 0.98 and RT[c].notna().mean() > 0.98]
print(f"기간 {DA.index.min().date()} ~ {DA.index.max().date()}  {len(DA):,}시간 · 후보 노드 {len(cand)}개")

sp_y = y_da - y_rt
rows = []
for c in cand:
    rows.append(dict(id=c,
                     corr_da=DA[c].corr(y_da), corr_rt=RT[c].corr(y_rt),
                     rmse_da=np.sqrt(((DA[c] - y_da) ** 2).mean()), rmse_rt=np.sqrt(((RT[c] - y_rt) ** 2).mean()),
                     corr_spread=(DA[c] - RT[c]).corr(sp_y)))
S = pd.DataFrame(rows)
for c, asc in [("corr_da", False), ("corr_rt", False), ("rmse_da", True), ("rmse_rt", True), ("corr_spread", False)]:
    S[c + "_r"] = S[c].rank(ascending=asc)
S["rank"] = S[[c for c in S.columns if c.endswith("_r")]].mean(axis=1)
S = S.sort_values("rank")
a = pd.read_csv(BASE / "raw/hub_objects.csv") if (BASE / "raw/hub_objects.csv").exists() else None
import sys
sys.path.insert(0, str(BASE / "scripts")); import dl
obj = dl.read_csv("ercot/metadata/objects/all.csv.gz")
nm = dict(zip(obj.OBJECTID, obj.OBJECTNAME)); zn = dict(zip(obj.OBJECTID, obj.ZONE))
S["name"] = S.id.map(nm); S["zone"] = S.id.map(zn)
print("\n후보 상위 12")
print(S.head(12)[["name", "zone", "corr_da", "corr_rt", "rmse_da", "rmse_rt", "corr_spread", "rank"]].round(3).to_string(index=False))

TRAIN = DA.index < "2026-01-01"
TEST = ~TRAIN


def fit(cols, mask):
    X = pd.concat([DA.loc[mask, cols], RT.loc[mask, cols]])
    y = pd.concat([y_da[mask], y_rt[mask]])
    k = X.notna().all(axis=1) & y.notna()
    Xv, yv = X[k].values, y[k].values
    w, _ = nnls(Xv, yv)
    if w.sum() > 0:
        w = w / w.sum()
    icpt = float((yv - Xv @ w).mean())
    return dict(ids=[int(c) for c in cols], names=[nm[c] for c in cols],
                weights=[round(float(v), 4) for v in w], intercept=round(icpt, 3))


def tb2(s):
    g = pd.DataFrame({"p": s, "d": s.index.normalize()}).dropna()
    c = g.groupby("d").p.transform("size")
    g = g[c == 24]
    return g.groupby("d").p.apply(lambda v: v.nlargest(2).mean() - v.nsmallest(2).mean())


def ev(spec, mask):
    p_da = spec["intercept"] + DA.loc[mask, spec["ids"]].values @ np.array(spec["weights"])
    p_rt = spec["intercept"] + RT.loc[mask, spec["ids"]].values @ np.array(spec["weights"])
    p_da = pd.Series(p_da, index=DA.index[mask]); p_rt = pd.Series(p_rt, index=DA.index[mask])
    t_rt, t_rt_true = tb2(p_rt), tb2(y_rt[mask])
    t_da, t_da_true = tb2(p_da), tb2(y_da[mask])
    j_rt = pd.DataFrame({"p": t_rt, "t": t_rt_true}).dropna()
    j_da = pd.DataFrame({"p": t_da, "t": t_da_true}).dropna()
    return dict(tb2_rt_mae=float((j_rt.p - j_rt.t).abs().mean()), tb2_rt_true=float(j_rt.t.mean()),
                tb2_rt_proxy=float(j_rt.p.mean()), tb2_da_mae=float((j_da.p - j_da.t).abs().mean()),
                rmse_rt=float(np.sqrt(((p_rt - y_rt[mask]) ** 2).mean())), n_days=int(len(j_rt)))


CANDS = {
    "단일 최적": [int(S.id.iloc[0])],
    "상위 2": [int(x) for x in S.id.head(2)],
    "상위 3": [int(x) for x in S.id.head(3)],
    "상위 5": [int(x) for x in S.id.head(5)],
}
print("\nOOS 검증 (학습 2024-08~2025-12 → 시험 2026-01~09)")
best, best_score = None, 1e9
for lab, cols in CANDS.items():
    spec = fit(cols, TRAIN)
    e = ev(spec, TEST)
    score = e["tb2_rt_mae"]
    print(f"  {lab:8s} {'+'.join(spec['names']):34s} w={spec['weights']} icpt={spec['intercept']:+.2f}"
          f" | RT TB2 MAE ${e['tb2_rt_mae']:.2f} (실측 ${e['tb2_rt_true']:.1f} vs 대리 ${e['tb2_rt_proxy']:.1f}) DA MAE ${e['tb2_da_mae']:.2f}")
    if score < best_score:
        best, best_score, best_lab, best_ev = spec, score, lab, e

full = fit(best["ids"], np.ones(len(DA), bool))
print(f"\n채택: {best_lab} — {'+'.join(full['names'])}")
print(f"  전 구간 재적합 가중치 {full['weights']}, 절편 {full['intercept']}")
out = dict(target="GKS_BESS_RN", target_id=GKS, chosen=best_lab, **full,
           eligibility="2020-01-15에 DA 가격이 존재한 노드만 후보", oos=best_ev,
           fit_window=f"{DA.index.min().date()}..{DA.index.max().date()} (OOS 선택 후 전 구간 재적합)")
json.dump(out, open(D / "gks_proxy_definition.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
S.head(30).to_csv(D / "gks_proxy_scan_top30.csv", index=False)
print("wrote gks_proxy_definition.json")
