"""GKS annual RT TB2 vs ERCOT system lambda, 2020-2023 — v2.

Fix vs v1: the winning candidate was DC_R, an INTERTIE (DC tie) node. It tracks GKS well in
2024-26 but its own 2020 TB2 is $186 against a $53 South hub — DC-tie price behaviour is not a
credible stand-in for a Valley generator node historically. v2 restricts candidates to SOUTH
GENERATOR nodes that were already priced in 2020.
Real data only. Feb-2021 (Uri) reported separately.
"""
import glob, json, pickle, sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import nnls

BASE = Path(__file__).resolve().parents[1]; D = BASE / "derived"
sys.path.insert(0, str(BASE / "scripts")); import dl
GKS, HB_SOUTH, HB_BUSAVG = 10017907494, 10000697079, 10000698380
COLS = ["OBJECTID", "DATETIME", "TIMEZONE", "DALMP", "DACONG", "DALOSS", "RTLMP", "RTCONG",
        "RTLOSS", "RTFINAL", "LOADID", "HALMP", "HACONG", "HALOSS", "ISO", "ALT"]

obj = dl.read_csv("ercot/metadata/objects/all.csv.gz")
nm = dict(zip(obj.OBJECTID, obj.OBJECTNAME))
gen_south = set(obj[(obj.OBJECTTYPE == "price_node") & (obj.ZONE == "SOUTH") & (obj.SUBTYPE == "GENERATOR")].OBJECTID)
S = pd.read_csv(D / "gks_proxy_diag.csv")
scan = pd.read_csv(D / "gks_proxy_scan_top30.csv")
cands = [int(i) for i in scan.id if int(i) in gen_south][:10]
print("후보 (SOUTH 발전기, 2020년 가격 존재):", [nm[c] for c in cands])


def tb2(s):
    g = pd.DataFrame({"p": s, "d": s.index.normalize()}).dropna()
    c = g.groupby("d").p.transform("size")
    g = g[c == 24]
    return g.groupby("d").p.apply(lambda v: v.nlargest(2).mean() - v.nsmallest(2).mean())


# ---------------- fit on the GKS overlap ----------------
parts = []
for f in sorted(glob.glob(str(BASE / "raw/price_panel/*.parquet"))):
    if Path(f).stem < "202408":
        continue
    m = pd.read_parquet(f)
    parts.append(m[m.OBJECTID.isin(set(cands) | {GKS, HB_SOUTH})])
p = pd.concat(parts, ignore_index=True)
p["dt"] = pd.to_datetime(p.DATETIME)
DA = p.pivot_table(index="dt", columns="OBJECTID", values="DALMP")
RT = p.pivot_table(index="dt", columns="OBJECTID", values="RTLMP")
ok = DA[GKS].notna() & RT[GKS].notna()
DA, RT = DA[ok], RT[ok]
TR = DA.index < "2026-01-01"


def fit(cols, mask):
    X = pd.concat([DA.loc[mask, cols], RT.loc[mask, cols]])
    y = pd.concat([DA.loc[mask, GKS], RT.loc[mask, GKS]])
    k = X.notna().all(axis=1) & y.notna()
    w, _ = nnls(X[k].values, y[k].values)
    if w.sum() > 0:
        w = w / w.sum()
    icpt = float((y[k].values - X[k].values @ w).mean())
    return dict(ids=[int(c) for c in cols], names=[nm[c] for c in cols],
                weights=[round(float(v), 4) for v in w], intercept=round(icpt, 3))


def ev(spec, mask):
    pr = pd.Series(spec["intercept"] + RT.loc[mask, spec["ids"]].values @ np.array(spec["weights"]), index=RT.index[mask])
    j = pd.DataFrame({"p": tb2(pr), "t": tb2(RT.loc[mask, GKS])}).dropna()
    return dict(mae=float((j.p - j.t).abs().mean()), bias=float(100 * (j.p.mean() / j.t.mean() - 1)),
                proxy=float(j.p.mean()), true=float(j.t.mean()), n=len(j))


print("\nOOS (학습 2024-08~2025-12 → 시험 2026)")
best = None
for k in [1, 2, 3, 5]:
    spec = fit(cands[:k], TR)
    e = ev(spec, ~TR)
    print(f"  상위{k}개: {'+'.join(spec['names']):46s} MAE ${e['mae']:.2f}  편향 {e['bias']:+.1f}%  (대리 ${e['proxy']:.1f} vs 실측 ${e['true']:.1f})")
    if best is None or e["mae"] < best[1]["mae"]:
        best = (spec, e, k)
spec = fit(best[0]["ids"], np.ones(len(DA), bool))
full_ev = ev(spec, np.ones(len(DA), bool))
print(f"\n채택: {'+'.join(spec['names'])}  가중치 {spec['weights']} 절편 {spec['intercept']}")
print(f"  전 겹침기간 재현: 대리 ${full_ev['proxy']:.1f} vs 실측 ${full_ev['true']:.1f} (편향 {full_ev['bias']:+.1f}%, MAE ${full_ev['mae']:.2f}, {full_ev['n']}일)")

# ---------------- fetch 2020-2023 for chosen nodes ----------------
WANT = set(spec["ids"]) | {HB_SOUTH, HB_BUSAVG}
CACHE = BASE / "raw/gks_px_2020_2023_v2.parquet"


