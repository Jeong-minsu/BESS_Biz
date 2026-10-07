"""Is HB_BUSAVG the same as ERCOT system lambda? Compare them on 2026 Jan-Sep.
HB_BUSAVG  : a settlement HUB — unweighted average of ERCOT bus LMPs (energy + congestion + loss)
system lambda : the system marginal energy price only (no congestion, no loss), ISO-level
Real data only.
"""
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
import numpy as np, pandas as pd

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "scripts")); import dl

BUS = 10000698380


def one(d):
    df = dl.try_read_csv(f"ercot/ancillary/system_lambda/{d:%Y%m%d}.csv.gz", header=None)
    if df is None:
        return None
    df = df.iloc[:, [2, 4]]
    df.columns = ["dt", "lam"]
    df["dt"] = pd.to_datetime(df.dt)
    df["lam"] = pd.to_numeric(df.lam, errors="coerce")
    return df


days, d = [], date(2026, 1, 1)
while d <= date(2026, 9, 13):
    days.append(d); d += timedelta(days=1)
with ThreadPoolExecutor(16) as ex:
    parts = [p for p in ex.map(one, days) if p is not None]
lam = pd.concat(parts, ignore_index=True)
lam["he_ts"] = lam.dt.dt.ceil("h")
lh = lam.groupby("he_ts").lam.mean()
print(f"system lambda: {len(parts)}일, 5분 {len(lam):,}건 -> 시간 {len(lh):,}건")

import glob
ps = []
for f in sorted(glob.glob(str(BASE / "raw/price_panel/2026*.parquet"))):
    m = pd.read_parquet(f)
    ps.append(m[m.OBJECTID == BUS])
hb = pd.concat(ps)
hb["dt"] = pd.to_datetime(hb.DATETIME)
hb = hb.set_index("dt").RTLMP

T = pd.DataFrame({"hub": hb, "lambda": lh}).dropna()
T = T[T.index < "2026-09-14"]
T["day"] = T.index.normalize()
print(f"\n비교 구간 {T.index.min().date()} ~ {T.index.max().date()} ({len(T):,}시간)")
print(f"  시간 평균 : 허브 ${T.hub.mean():.2f}  vs  system lambda ${T['lambda'].mean():.2f}  (차이 {T.hub.mean()-T['lambda'].mean():+.2f})")
print(f"  상관계수  : {T.hub.corr(T['lambda']):.4f}   두 값이 정확히 같은 시간 비율: {100*np.isclose(T.hub, T['lambda'], atol=0.01).mean():.1f}%")
d = (T.hub - T["lambda"])
print(f"  시간별 차이: 평균 {d.mean():+.2f}, 표준편차 {d.std():.2f}, 5%~95% {np.percentile(d,5):+.1f} ~ {np.percentile(d,95):+.1f}")


def tb2(s):
    g = pd.DataFrame({"p": s, "day": s.index.normalize()}).dropna()
    c = g.groupby("day").p.transform("size")
    g = g[c == 24]
    return g.groupby("day").p.apply(lambda v: v.nlargest(2).mean() - v.nsmallest(2).mean())


t_hub, t_lam = tb2(T.hub), tb2(T["lambda"])
j = pd.DataFrame({"hub": t_hub, "lam": t_lam}).dropna()
print(f"\n일별 이론 차익(TB2) 평균, {len(j)}일: 허브 ${j.hub.mean():.1f}  vs  system lambda ${j.lam.mean():.1f}"
      f"  (lambda가 {100*(j.lam.mean()/j.hub.mean()-1):+.1f}%)")
print("\n참고) 이번 전망에서 '시스템 허브'로 쓴 값은 HB_BUSAVG(허브)이며 system lambda가 아님.")
