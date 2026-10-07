"""Estimate monthly revenue uplift IF GKS BESS had been fully operational at
100 MW / 200 MWh nameplate, applied to **GK actual** physical revenue (from
Tenaska PTP `energy_as_detail` JSON files) over the available window.

Same logic as `build_smartbidder_fullcap_uplift.py`:

  1. Aggregate Tenaska `energy_as_detail` daily JSON files: sum each
     `_Amt` datapoint into hourly product revenue, then daily, then
     monthly.
  2. Pull Smartbidder `/soc-detailed` WITHOUT a strategy filter (=
     realized SoC) for the same window.
  3. For each day: bound  ⇔  peak_realized_soc_mwh / cap_max  > 0.93
  4. Per-day uplift factor (bound days only):  (200 / cap_max) − 1
  5. Apply CONSERVATIVE multiplier 0.8 to soften linear scaling.
  6. Virtual revenue is NOT included here — Tenaska PTP doesn't expose
     DART virtual position revenue (it's a separate financial account).
     For an apples-to-apples comparison we present GK actual physical
     only, alongside benchmark physical.

Outputs:
  shared/data/pnl/gks/monthly/gk_fullcap_uplift.csv
"""
from __future__ import annotations
import json, sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env_loader import load_env_sections, first
from fetch_pnl_data import smartbidder_token, SMARTBIDDER_BASE
from build_smartbidder_benchmark_monthly import month_chunks, _iso_cpt
import requests

ENV_PATH      = Path(__file__).resolve().parents[2] / ".env"
PNL_HOURLY    = Path(__file__).resolve().parents[2] / "shared/data/pnl/gks/hourly"
OUT_DIR       = Path(__file__).resolve().parents[2] / "shared/data/pnl/gks/monthly"
CPT           = ZoneInfo("America/Chicago")
GKS_KW        = 100_000
NAMEPLATE_MWH = 200.0
BIND_THRESHOLD       = 0.93
CONSERVATIVE_FACTOR  = 0.8   # haircut on naive linear scaling

# Tenaska _Amt datapoint → display label
AMT_LABEL = {
    "DA_Energy_Amt":                          "DA Energy",
    "RT_Energy_Amt":                          "RT Energy",
    "DA_RRS_Amt":                             "DA RRS",
    "DA_NS_Amt":                              "DA Non-Spin",
    "DA_ECRS_Amt":                            "DA ECRS",
    "DA_Reg_Up_Amt":                          "DA RegUp",
    "DA_Reg_Down_Amt":                        "DA RegDown",
    "RT_Ancillary_Imbalance_Amt":             "RT AS Imbalance",
    "RT_Reliability_Deployment_Imbalance_Amt":"RT Reliability Deploy",
}

ROW_ORDER = [
    "DA Energy", "RT Energy",
    "DA RegUp", "DA RegDown", "DA RRS", "DA ECRS", "DA Non-Spin",
    "RT AS Imbalance", "RT Reliability Deploy",
]


def load_daily_revenue() -> pd.DataFrame:
    """Walk PNL_HOURLY, sum each _Amt datapoint per file → daily rows."""
    rows = []
    for p in sorted(PNL_HOURLY.glob("*_energy_as_detail.json")):
        day = date.fromisoformat(p.stem.split("_energy_as_detail")[0])
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️ {p.name}: {e}")
            continue
        totals = defaultdict(float)
        for r in data:
            dp = r.get("datapoint")
            v  = r.get("value")
            if dp in AMT_LABEL and v is not None:
                totals[dp] += float(v)
        for dp, usd in totals.items():
            rows.append({"day": day, "datapoint": dp,
                         "label": AMT_LABEL[dp], "usd": usd})
    return pd.DataFrame(rows)


