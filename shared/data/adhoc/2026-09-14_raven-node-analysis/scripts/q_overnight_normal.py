"""Winter overnight (HE1-6): is LONG favourable once spike/tight periods are excluded?

Two ways to exclude, and they differ in usability:
  (A) EX-ANTE  — forecast tightness tercile (known before the 10:00 CT bid deadline)  -> tradeable
  (B) EX-POST  — DA price level of the hour itself (a virtual is bid BEFORE DA clears) -> diagnostic only
SHORT PnL = +(DA-RT), LONG PnL = -(DA-RT). RVN proxy series.
"""
from pathlib import Path
import numpy as np, pandas as pd

BASE = Path(__file__).resolve().parents[1]
h = pd.read_parquet(BASE / "derived/dart3y_hourly_panel.parquet")
w = h[(h.season == "겨울") & (h.he <= 6)].copy()
w["wy"] = np.where(pd.to_datetime(w.day).dt.month == 12, pd.to_datetime(w.day).dt.year + 1, pd.to_datetime(w.day).dt.year)


def line(tag, x):
    x = x.dropna()
    if len(x) < 30:
        return f"{tag:>26} | n={len(x):>4}  (표본 부족)"
    s, l = x, -x
    sw, lw = (s > 0).mean() * 100, (l > 0).mean() * 100
    spl = s[s > 0].mean() / -s[s < 0].mean() if (s < 0).any() else np.nan
    lpl = l[l > 0].mean() / -l[l < 0].mean() if (l < 0).any() else np.nan
    best = "LONG" if (lw > sw and lpl > spl) else ("SHORT" if (sw > lw and spl > lpl) else "혼재")
    return (f"{tag:>26} | n={len(x):>4} | SHORT {sw:5.1f}% P/L {spl:4.2f} 평균 {s.mean():+7.2f} 중앙값 {s.median():+6.2f}"
            f" | LONG {lw:5.1f}% P/L {lpl:4.2f} 평균 {l.mean():+7.2f} | {best}")


print("=" * 130)
print("[A] 사전 구분 — 입찰 전 예측 기준 계통 타이트함 (겨울 새벽 HE1-6)")
print(line("전체", w.spread))
for t in ["여유", "보통", "타이트"]:
    print(line(f"예측 {t}", w[w.tight == t].spread))
print()
print("  ↳ 같은 구간에서 상위 스파이크만 제외했을 때")
for t in ["여유", "보통", "타이트"]:
    x = w[w.tight == t].spread.dropna().sort_values()
    for k in [0, 3, 10]:
        y = x.iloc[:len(x) - k] if k else x
        print(line(f"예측 {t} · 상위{k}h 제외", y))

print("\n" + "=" * 130)
print("[B] 사후 구분 — 그 시간의 DA 가격 수준 (가상거래는 DA 청산 전에 입찰하므로 실거래엔 사용 불가)")
# reconstruct DA level for the proxy from the panel
import glob
N = {"CBEC_ALL": 10001765766, "RBN_BESS1": 10017290064, "TAV_RN": 10016969364}
W, B0 = {"CBEC_ALL": 0.4148, "RBN_BESS1": 0.5407, "TAV_RN": 0.0445}, -0.065
ps = []
for f in sorted(glob.glob(str(BASE / "raw/price_panel/*.parquet"))):
    if Path(f).stem < "202312":
        continue
    d = pd.read_parquet(f)
    ps.append(d[d.OBJECTID.isin(N.values())])
p = pd.concat(ps)
inv = {v: k for k, v in N.items()}
p["node"] = p.OBJECTID.map(inv)
p["dt"] = pd.to_datetime(p.DATETIME)
DA = p.pivot_table(index="dt", columns="node", values="DALMP")
da_proxy = (B0 + sum(W[k] * DA[k] for k in W)).rename("da")
w = w.join(da_proxy, how="left")
q = w.da.quantile([.5, .8, .9, .95]).round(1).to_dict()
print("  겨울 새벽 DA 가격 분위:", q)
for lab, m in [("DA < $50", w.da < 50), ("DA $50~100", (w.da >= 50) & (w.da < 100)),
               ("DA >= $100", w.da >= 100), ("DA >= $200", w.da >= 200)]:
    print(line(lab, w[m].spread))

print("\n" + "=" * 130)
print("[C] 겨울 새벽에서 스파이크가 실제로 언제 났는지 (spread 상위 20시간)")
top = w.nlargest(20, "spread")[["day", "he", "spread", "da", "tight"]]
top["day"] = pd.to_datetime(top.day).dt.date
print(top.to_string(index=False))
print("\n  상위 20시간의 예측 타이트함 분포:", top.tight.value_counts().to_dict())
print("  상위 20시간이 속한 날짜:", sorted({str(d) for d in top.day}))

print("\n" + "=" * 130)
print("[D] 연도별 — 예측 '여유+보통' 구간만 (겨울 새벽)")
for y, g in w[w.tight.isin(["여유", "보통"])].groupby("wy"):
    print(line(f"{y}년 겨울 여유·보통", g.spread))
