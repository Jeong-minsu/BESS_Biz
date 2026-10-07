"""GKS (proxy-reconstructed) annual average RT TB2 vs ERCOT system lambda TB2, 2020-2023.

GKS_BESS_RN has prices only from 2024-08, so 2020-2023 uses the GKS proxy fitted in
gks_proxy_fit.py (nodes restricted to those already priced in 2020).
Reference series: HB_SOUTH (South hub), HB_BUSAVG (all-bus average hub), system lambda (energy-only).
"Premium" = proxy RT TB2 / lambda RT TB2 - 1.
Real data only; Feb-2021 (Uri) reported separately because it dominates any 2021 average.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
import sys
import numpy as np, pandas as pd

BASE = Path(__file__).resolve().parents[1]; D = BASE / "derived"
sys.path.insert(0, str(BASE / "scripts")); import dl

defn = json.load(open(D / "gks_proxy_definition.json", encoding="utf-8"))
PROXY_IDS, PROXY_W, ICPT = defn["ids"], np.array(defn["weights"]), defn["intercept"]
HB_SOUTH, HB_BUSAVG, GKS = 10000697079, 10000698380, 10017907494
WANT = set(PROXY_IDS) | {HB_SOUTH, HB_BUSAVG, GKS}
COLS = ["OBJECTID", "DATETIME", "TIMEZONE", "DALMP", "DACONG", "DALOSS", "RTLMP", "RTCONG",
        "RTLOSS", "RTFINAL", "LOADID", "HALMP", "HACONG", "HALOSS", "ISO", "ALT"]
PX_CACHE, LAM_CACHE = BASE / "raw/gks_px_2020_2023.parquet", BASE / "raw/lambda_2020_2023.parquet"


def px_day(d):
    df = dl.try_read_csv(f"ercot/prices/lmp/hourly/{d:%Y%m%d}.csv.gz", header=None)
    if df is None:
        return None
    df.columns = COLS[:df.shape[1]]
    df = df[df.OBJECTID.isin(WANT)][["OBJECTID", "DATETIME", "DALMP", "RTLMP"]]
    return df.assign(day=pd.Timestamp(d)) if len(df) else None


def lam_day(d):
    df = dl.try_read_csv(f"ercot/ancillary/system_lambda/{d:%Y%m%d}.csv.gz", header=None)
    if df is None:
        return None
    o = df.iloc[:, [2, 4]].copy()
    o.columns = ["dt", "lam"]
    return o


days, d = [], date(2020, 1, 1)
while d <= date(2023, 12, 31):
    days.append(d); d += timedelta(days=1)

if PX_CACHE.exists():
    px = pd.read_parquet(PX_CACHE)
else:
    with ThreadPoolExecutor(16) as ex:
        parts = [p for p in ex.map(px_day, days) if p is not None]
    px = pd.concat(parts, ignore_index=True)
    px.to_parquet(PX_CACHE, index=False)
    print(f"가격 {len(parts)}일 수집")
if LAM_CACHE.exists():
    lam = pd.read_parquet(LAM_CACHE)
else:
    with ThreadPoolExecutor(16) as ex:
        parts = [p for p in ex.map(lam_day, days) if p is not None]
    lam = pd.concat(parts, ignore_index=True)
    lam.to_parquet(LAM_CACHE, index=False)
    print(f"lambda {len(parts)}일 수집")

px["dt"] = pd.to_datetime(px.DATETIME)
RT = px.pivot_table(index="dt", columns="OBJECTID", values="RTLMP")
have = [i for i in PROXY_IDS if i in RT.columns]
RT["PROXY"] = ICPT + RT[have].values @ PROXY_W[: len(have)]
lam["dt"] = pd.to_datetime(lam.dt)
lam["lam"] = pd.to_numeric(lam.lam, errors="coerce")
lh = lam.groupby(lam.dt.dt.ceil("h")).lam.mean()
RT["LAMBDA"] = lh.reindex(RT.index)

# add the 2024-2026 window (real GKS + proxy) from the existing panel for continuity
import glob
parts = []
for f in sorted(glob.glob(str(BASE / "raw/price_panel/*.parquet"))):
    m = pd.read_parquet(f)
    parts.append(m[m.OBJECTID.isin(WANT)][["OBJECTID", "DATETIME", "RTLMP"]])
p2 = pd.concat(parts, ignore_index=True)
p2["dt"] = pd.to_datetime(p2.DATETIME)
R2 = p2.pivot_table(index="dt", columns="OBJECTID", values="RTLMP")
have2 = [i for i in PROXY_IDS if i in R2.columns]
R2["PROXY"] = ICPT + R2[have2].values @ PROXY_W[: len(have2)]
lam2 = []
d = date(2023, 9, 1)
while d <= date(2026, 9, 13):
    lam2.append(d); d += timedelta(days=1)
L2 = BASE / "raw/lambda_2023_2026.parquet"
if L2.exists():
    l2 = pd.read_parquet(L2)
else:
    with ThreadPoolExecutor(16) as ex:
        ps = [p for p in ex.map(lam_day, lam2) if p is not None]
    l2 = pd.concat(ps, ignore_index=True)
    l2.to_parquet(L2, index=False)
l2["dt"] = pd.to_datetime(l2.dt)
l2["lam"] = pd.to_numeric(l2.lam, errors="coerce")
R2["LAMBDA"] = l2.groupby(l2.dt.dt.ceil("h")).lam.mean().reindex(R2.index)

ALL = pd.concat([RT, R2[[c for c in RT.columns if c in R2.columns]]]).sort_index()
ALL = ALL[~ALL.index.duplicated()]


def tb2(s):
    g = pd.DataFrame({"p": s, "d": s.index.normalize()}).dropna()
    c = g.groupby("d").p.transform("size")
    g = g[c == 24]
    return g.groupby("d").p.apply(lambda v: v.nlargest(2).mean() - v.nsmallest(2).mean())


T = pd.DataFrame({"proxy": tb2(ALL.PROXY), "lambda": tb2(ALL.LAMBDA),
                  "hb_south": tb2(ALL[HB_SOUTH]) if HB_SOUTH in ALL else np.nan,
                  "hb_busavg": tb2(ALL[HB_BUSAVG]) if HB_BUSAVG in ALL else np.nan,
                  "gks_real": tb2(ALL[GKS]) if GKS in ALL else np.nan})
T["year"] = T.index.year
T.to_csv(D / "gks_tb2_vs_lambda_daily.csv")

print("\n연평균 일별 RT 이론 차익(TB2), $/MWh — GKS 대리 노드 vs system lambda")
print(f"{'연도':>6} {'일수':>5} {'GKS 대리':>9} {'lambda':>9} {'프리미엄':>9} | {'남부 허브':>9} {'전버스 허브':>10} {'GKS 실측':>9}")
rows = []
for y, g in T.groupby("year"):
    g = g.dropna(subset=["proxy", "lambda"])
    if len(g) < 60:
        continue
    pr, lm = g.proxy.mean(), g["lambda"].mean()
    prem = 100 * (pr / lm - 1)
    real = g.gks_real.mean() if g.gks_real.notna().sum() > 30 else np.nan
    rows.append(dict(year=int(y), days=len(g), proxy=pr, lam=lm, premium_pct=prem,
                     hb_south=g.hb_south.mean(), hb_busavg=g.hb_busavg.mean(), gks_real=real))
    print(f"{y:>6} {len(g):>5} {pr:>9.1f} {lm:>9.1f} {prem:>+8.1f}% | {g.hb_south.mean():>9.1f} "
          f"{g.hb_busavg.mean():>10.1f} {('%.1f' % real) if not np.isnan(real) else '—':>9}")

print("\n2021년 2월(Uri) 제외:")
noUri = T[~((T.index.year == 2021) & (T.index.month == 2))]
for y in [2021]:
    g = noUri[noUri.year == y].dropna(subset=["proxy", "lambda"])
    print(f"  {y}: 대리 ${g.proxy.mean():.1f}  lambda ${g['lambda'].mean():.1f}  프리미엄 {100*(g.proxy.mean()/g['lambda'].mean()-1):+.1f}%  ({len(g)}일)")

g4 = T[(T.year >= 2020) & (T.year <= 2023)].dropna(subset=["proxy", "lambda"])
g4n = noUri[(noUri.year >= 2020) & (noUri.year <= 2023)].dropna(subset=["proxy", "lambda"])
print(f"\n2020~2023 4년 통합: 대리 ${g4.proxy.mean():.1f} vs lambda ${g4['lambda'].mean():.1f} → 프리미엄 {100*(g4.proxy.mean()/g4['lambda'].mean()-1):+.1f}%")
print(f"  (Uri 제외) 대리 ${g4n.proxy.mean():.1f} vs lambda ${g4n['lambda'].mean():.1f} → {100*(g4n.proxy.mean()/g4n['lambda'].mean()-1):+.1f}%")

gr = T.dropna(subset=["gks_real", "lambda"])
if len(gr) > 100:
    print(f"\n[검증] GKS 실측이 있는 {len(gr)}일: 실측 ${gr.gks_real.mean():.1f} vs lambda ${gr['lambda'].mean():.1f} "
          f"→ 실측 프리미엄 {100*(gr.gks_real.mean()/gr['lambda'].mean()-1):+.1f}%  |  같은 날 대리 ${gr.proxy.mean():.1f} "
          f"(대리가 실측보다 {100*(gr.proxy.mean()/gr.gks_real.mean()-1):+.1f}%)")

json.dump({"annual": rows, "proxy": defn["names"], "note": "premium = proxy RT TB2 / system lambda RT TB2 - 1"},
          open(D / "gks_tb2_vs_lambda.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=float)
print("\nwrote gks_tb2_vs_lambda.json / _daily.csv")
