"""Fetch GKS_BESS_RN hourly DA/RT LMP, 2024-01-01 .. 2026-09-22 (Yes Energy)."""
from __future__ import annotations
import sys, time
from datetime import date
from pathlib import Path
import requests, truststore
from requests.auth import HTTPBasicAuth

truststore.inject_into_ssl()

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "raw"
ITEMS = ["DALMP:GKS_BESS_RN", "RTLMP:GKS_BESS_RN"]

sec = load_env_sections(PROJECT_ROOT / ".env").get("yes_energy", {})
user, pwd = sec.get("YES_ENERGY_USERNAME"), sec.get("YES_ENERGY_PASSWORD")
if not user or not pwd:
    sys.exit("no yes_energy creds")

params = {
    "items": ",".join(ITEMS),
    "startdate": date(2024, 1, 1).isoformat(),
    "enddate": date(2026, 9, 22).isoformat(),
    "agglevel": "hour",
}
url = "https://services.yesenergy.com/PS/rest/timeseries/multiple.csv"
for attempt in range(3):
    try:
        r = requests.get(url, params=params, auth=HTTPBasicAuth(user, pwd), timeout=300)
        if r.status_code == 200:
            out = RAW / "ye_gks_lmp.csv"
            out.write_text(r.text, encoding="utf-8")
            print(f"OK {len(r.text)} bytes -> {out}")
            print(r.text[:300])
            sys.exit(0)
        if r.status_code == 401:
            sys.exit("YE 401 - credentials rejected")
        print(f"YE HTTP {r.status_code} {r.text[:200]!r}")
    except requests.RequestException as e:
        print(f"YE {type(e).__name__}: {e}")
    time.sleep([5, 10, 15][attempt])
sys.exit("YE fetch failed")
