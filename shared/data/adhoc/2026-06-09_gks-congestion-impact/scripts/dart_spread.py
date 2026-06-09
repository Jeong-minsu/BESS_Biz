"""DART spread (DA-RT congestion-basis) attribution at GKS_BESS_RN for the 5 LIVE
POS constraints. REAL data only (gks_msf_raw.parquet = market_shift_factors @ GKS node).

Convention (project): spread = DA - RT.
  nodal MCC contribution of constraint k = -SHIFTFACTOR(k->GKS) * SHADOWPRICE(lambda_k) (per market).
  hourly spread(h) = MCC_DA(h) - MCC_RT(h).
    spread > 0 => DA congestion component richer => DA expensive => SHORT-favorable (short DA / long RT).
    spread < 0 => RT richer => RT expensive       => LONG-favorable.
  RT is 5-min -> hourly RT MCC = sum(5-min MCC in hour)/12 (missing intervals = 0) = time-weighted hour mean.
  Units: $/MWh-hour per 1 MW continuous position. Multiple contingencies on the same constraint name
  in the same interval are SUMMED (each is a distinct binding contributing to nodal MCC).

Scope: congestion-driven basis CHARACTERIZATION (congestion-analyst). NOT position sizing / win-rate /
bid construction (dart-virtual-trader). Signal-character only, no position recommendation.

Run:  python dart_spread.py            # compute + print + dump metrics JSON
      python dart_spread.py --write    # also inject section8_dart_spread + rewrite KR fields into datapacks
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

DERIVED = Path(__file__).resolve().parents[1] / "derived"
RAW = DERIVED / "gks_msf_raw.parquet"
TARGETS = ["HAINE__LA_PAL1_1", "421__A", "BLESSING_1382", "STPELM27_1", "WESTEX"]
EPS = 1e-9

CONVENTION = (
    "spread = DA - RT ; MCC_market = -SHIFTFACTOR x SHADOWPRICE ; hourly spread(h) = MCC_DA(h) - MCC_RT(h). "
    "spread>0 => DA expensive => SHORT-favorable (short DA / long RT) ; spread<0 => RT expensive => LONG-favorable. "
    "RT 5-min -> hourly = sum/12 (missing=0). Units $/MWh-hour per 1 MW continuous position."
)
CAVEATS_COMMON = [
    "이것은 congestion(=MCC) 컴포넌트의 DA-RT basis 특성화임 (congestion-analyst 영역). 실제 short/long 포지션 사이징·승률·손익비·입찰은 dart-virtual-trader 몫. 여기서 포지션 추천은 하지 않음 — 시그널 방향/타이밍 특성만.",
    "spread = MCC_DA - MCC_RT 만 반영 (energy/loss 컴포넌트·SCED 출력 deviation 제외). 실제 노드 DART spread는 system energy basis가 추가로 들어감.",
    "RT는 5분 -> 시간평균(sum/12, 미바인딩 5분=0)으로 DA hourly와 hour-join. RT λ source = market_shift_factors MARKET='RT' @ GKS pricenode (SCED resource-level cross-check 권장).",
    "Window = GKS_BESS_RN 노드 존재기간 2024-07-03..2026-06-08 (~23mo). 2025-onset 제약(421__A, STPELM27_1)은 full-window 분모가 현재 수준을 과소평가.",
    "month_hour_spread = 0(미바인딩) 시간 포함 기대 spread 기여($/MWh-h); short=양수, long=음수. 빈도×심도 혼합 신호임.",
]


def load() -> pd.DataFrame:
    df = pd.read_parquet(RAW)
    df["dt"] = pd.to_datetime(df["DATETIME"], format="%m/%d/%Y %H:%M:%S")
    df["hour"] = df["dt"].dt.floor("h")
    df["mcc"] = -df["SHIFTFACTOR"] * df["SHADOWPRICE"]
    return df


def per_constraint(df: pd.DataFrame, name: str) -> dict:
    sub = df[df["CONSTRAINTNAME"] == name]
    da = sub[sub["MARKET"] == "DA"]
    rt = sub[sub["MARKET"] == "RT"]
    mcc_da = da.groupby("hour")["mcc"].sum()
    mcc_rt = rt.groupby("hour")["mcc"].sum() / 12.0
    h = pd.DataFrame({"mcc_da": mcc_da, "mcc_rt": mcc_rt}).fillna(0.0)
    h["spread"] = h["mcc_da"] - h["mcc_rt"]

    cum_da = float(mcc_da.sum())
    cum_rt = float(rt["mcc"].sum() / 12.0)
    cum_spread = float(h["spread"].sum())
    da_abs = float(h["mcc_da"].abs().sum())
    rt_abs = float(h["mcc_rt"].abs().sum())

    active = h["spread"].abs() > EPS
    n_active = int(active.sum())
    short_m = h["spread"] > EPS
    long_m = h["spread"] < -EPS
    n_short, n_long = int(short_m.sum()), int(long_m.sum())
    gross_short = float(h.loc[short_m, "spread"].sum())
    gross_long = float(-h.loc[long_m, "spread"].sum())
    gross_tot = gross_short + gross_long
    minority_share = (min(gross_short, gross_long) / gross_tot) if gross_tot > 0 else 0.0

    net_lean = "mixed" if minority_share >= 0.35 else ("short" if cum_spread > 0 else "long")

    # DA vs RT dominance by contribution magnitude
    r = da_abs / (rt_abs + EPS)
    dom = "DA-dominant" if r >= 1.5 else ("RT-dominant" if r <= 1 / 1.5 else "balanced")

    # nuance: chronic DA-only lean vs RT-spike opposite lean
    da_only = h[(h["mcc_da"].abs() > EPS) & (h["mcc_rt"].abs() <= EPS)]
    rt_active = h[h["mcc_rt"].abs() > EPS]
    nuance = {
        "da_only_hours": int(len(da_only)),
        "da_only_cum_usd_per_mw": round(float(da_only["spread"].sum()), 1),
        "da_only_lean": "short" if da_only["spread"].sum() > 0 else "long",
    }
    if len(rt_active) >= 10:
        thr = rt_active["mcc_rt"].abs().quantile(0.9)
        spike = rt_active[rt_active["mcc_rt"].abs() >= thr]
        nuance.update({
            "rt_spike_def": "top-decile |MCC_RT| hours among RT-active hours",
            "rt_spike_hours": int(len(spike)),
            "rt_spike_pct_short": round(100 * (spike["spread"] > EPS).mean(), 1),
            "rt_spike_pct_long": round(100 * (spike["spread"] < -EPS).mean(), 1),
            "rt_spike_mean_spread": round(float(spike["spread"].mean()), 2),
            "rt_spike_net_lean": "short" if spike["spread"].sum() > 0 else "long",
            "worst_long_hour_spread": round(float(h["spread"].min()), 2),
            "max_short_hour_spread": round(float(h["spread"].max()), 2),
        })

    # month x hour signed mean spread (expected contribution incl. zero hours)
    full = pd.date_range(df["hour"].min(), df["hour"].max(), freq="h")
    g = pd.DataFrame({"spread": h["spread"].reindex(full).fillna(0.0).values}, index=full)
    g["m"], g["he"] = g.index.month, g.index.hour
    mh = g.groupby(["m", "he"])["spread"].mean().unstack("he").reindex(index=range(1, 13), columns=range(24))
    matrix = [[round(float(v), 3) if pd.notna(v) else 0.0 for v in mh.loc[m]] for m in range(1, 13)]

    return {
        "cum_da": round(cum_da, 1), "cum_rt": round(cum_rt, 1), "cum_spread": round(cum_spread, 1),
        "da_abs": round(da_abs, 1), "rt_abs": round(rt_abs, 1),
        "net_lean": net_lean, "minority_share": round(minority_share, 3),
        "da_dominant_or_rt": dom, "r_da_over_rt": round(r, 2),
        "n_active_hours": n_active,
        "pct_hours_short": round(100 * n_short / n_active, 1) if n_active else 0.0,
        "pct_hours_long": round(100 * n_long / n_active, 1) if n_active else 0.0,
        "mean_spread_when_active": round(float(h.loc[active, "spread"].mean()), 3) if n_active else 0.0,
        "gross_short_usd_per_mw": round(gross_short, 1), "gross_long_usd_per_mw": round(gross_long, 1),
        "nuance": nuance, "month_hour_spread": matrix,
    }


def main():
    df = load()
    print(f"data window: {df.dt.min()} -> {df.dt.max()}\n")
    out = {}
    for t in TARGETS:
        r = per_constraint(df, t)
        out[t] = r
        print(f"== {t}: cum_DA={r['cum_da']} cum_RT={r['cum_rt']} cum_spread={r['cum_spread']} "
              f"net={r['net_lean']}(min {r['minority_share']}) {r['da_dominant_or_rt']}(r={r['r_da_over_rt']}) "
              f"short {r['pct_hours_short']}%/long {r['pct_hours_long']}% mean_act={r['mean_spread_when_active']} "
              f"gS={r['gross_short_usd_per_mw']} gL={r['gross_long_usd_per_mw']}")
        n = r["nuance"]
        print(f"     nuance: DA-only {n['da_only_hours']}h cum={n['da_only_cum_usd_per_mw']}({n['da_only_lean']}); "
              f"RT-spike {n.get('rt_spike_hours')}h short {n.get('rt_spike_pct_short')}%/long {n.get('rt_spike_pct_long')}% "
              f"net {n.get('rt_spike_net_lean')} worstLong={n.get('worst_long_hour_spread')} maxShort={n.get('max_short_hour_spread')}")
    (DERIVED / "dart_spread_metrics.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nwrote", DERIVED / "dart_spread_metrics.json")
    if "--write" in sys.argv:
        from dart_spread_narratives import update_datapacks
        update_datapacks(out, DERIVED, CONVENTION, CAVEATS_COMMON)


if __name__ == "__main__":
    main()
