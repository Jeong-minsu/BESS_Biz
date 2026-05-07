"""Probe Yes Energy /timeseries/multiple.csv to identify which items / separator works."""
from __future__ import annotations
import sys
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env_loader import load_env_sections

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
BASE = "https://services.yesenergy.com/PS/rest"
DATE = "2026-05-05"

TESTS = [
    # (label, items_string, separator_used)
    ("single LOAD_FORECAST:ERCOT (basic)",      "LOAD_FORECAST:ERCOT"),
    ("single LOAD_FORECAST_BID_CLOSE:ERCOT",    "LOAD_FORECAST_BID_CLOSE:ERCOT"),
    ("single LOAD_FORECAST_BID_CLOSE:WZ_ERCOT", "LOAD_FORECAST_BID_CLOSE:WZ_ERCOT"),
    ("single NET_LOAD_FORECAST_BID_CLOSE:ERCOT","NET_LOAD_FORECAST_BID_CLOSE:ERCOT"),
    ("single WIND_STWPF:GR_WEST (basic)",       "WIND_STWPF:GR_WEST"),
    ("single WIND_STWPF_BIDCLOSE:GR_WEST",      "WIND_STWPF_BIDCLOSE:GR_WEST"),
    ("single SOLAR_COPHSL_BIDCLOSE:ERCOT",      "SOLAR_COPHSL_BIDCLOSE:ERCOT"),
    ("single SOLAR_STPPF:ERCOT (basic)",        "SOLAR_STPPF:ERCOT"),
    ("multi via , (comma)",                     "LOAD_FORECAST:ERCOT,WIND_STWPF:GR_WEST"),
    ("multi via ; (semicolon — current code)",  "LOAD_FORECAST:ERCOT;WIND_STWPF:GR_WEST"),
]

def main():
    sec = load_env_sections(ENV_PATH).get("yes_energy", {})
    user, pwd = sec.get("YES_ENERGY_USERNAME"), sec.get("YES_ENERGY_PASSWORD")
    auth = HTTPBasicAuth(user, pwd)

    for label, items in TESTS:
        params = {"items": items, "startdate": DATE, "enddate": DATE, "agglevel": "hour"}
        r = requests.get(f"{BASE}/timeseries/multiple.csv", params=params, auth=auth, timeout=60)
        body = r.text[:200].replace("\n", " | ")
        print(f"[{r.status_code}] {label}")
        print(f"  body: {body}")
        print()

if __name__ == "__main__":
    main()
