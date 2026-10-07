"""Quick check: overnight (HE1-6) DART side at RVN — SHORT or LONG?
Dashboard shows SHORT on the MEAN; the user recalls LONG winning on hit-rate and profit/loss ratio
for the ERCOT system in winter. Mean and hit-rate can disagree when a few spike hours dominate.
SHORT PnL = +(DA-RT), LONG PnL = -(DA-RT). Proxy series for RVN; HB_BUSAVG for the system.
"""
import glob
from pathlib import Path
import numpy as np, pandas as pd

BASE = Path(__file__).resolve().parents[1]
h = pd.read_parquet(BASE / "derived/dart3y_hourly_panel.parquet")
BUS = 10000698380
ps = []
for f in sorted(glob.glob(str(BASE / "raw/price_panel/*.parquet"))):
    if Path(f).stem < "202312":
        continue
    d = pd.read_parquet(f)
    ps.append(d[d.OBJECTID == BUS])
b = pd.concat(ps)
b["dt"] = pd.to_datetime(b.DATETIME)
b = b.set_index("dt")
h = h.join((b.DALMP - b.RTLMP).rename("sys"), how="left")


def stat(x, side):
    pnl = x if side == "SHORT" else -x
    w, l = pnl[pnl > 0], -pnl[pnl < 0]
    return dict(win=100 * (pnl > 0).mean(), pl=(w.mean() / l.mean()) if len(l) and l.mean() > 0 else np.nan,
                mean=pnl.mean(), med=pnl.median(), p99=-np.percentile(pnl, 1))


for col, lab in [("spread", "RVN (대리노드)"), ("sys", "ERCOT 시스템 평균")]:
    print("=" * 104)
    print(f"{lab} — 새벽 1~6시 (HE1-6)")
    print(f"{'계절':>6} {'시간수':>6} | {'SHORT승률':>9} {'P/L':>5} {'평균':>7} {'중앙값':>7} | "
          f"{'LONG승률':>9} {'P/L':>5} {'평균':>7} {'중앙값':>7} | {'승률·P/L 동시우위':>16}")
    for s in ["겨울", "봄", "여름", "가을", "전체"]:
        x = h[h.he <= 6] if s == "전체" else h[(h.he <= 6) & (h.season == s)]
        x = x[col].dropna()
        if len(x) < 50:
            continue
        S, L = stat(x, "SHORT"), stat(x, "LONG")
        both = "LONG" if (L["win"] > S["win"] and L["pl"] > S["pl"]) else ("SHORT" if (S["win"] > L["win"] and S["pl"] > L["pl"]) else "혼재")
        print(f"{s:>6} {len(x):>6} | {S['win']:>8.1f}% {S['pl']:>5.2f} {S['mean']:>+7.2f} {S['med']:>+7.2f} | "
              f"{L['win']:>8.1f}% {L['pl']:>5.2f} {L['mean']:>+7.2f} {L['med']:>+7.2f} | {both:>16}")

print("\n" + "=" * 104)
print("RVN 겨울 새벽 — 시간대별 (평균이 SHORT를 가리키는 이유 확인)")
w = h[(h.season == "겨울") & (h.he <= 6)]
for he in range(1, 7):
    x = w[w.he == he].spread.dropna()
    S, L = stat(x, "SHORT"), stat(x, "LONG")
    top = x.nlargest(3).round(0).tolist()
    print(f"  HE{he}  n={len(x):3d}  SHORT 승률 {S['win']:5.1f}% P/L {S['pl']:4.2f} 평균 {S['mean']:+7.2f} 중앙값 {S['med']:+6.2f}"
          f"   | 상위3 시간 spread {top}")

print("\n겨울 새벽 상위 스파이크 제거 효과 (RVN):")
x = w.spread.dropna().sort_values()
for k in [0, 3, 10, 20]:
    y = x.iloc[:len(x) - k] if k else x
    S, L = stat(y, "SHORT"), stat(y, "LONG")
    print(f"  상위 {k:2d}시간 제외: SHORT 평균 {S['mean']:+6.2f} (승률 {S['win']:.1f}%) | LONG 평균 {L['mean']:+6.2f} (승률 {L['win']:.1f}%)")

print("\n연도별 안정성 (겨울 새벽, RVN):")
w2 = w.copy()
w2["wy"] = np.where(pd.to_datetime(w2.day).dt.month == 12, pd.to_datetime(w2.day).dt.year + 1, pd.to_datetime(w2.day).dt.year)
for y, g in w2.groupby("wy"):
    x = g.spread.dropna()
    if len(x) < 50:
        continue
    S, L = stat(x, "SHORT"), stat(x, "LONG")
    print(f"  {y}년 겨울: n={len(x):3d}  SHORT 승률 {S['win']:5.1f}% 평균 {S['mean']:+7.2f} | LONG 승률 {L['win']:5.1f}% P/L {L['pl']:4.2f} 평균 {L['mean']:+7.2f}")
