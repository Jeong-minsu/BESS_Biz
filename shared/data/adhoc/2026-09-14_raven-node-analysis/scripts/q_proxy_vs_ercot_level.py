"""Proxy-reconstructed Raven RT TB2 level vs ERCOT market level, on the SAME Jan-Sep basis
used by the FY2027 forecast. Two market references:
  (a) all-node average : cross-sectional mean of every ERCOT price_node's daily RT TB2
  (b) system hub       : HB_BUSAVG daily RT TB2
Real data only.
"""
import glob
from pathlib import Path
import numpy as np, pandas as pd

BASE = Path(__file__).resolve().parents[1]
N = {"CBEC_ALL": 10001765766, "RBN_BESS1": 10017290064, "TAV_RN": 10016969364,
     "RVN": 10019925379, "HB_BUSAVG": 10000698380, "HB_HOUSTON": 10000697077}
W, B0 = {"CBEC_ALL": 0.4148, "RBN_BESS1": 0.5407, "TAV_RN": 0.0445}, -0.065


def tb2_all(df, col):
    d = df[["OBJECTID", "FLOWDAY", col]].dropna()
    n = d.groupby(["OBJECTID", "FLOWDAY"])[col].transform("size")
    d = d[n == 24].sort_values(["OBJECTID", "FLOWDAY", col])
    r = d.groupby(["OBJECTID", "FLOWDAY"]).cumcount()
    bot = d[r <= 1].groupby(["OBJECTID", "FLOWDAY"])[col].mean()
    top = d[r >= 22].groupby(["OBJECTID", "FLOWDAY"])[col].mean()
    return (top - bot).rename("tb2").reset_index()


sys_rows, node_rows = [], []
for f in sorted(glob.glob(str(BASE / "raw/price_panel/*.parquet"))):
    ym = Path(f).stem
    if not ("202401" <= ym <= "202609") or int(ym[4:]) > 9:      # Jan-Sep of 2024/2025/2026
        continue
    m = pd.read_parquet(f)
    t = tb2_all(m, "RTLMP")
    s = t.groupby("FLOWDAY").tb2.agg(["mean", "median"]).reset_index()
    sys_rows.append(s)
    node_rows.append(m[m.OBJECTID.isin(N.values())])

sysd = pd.concat(sys_rows, ignore_index=True)
px = pd.concat(node_rows, ignore_index=True)
inv = {v: k for k, v in N.items()}
px["node"] = px.OBJECTID.map(inv)
px["dt"] = pd.to_datetime(px.DATETIME)

rt = px.pivot_table(index="dt", columns="node", values="RTLMP")
have = [k for k in W if k in rt.columns]
rt["PROXY"] = B0 + sum(W[k] * rt[k] for k in have)
rt["day"] = rt.index.normalize()


def daily_tb2(series, day):
    d = pd.DataFrame({"p": series, "day": day}).dropna()
    c = d.groupby("day").p.transform("size")
    d = d[c == 24]
    return d.groupby("day").p.apply(lambda v: v.nlargest(2).mean() - v.nsmallest(2).mean())


out = {}
for col in ["PROXY", "RVN", "HB_BUSAVG", "HB_HOUSTON"]:
    if col in rt.columns:
        out[col] = daily_tb2(rt[col], rt["day"])
sysd["FLOWDAY"] = pd.to_datetime(sysd.FLOWDAY)
out["ALLNODE_mean"] = sysd.set_index("FLOWDAY")["mean"]
out["ALLNODE_median"] = sysd.set_index("FLOWDAY")["median"]
T = pd.DataFrame(out)
T["year"] = T.index.year

print("실시간 이론 차익 (RT TB2) 연도별 평균 — 1~9월 기준, $/MWh")
print(f"{'연도':>6} {'일수':>5} {'대리노드':>9} {'전노드 평균':>11} {'전노드 중앙':>11} {'시스템 허브':>11} {'Houston 허브':>12}"
      f" | {'vs 전노드평균':>12} {'vs 전노드중앙':>13} {'vs 시스템허브':>12}")
rows = []
for y, g in T.groupby("year"):
    g = g.dropna(subset=["PROXY", "ALLNODE_mean", "HB_BUSAVG"])
    p, am, amd, hb, hh = g.PROXY.mean(), g.ALLNODE_mean.mean(), g.ALLNODE_median.mean(), g.HB_BUSAVG.mean(), g.HB_HOUSTON.mean()
    d1, d2, d3 = 100 * (p / am - 1), 100 * (p / amd - 1), 100 * (p / hb - 1)
    rows.append(dict(year=int(y), days=len(g), proxy=p, allnode_mean=am, allnode_median=amd, hub=hb, houston=hh,
                     vs_allnode_mean=d1, vs_allnode_median=d2, vs_hub=d3))
    print(f"{y:>6} {len(g):>5} {p:>9.1f} {am:>11.1f} {amd:>11.1f} {hb:>11.1f} {hh:>12.1f}"
          f" | {d1:>+11.1f}% {d2:>+12.1f}% {d3:>+11.1f}%")

r = pd.DataFrame(rows)
print(f"\n3년 평균 격차: 전노드 평균 대비 {r.vs_allnode_mean.mean():+.1f}%, "
      f"전노드 중앙값 대비 {r.vs_allnode_median.mean():+.1f}%, 시스템 허브 대비 {r.vs_hub.mean():+.1f}%")

# cross-check: proxy vs real RVN on the overlap (2026 Jun-Sep)
ov = T.dropna(subset=["PROXY", "RVN"])
if len(ov):
    print(f"\n[검증] 실측 RVN이 있는 {len(ov)}일: 대리 {ov.PROXY.mean():.2f} vs 실측 {ov.RVN.mean():.2f} "
          f"({100*(ov.PROXY.mean()/ov.RVN.mean()-1):+.1f}%) · 같은 날 전노드 평균 {ov.ALLNODE_mean.mean():.2f} "
          f"→ 실측 RVN은 전노드 평균 대비 {100*(ov.RVN.mean()/ov.ALLNODE_mean.mean()-1):+.1f}%")
