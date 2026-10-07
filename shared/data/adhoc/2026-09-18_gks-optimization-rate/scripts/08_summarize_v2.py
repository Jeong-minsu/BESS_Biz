"""08 - 최종 집계. 분자 = ERCOT 정산명세(GSD), 분모 = TB2(100MW/2h, 노드 RTSPP).

집계구간: 2025 = COD 이후 3/1~12/31, 2026 = 1/1~9/16
opt = 정산수익 / TB2 = Price x Quantity
  Quantity = Σ_h max(|물리 net MW|, DA AS 낙찰 MW) / (100MW x 24h)
  TB2 벤치마크 자체의 가동률은 4h/24h = 16.7% -> qty_rel = Quantity / 16.7%, price_rel = opt / qty_rel
"""
from pathlib import Path
import numpy as np, pandas as pd

D = Path(__file__).resolve().parents[1] / "derived"
W25 = ("2025-03-01", "2025-12-31")
W26 = ("2026-01-01", "2026-09-16")
INCIDENT = ("2026-03-24", "2026-04-13")
Q_REF = 4.0 / 24.0

d = pd.read_parquet(D / "gks_daily_opt_v2.parquet")
d["date"] = pd.to_datetime(d["date"])
d = d[(d["tb2_rev"] > 0) & d["gsd_rev"].notna()]
d["win"] = np.where(d["date"].between(*W25), "2025 (3/1~12/31)",
            np.where(d["date"].between(*W26), "2026 (1/1~9/16)", None))


def agg(x, qcol="quantity", rev="gsd_rev"):
    tb, act, q = x["tb2_rev"].sum(), x[rev].sum(), x[qcol].mean()
    dis, chg = x["discharge_mwh"].sum(), x["charge_mwh"].sum()
    wap_d = x["discharge_rev"].sum() / dis if dis else np.nan
    wap_c = x["charge_cost"].sum() / chg if chg else np.nan
    return pd.Series({
        "days": len(x), "rev_$": act, "rev_$/day": act / len(x),
        "energy_$": x["gsd_energy"].sum(), "as_da_$": x["gsd_as_da"].sum(),
        "as_rt_$": x["gsd_as_rt"].sum(), "dev_$": x["gsd_dev"].sum(),
        "tb2_$": tb, "opt_rate": act / tb,
        "quantity": q, "qty_rel": q / Q_REF, "price_rel": (act / tb) / (q / Q_REF),
        "cycles/day": dis / 200.0 / len(x),
        "spread_capture": (wap_d - wap_c) / (x["tb2_rev"] / 200.0).mean(),
        "tb2_spread": x["tb2_spread"].mean(),
        "as_MW_avg": x["as_awarded_mwh"].sum() / 24 / len(x),
    })


pd.set_option("display.width", 260)
fmt = lambda v: f"{v:,.3f}"
print("=== 연도별 (분자 = ERCOT 정산명세) ===")
print(d.dropna(subset=["win"]).groupby("win").apply(agg, include_groups=False).to_string(float_format=fmt))
print("")
print("=== 2026 정지구간(3/24~4/13) 제외 ===")
x = d[~d["date"].between(*INCIDENT)].dropna(subset=["win"])
print(x.groupby("win").apply(agg, include_groups=False).to_string(float_format=fmt))
print("")
print("=== 월별 ===")
m = d.groupby(d["date"].dt.to_period("M")).apply(agg, include_groups=False)
print(m[["days", "rev_$", "energy_$", "as_da_$", "as_rt_$", "tb2_$", "opt_rate",
         "quantity", "qty_rel", "price_rel", "cycles/day", "spread_capture",
         "tb2_spread"]].to_string(float_format=fmt))
