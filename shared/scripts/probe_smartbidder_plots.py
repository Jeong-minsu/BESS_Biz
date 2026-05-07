"""Probe Smartbidder /plots/* — find which AS-related plot type returns 200."""
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

# All 35 plot_type values listed in API doc
PLOT_TYPES = [
    "Energy Price Forecasts",                      # known good, baseline
    "Ancillary Price Forecasts",                   # what we want; got 404
    "Ancillary Throughput Forecasts",
    "Ancillary Spread Forecast",
    "Ancillary Bids",
    "Ancillary Prices",
    "DA-RT Forecast",
    "RT Price Spike Probabilities",
    "Hourly Average DA-RT Spread",
    "DA Energy Prices",
    "RT Energy Prices",
    "Power Availability",
    "Renewable Generation",
    "DA Renewable Forecast",
    "Average Sale Price",
    "Average SOC",
]

def main():
    sec = load_env_sections(ENV_PATH).get("smartbidder", {})
    tok = smartbidder_token(sec)
    H = {"Authorization": f"Bearer {tok}", "Accept": "text/csv"}
    client   = first(sec, "SMARTBIDDER_CLIENT", default="apex")
    resource = first(sec, "Resource", "SMARTBIDDER_RESOURCE", default="Kiskadee Storage")
    params_base = {
        "client": client, "iso": "ERCOT", "resource": resource,
        "start_date": f"{TARGET.isoformat()}T00:00:00-05:00",
        "end_date":   f"{NEXT.isoformat()}T00:00:00-05:00",
    }

    for plot in PLOT_TYPES:
        url = f"{SMARTBIDDER_BASE}/plots/{urllib.parse.quote(plot)}"
        r = requests.get(url, params=params_base, headers=H, timeout=30)
        body = r.text[:160].replace("\n", " | ")
        print(f"[{r.status_code:3d}] {plot:38s} body[:160]={body}")

if __name__ == "__main__":
    main()
