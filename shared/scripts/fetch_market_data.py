"""
Market Analyst — D+1 raw data fetch (production)

Run from BESS_Biz/ root:
    python shared/scripts/fetch_market_data.py
    python shared/scripts/fetch_market_data.py --target-date 2026-05-01

Reads .env from project root, calls Yes Energy DataSignals + Smartbidder,
saves raw outputs to shared/data/raw/{vendor}/{date}.csv|json,
prints quick 24h summary stats to stdout.

Vendors covered:
- Yes Energy: 9 bidclose items per market-analyst.md §2
- Smartbidder: Energy + AS price forecasts, P(DA<RT)
- AG2 WSI Trader: weather + WindCast IQ wind + hourly load forecast
- Enverus Mosaic: load / net-load / solar / wind forecasts

Not yet covered (extend later):
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


# ---------- AG2 (WSI Trader) ----------
AG2_BASE = "https://www.wsitrader.com/Services/CSVDownloadService.svc"

# Texas weather stations for ERCOT (ICAO) — fetch-ercot-data SKILL.md §3a
AG2_WEATHER_SITES = ["KDFW", "KIAH", "KAUS", "KSAT", "KMAF", "KCRP", "KBRO"]

# WindCast IQ ERCOT regional SiteIds — fetch-ercot-data SKILL.md §3b
AG2_WIND_SITES = {
    "ERCOT":     "89b6bb6e-fdc5-11e5-8259-0019b9b47402",
    "Coastal":   "089d129d-5f7a-11e9-937a-0e215c336de8",
    "Panhandle": "08aed221-5f7a-11e9-937a-0e215c336de8",
    "North":     "89be4149-fdc5-11e5-8259-0019b9b47402",
    "South":     "89dee8da-fdc5-11e5-8259-0019b9b47402",
    "West":      "89e1b0f3-fdc5-11e5-8259-0019b9b47402",
}

AG2_LOAD_REGIONS  = ["RTO", "Houston", "West", "North", "South"]
AG2_LOAD_SUBZONES = ["Coast", "East", "FarWest", "North", "South",
                     "SouthCentral", "West", "NorthCentral"]


def _ag2_auth(ag2_section: dict[str, str]) -> dict[str, str]:
    """AG2 auth is query-string (not header): Account / Profile / Password."""
    user, pwd, profile = (ag2_section.get("USER"), ag2_section.get("PASSWORD"),
                          ag2_section.get("Profile"))
    if not user or not pwd or not profile:
        raise RuntimeError("AG2 USER / PASSWORD / Profile missing in [ag2] .env section")
    return {"Account": user, "Profile": profile, "Password": pwd}


def ag2_get(endpoint: str, auth: dict[str, str], extra: dict[str, Any],
            retries: int = 3) -> str:
    """GET an AG2 CSVDownloadService endpoint; return CSV text or raise."""
    url = f"{AG2_BASE}/{endpoint}"
    for attempt in range(retries):
        try:
            r = requests.get(url, params={**auth, **extra}, timeout=90)
            if r.status_code == 200:
                return r.text
            print(f"  AG2 {endpoint} HTTP {r.status_code} (attempt {attempt+1}/{retries})")
        except requests.RequestException as e:
            print(f"  AG2 {endpoint} {type(e).__name__}: {e} (attempt {attempt+1}/{retries})")
        time.sleep([3, 6, 9][min(attempt, 2)])
    raise RuntimeError(f"AG2 {endpoint} failed after {retries} retries")


def fetch_ag2(ag2_section: dict[str, str], target: date, out_dir: Path) -> dict[str, Any]:
    """Fetch AG2 weather + WindCast IQ wind + hourly load (WSI source).

    Each product is non-fatal — WindCast IQ and Load are subscriber-only, so a
    missing subscription logs a warning and is skipped. Returns {product: path|error}.
    """
    auth = _ag2_auth(ag2_section)
    out_dir.mkdir(parents=True, exist_ok=True)
    issue_date = target - timedelta(days=1)   # forecast issued on D-1
    results: dict[str, Any] = {}

    def _save(name: str, csv: str) -> None:
        p = out_dir / f"{target.isoformat()}_{name}.csv"
        p.write_text(csv, encoding="utf-8")
        results[name] = p
        print(f"   saved → {p.relative_to(PROJECT_ROOT)}  ({len(csv)} chars)")

    # Weather — GetHourlyForecast, 7 Texas stations (≤10 per call)
    try:
        _save("weather", ag2_get("GetHourlyForecast", auth, {
            "Region": "NA", "SiteIds[]": AG2_WEATHER_SITES,
            "TempUnits": "F", "timeutc": "false"}))
    except Exception as e:
        results["weather"] = f"ERROR: {e}"
        print(f"   ⚠️ AG2 weather skipped: {e}")

    # WindCast IQ wind power — 6 ERCOT regional aggregates (subscriber-only)
    try:
        _save("windcast", ag2_get("GetWindcastIQHourlyForecast", auth, {
            "ForecastDate": issue_date.isoformat(), "ForecastType": "Primary",
            "SiteIds": ",".join(AG2_WIND_SITES.values()), "timeutc": "false"}))
    except Exception as e:
        results["windcast"] = f"ERROR: {e}"
        print(f"   ⚠️ AG2 WindCast IQ skipped (subscriber-only): {e}")

    # Hourly load — WSI source. Two calls: multi-region, then multi-subzone
    # (vendor rule: multiple Subzones require a single Region).
    try:
        _save("load_regions", ag2_get("GetHourlyLoadData", auth, {
            "ISO": "ERCOT", "Regions[]": AG2_LOAD_REGIONS,
            "Sources[]": "WSI", "timeutc": "false"}))
    except Exception as e:
        results["load_regions"] = f"ERROR: {e}"
        print(f"   ⚠️ AG2 load/regions skipped (subscriber-only): {e}")
    try:
        _save("load_subzones", ag2_get("GetHourlyLoadData", auth, {
            "ISO": "ERCOT", "Regions[]": "RTO", "Subzones[]": AG2_LOAD_SUBZONES,
            "Sources[]": "WSI", "timeutc": "false"}))
    except Exception as e:
        results["load_subzones"] = f"ERROR: {e}"
        print(f"   ⚠️ AG2 load/subzones skipped (subscriber-only): {e}")

    return results


# ---------- Enverus (Mosaic) ----------
ENVERUS_BASE = "https://api-mosaic-prod.enverus.com/mosaic-api"

# Mosaic dataset IDs. net_load + wind STPF are confirmed in fetch-ercot-data
# SKILL.md §2; load + solar are inferred from the same naming pattern and are
# non-fatal if the dataset does not resolve.
ENVERUS_DATASETS = {
    "net_load_fc": "ercot-load-system_wide-env_forecast_net_load",
    "wind_stpf":   "ercot-generation_wind-system_wide-env_forecast_generation_stpf",
    "load_fc":     "ercot-load-system_wide-env_forecast_load",
    "solar_stpf":  "ercot-generation_solar-system_wide-env_forecast_generation_stpf",
}


def enverus_get(dataset: str, auth: HTTPBasicAuth, target: date,
                retries: int = 3) -> str:
    """GET an Enverus Mosaic timeseries; return CSV text or raise."""
    url = f"{ENVERUS_BASE}/timeseries/{dataset}"
    params = {
        "entity_ids": "ERCOT",
        "start_datetime": target.isoformat(),
        "end_datetime": (target + timedelta(days=1)).isoformat(),
        "as_of": "prior_day_rolling",      # D-1 vintage, no look-ahead
        "response_type": "csv_wide",
    }
    for attempt in range(retries):
        try:
            # Enverus server cert sometimes fails verification — verify=False
            # is the established workaround (fetch-ercot-data SKILL.md §2).
            r = requests.get(url, params=params, auth=auth, timeout=90, verify=False)
            if r.status_code == 200:
                return r.text
            print(f"  Enverus {dataset} HTTP {r.status_code} (attempt {attempt+1}/{retries})")
        except requests.RequestException as e:
            print(f"  Enverus {dataset} {type(e).__name__}: {e} (attempt {attempt+1}/{retries})")
        time.sleep([3, 6, 9][min(attempt, 2)])
    raise RuntimeError(f"Enverus {dataset} failed after {retries} retries")


def fetch_enverus(env_section: dict[str, str], target: date,
                  out_dir: Path) -> dict[str, Any]:
    """Fetch Enverus Mosaic load / net-load / solar / wind forecasts (system-wide).

    Each dataset is non-fatal. Returns {dataset_key: path|error}.
    """
    user, pwd = env_section.get("USERNAME"), env_section.get("PASSWORD")
    if not user or not pwd:
        raise RuntimeError("Enverus USERNAME / PASSWORD missing in [enverus] .env section")

    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    out_dir.mkdir(parents=True, exist_ok=True)
    auth = HTTPBasicAuth(user, pwd)
    results: dict[str, Any] = {}
    for key, dataset in ENVERUS_DATASETS.items():
        try:
            csv = enverus_get(dataset, auth, target)
            p = out_dir / f"{target.isoformat()}_{key}.csv"
            p.write_text(csv, encoding="utf-8")
            results[key] = p
            print(f"   saved → {p.relative_to(PROJECT_ROOT)}  ({len(csv)} chars)")
        except Exception as e:
            results[key] = f"ERROR: {e}"
            print(f"   ⚠️ Enverus {key} ({dataset}) skipped: {e}")
    return results


# ---------- main ----------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-date", default=None,
                    help="ERCOT operating day (YYYY-MM-DD). Default = tomorrow.")
    ap.add_argument("--skip-smartbidder", action="store_true")
    ap.add_argument("--skip-ag2", action="store_true")
    ap.add_argument("--skip-enverus", action="store_true")
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

    # --- AG2 (WSI Trader) ---
    ag2_results: dict[str, Any] = {}
    if not args.skip_ag2:
        print("\n📥 AG2 WSI Trader (weather + WindCast IQ + hourly load) ...")
        try:
            ag2_results = fetch_ag2(sections.get("ag2", {}), target, RAW_DIR / "ag2")
        except Exception as e:
            print(f"   ⚠️ AG2 fetch failed (non-fatal): {type(e).__name__}: {e}")

    # --- Enverus (Mosaic) ---
    enverus_results: dict[str, Any] = {}
    if not args.skip_enverus:
        print("\n📥 Enverus Mosaic (load / net-load / solar / wind forecasts) ...")
        try:
            enverus_results = fetch_enverus(sections.get("enverus", {}), target,
                                            RAW_DIR / "enverus")
        except Exception as e:
            print(f"   ⚠️ Enverus fetch failed (non-fatal): {type(e).__name__}: {e}")

    # --- Summary JSON ---
    def _paths(d: dict[str, Any]) -> dict[str, str]:
        return {k: (str(v.relative_to(PROJECT_ROOT)) if isinstance(v, Path) else str(v))
                for k, v in d.items()}

    summary = {
        "target_date": target.isoformat(),
        "fetched_at_utc": datetime.utcnow().isoformat() + "Z",
        "yes_energy": yes_stats,
        "ag2": _paths(ag2_results),
        "enverus": _paths(enverus_results),
    }
    summary_path = RAW_DIR / "yes-energy" / f"{target.isoformat()}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n📊 Summary → {summary_path.relative_to(PROJECT_ROOT)}")
    print(f"\n✅ Done. Next: feed {summary_path.name} to market-analyst agent for briefing.")


if __name__ == "__main__":
    main()
