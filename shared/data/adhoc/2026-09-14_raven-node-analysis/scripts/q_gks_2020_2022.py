"""GKS (proxy) RT TB2 premium over ERCOT system lambda, 2020-2022 combined, Uri (Feb-2021) excluded."""
from pathlib import Path
import pandas as pd

D = Path(__file__).resolve().parents[1] / "derived"
T = pd.read_csv(D / "gks_tb2_vs_lambda_daily_v2.csv", index_col=0, parse_dates=True)
T["year"] = T.index.year
base = T[(T.year >= 2020) & (T.year <= 2022)].dropna(subset=["proxy", "lam"])
noUri = base[~((base.index.year == 2021) & (base.index.month == 2))]
BIAS = 1.043   # proxy overstates real GKS TB2 by +4.3% over the 771-day overlap


def show(lab, g):
    p, l, h = g.proxy, g.lam, g.hb_south
    trim = lambda s: s.sort_values().iloc[:-5].mean()
    print(f"\n{lab}  ({len(g)}일)")
    print(f"  평균        : 대리 {p.mean():7.1f}  lambda {l.mean():7.1f}  남부허브 {h.mean():7.1f}"
          f"   -> lambda 대비 {100*(p.mean()/l.mean()-1):+6.1f}%")
    print(f"  중앙값      : 대리 {p.median():7.1f}  lambda {l.median():7.1f}  남부허브 {h.median():7.1f}"
          f"   -> {100*(p.median()/l.median()-1):+6.1f}%")
    print(f"  상위5일 제외 : 대리 {trim(p):7.1f}  lambda {trim(l):7.1f}"
          f"                    -> {100*(trim(p)/trim(l)-1):+6.1f}%")
    print(f"  남부허브 대비: 평균 {100*(p.mean()/h.mean()-1):+.1f}%, 중앙값 {100*(p.median()/h.median()-1):+.1f}%")
    print(f"  편향(+4.3%) 보정 후 lambda 대비: 평균 {100*((p.mean()/BIAS)/l.mean()-1):+.1f}%, "
          f"중앙값 {100*((p.median()/BIAS)/l.median()-1):+.1f}%")


show("2020~2022 전체", base)
show("2020~2022 (2021년 2월 Uri 제외)", noUri)

print("\n연도별 (Uri 제외 기준):")
for y, g in noUri.groupby("year"):
    print(f"  {y}: 평균 {100*(g.proxy.mean()/g.lam.mean()-1):+7.1f}%   중앙값 {100*(g.proxy.median()/g.lam.median()-1):+7.1f}%"
          f"   (대리 {g.proxy.mean():.1f} / lambda {g.lam.mean():.1f}, {len(g)}일)")
