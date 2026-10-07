"""Same shape as build_smartbidder_fullcap_uplift.py, but for the GK
**realized** (active) strategy as reported by Ascend Smartbidder, not the
Mount Blue Sky benchmark.

Why this exists: user asked to view GK actual performance via Ascend
instead of Tenaska PTP.  Ascend's `/revenue` defaults to the active
(realized) strategy when no `strategy` query param is passed.

Important caveat (Ascend docs): `/revenue` is an *estimate*, not the
settled invoice number. Useful for relative benchmarking and faster
backfill; do NOT reconcile to billed P&L.
"""
from __future__ import annotations
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env_loader import load_env_sections, first
from fetch_pnl_data import smartbidder_token, SMARTBIDDER_BASE
from build_smartbidder_benchmark_monthly import (
    month_chunks, _iso_cpt, fetch_soc, PRODUCT_LABEL,
)

ENV_PATH       = Path(__file__).resolve().parents[2] / ".env"
OUT_DIR        = Path(__file__).resolve().parents[2] / "shared/data/pnl/gks/monthly"
CPT            = ZoneInfo("America/Chicago")
GKS_KW         = 100_000
NAMEPLATE_MWH  = 200.0
BIND_THRESHOLD       = 0.93
CONSERVATIVE_FACTOR  = 0.8


def fetch_realized_revenue(token: str, sb: dict, start: date, end: date) -> pd.DataFrame:
    """/revenue, hourly, no strategy → active/realized."""
    client   = first(sb, "SMARTBIDDER_CLIENT", default="apex")
    resource = first(sb, "Resource", "SMARTBIDDER_RESOURCE", default="Kiskadee Storage")
    params = {
        "client": client, "iso": "ERCOT", "resource": resource,
        "start_date": _iso_cpt(start),
        "end_date":   _iso_cpt(end),
        "return_format": "json",
        "resolution": "hourly",
    }
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    r = requests.get(f"{SMARTBIDDER_BASE}/revenue", params=params, headers=headers, timeout=300)
    if r.status_code == 204:
        return pd.DataFrame()
    if r.status_code >= 400:
        raise RuntimeError(f"/revenue {r.status_code}: {r.text[:400]}")
    j = r.json()
    return pd.DataFrame(j["data"], columns=j["columns"])


