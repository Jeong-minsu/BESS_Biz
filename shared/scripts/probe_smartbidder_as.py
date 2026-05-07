"""Deep-probe Smartbidder for ANY surface that returns AS price forecasts ($/MWh per product per HE)."""
from __future__ import annotations
import sys, urllib.parse
from datetime import date, timedelta
from pathlib import Path
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env_loader import load_env_sections, first
from fetch_pnl_data import smartbidder_token, SMARTBIDDER_BASE

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
TARGET = date.fromisoformat("2026-05-05")
NEXT   = TARGET + timedelta(days=1)

def main():
    sec = load_env_sections(ENV_PATH).get("smartbidder", {})
    tok = smartbidder_token(sec)
    H = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    client   = first(sec, "SMARTBIDDER_CLIENT", default="apex")
    resource = first(sec, "Resource", "SMARTBIDDER_RESOURCE", default="Kiskadee Storage")
    node     = sec.get("Node", "GKS_BESS_RN")
    base = {"client": client, "iso": "ERCOT", "resource": resource,
            "start_date": f"{TARGET.isoformat()}T00:00:00-05:00",
            "end_date":   f"{NEXT.isoformat()}T00:00:00-05:00"}

    # 1) Different /plots/ name spellings + with node
    plot_variants = [
        "Ancillary Price Forecasts",
        "DA Ancillary Price Forecasts",
        "Ancillary Service Price Forecasts",
        "AS Price Forecasts",
        "DA AS Price Forecasts",
        "Forecasted Ancillary Prices",
        "Day-Ahead Ancillary Prices",
    ]
    print("\n=== /plots/<name> with resource only ===")
    for p in plot_variants:
        url = f"{SMARTBIDDER_BASE}/plots/{urllib.parse.quote(p)}"
        r = requests.get(url, params=base, headers=H, timeout=20)
        print(f"  [{r.status_code}] {p!r}")

    print("\n=== /plots/<name> with resource + node ===")
    base_n = {**base, "node": node}
    for p in plot_variants:
        url = f"{SMARTBIDDER_BASE}/plots/{urllib.parse.quote(p)}"
        r = requests.get(url, params=base_n, headers=H, timeout=20)
        print(f"  [{r.status_code}] {p!r}")

    # 2) Data API surfaces (non-plots) — try documented and likely paths
    print("\n=== Data API endpoints ===")
    base_json = {**base, "return_format": "json"}
    data_paths = [
        "/forecast-composite",                  # documented (energy spike probs)
        "/ancillary-prices",
        "/ancillary-forecasts",
        "/ancillary-price-forecasts",
        "/da-ancillary-prices",
        "/forecasted-ancillary-prices",
        "/forecasted-prices",
        "/forecasts",
        "/forecasts/ancillary",
        "/forecasts/ancillary-prices",
        "/da-prices",
        "/clearing-prices",
        "/da-cleared-prices",
    ]
    for path in data_paths:
        r = requests.get(f"{SMARTBIDDER_BASE}{path}", params=base_json, headers=H, timeout=20)
        body = r.text[:120].replace("\n", " | ")
        print(f"  [{r.status_code:3d}] {path:38s} body: {body}")

    # 3) Maybe a /reports or /api index
    print("\n=== Discovery endpoints ===")
    for path in ("/", "/api", "/api/v1", "/v1", "/openapi.json", "/swagger.json",
                 "/help", "/endpoints", "/api/help"):
        r = requests.get(f"{SMARTBIDDER_BASE}{path}", headers=H, timeout=15)
        body = r.text[:120].replace("\n", " | ")
        print(f"  [{r.status_code:3d}] {path:18s} body: {body}")

if __name__ == "__main__":
    main()
