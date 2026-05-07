"""
Ad-hoc: GKS_BESS_RN daily virtual exposure, 2026-01-01 .. 2026-05-05.

"Virtual" = volume committed in DA but not physically delivered/consumed in RT
            (financially closed at RT price).

Energy virtual (MWh / hr) — per-leg (primary, user-defined):
    |DA_Sales_Qty - RT_Generation_Qty| + |DA_Purchases_Qty - RT_Consumption_Qty|

    Sales-leg and Purchases-leg are settled separately (each MW you committed
    to sell vs. actually generated; each MW you committed to buy vs. actually
    consumed). Both legs of a financial buyback count.

Also reported (for reference): net formula
    |DA_net - RT_net|, where DA_net = Sales-Purchases, RT_net = Gen-Cons
    Differs only when RT has simultaneous nonzero Gen and Cons in the same hour
    (intra-hour wash). On 2026-01-01..05-05, gap = ~0.24% / ~1.8 MWh per day.

AS reporting (UNIT BUG FIX 2026-05-06):
    DA_RRS_Amt / DA_ECRS_Amt / DA_NS_Amt / DA_Reg_*_Amt are DOLLARS (DA AS
    revenue = Award_MW * MCPC), NOT megawatts. They were previously mis-
    summed as MW.

    Correct DA AS award MW per product = Gen_RRS_Qty / Gen_ECRS_Qty /
    Gen_NS_Qty (verified to match Awarded_RRS-PFR / Awarded_ECRS /
    Awarded_NSRS in DA_Awards_Prices_All viewport).

    Per-product RT-recleared AS MW is NOT exposed by Tenaska PTP; only the
    pooled financial result via RT_Ancillary_Imbalance_Amt ($) is. So:
        - DA AS award MW per product → reported (= max possible virtual)
        - RT AS imbalance ($) → reported as financial proxy
        - Per-product AS virtual MW → cannot be computed from this dataset

AS virtual (MW / hr) — only products with RT-delivered counterpart:
    RRS:  |DA_RRS_Amt  - Gen_RRS_Qty|
    ECRS: |DA_ECRS_Amt - Gen_ECRS_Qty|
    NS:   |DA_NS_Amt   - Gen_NS_Qty|

Reg-Up / Reg-Down: no Gen_* counterpart in Battery-Settlement-Details, reported
as DA-awarded MW only (informational; not summed into AS virtual).

Reuses fetch_pnl_data.py auth + query helpers via direct import.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_pnl_data import (  # noqa: E402
    PROJECT_ROOT, ENV_PATH, PNL_DIR,
    tenaska_token, discover_tenaska_endpoints, tenaska_query, flatten_query,
)
from _env_loader import load_env_sections  # noqa: E402

START = date(2026, 1, 1)
END   = date(2026, 5, 5)  # inclusive

GKS_ESR_UUID = "ef8d8d31-47c4-4212-b893-a2dbb2070a2f"

OUT_DIR = PROJECT_ROOT / "shared" / "data" / "pnl" / "gks" / "adhoc"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def daterange(s: date, e: date):
    d = s
    while d <= e:
        yield d
        d += timedelta(days=1)


def fetch_day(token: str, root: str, ep: str, day: date) -> list[dict]:
    """Fetch energy_as_detail for one flowday (cached)."""
    cached = PNL_DIR / f"{day.isoformat()}_energy_as_detail.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))

    j = tenaska_query(
        token, root, ep, day,
        resource_filter="",
        datapoints=None,
        element_definition="Entity",
        path="query",
        element_identifiers=[GKS_ESR_UUID],
    )
    rows = flatten_query(j)
    cached.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
    raw_path = PNL_DIR / f"{day.isoformat()}_energy_as_detail_raw.json"
    raw_path.write_text(json.dumps(j, indent=2, default=str), encoding="utf-8")
    return rows


def daily_exposure(rows: list[dict]) -> dict:
    """Compute hourly virtual exposure and return daily aggregates."""
    by_dp_hr: dict[str, dict[str, float]] = defaultdict(dict)
    for r in rows:
        v = r.get("value")
        if isinstance(v, (int, float)):
            by_dp_hr[r["datapoint"]][r["interval_start_utc"]] = v

    hours = sorted({h for dp in by_dp_hr.values() for h in dp.keys()})

    def g(dp: str, h: str) -> float:
        return float(by_dp_hr.get(dp, {}).get(h, 0.0))

    energy_virt_perleg = 0.0  # |DA_S-RT_G| + |DA_P-RT_C|   (primary)
    energy_virt_net    = 0.0  # |DA_net - RT_net|            (reference)
    da_sales_mwh = 0.0
    da_purch_mwh = 0.0
    rt_gen_mwh   = 0.0
    rt_con_mwh   = 0.0

    da_award_rrs = da_award_ecrs = da_award_ns = 0.0
    da_rev_rrs = da_rev_ecrs = da_rev_ns = 0.0
    da_rev_regup = da_rev_regdn = 0.0
    rt_as_imbalance_usd = 0.0
    rt_reldepl_imbalance_usd = 0.0

    for h in hours:
        da_s = g("DA_Sales_Qty", h)
        da_p = g("DA_Purchases_Qty", h)
        rt_g = g("RT_Generation_Qty", h)
        rt_c = g("RT_Consumption_Qty", h)
        energy_virt_perleg += abs(da_s - rt_g) + abs(da_p - rt_c)
        energy_virt_net    += abs((da_s - da_p) - (rt_g - rt_c))

        da_sales_mwh += da_s
        da_purch_mwh += da_p
        rt_gen_mwh   += rt_g
        rt_con_mwh   += rt_c

        # DA AS award MW per product (Gen_*_Qty == Awarded_* per DA_Awards_Prices_All)
        da_award_rrs  += g("Gen_RRS_Qty", h)
        da_award_ecrs += g("Gen_ECRS_Qty", h)
        da_award_ns   += g("Gen_NS_Qty", h)

        # DA AS revenue $ (= Award_MW * DA_MCPC; NOT megawatts despite "Amt" suffix)
        da_rev_rrs   += g("DA_RRS_Amt", h)
        da_rev_ecrs  += g("DA_ECRS_Amt", h)
        da_rev_ns    += g("DA_NS_Amt", h)
        da_rev_regup += g("DA_Reg_Up_Amt", h)
        da_rev_regdn += g("DA_Reg_Down_Amt", h)

        # RT AS imbalance $ — pooled all-product DA→RT settlement delta (no MW breakdown)
        rt_as_imbalance_usd      += g("RT_Ancillary_Imbalance_Amt", h)
        rt_reldepl_imbalance_usd += g("RT_Reliability_Deployment_Imbalance_Amt", h)

    da_award_total = da_award_rrs + da_award_ecrs + da_award_ns

    return {
        "hours_with_data": len(hours),
        # Energy — primary (per-leg) and reference (net)
        "energy_virtual_mwh":         round(energy_virt_perleg, 2),
        "energy_virtual_mwh_perleg":  round(energy_virt_perleg, 2),
        "energy_virtual_mwh_net":     round(energy_virt_net, 2),
        "da_sales_mwh":         round(da_sales_mwh, 2),
        "da_purchases_mwh":     round(da_purch_mwh, 2),
        "rt_gen_mwh":           round(rt_gen_mwh, 2),
        "rt_consumption_mwh":   round(rt_con_mwh, 2),
        # DA AS award MW per product (= Gen_*_Qty, max possible AS virtual)
        "da_award_rrs_mwh":     round(da_award_rrs, 2),
        "da_award_ecrs_mwh":    round(da_award_ecrs, 2),
        "da_award_ns_mwh":      round(da_award_ns, 2),
        "da_award_as_total_mwh": round(da_award_total, 2),
        # DA AS revenue $ (= Award * MCPC, includes Reg-Up/Down via $ only)
        "da_revenue_rrs_usd":   round(da_rev_rrs, 2),
        "da_revenue_ecrs_usd":  round(da_rev_ecrs, 2),
        "da_revenue_ns_usd":    round(da_rev_ns, 2),
        "da_revenue_regup_usd": round(da_rev_regup, 2),
        "da_revenue_regdn_usd": round(da_rev_regdn, 2),
        # RT AS settlement (financial proxy for AS virtual)
        "rt_as_imbalance_usd":     round(rt_as_imbalance_usd, 2),
        "rt_reldepl_imbalance_usd": round(rt_reldepl_imbalance_usd, 2),
    }


def main() -> None:
    sections = load_env_sections(ENV_PATH)
    tk_section = sections.get("tenaska", {})
    eps = discover_tenaska_endpoints(tk_section)
    token = tenaska_token(tk_section)
    root = eps["root"]
    ep   = eps["energy_as_detail"]
    print(f"📥 Fetching energy_as_detail for {START} .. {END} from {root}/{ep}")

    daily: dict[str, dict] = {}
    days = list(daterange(START, END))
    for i, d in enumerate(days, 1):
        cached = PNL_DIR / f"{d.isoformat()}_energy_as_detail.json"
        was_cached = cached.exists()
        try:
            rows = fetch_day(token, root, ep, d)
        except Exception as e:
            print(f"  [{i:>3}/{len(days)}] {d}  ❌ {type(e).__name__}: {e}")
            continue
        agg = daily_exposure(rows)
        daily[d.isoformat()] = agg
        flag = "📂" if was_cached else "🌐"
        print(f"  [{i:>3}/{len(days)}] {d} {flag} hrs={agg['hours_with_data']:>2}  "
              f"E_virt={agg['energy_virtual_mwh']:>7.1f}MWh  "
              f"DA_AS_award={agg['da_award_as_total_mwh']:>6.1f}MWh "
              f"(RRS={agg['da_award_rrs_mwh']:>5.1f} ECRS={agg['da_award_ecrs_mwh']:>5.1f} NS={agg['da_award_ns_mwh']:>5.1f})  "
              f"RT_AS_imb=${agg['rt_as_imbalance_usd']:>9.0f}")
        if not was_cached:
            time.sleep(1.1)  # PTP 1 call/sec sustained

    # Aggregate
    n = len(daily)
    if n == 0:
        print("❌ no data")
        return

    fields_avg = ["energy_virtual_mwh", "energy_virtual_mwh_perleg",
                  "energy_virtual_mwh_net",
                  "da_sales_mwh", "da_purchases_mwh",
                  "rt_gen_mwh", "rt_consumption_mwh",
                  "da_award_rrs_mwh", "da_award_ecrs_mwh", "da_award_ns_mwh",
                  "da_award_as_total_mwh",
                  "da_revenue_rrs_usd", "da_revenue_ecrs_usd", "da_revenue_ns_usd",
                  "da_revenue_regup_usd", "da_revenue_regdn_usd",
                  "rt_as_imbalance_usd", "rt_reldepl_imbalance_usd"]
    avg = {f: round(sum(d[f] for d in daily.values()) / n, 2) for f in fields_avg}

    out = {
        "resource": "GKS_BESS_RN (Great Kiskadee Storage - ESR)",
        "period": {"start": START.isoformat(), "end": END.isoformat(), "days": n},
        "definition": {
            "energy_virtual_mwh_perleg": "primary: abs(DA_Sales-RT_Gen)+abs(DA_Pur-RT_Cons), summed over hours",
            "energy_virtual_mwh_net":   "reference: abs((DA_Sales-DA_Pur)-(RT_Gen-RT_Cons)), summed over hours",
            "da_award_*_mwh":           "DA AS award MW from Gen_*_Qty (= Awarded_* in DA_Awards_Prices_All viewport)",
            "da_revenue_*_usd":         "DA AS revenue $ from DA_*_Amt (= Award_MW * DA_MCPC; UNIT FIX 2026-05-06)",
            "rt_as_imbalance_usd":      "RT_Ancillary_Imbalance_Amt: pooled DA→RT recleared AS settlement delta ($)",
            "as_virtual_mw":            "NOT computable from this dataset — Tenaska PTP does not expose RT-recleared AS MW per product",
        },
        "daily_average": avg,
        "daily": daily,
    }
    out_path = OUT_DIR / f"virtual_exposure_{START}_{END}.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")

    print()
    print(f"=== Daily average over {n} days ({START} .. {END}) ===")
    print(f"  Energy virtual per-leg  (MWh/day):       {avg['energy_virtual_mwh_perleg']:>9.1f}   ← primary")
    print(f"  Energy virtual net      (MWh/day):       {avg['energy_virtual_mwh_net']:>9.1f}")
    print(f"  DA Sales / Purchases (MW·hr/day):        "
          f"{avg['da_sales_mwh']:>9.1f} / {avg['da_purchases_mwh']:>5.1f}")
    print(f"  RT Gen / Consumption (MW·hr/day):        "
          f"{avg['rt_gen_mwh']:>9.1f} / {avg['rt_consumption_mwh']:>5.1f}")
    print()
    print(f"  DA AS award MW·hr/day (= max possible AS virtual):")
    print(f"     RRS:                                  {avg['da_award_rrs_mwh']:>9.1f}")
    print(f"     ECRS:                                 {avg['da_award_ecrs_mwh']:>9.1f}")
    print(f"     NS:                                   {avg['da_award_ns_mwh']:>9.1f}")
    print(f"     ─ total (RRS+ECRS+NS):                {avg['da_award_as_total_mwh']:>9.1f}")
    print(f"  DA AS revenue $/day:")
    print(f"     RRS:                                 ${avg['da_revenue_rrs_usd']:>9,.0f}")
    print(f"     ECRS:                                ${avg['da_revenue_ecrs_usd']:>9,.0f}")
    print(f"     NS:                                  ${avg['da_revenue_ns_usd']:>9,.0f}")
    print(f"     Reg-Up:                              ${avg['da_revenue_regup_usd']:>9,.0f}")
    print(f"     Reg-Down:                            ${avg['da_revenue_regdn_usd']:>9,.0f}")
    print(f"  RT AS imbalance $/day (DA→RT pooled):   ${avg['rt_as_imbalance_usd']:>9,.0f}  ← financial AS-virtual proxy")
    print(f"  RT Reliab. Deploy. imbalance $/day:     ${avg['rt_reldepl_imbalance_usd']:>9,.0f}")
    print()
    print(f"  ⚠  Per-product AS virtual MW NOT computable — Tenaska PTP does not")
    print(f"     expose RT-recleared AS MW per product (only pooled $ via RT_Ancillary_Imbalance_Amt).")
    print(f"\n📄 Full details → {out_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
