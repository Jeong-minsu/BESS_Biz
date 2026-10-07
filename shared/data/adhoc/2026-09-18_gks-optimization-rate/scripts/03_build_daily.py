"""03 — GKS 일별 최적화율 분해 (Price x Quantity).

opt_rate = actual_rev / TB2_rev = price_capture x quantity
  quantity_d  = Σ_h max(|physical net MW|, Σ AS awarded MW) / (100MW x 24h)
  TB2_rev_d   = (top2 RTSPP 평균 − bottom2 RTSPP 평균) x 200MWh   (100MW/2h, 1 cycle/day)
  actual_rev  = 물리 에너지 수익(Σ net MWh x RTSPP) + AS 수익(DA AS + RT AS imbalance)
  price_capture = actual_rev / (TB2_rev x quantity)

입력: shared/data/pnl/gks/hourly/<date>_battery_settlement.json (PTP 결제 실적)
      derived/as_dam_mcpc_hourly_2025_2026.parquet (ERCOT DAM MCPC, AS award MW 환산용)
출력: derived/gks_daily_opt.csv / .parquet
"""
from __future__ import annotations
import json, sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ADHOC = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[5]
PTP_DIR = ROOT / "shared" / "data" / "pnl" / "gks" / "hourly"
DERIVED = ADHOC / "derived"

CAP_MW = 100.0            # GKS nameplate
DUR_H = 2.0               # 200 MWh / 100 MW
RTCB = date(2025, 12, 5)
EL_PRE = "Great Kiskadee Storage, LLC Gen"
EL_POST = "Great Kiskadee Storage - ESR"

AS_AMT = {"RRS": "DA_RRS_Amt", "ECRS": "DA_ECRS_Amt", "NSPIN": "DA_NS_Amt",
          "REGUP": "DA_Reg_Up_Amt", "REGDN": "DA_Reg_Down_Amt"}
AS_QTY = {"RRS": "Gen_RRS_Qty", "ECRS": "Gen_ECRS_Qty", "NSPIN": "Gen_NS_Qty"}


def load_mcpc() -> pd.DataFrame:
    f = DERIVED / "as_dam_mcpc_hourly_2025_2026.parquet"
    df = pd.read_parquet(f)
    df["date"] = pd.to_datetime(df["deliveryDate"]).dt.date
    df["he"] = df["hourEnding"].astype(str).str.split(":").str[0].astype(int)
    df["MCPC"] = pd.to_numeric(df["MCPC"], errors="coerce")
    w = df.pivot_table(index=["date", "he"], columns="ancillaryType",
                       values="MCPC", aggfunc="first")
    w.columns = [f"MCPC_{c.upper()}" for c in w.columns]
    return w.reset_index()


def hourly_frame(f: Path) -> pd.DataFrame:
    arr = json.loads(f.read_text(encoding="utf-8"))
    if not arr:
        return pd.DataFrame()
    df = pd.DataFrame(arr)
    d = date.fromisoformat(f.name[:10])
    el = EL_PRE if d < RTCB else EL_POST
    sub = df[df["element"] == el]
    if sub.empty or "RT_Generation_Qty" not in set(sub["datapoint"]):
        alt = df[df["element"] == (EL_POST if el == EL_PRE else EL_PRE)]
        if "RT_Generation_Qty" in set(alt["datapoint"]):
            sub = alt
    if sub.empty:
        return pd.DataFrame()
    sub = sub.copy()
    ts = pd.to_datetime(sub["interval_start_utc"], utc=True).dt.tz_convert("America/Chicago")
    sub["date"] = ts.dt.date
    sub["he"] = ts.dt.hour + 1
    sub["value"] = pd.to_numeric(sub["value"], errors="coerce")
    w = sub.pivot_table(index=["date", "he"], columns="datapoint",
                        values="value", aggfunc="sum").reset_index()
    return w