def px_day(d):
    df = dl.try_read_csv(f"ercot/prices/lmp/hourly/{d:%Y%m%d}.csv.gz", header=None)
    if df is None:
        return None
    df.columns = COLS[:df.shape[1]]
    df = df[df.OBJECTID.isin(WANT)][["OBJECTID", "DATETIME", "RTLMP"]]
    return df if len(df) else None


if CACHE.exists():
    hist = pd.read_parquet(CACHE)
else:
    days, d = [], date(2020, 1, 1)
    while d <= date(2023, 12, 31):
        days.append(d); d += timedelta(days=1)
    with ThreadPoolExecutor(16) as ex:
        ps = [x for x in ex.map(px_day, days) if x is not None]
    hist = pd.concat(ps, ignore_index=True)
    hist.to_parquet(CACHE, index=False)
    print(f"\n2020-2023 가격 {len(ps)}일 수집")
hist["dt"] = pd.to_datetime(hist.DATETIME)
H = hist.pivot_table(index="dt", columns="OBJECTID", values="RTLMP")
have = [i for i in spec["ids"] if i in H.columns]
if len(have) < len(spec["ids"]):
    print("경고: 2020-2023에 없는 구성원", [nm[i] for i in spec["ids"] if i not in H.columns])
H["PROXY"] = spec["intercept"] + H[have].values @ np.array(spec["weights"])[: len(have)]

lam = pd.concat([pd.read_parquet(BASE / "raw/lambda_2020_2023.parquet"),
                 pd.read_parquet(BASE / "raw/lambda_2023_2026.parquet")], ignore_index=True)
lam["dt"] = pd.to_datetime(lam.dt)
lam["lam"] = pd.to_numeric(lam.lam, errors="coerce")
lh = lam.groupby(lam.dt.dt.ceil("h")).lam.mean()

# recent window (real GKS)
R2 = RT.copy()
R2["PROXY"] = spec["intercept"] + RT[spec["ids"]].values @ np.array(spec["weights"])

T = pd.DataFrame({
    "proxy": pd.concat([tb2(H.PROXY), tb2(R2.PROXY)]),
    "gks_real": tb2(R2[GKS]),
    "hb_south": pd.concat([tb2(H[HB_SOUTH]), tb2(RT[HB_SOUTH])]),
    "lam": tb2(lh),
})
T = T[~T.index.duplicated()]
T["year"] = T.index.year
T.to_csv(D / "gks_tb2_vs_lambda_daily_v2.csv")

print("\n연평균 일별 RT 이론 차익(TB2) $/MWh — GKS(대리) vs system lambda")
print(f"{'연도':>6} {'일수':>5} {'GKS 대리':>9} {'lambda':>8} {'프리미엄':>9} | {'남부 허브':>9} {'GKS 실측':>9}")
rows = []
for y, g in T.groupby("year"):
    g2 = g.dropna(subset=["proxy", "lam"])
    if len(g2) < 60:
        continue
    prem = 100 * (g2.proxy.mean() / g2.lam.mean() - 1)
    real = g.gks_real.mean() if g.gks_real.notna().sum() > 60 else np.nan
    rows.append(dict(year=int(y), days=len(g2), proxy=float(g2.proxy.mean()), lam=float(g2.lam.mean()),
                     premium_pct=float(prem), hb_south=float(g2.hb_south.mean()),
                     gks_real=None if np.isnan(real) else float(real)))
    print(f"{y:>6} {len(g2):>5} {g2.proxy.mean():>9.1f} {g2.lam.mean():>8.1f} {prem:>+8.1f}% | "
          f"{g2.hb_south.mean():>9.1f} {('%.1f' % real) if not np.isnan(real) else '—':>9}")

noUri = T[~((T.index.year == 2021) & (T.index.month == 2))]
for lab, TT in [("2020~2023", T), ("2020~2023 (2021년 2월 Uri 제외)", noUri)]:
    g = TT[(TT.year >= 2020) & (TT.year <= 2023)].dropna(subset=["proxy", "lam"])
    print(f"\n{lab}: 대리 ${g.proxy.mean():.1f} vs lambda ${g.lam.mean():.1f} → 프리미엄 {100*(g.proxy.mean()/g.lam.mean()-1):+.1f}% ({len(g)}일)")
g21 = noUri[noUri.year == 2021].dropna(subset=["proxy", "lam"])
print(f"  2021년만 Uri 제외: 대리 ${g21.proxy.mean():.1f} vs lambda ${g21.lam.mean():.1f} → {100*(g21.proxy.mean()/g21.lam.mean()-1):+.1f}%")

gr = T.dropna(subset=["gks_real", "lam"])
print(f"\n[검증] GKS 실측 {len(gr)}일: 실측 ${gr.gks_real.mean():.1f} / lambda ${gr.lam.mean():.1f} → 실측 프리미엄 {100*(gr.gks_real.mean()/gr.lam.mean()-1):+.1f}%"
      f"  | 대리 ${gr.proxy.mean():.1f} (실측 대비 {100*(gr.proxy.mean()/gr.gks_real.mean()-1):+.1f}%)")

json.dump(dict(proxy=spec, overlap_fit=full_ev, annual=rows), open(D / "gks_tb2_vs_lambda_v2.json", "w", encoding="utf-8"),
          indent=1, ensure_ascii=False, default=float)
print("\nwrote gks_tb2_vs_lambda_v2.json")
