"""10 - DART 제외, AS를 P/Q에 분배한 단일 P x Q 분해.

분자 = 물리에너지(Σ net MWh x RTSPP) + AS(순: DA 낙찰 - RT 되사기)   ← DART virtual 제외
분모 = TB2 = TB2스프레드 x 200MWh

Q(가동률) : 에너지와 AS를 하나의 '커밋 용량시간'으로 합산
    Q = Σ_h max(|물리 net MW|, AS 낙찰 MW) / (100MW x 24h)
    TB2 벤치마크 자체의 커밋은 4h/24h = 16.7% -> Q_rel = Q / 16.7%
P(타점)  : 커밋 용량시간 1단위당 수익, TB2 = 100%
    P = opt / Q_rel        (=> opt = P x Q_rel, 항등식)

참고로 MWh 물량 기준 변형도 같이 낸다:
    Q_mwh = (방전MWh + AS낙찰MWh) / 200MWh ,  P_mwh = opt / Q_mwh
"""
from pathlib import Path
import numpy as np, pandas as pd

D = Path(__file__).resolve().parents[1] / "derived"
Q_REF = 4.0 / 24.0
WINS = [("2025 (3/1~12/31)", "2025-03-01", "2025-12-31", False),
        ("2025 3~7월 (정상)", "2025-03-01", "2025-07-31", False),
        ("2025 8~12월 (디레이트)", "2025-08-01", "2025-12-31", False),
        ("2026 (1/1~9/16)", "2026-01-01", "2026-09-16", False),
        ("2026 정지구간 제외", "2026-01-01", "2026-09-16", True)]

d = pd.read_parquet(D / "gks_daily_opt_v2.parquet")
d["date"] = pd.to_datetime(d["date"])
d = d[(d["tb2_rev"] > 0) & d["gsd_rev"].notna()]


def row(lbl, a, b, drop_inc):
    x = d[d["date"].between(a, b)]
    if drop_inc:
        x = x[~x["date"].between("2026-03-24", "2026-04-13")]
    n = len(x)
    tb2 = x["tb2_rev"].sum()
    energy = x["energy_rev"].sum()                       # 물리 에너지 (RT 배치대가 포함)
    as_net = x["gsd_as_da"].sum() + x["gsd_as_rt"].sum()  # AS 순 (되사기 차감)
    rev = energy + as_net
    opt = rev / tb2
    Q = x["quantity"].mean()
    Q_rel = Q / Q_REF
    dis = x["discharge_mwh"].sum()
    Q_mwh = (dis + x["as_awarded_mwh"].sum()) / 200.0 / n
    return pd.Series({
        "days": n, "수익$": rev, "에너지$": energy, "AS순$": as_net, "TB2$": tb2,
        "opt": opt,
        "Q 가동률": Q, "Q 배수(TB2=1)": Q_rel, "P 타점(TB2=1)": opt / Q_rel,
        "PxQ": (opt / Q_rel) * Q_rel,
        "Q_mwh 물량배수": Q_mwh, "P_mwh 타점": opt / Q_mwh,
        "사이클/일": dis / 200.0 / n, "AS낙찰MW": x["as_awarded_mwh"].sum() / 24 / n,
    }, name=lbl)


pd.set_option("display.width", 300)
t = pd.DataFrame([row(*w) for w in WINS])
print("=== DART 제외 · AS 포함 단일 P x Q ===")
print(t.to_string(float_format=lambda v: f"{v:,.3f}"))
print("")
print("=== 월별 ===")
m = pd.DataFrame([row(str(p), str(p.start_time.date()), str(p.end_time.date()), False)
                  for p in sorted(d["date"].dt.to_period("M").unique())])
print(m[["days", "수익$", "TB2$", "opt", "Q 가동률", "Q 배수(TB2=1)", "P 타점(TB2=1)",
         "사이클/일", "AS낙찰MW"]].to_string(float_format=lambda v: f"{v:,.3f}"))
