"""Robustness of the 2026 out-of-sample DART result.
For each rule family selected on 2023-12..2025 (dart3y_results.json):
  - which cells were chosen (hour / season / tightness, side)
  - 2026 PnL by month, and with the best 3 / worst 3 days removed (spike dependence)
  - max drawdown, worst 1% hour loss
  - cross-check Jun-Sep 2026 on REAL RVN_RN prices instead of the proxy
Real data only.
"""
import json
from pathlib import Path
import numpy as np, pandas as pd

BASE = Path(__file__).resolve().parents[1]; D = BASE / "derived"
res = json.load(open(D / "dart3y_results.json"))
h = pd.read_parquet(D / "dart3y_hourly_panel.parquet")
BLOCKS = {"새벽 1–6시": range(1, 7), "아침 7–11시": range(7, 12), "낮 12–16시": range(12, 17),
          "저녁 17–21시": range(17, 22), "밤 22–24시": range(22, 25)}
h["block"] = h.he.map({hh: b for b, rr in BLOCKS.items() for hh in rr})
h["tight"] = h["tight"].astype(str)
h["he_s"] = h.he.astype(str)
KEYS = {"① 시간대만 (24칸)": ["he_s"], "② 계절 × 시간대 (96칸)": ["season", "he_s"],
        "③ 타이트함 × 시간대 (72칸)": ["tight", "he_s"], "④ 계절 × 타이트함 × 구간 (60칸)": ["season", "tight", "block"]}
test = h[h.day >= "2026-01-01"].copy()

out = {}
for fam, keys in KEYS.items():
    cells = res["E_oos"][fam]["cells"]
    for col in ("pnl", "pnl_real"):
        test[col] = np.nan
    for c in cells:
        m = np.ones(len(test), bool)
        for k, v in zip(keys, c["cell"]):
            m &= (test[k].astype(str) == str(v)).values
        sgn = 1 if c["side"] == "short" else -1
        test.loc[m, "pnl"] = sgn * test.loc[m, "spread"]
        test.loc[m, "pnl_real"] = sgn * test.loc[m, "real_spread"]
    p = test.dropna(subset=["pnl"])
    daily = p.groupby("day").pnl.sum().sort_values()
    cum = daily.sort_index().cumsum()
    dd = float((cum - cum.cummax()).min())
    ex = daily.iloc[3:-3]
    monthly = p.groupby(p.day.dt.month).pnl.sum()
    real = p[(p.day >= "2026-06-04") & p.pnl_real.notna()]
    prox_same = real.pnl.sum(); real_sum = real.pnl_real.sum()
    out[fam] = {
        "cells": [(" / ".join(map(str, c["cell"])), "SHORT" if c["side"] == "short" else "LONG", round(c["train_ev"], 2), round(c["t"], 2)) for c in cells],
        "total": float(daily.sum()), "ev": float(p.pnl.mean()), "hours": int(len(p)),
        "total_ex_best3_worst3": float(ex.sum()), "ev_ex_best3_worst3": float(ex.sum() / (len(p) * len(ex) / len(daily))),
        "best3_days": [(str(d.date()), round(v, 0)) for d, v in daily.iloc[-3:][::-1].items()],
        "worst3_days": [(str(d.date()), round(v, 0)) for d, v in daily.iloc[:3].items()],
        "max_drawdown": dd, "worst1pct_hour": float(-np.percentile(p.pnl, 1)),
        "monthly": {int(k): round(float(v), 0) for k, v in monthly.items()},
        "months_positive": f"{int((monthly > 0).sum())}/{len(monthly)}",
        "real_check_jun_sep": {"hours": int(len(real)), "proxy_total": float(prox_same), "real_total": float(real_sum),
                               "real_ev": float(real.pnl_real.mean()) if len(real) else None,
                               "real_hit": float((real.pnl_real > 0).mean()) if len(real) else None},
    }
    o = out[fam]
    print(f"\n===== {fam} =====")
    print("  선택된 칸 (학습 EV, t):", "; ".join(f"{a} {s} ({e:+.2f}, t{t:+.1f})" for a, s, e, t in o["cells"]))
    print(f"  2026 합계 ${o['total']:+,.0f}/MW  EV {o['ev']:+.2f}  | 최고3일·최악3일 제외 ${o['total_ex_best3_worst3']:+,.0f}")
    print(f"  최고 3일 {o['best3_days']}  최악 3일 {o['worst3_days']}")
    print(f"  월별 {o['monthly']}  흑자월 {o['months_positive']}  최대낙폭 ${dd:,.0f}  최악1% 시간손실 ${o['worst1pct_hour']:.0f}")
    rc = o["real_check_jun_sep"]
    if rc["hours"]:
        print(f"  실측 Raven 교차검증(6/4~9/13, {rc['hours']}h): proxy ${rc['proxy_total']:+,.0f} vs 실측 ${rc['real_total']:+,.0f}, 실측 EV {rc['real_ev']:+.2f}, 적중 {rc['real_hit']:.1%}")

json.dump(out, open(D / "dart3y_robustness.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("\nwrote dart3y_robustness.json")
