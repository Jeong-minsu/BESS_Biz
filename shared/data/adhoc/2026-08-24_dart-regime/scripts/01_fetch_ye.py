"""
DART regime analysis #01 — Yes Energy fetch, 2026-07-01 .. 2026-08-23.

Items:
  DALMP / RTLMP for GKS_BESS_RN                     (hourly LMP)
  NET_LOAD_FORECAST_BID_CLOSE:ERCOT                 (D-1 bid-close vintage, leakage-free)
  WIND_STWPF_BIDCLOSE:GR_SOUTH / GR_COASTAL         (D-1 bid-close wind FC)

Output: raw/ye_lmp_fc.csv
"""
from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC = Path(__file__).resolve().parents[1]
RAW = ADHOC / "raw"
RAW.mkdir(parents=True, exist_ok=True)

YES_BASE = "https://services.yesenergy.com/PS/rest"
START = date(2026, 7, 1)
END = date(2026, 8, 23)

ITEMS = [
    "DALMP:GKS_BESS_RN",
    "RTLMP:GKS_BESS_RN",
    "NET_LOAD_FORECAST_BID_CLOSE:ERCOT",
    "WIND_STWPF_BIDCLOSE:GR_SOUTH",
    "WIND_STWPF_BIDCLOSE:GR_COASTAL",
]


def main() -> None:
    sec = load_env_sections(PROJECT_ROOT / ".env").get("yes_energy", {})
    user, pwd = sec.get("YES_ENERGY_USERNAME"), sec.get("YES_ENERGY_PASSWORD")
    if not user or not pwd:
        sys.exit("no yes_energy creds")

    params = {
        "items": ",".join(ITEMS),
        "startdate": START.isoformat(),
        "enddate": END.isoformat(),
        "agglevel": "hour",
    }
    url = f"{YES_BASE}/timeseries/multiple.csv"
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, auth=HTTPBasicAuth(user, pwd), timeout=180)
            if r.status_code == 200:
                out = RAW / "ye_lmp_fc.csv"
                out.write_text(r.text, encoding="utf-8")
                print(f"OK {len(r.text)} bytes -> {out}")
                print(r.text[:300])
                return
            if r.status_code == 401:
                sys.exit("YE 401 - credentials rejected")
            print(f"YE HTTP {r.status_code} body[:200]={r.text[:200]!r}")
        except requests.RequestException as e:
            print(f"YE {type(e).__name__}: {e}")
        time.sleep([5, 10, 15][attempt])
    sys.exit("YE fetch failed")


if __name__ == "__main__":
    main()
