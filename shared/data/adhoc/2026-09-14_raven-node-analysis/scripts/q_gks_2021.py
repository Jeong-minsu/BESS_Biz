"""2021 only: GKS (proxy) vs ERCOT system lambda RT TB2, with and without Uri (Feb-2021)."""
from pathlib import Path
import pandas as pd

D = Path(__file__).resolve().parents[1] / "derived"
T = pd.read_csv(D / "gks_tb2_vs_lambda_daily_v2.csv", index_col=0, parse_dates=True)
y21 = T[T.index.year == 2021].dropna(subset=["proxy", "lam"])
feb = y21[y21.index.month == 2]
ex = y21[y21.index.month != 2]
BIAS = 1.043   # proxy overstates real GKS TB2 by +4.3% (771-day overlap)

print(f"{'구간':>22} {'일수':>5} | {'GKS 대리':>9} {'lambda':>8} {'프리미엄':>9} | {'남부허브':>9}")
for lab, g in [("2021 전체", y21), ("2021 (2월 Uri 제외)", ex), ("2021년 2월만 (Uri)", feb)]:
    print(f"{lab:>22} {len(g):>5} | {g.proxy.mean():>9.1f} {g.lam.mean():>8.1f} "
          f"{100*(g.proxy.mean()/g.lam.mean()-1):>+8.1f}% | {g.hb_south.mean():>9.1f}")

print(f"\n2021 (2월 제외) 상세 — {len(ex)}일")
print(f"  평균        : GKS 대리 ${ex.proxy.mean():.1f}   lambda ${ex.lam.mean():.1f}   -> {100*(ex.proxy.mean()/ex.lam.mean()-1):+.1f}%")
print(f"  중앙값      : GKS 대리 ${ex.proxy.median():.1f}   lambda ${ex.lam.median():.1f}   -> {100*(ex.proxy.median()/ex.lam.median()-1):+.1f}%")
t = lambda s: s.sort_values().iloc[:-5].mean()
print(f"  상위5일 제외 : GKS 대리 ${t(ex.proxy):.1f}   lambda ${t(ex.lam):.1f}   -> {100*(t(ex.proxy)/t(ex.lam)-1):+.1f}%")
print(f"  편향 보정 후 : GKS ${ex.proxy.mean()/BIAS:.1f} (평균) / ${ex.proxy.median()/BIAS:.1f} (중앙값)"
      f"   -> 평균 {100*((ex.proxy.mean()/BIAS)/ex.lam.mean()-1):+.1f}%, 중앙값 {100*((ex.proxy.median()/BIAS)/ex.lam.median()-1):+.1f}%")
print(f"  남부 허브    : ${ex.hb_south.mean():.1f} (평균), ${ex.hb_south.median():.1f} (중앙값)")

print("\n월별 (2021)")
print(f"{'월':>4} {'일수':>4} {'GKS 대리':>9} {'lambda':>9} {'프리미엄':>9} {'남부허브':>9}")
for m, g in y21.groupby(y21.index.month):
    mark = "  <- Uri" if m == 2 else ""
    print(f"{m:>4} {len(g):>4} {g.proxy.mean():>9.1f} {g.lam.mean():>9.1f} "
          f"{100*(g.proxy.mean()/g.lam.mean()-1):>+8.1f}% {g.hb_south.mean():>9.1f}{mark}")

print("\n2021 (2월 제외) 이론 차익 상위 5일")
print(ex.nlargest(5, "proxy")[["proxy", "lam", "hb_south"]].round(0).to_string())
