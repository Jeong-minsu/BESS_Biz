"""04 — 연도별 최적화율 = Price(TB2 캡처율) x Quantity(가동률) 집계 + 교차검증."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ADHOC = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[5]
DERIVED = ADHOC / "derived"
REF = ROOT / "shared/data/adhoc/2026-05-11_yoy-comparison/derived/daily_metrics_combined.parquet"
INCIDENT = ("2026-03-24", "2026-04-13")   # 사이버 이슈 + 변전소 화재 정지


# TB2 벤치마크 자체의 용량 커밋: 4시간(방전 2h + 충전 2h) x 100MW / (100MW x 24h)
Q_REF = 4.0 / 24.0


def agg(d: pd.DataFrame, qcol="quantity") -> pd.Series:
    tb = d["tb2_rev"].sum()
    act = d["actual_rev"].sum()
    q = d[qcol].mean()
    tb_eff = (d["tb2_rev"] * d[qcol]).sum()
    return pd.Series({
        "days": len(d),
        "actual_rev_$": act,
        "energy_$": d["energy_rev"].sum(),
        "as_$": d["as_rev"].sum(),
        "dart_$": d["dart_rev"].sum(),
        "tb2_rev_$": tb,
        "opt_rate": act / tb if tb else np.nan,
        "quantity": q,
        "price_capture": act / tb_eff if tb_eff else np.nan,
        "tb2_spread_$/MWh": d["tb2_spread"].mean(),
        "discharge_MWh_d": d["discharge_mwh"].mean(),
        "as_MW_avg": d["as_awarded_mwh"].mean() / 24,
        "rev_$/day": act / len(d),
        # TB2 기준(=1.0)으로 정규화: opt = price_rel x qty_rel
        "qty_rel": q / Q_REF,
        "price_rel": (act / tb) / (q / Q_REF) if tb and q else np.nan,
    })


def show(t: pd.DataFrame, title: str):
    t = t.copy()
    t["check_PxQ"] = t["price_rel"] * t["qty_rel"]
    print(f"\n=== {title} ===")
    print(t.to_string(float_format=lambda x: f"{x:,.3f}"))


def main():
    d = pd.read_parquet(DERIVED / "gks_daily_opt.parquet")
    d["date"] = pd.to_datetime(d["date"])
    d = d[d["tb2_rev"] > 0]
    pd.set_option("display.width", 250)

    print("커버리지:")
    print(d.groupby("year").agg(days=("date", "size"), first=("date", "min"),
                                last=("date", "max")).to_string())
    print(f"\nquantity > 1 인 날: {(d['quantity'] > 1).sum()}일 (max {d['quantity'].max():.3f})")

    show(d.groupby("year").apply(agg, include_groups=False), "연도별 (에너지+AS)")

    inc = d["date"].between(*INCIDENT)
    show(d[~inc].groupby("year").apply(agg, include_groups=False),
         "연도별 — 2026 정지구간(3/24~4/13) 제외")

    # DART 포함 버전
    d2 = d.copy(); d2["actual_rev"] = d2["actual_rev"] + d2["dart_rev"]
    show(d2.groupby("year").apply(agg, include_groups=False), "연도별 (에너지+AS+DART virtual)")

    show(d.groupby("year").apply(agg, "quantity_energy", include_groups=False),
         "연도별 — Quantity를 물리 충방전만으로 정의 (AS 커밋 제외)")

    m = d.groupby(d["date"].dt.to_period("M")).apply(agg, include_groups=False)
    m["check_PxQ"] = m["price_rel"] * m["qty_rel"]
    print("\n=== 월별 ===")
    print(m[["days", "actual_rev_$", "energy_$", "as_$", "tb2_rev_$", "opt_rate",
             "quantity", "qty_rel", "price_rel", "tb2_spread_$/MWh"]]
          .to_string(float_format=lambda x: f"{x:,.3f}"))

    # ---- 교차검증: 기존 yoy 산출물(2/14~4/30) ----
    if REF.exists():
        r = pd.read_parquet(REF)
        r["date"] = pd.to_datetime(r["date"])
        j = d.merge(r[["date", "Energy_Rev_$", "Discharge_MWh", "Charge_MWh", "TB2_RT_$"]],
                    on="date", how="inner")
        if len(j):
            print(f"\n=== 교차검증 vs 2026-05-11 yoy 산출물 ({len(j)}일 겹침) ===")
            for a, b in [("energy_rev", "Energy_Rev_$"), ("discharge_mwh", "Discharge_MWh"),
                         ("charge_mwh", "Charge_MWh"), ("tb2_spread", "TB2_RT_$")]:
                num = (j[a] - j[b]).abs().sum()
                den = j[b].abs().sum()
                print(f"  {a:16s} vs {b:16s}  상대오차 {num/den*100 if den else np.nan:6.2f}%  "
                      f"(mine {j[a].sum():,.0f} / ref {j[b].sum():,.0f})")


if __name__ == "__main__":
    main()
