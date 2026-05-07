"""
Market Analyst — D+1 raw data fetch (production)

Run from BESS_Biz/ root:
    python shared/scripts/fetch_market_data.py
    python shared/scripts/fetch_market_data.py --target-date 2026-05-01

Reads .env from project root, calls Yes Energy DataSignals + Smartbidder,
saves raw outputs to shared/data/raw/{vendor}/{date}.csv|json,
prints quick 24h summary stats to stdout.

Vendors covered (Smoke test scope):
- Yes Energy: 9 bidclose items per market-analyst.md §2
- Smartbidder: Energy + AS price forecasts, P(DA<RT)

Skipped in this Smoke test (extend later):
- AG2 WSI Trader (load/wind/weather)
- Enverus Mosaic (outages, PRC)
- ERCOT Public API
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from _env_loader import load_env_sections, first  # local helper

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ---------- Paths ----------
PROJECT_ROOT = Path(__file__).resolve().parents[2]   # BESS_Biz/
ENV_PATH     = PROJECT_ROOT / ".env"
RAW_DIR      = PROJECT_ROOT / "shared" / "data" / "raw"


# ---------- Yes Energy ----------
YES_BASE = "https://services.yesenergy.com/PS/rest"

# market-analyst.md §2 bidclose items.
# Verified 2026-05-04: LOAD_FORECAST_BID_CLOSE:* items are retired in YE catalog —
# fall back to LOAD_FORECAST:* (basic) for load. NET_LOAD_FORECAST_BID_CLOSE:ERCOT
# and *_BIDCLOSE wind/solar items still work.
BIDCLOSE_ITEMS = [
    "LOAD_FORECAST:WZ_ERCOT",                # was LOAD_FORECAST_BID_CLOSE:WZ_ERCOT (retired)
    "LOAD_FORECAST:ERCOT",                   # systemwide load FC
    "NET_LOAD_FORECAST_BID_CLOSE:ERCOT",
    "SOLAR_COPHSL_BIDCLOSE:ERCOT",
    "WIND_COPHSL_BIDCLOSE:ERCOT",
    "WIND_STWPF_BIDCLOSE:GR_WEST",
    "WIND_COPHSL_BIDCLOSE:GR_NORTH",
    "WIND_STWPF_BIDCLOSE:GR_COASTAL",
    "WIND_STWPF_BIDCLOSE:GR_SOUTH",
    "TOTAL_RESOURCE_CAP_OUT:ERCOT",
]


def yes_fetch_bidclose(ye_section: dict[str, str], target_date: date, retries: int = 3) -> str:
    """Return raw CSV text from Yes Energy /timeseries/multiple.csv

    ye_section: the 'yes_energy' section dict from load_env_sections().
    """
    user = ye_section.get("YES_ENERGY_USERNAME")
    pwd  = ye_section.get("YES_ENERGY_PASSWORD")
    if not user or not pwd:
        sys.exit("❌ YES_ENERGY_USERNAME / YES_ENERGY_PASSWORD missing in [yes_energy] section of .env")

    params = {
        # Yes Energy /timeseries/multiple.csv uses comma-separated items.
        # Semicolon was treated as a single composite item → 'error' CSV.
        "items":     ",".join(BIDCLOSE_ITEMS),
        "startdate": target_date.isoformat(),
        "enddate":   target_date.isoformat(),
        "agglevel":  "hour",
    }
    url = f"{YES_BASE}/timeseries/multiple.csv"

    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, auth=HTTPBasicAuth(user, pwd), timeout=60)
            if r.status_code == 200:
                return r.text
            if r.status_code == 401:
                sys.exit("❌ Yes Energy 401 — credentials rejected (do not retry)")
            print(f"  Yes Energy HTTP {r.status_code} (attempt {attempt+1}/{retries})")
        except requests.RequestException as e:
            print(f"  Yes Energy {type(e).__name__}: {e} (attempt {attempt+1}/{retries})")
        time.sleep([5, 10, 15][min(attempt, 2)])
    sys.exit("❌ Yes Energy bidclose fetch failed after retries")


def quick_stats_yes(csv_text: str) -> dict[str, Any]:
    """Return a tiny per-item summary: 24h mean, top/bottom 2 HE."""
    import io
    import pandas as pd
    df = pd.read_csv(io.StringIO(csv_text))
    if "HOURENDING" not in df.columns:
        return {"warning": "Unexpected schema", "columns": df.columns.tolist()}

    out: dict[str, Any] = {}
    for col in df.columns:
        if col in ("DATETIME", "HOURENDING"):
            continue
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            continue
        # top/bottom 2 hours via HOURENDING
        joined = df[["HOURENDING", col]].dropna().copy()
        joined[col] = pd.to_numeric(joined[col], errors="coerce")
        top2 = joined.nlargest(2, col)
        bot2 = joined.nsmallest(2, col)
        out[col] = {
            "mean":   round(float(s.mean()), 2),
            "min":    round(float(s.min()), 2),
            "max":    round(float(s.max()), 2),
            "top2_HE":    top2["HOURENDING"].tolist(),
            "bottom2_HE": bot2["HOURENDING"].tolist(),
        }
    return out


# ---------- Smartbidder (MSAL) ----------
SMARTBIDDER_BASE = "https://data.ascendanalytics.com"


def smartbidder_token(sb_section: dict[str, str]) -> str:
    """sb_section: the 'smartbidder' section dict from load_env_sections()."""
    try:
        from msal import ConfidentialClientApplication
    except ImportError:
        sys.exit("❌ pip install msal — required for Smartbidder")

    application_id = sb_section.get("APPLICATION_ID",
                                    "https://dataascendanalyticscom.azurewebsites.net")
    client_id     = sb_section.get("CLIENT_ID")
    client_secret = sb_section.get("CLIENT_SECRET")
    tenant        = sb_section.get("_TENANT", "onascend.com")
    authority     = f"https://login.microsoftonline.com/{tenant}"

    if not client_id or not client_secret:
        sys.exit("❌ Smartbidder CLIENT_ID / CLIENT_SECRET missing in [smartbidder] section of .env")

    app = ConfidentialClientApplication(client_id, client_secret, authority)
    res = app.acquire_token_for_client([f"{application_id}/.default"])
    if "access_token" not in res:
        sys.exit(f"❌ Smartbidder token error: {res.get('error_description', res)}")
    return res["access_token"]


def smartbidder_plot(token: str, plot_type: str, client: str, resource: str,
                    start_dt: str, end_dt: str) -> str:
    url = f"{SMARTBIDDER_BASE}/plots/{urllib.parse.quote(plot_type)}"
    params = {
        "client": client, "iso": "ERCOT", "resource": resource,
        "start_date": start_dt, "end_date": end_dt,
    }
    headers = {"Authorization": f"Bearer {token}", "Accept": "text/csv"}
    r = requests.get(url, params=params, headers=headers, timeout=60)
    if r.status_code == 204:
        return ""  # no data
    r.raise_for_status()
    return r.text


# ---------- main ----------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-date", default=None,
                    help="ERCOT operating day (YYYY-MM-DD). Default = tomorrow.")
    ap.add_argument("--skip-smartbidder", action="store_true")
    args = ap.parse_args()

    target = (date.fromisoformat(args.target_date)
              if args.target_date else date.today() + timedelta(days=1))
    print(f"🎯 Target date (D+1): {target.isoformat()}")

    sections = load_env_sections(ENV_PATH)
    ye_section = sections.get("yes_energy", {})
    sb_section = sections.get("smartbidder", {})
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # --- Yes Energy ---
    print("\n📥 Yes Energy bidclose fetch ...")
    yes_csv = yes_fetch_bidclose(ye_section, target)
    yes_path = RAW_DIR / "yes-energy" / f"{target.isoformat()}.csv"
    yes_path.parent.mkdir(parents=True, exist_ok=True)
    yes_path.write_text(yes_csv, encoding="utf-8")
    print(f"   saved → {yes_path.relative_to(PROJECT_ROOT)}  ({len(yes_csv)} chars)")
    yes_stats = quick_stats_yes(yes_csv)

    print("\n   Quick stats (mean / min / max / top2 HE / bottom2 HE):")
    for item, st in yes_stats.items():
        if "mean" in st:
            print(f"   • {item:55s} mean={st['mean']:>9.1f}  "
                  f"top2={st['top2_HE']}  bot2={st['bottom2_HE']}")

    # --- Smartbidder ---
    if not args.skip_smartbidder:
        print("\n📥 Smartbidder forecasts ...")
        try:
            tok = smartbidder_token(sb_section)
            # Smartbidder client default 'apex'; Resource key in [smartbidder] section
            client   = first(sb_section, "SMARTBIDDER_CLIENT", default="apex")
            resource = first(sb_section, "Resource", "SMARTBIDDER_RESOURCE",
                             default="Kiskadee Storage")
            start_dt = f"{target.isoformat()}T00:00:00-05:00"
            end_dt   = f"{(target + timedelta(days=1)).isoformat()}T00:00:00-05:00"
            print(f"   client={client!r}  resource={resource!r}")

            # Verified 2026-05-04 against /swagger.json — the skill doc's
            # 'Ancillary Price Forecasts' is a wrong/legacy name (404). The actual
            # registered plot is 'DA Ancillary Prices' (cleared + forecasted prices
            # per AS product: Non-Spin, RegDown, RegUp, RRS, ECRS).
            for plot in ("Energy Price Forecasts",
                         "DA Ancillary Prices",
                         "RT Ancillary Prices",
                         "DA-RT Forecast"):
                csv = smartbidder_plot(tok, plot, client, resource, start_dt, end_dt)
                p = RAW_DIR / "smartbidder" / f"{target.isoformat()}_{plot.replace(' ', '_')}.csv"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(csv, encoding="utf-8")
                print(f"   saved → {p.relative_to(PROJECT_ROOT)}  ({len(csv)} chars)")
        except SystemExit:
            raise
        except Exception as e:
            print(f"   ⚠️ Smartbidder fetch failed (non-fatal): {type(e).__name__}: {e}")

    # --- Summary JSON ---
    summary = {
        "target_date": target.isoformat(),
        "fetched_at_utc": datetime.utcnow().isoformat() + "Z",
        "yes_energy": yes_stats,
    }
    summary_path = RAW_DIR / "yes-energy" / f"{target.isoformat()}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n📊 Summary → {summary_path.relative_to(PROJECT_ROOT)}")
    print(f"\n✅ Done. Next: feed {summary_path.name} to market-analyst agent for briefing.")


if __name__ == "__main__":
    main()
