"""Probe ERCOT Public API for RT AS clearing price report endpoints (post-RTC+B)."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ERCOT_BASE = "https://api.ercot.com/api/public-reports"
TOKEN_URL = ("https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/"
             "B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token")
CLIENT_ID = "fec253ea-0d06-4272-a5e6-b478baeecd70"


def get_token(u, p):
    data = {
        "grant_type": "password", "username": u, "password": p,
        "scope": f"openid {CLIENT_ID} offline_access",
        "client_id": CLIENT_ID, "response_type": "id_token",
    }
    r = requests.post(TOKEN_URL, data=data, timeout=60)
    r.raise_for_status()
    return r.json()["id_token"]


# Candidate report IDs for SCED RT AS clearing prices (post-RTC).
# Strategy: try common patterns. The DAM AS (np4-188-cd) suggests np6-* for RT.
candidates = [
    "/np6-788-cd/rtm_clear_price_for_cap",
    "/np6-959-cd/rtm_clear_price_for_cap",
    "/np6-959-cd/sced_clear_price_for_cap",
    "/np6-905-cd/spp_node_zone_hub",                  # known: RT energy SPP
    "/np6-86-cd/shdw_prices_bnd_trns_const",
    "/np4-188-cd/dam_clear_price_for_cap",            # known: DAM AS MCPC
    # Possible RT AS (post-RTC):
    "/np6-787-cd/rtm_clear_price_for_cap",
    "/np6-321-cd/rtm_as_capacity",
    "/np6-732-cd",
    "/np6-787-cd",
    "/np6-787-cd/rtm_capacity_clearing_prices",
    "/np6-959-cd",
    "/np4-187-cd/dam_clear_capacity",
    # ERCOT also has "np4-742-cr": Resource AS Awards
    "/np4-742-cr/aw_capac_settle_pt",
    # Try generic discovery paths
    "/archive",
    "/",
    "",
]

def main():
    sec = load_env_sections(PROJECT_ROOT / ".env").get("ercot", {})
    user = sec.get("ERCOT_USERNAME"); pwd = sec.get("ERCOT_PASSWORD"); sub = sec.get("ERCOT_SUBSCRIPTION_KEY")
    token = get_token(user, pwd)
    headers = {"Authorization": f"Bearer {token}", "Ocp-Apim-Subscription-Key": sub}

    for path in candidates:
        url = f"{ERCOT_BASE}{path}"
        try:
            r = requests.get(url, headers=headers,
                             params={"size": 1, "page": 1,
                                     "deliveryDateFrom": "2026-02-01",
                                     "deliveryDateTo":   "2026-02-01"},
                             timeout=30)
            sample = r.text[:300].replace("\n", " | ")
            print(f"[{r.status_code}] {path}")
            print(f"   body: {sample[:250]}")
        except Exception as e:
            print(f"[ERR] {path} -> {type(e).__name__}: {e}")
        print()


if __name__ == "__main__":
    main()