def fetch_realized_soc(token: str, sb: dict, start: date, end: date) -> pd.DataFrame:
    """/soc-detailed, no strategy → realized."""
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
    sb = load_env_sections(ENV_PATH).get("smartbidder", {})
    token = smartbidder_token(sb)

    start = date(2025, 12, 1)
    end   = datetime.now(CPT).date()
    print(f"🎯 window: {start} .. {end} (exclusive)")

    # -------- revenue (no strategy) --------
    rev_parts = []
    print("\n📥 /revenue  (realized, hourly, chunked by month)")
    for s, e in month_chunks(start, end):
        df = fetch_realized_revenue(token, sb, s, e)
        print(f"   {s} .. {e}  rows={len(df):>6}")
        if not df.empty:
            rev_parts.append(df)
    if not rev_parts:
        sys.exit("❌ no realized revenue rows returned")
    rev = pd.concat(rev_parts, ignore_index=True)

    rev["ts"] = pd.to_datetime(rev["timestamp"], utc=True).dt.tz_convert(CPT)
    period = (rev["ts"] - pd.Timedelta(minutes=1)).dt.tz_localize(None).dt.to_period("M")
    rev["month"] = period.dt.strftime("%Y-%m")
    rev = rev[rev["month"] >= start.strftime("%Y-%m")]
    rev["label"] = rev["product"].map(PRODUCT_LABEL).fillna(rev["product"])

    is_virtual = rev["label"].isin(["DA Virtual Energy", "RT Virtual Energy"])
    is_total   = rev["label"] == "Total"

    by_month = (rev[~is_total].assign(virt=is_virtual[~is_total])
                .groupby(["month", "virt"])["revenue"].sum().unstack(fill_value=0.0))
    by_month.columns = ["physical_usd", "virtual_usd"]
    by_month["total_usd"] = by_month["physical_usd"] + by_month["virtual_usd"]
    stored_total = rev[is_total].groupby("month")["revenue"].sum()
    by_month["stored_total_usd"] = stored_total
    by_month["recon_diff_usd"]   = (by_month["total_usd"] - by_month["stored_total_usd"]).round(2)

    # per-product pivot (for the side display)
    products_kw = (rev[~is_total]
                   .pivot_table(index="month", columns="label",
                                values="revenue", aggfunc="sum", fill_value=0.0)
                   / GKS_KW).round(3)
    # column order to match benchmark layout where possible
    pref = ["DA Energy", "RT Energy", "RT Energy Deviation",
            "DA Virtual Energy", "RT Virtual Energy",
            "DA RegUp", "DA RegDown", "DA RRS", "DA ECRS", "DA Non-Spin", "DA Sync Reserve",
            "RT RegUp", "RT RegDown", "RT RRS", "RT ECRS", "RT Non-Spin", "RT Sync Reserve",
            "ORDC Adder"]
    cols = [c for c in pref if c in products_kw.columns] + \
           [c for c in products_kw.columns if c not in pref]
    products_kw = products_kw[cols]
    # drop all-zero columns for tidiness
    products_kw = products_kw.loc[:, (products_kw != 0).any(axis=0)]

    # -------- soc / per-day binding --------
    soc_parts = []
    print("\n📥 /soc-detailed  (realized, 5-min, chunked by month)")
    for s, e in month_chunks(start, end):
        df = fetch_realized_soc(token, sb, s, e)
        print(f"   {s} .. {e}  rows={len(df):>6}")
        if not df.empty:
            soc_parts.append(df)
    soc = pd.concat(soc_parts, ignore_index=True)
    soc["ts"]  = pd.to_datetime(soc["timestamp"], utc=True).dt.tz_convert(CPT)
    soc["day"] = soc["ts"].dt.date
    daily = soc.groupby("day").agg(
        peak_soc_mwh = ("soc_mwh", "max"),
        cap_max      = ("soc_mwh_max", "max"),
    ).reset_index()
    daily["month"] = pd.to_datetime(daily["day"]).dt.strftime("%Y-%m")
    daily["fill"]  = daily["peak_soc_mwh"] / daily["cap_max"].replace(0, pd.NA)
    daily["bound"] = (daily["fill"] > BIND_THRESHOLD).fillna(False)
    daily["fac"]   = ((NAMEPLATE_MWH / daily["cap_max"]) - 1).clip(lower=0) \
                      .where(daily["bound"], 0.0)
    mu = daily.groupby("month").agg(
        days = ("day", "size"),
        bound_days = ("bound", "sum"),
        avg_cap_mwh = ("cap_max", "mean"),
        avg_uplift_factor = ("fac", "mean"),
    ).round(3)

    # -------- combine --------
    out = pd.DataFrame(index=by_month.index)
    out["physical_$/kW"]            = (by_month["physical_usd"]     / GKS_KW).round(3)
    out["virtual_$/kW"]             = (by_month["virtual_usd"]      / GKS_KW).round(3)
    out["stored_total_$/kW"]        = (by_month["stored_total_usd"] / GKS_KW).round(3)
    out["bound_days"]               = mu.apply(lambda r: f"{int(r['bound_days'])}/{int(r['days'])}", axis=1)
    out["avg_cap_mwh"]              = mu["avg_cap_mwh"].round(1)
    out["avg_uplift_factor"]        = mu["avg_uplift_factor"]
    out["naive_uplift_$/kW"]        = (out["physical_$/kW"] * out["avg_uplift_factor"]).round(3)
    out["conservative_uplift_$/kW"] = (out["naive_uplift_$/kW"] * CONSERVATIVE_FACTOR).round(3)
    out["fullcap_total_consv_$/kW"] = (out["stored_total_$/kW"] + out["conservative_uplift_$/kW"]).round(3)

    print("\n=== GK actual (Ascend realized) — per product $/kW ===")
    pd.set_option("display.width", 240); pd.set_option("display.max_columns", None)
    print(products_kw.to_string())

    print("\n=== GK fullcap uplift (Ascend realized, 0.8× conservative) ===")
    print(out.to_string())

    ytd = out[["physical_$/kW","virtual_$/kW","stored_total_$/kW",
               "naive_uplift_$/kW","conservative_uplift_$/kW",
               "fullcap_total_consv_$/kW"]].sum().round(3)
    print("\n--- YTD ---")
    print(ytd.to_string())

    products_kw.to_csv(OUT_DIR / "gk_ascend_monthly_per_kw.csv")
    out.to_csv(OUT_DIR / "gk_ascend_fullcap_uplift.csv")
    print(f"\n💾 wrote {OUT_DIR / 'gk_ascend_monthly_per_kw.csv'}")
    print(f"💾 wrote {OUT_DIR / 'gk_ascend_fullcap_uplift.csv'}")


if __name__ == "__main__":
    main()
