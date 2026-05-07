"""Probe NP6-331-CD endpoint structure to learn the URL pattern + params."""
from __future__ import annotations
import sys, json
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
    data = {"grant_type":"password","username":u,"password":p,
            "scope":f"openid {CLIENT_ID} offline_access","client_id":CLIENT_ID,
            "response_type":"id_token"}
    r = requests.post(TOKEN_URL, data=data, timeout=60); r.raise_for_status()
    return r.json()["id_token"]


def main():
    sec = load_env_sections(PROJECT_ROOT / ".env").get("ercot", {})
    token = get_token(sec["ERCOT_USERNAME"], sec["ERCOT_PASSWORD"])
    headers = {"Authorization": f"Bearer {token}", "Ocp-Apim-Subscription-Key": sec["ERCOT_SUBSCRIPTION_KEY"]}

    # First fetch parent description
    r = requests.get(f"{ERCOT_BASE}/np6-331-cd", headers=headers, timeout=30)
    print(f"[parent] {r.status_code}")
    print(json.dumps(r.json(), indent=2)[:1500])
    print()

    # Try common sub-paths
    for sub in ["", "/rtm_clear_price_for_cap", "/clear_price_for_cap",
                "/rtm_capacity_clear_price", "/15min_clear_price_for_cap",
                "/15_min_clear_price_for_cap", "/rt_clear_price",
                "/clearing_prices", "/data"]:
        url = f"{ERCOT_BASE}/np6-331-cd{sub}"
        r = requests.get(url, headers=headers,
                         params={"size":1, "page":1,
                                 "deliveryDateFrom":"2026-02-01",
                                 "deliveryDateTo":"2026-02-01"},
                         timeout=30)
        print(f"[{r.status_code}] {url}")
        print(f"   body: {r.text[:300]}")
        print()


if __name__ == "__main__":
    main()