def fetch_realized_soc(token: str, sb: dict, start: date, end: date) -> pd.DataFrame:
    """Smartbidder /soc-detailed without strategy filter = realized SoC."""
    client   = first(sb, "SMARTBIDDER_CLIENT", default="apex")
    resource = first(sb, "Resource", "SMARTBIDDER_RESOURCE", default="Kiskadee Storage")
    params = {
        "client": client, "iso": "ERCOT", "resource": resource,
        "start_date": _iso_cpt(start),
        "end_date":   _iso_cpt(end),
        "return_format": "json",
    }
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    r = requests.get(f"{SMARTBIDDER_BASE}/soc-detailed", params=params, headers=headers, timeout=300)
    if r.status_code == 204:
        return pd.DataFrame()
    r.raise_for_status()
    j = r.json()
    return pd.DataFrame(j["data"], columns=j["columns"])


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    daily_rev = load_daily_revenue()
    if daily_rev.empty:
        sys.exit("❌ no GK PnL data found locally")

    daily_rev["month"] = pd.to_datetime(daily_rev["day"]).dt.strftime("%Y-%m")
    first_day = daily_rev["day"].min()
    last_day  = daily_rev["day"].max()
    print(f"🎯 GK actual window: {first_day} .. {last_day}  ({len(daily_rev['day'].unique())} days)")

    # Restrict to "comparable" window starting 2025-12 if any data; else 2026-01
    cutoff = date(2025, 12, 1)
    daily_rev = daily_rev[pd.to_datetime(daily_rev["day"]).dt.date >= cutoff]
    if daily_rev.empty:
        sys.exit("❌ no GK PnL data on/after 2025-12-01")

    # -------- monthly revenue pivot --------
    monthly_usd = (daily_rev.pivot_table(index="month", columns="label",
                                          values="usd", aggfunc="sum",
                                          fill_value=0.0))
    cols = [c for c in ROW_ORDER if c in monthly_usd.columns]
    monthly_usd = monthly_usd[cols]
    monthly_usd["Total Physical"] = monthly_usd.sum(axis=1)
    monthly_kw = (monthly_usd / GKS_KW).round(3)

    # -------- realized SoC for same window --------
    sb = load_env_sections(ENV_PATH).get("smartbidder", {})
    token = smartbidder_token(sb)
    start = pd.to_datetime(daily_rev["day"].min()).date()
    end   = pd.to_datetime(daily_rev["day"].max()).date() + timedelta(days=1)
    soc_parts = []
    print(f"\n📥 realized SoC (no strategy filter)  {start} .. {end}")
    for s, e in month_chunks(start, end):
        df = fetch_realized_soc(token, sb, s, e)
        print(f"   {s} .. {e}  rows={len(df)}")
        if not df.empty:
            soc_parts.append(df)
    soc = pd.concat(soc_parts, ignore_index=True) if soc_parts else pd.DataFrame()

    if soc.empty:
        print("⚠️ realized SoC empty — using bench cap data as fallback")
        # fall back to nameplate (degenerate: no uplift possible)
        uplift_factor = pd.Series(0.0, index=monthly_kw.index)
        bound_days_str = pd.Series("n/a", index=monthly_kw.index)
        avg_cap_str    = pd.Series("n/a", index=monthly_kw.index)
    else:
        soc["ts"]  = pd.to_datetime(soc["timestamp"], utc=True).dt.tz_convert(CPT)
        soc["day"] = soc["ts"].dt.date
        daily_soc = soc.groupby("day").agg(
            peak_soc_mwh = ("soc_mwh", "max"),
            cap_max      = ("soc_mwh_max", "max"),
        ).reset_index()
        daily_soc["month"] = pd.to_datetime(daily_soc["day"]).dt.strftime("%Y-%m")
        daily_soc["fill"]  = daily_soc["peak_soc_mwh"] / daily_soc["cap_max"].replace(0, pd.NA)
        daily_soc["bound"] = (daily_soc["fill"] > BIND_THRESHOLD).fillna(False)
        daily_soc["fac"]   = ((NAMEPLATE_MWH / daily_soc["cap_max"]) - 1).clip(lower=0) \
                              .where(daily_soc["bound"], 0.0)
        mu = daily_soc.groupby("month").agg(
            days = ("day", "size"),
            bound_days = ("bound", "sum"),
            avg_cap_mwh = ("cap_max", "mean"),
            avg_uplift_factor = ("fac", "mean"),
        ).round(3)
        uplift_factor = mu["avg_uplift_factor"]
        bound_days_str = mu.apply(lambda r: f"{int(r['bound_days'])}/{int(r['days'])}", axis=1)
        avg_cap_str    = mu["avg_cap_mwh"].round(1).astype(str)

    # -------- combine + apply 0.8 haircut --------
    out = pd.DataFrame(index=monthly_kw.index)
    out["physical_$/kW"]              = monthly_kw["Total Physical"]
    out["bound_days"]                 = bound_days_str
    out["avg_cap_mwh"]                = avg_cap_str
    out["avg_uplift_factor"]          = uplift_factor.reindex(out.index).round(3)
    out["naive_uplift_$/kW"]          = (out["physical_$/kW"] * out["avg_uplift_factor"]).round(3)
    out["conservative_uplift_$/kW"]   = (out["naive_uplift_$/kW"] * CONSERVATIVE_FACTOR).round(3)
    out["physical_fullcap_$/kW"]      = (out["physical_$/kW"] + out["conservative_uplift_$/kW"]).round(3)

    # Show per-product breakdown too
    print("\n=== GK actual monthly physical revenue ($/kW) ===")
    pd.set_option("display.width", 220); pd.set_option("display.max_columns", None)
    print(monthly_kw.to_string())

    print("\n=== GK fullcap uplift (conservative 0.8× linear) ===")
    print(out.to_string())

    ytd = pd.DataFrame({
        "physical_$/kW":            [out["physical_$/kW"].sum()],
        "naive_uplift_$/kW":        [out["naive_uplift_$/kW"].sum()],
        "conservative_uplift_$/kW": [out["conservative_uplift_$/kW"].sum()],
        "physical_fullcap_$/kW":    [out["physical_fullcap_$/kW"].sum()],
    }, index=["YTD"]).round(3)
    print("\n--- YTD ---")
    print(ytd.to_string())

    monthly_kw.to_csv(OUT_DIR / "gk_actual_monthly_physical_per_kw.csv")
    out.to_csv(OUT_DIR / "gk_fullcap_uplift.csv")
    print(f"\n💾 wrote {OUT_DIR / 'gk_actual_monthly_physical_per_kw.csv'}")
    print(f"💾 wrote {OUT_DIR / 'gk_fullcap_uplift.csv'}")


if __name__ == "__main__":
    main()
