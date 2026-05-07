"""
Compare two energy-virtual formulas on the cached 2026-01-01..2026-05-05 data:

  A) net:     |DA_net - RT_net|     where DA_net=DA_Sales-DA_Purchases,
                                          RT_net=RT_Gen-RT_Cons
  B) per-leg: |DA_Sales - RT_Gen| + |DA_Purchases - RT_Cons|

Reads the per-day JSON already written under shared/data/pnl/gks/hourly/.
"""
from __future__ import annotations
import json, sys
from datetime import date, timedelta
from pathlib import Path
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PNL_DIR      = PROJECT_ROOT / "shared" / "data" / "pnl" / "gks" / "hourly"

START = date(2026, 1, 1)
END   = date(2026, 5, 5)


def daterange(s, e):
    d = s
    while d <= e:
        yield d
        d += timedelta(days=1)


def hourly(d: date):
    p = PNL_DIR / f"{d.isoformat()}_energy_as_detail.json"
    if not p.exists():
        return None
    rows = json.loads(p.read_text(encoding="utf-8"))
    by = defaultdict(dict)
    for r in rows:
        v = r.get("value")
        if isinstance(v, (int, float)):
            by[r["datapoint"]][r["interval_start_utc"]] = v
    return by


def daily_two(by) -> tuple[float, float, float]:
    hours = sorted({h for dp in by.values() for h in dp.keys()})
    g = lambda dp, h: float(by.get(dp, {}).get(h, 0.0))
    A = B = 0.0
    # also track per-leg components for diagnostics
    leg_sales = leg_pur = 0.0
    for h in hours:
        ds = g("DA_Sales_Qty", h);     dp = g("DA_Purchases_Qty", h)
        rg = g("RT_Generation_Qty", h); rc = g("RT_Consumption_Qty", h)
        A += abs((ds - dp) - (rg - rc))
        s_leg = abs(ds - rg)
        p_leg = abs(dp - rc)
        B += s_leg + p_leg
        leg_sales += s_leg
        leg_pur   += p_leg
    return A, B, leg_sales + leg_pur and (leg_sales, leg_pur)  # not used


def main():
    rows = []
    sumA = sumB = 0.0
    n = 0
    for d in daterange(START, END):
        by = hourly(d)
        if by is None:
            continue
        A, B, _ = daily_two(by)
        rows.append((d.isoformat(), A, B, B - A))
        sumA += A; sumB += B; n += 1

    print(f"{'date':<12} {'A net':>10} {'B per-leg':>12} {'B-A':>9}")
    print("-" * 46)
    # show top 10 worst-divergence days
    rows_sorted = sorted(rows, key=lambda r: r[3], reverse=True)
    print("Top 10 days where B exceeds A the most:")
    for r in rows_sorted[:10]:
        print(f"{r[0]:<12} {r[1]:>10.1f} {r[2]:>12.1f} {r[3]:>9.1f}")
    print()
    print(f"Aggregate over {n} days:")
    print(f"  Sum A (net):     {sumA:>10.1f} MWh   →  daily avg {sumA/n:>7.1f}")
    print(f"  Sum B (per-leg): {sumB:>10.1f} MWh   →  daily avg {sumB/n:>7.1f}")
    print(f"  B - A:           {sumB - sumA:>10.1f} MWh   →  daily avg {(sumB-sumA)/n:>7.1f}")
    pct = (sumB - sumA) / sumA * 100 if sumA else 0
    print(f"  Relative gap:    {pct:>10.2f}%   (per-leg vs net)")


if __name__ == "__main__":
    main()
