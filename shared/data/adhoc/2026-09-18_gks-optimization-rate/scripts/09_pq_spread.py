"""09 - opt를 P(타점 정확도) x Q(가동률=사이클)로 표현.

물리 에너지 수익 = WAP_dis x 방전MWh - WAP_chg x 충전MWh
              = 방전MWh x (WAP_dis - WAP_chg x 충방전비)      <- 항등식
TB2            = TB2스프레드 x 200MWh
=> opt_energy = [ (WAP_dis - WAP_chg x 충방전비) / TB2스프레드 ] x [ 방전MWh / 200 ] = P x Q
   P = 실효 스프레드 캡처(충전 과소비 반영), Q = 사이클/일
   (참고용 P_naive = (WAP_dis - WAP_chg)/TB2스프레드 — 충방전비를 무시한 '순수 타점')
전체 opt = opt_energy + opt_DART + opt_AS(순, 되사기 차감)
"""
from pathlib import Path
import numpy as np, pandas as pd

D = Path(__file__).resolve().parents[1] / "derived"
WINS = [("2025 (3/1~12/31)", "2025-03-01", "2025-12-31"),
        ("2025 3~7월 (정상)", "2025-03-01", "2025-07-31"),
        ("2025 8~12월 (디레이트)", "2025-08-01", "2025-12-31"),
        ("2026 (1/1~9/16)", "2026-01-01", "2026-09-16"),
        ("2026 정지구간 제외", "2026-01-01", "2026-09-16")]

d = pd.read_parquet(D / "gks_daily_opt_v2.parquet")
d["date"] = pd.to_datetime(d["date"])
d = d[(d["tb2_rev"] > 0) & d["gsd_rev"].notna()]


def row(lbl, a, b, drop_incident=False):
    x = d[d["date"].between(a, b)]
    if drop_incident:
        x = x[~x["date"].between("2026-03-24", "2026-04-13")]
    n = len(x)
    dis, chg = x["discharge_mwh"].sum(), x["charge_mwh"].sum()
    wap_d = x["discharge_rev"].sum() / dis
    wap_c = x["charge_cost"].sum() / chg
    tb2 = x["tb2_rev"].sum()
    tb2_sp = (x["tb2_rev"] / 200.0).mean()
    ratio = chg / dis
    Q = dis / 200.0 / n
    P = (wap_d - wap_c * ratio) / tb2_sp
    P_naive = (wap_d - wap_c) / tb2_sp
    e_phys = x["energy_rev"].sum()
    as_net = x["gsd_as_da"].sum() + x["gsd_as_rt"].sum()
    dart = x["gsd_rev"].sum() - e_phys - as_net
    return pd.Series({
        "days": n,
        "P 타점(실효)": P, "P 타점(단순)": P_naive, "Q 사이클/일": Q,
        "P x Q = 에너지opt": P * Q,
        "에너지opt(실측)": e_phys / tb2,
        "+ AS(순)opt": as_net / tb2,
        "+ DART·기타opt": dart / tb2,
        "= 전체 opt": x["gsd_rev"].sum() / tb2,
        "방전WAP": wap_d, "충전WAP": wap_c, "충방전비": ratio, "TB2스프레드": tb2_sp,
    }, name=lbl)


t = pd.DataFrame([row(l, a, b, l.endswith("제외")) for l, a, b in WINS])
pd.set_option("display.width", 300)
print(t.to_string(float_format=lambda v: f"{v:,.3f}"))
print("")
print("=== 월별 (P x Q = 에너지 opt) ===")
m = pd.DataFrame([row(str(p), str(p.start_time.date()), str(p.end_time.date()))
                  for p in sorted(d["date"].dt.to_period("M").unique())])
print(m[["days", "P 타점(실효)", "Q 사이클/일", "P x Q = 에너지opt", "+ AS(순)opt",
         "+ DART·기타opt", "= 전체 opt", "TB2스프레드"]]
      .to_string(float_format=lambda v: f"{v:,.3f}"))