def main():
    mcpc = load_mcpc()
    files = sorted(PTP_DIR.glob("*_battery_settlement.json"))
    print(f"{len(files)} PTP day files")
    frames = [hourly_frame(f) for f in files]
    h = pd.concat([x for x in frames if not x.empty], ignore_index=True)
    h = h.merge(mcpc, on=["date", "he"], how="left")
    for c in ["RT_Generation_Qty", "RT_Consumption_Qty", "RTSPP_Avg", "DASPP",
              "DA_Energy_Amt", "RT_Energy_Amt", "BP_Dev_Amt",
              "RT_Ancillary_Imbalance_Amt", "RT_Reliability_Deployment_Imbalance_Amt",
              "DA_Sales_Qty", "DA_Purchases_Qty",
              *AS_AMT.values(), *AS_QTY.values()]:
        if c not in h.columns:
            h[c] = np.nan
        h[c] = pd.to_numeric(h[c], errors="coerce")

    # AS 시간별 낙찰 MW: 수량 데이터포인트 우선, 없으면 DA 금액 ÷ MCPC
    as_mw = pd.Series(0.0, index=h.index)
    for p, amt_col in AS_AMT.items():
        q_col = AS_QTY.get(p)
        q = h[q_col] if q_col and h[q_col].notna().any() else pd.Series(np.nan, index=h.index)
        price = h.get(f"MCPC_{p}", pd.Series(np.nan, index=h.index)).replace(0, np.nan)
        derived_q = (h[amt_col] / price)
        q = q.fillna(derived_q).fillna(0.0).clip(lower=0)
        h[f"as_mw_{p}"] = q
        as_mw = as_mw + q
    h["as_mw"] = as_mw

    h["phys_net_mw"] = h["RT_Generation_Qty"].fillna(0) - h["RT_Consumption_Qty"].fillna(0)
    h["commit_mw"] = np.maximum(h["phys_net_mw"].abs(), h["as_mw"])
    # RT Reliability Deployment Imbalance는 AS 배치에 따른 에너지 인도 대가 → 에너지로 분류
    # (2026-05-11 yoy 분석의 사용자 확정 분류와 동일)
    h["energy_rev"] = (h["phys_net_mw"] * h["RTSPP_Avg"]
                       + h["RT_Reliability_Deployment_Imbalance_Amt"].fillna(0))
    h["as_rev"] = (h[list(AS_AMT.values())].fillna(0).sum(axis=1)
                   + h["RT_Ancillary_Imbalance_Amt"].fillna(0))

    rows = []
    for d, s in h.groupby("date"):
        if len(s) < 23 or s["RTSPP_Avg"].notna().sum() < 23:
            continue
        rt = s["RTSPP_Avg"].astype(float)
        da = s["DASPP"].astype(float)
        tb2_spread = rt.nlargest(2).mean() - rt.nsmallest(2).mean()
        tb2_rev = tb2_spread * CAP_MW * DUR_H
        energy = float(s["energy_rev"].sum())
        as_rev = float(s["as_rev"].sum())
        ptp_da = float(s["DA_Energy_Amt"].fillna(0).sum())
        ptp_rt = float(s["RT_Energy_Amt"].fillna(0).sum())
        rows.append({
            "date": d,
            "year": d.year,
            "hours": len(s),
            "energy_rev": energy,
            "as_rev": as_rev,
            "dart_rev": ptp_da + ptp_rt - float((s["phys_net_mw"] * s["RTSPP_Avg"]).sum()),
            "bp_dev": float(s["BP_Dev_Amt"].fillna(0).sum()),
            "actual_rev": energy + as_rev,
            "tb2_spread": tb2_spread,
            "tb2_rev": tb2_rev,
            "tb2_da_spread": da.nlargest(2).mean() - da.nsmallest(2).mean(),
            "commit_mwh": float(s["commit_mw"].sum()),
            "energy_mwh_abs": float(s["phys_net_mw"].abs().sum()),
            "as_awarded_mwh": float(s["as_mw"].sum()),
            "discharge_rev": float((s["RT_Generation_Qty"].fillna(0) * s["RTSPP_Avg"]).sum()),
            "charge_cost": float((s["RT_Consumption_Qty"].fillna(0) * s["RTSPP_Avg"]).sum()),
            "discharge_mwh": float(s["RT_Generation_Qty"].fillna(0).sum()),
            "charge_mwh": float(s["RT_Consumption_Qty"].fillna(0).sum()),
            **{f"as_mwh_{p}": float(s[f"as_mw_{p}"].sum()) for p in AS_AMT},
        })
    d = pd.DataFrame(rows).sort_values("date")
    d["quantity"] = d["commit_mwh"] / (CAP_MW * d["hours"])
    d["quantity_energy"] = d["energy_mwh_abs"] / (CAP_MW * d["hours"])
    DERIVED.mkdir(parents=True, exist_ok=True)
    d.to_csv(DERIVED / "gks_daily_opt.csv", index=False)
    d.to_parquet(DERIVED / "gks_daily_opt.parquet", index=False)
    print(f"wrote {len(d)} days  {d.date.min()} .. {d.date.max()}")
    print(d.groupby("year").agg(days=("date", "size"), rev=("actual_rev", "sum"),
                                tb=("tb2_rev", "sum"), q=("quantity", "mean")).to_string())


if __name__ == "__main__":
    main()
