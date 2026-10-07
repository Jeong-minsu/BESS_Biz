"""14 - 연도별 Top10 (최적화율) + GKS 비교표 출력."""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import importlib.util
spec = importlib.util.spec_from_file_location("m13", HERE / "13_fleet_metrics.py")
m13 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m13)

DERIVED = HERE.parent / "derived"
# pre-RTC+B(2025-12-04 이전)는 시장 로직이 달라 제외 — post-RTC+B 구간만 집계
PERIODS = [("RTC+B 전체 (2025-12-05~2026-07-23)", "2025-12-05", "2026-07-31", 150),
           ("2026 (1/1~7/23)", "2026-01-01", "2026-07-31", 120)]
COLS = ["rank", "resource", "sp", "mw", "dur", "days", "opt", "opt_energy", "opt_as",
        "P_capture", "Q_cycles", "PxQ", "util_mw", "rev", "energy_rev", "as_rev", "tb"]


def fmt(v):
    return f"{v:,.3f}"


out = {}
for label, a, b, mind in PERIODS:
    tag = "2026"
    res = m13.build(tag, pd.Timestamp(a), pd.Timestamp(b))
    if res is None:
        print(f"{label}: 데이터 없음"); continue
    d, prof = res
    s = m13.summarize(d, prof, label, mind)
    # 용량/duration 추정 오류로 분모가 붕괴한 자원 제외 (물리적으로 불가능한 사이클)
    bad = s["Q_cycles"] > 2.0
    if bad.any():
        print(f"[{label}] 분모 이상치 제외: " +
              ", ".join(f"{r.resource}({r.Q_cycles:.1f}사이클, dur {r.dur:.2f}h)"
                        for r in s[bad].itertuples()))
    s = s[~bad].sort_values("opt", ascending=False).reset_index(drop=True)
    s["rank"] = s.index + 1
    out[label] = s
    gk = s[s["resource"].isin(m13.GKS)]
    print(f"\n{'='*130}\n[{label}]  대상 {len(s)}개 자원 (>= {m13.MIN_MW}MW, >= {mind}일)")
    print("--- 최적화율 Top 10 ---")
    print(s.head(10)[COLS].to_string(index=False, float_format=fmt))
    print("--- GKS ---")
    print(gk[COLS].to_string(index=False, float_format=fmt))
    print(f"--- 플릿 중앙값 --- opt {s['opt'].median():.3f} | P {s['P_capture'].median():.3f} "
          f"| Q {s['Q_cycles'].median():.3f} | opt_energy {s['opt_energy'].median():.3f} "
          f"| opt_as {s['opt_as'].median():.3f}")
    if len(gk):
        r = int(gk['rank'].iloc[0])
        print(f"--- GKS 순위: {r}/{len(s)} (상위 {r/len(s)*100:.0f}%) ---")

if out:
    pd.concat(out.values()).to_csv(DERIVED / "fleet_opt_by_resource.csv", index=False)
    print(f"\nwrote {DERIVED/'fleet_opt_by_resource.csv'}")
