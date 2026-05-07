"""Browse ERCOT API report catalog and find AS-related reports."""
from __future__ import annotations

import json
import re
import sys
import time
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


def main():
    sec = load_env_sections(PROJECT_ROOT / ".env").get("ercot", {})
    token = get_token(sec["ERCOT_USERNAME"], sec["ERCOT_PASSWORD"])
    headers = {"Authorization": f"Bearer {token}", "Ocp-Apim-Subscription-Key": sec["ERCOT_SUBSCRIPTION_KEY"]}

    all_products = []
    page = 1
    while True:
        r = requests.get(ERCOT_BASE + "/", headers=headers,
                         params={"size": 100, "page": page}, timeout=60)
        r.raise_for_status()
        body = r.json()
        prods = body.get("_embedded", {}).get("products", [])
        if not prods:
            break
        all_products.extend(prods)
        meta = body.get("_meta", {}) or body.get("page", {})
        total = meta.get("totalPages") or meta.get("totalElements") or 1
        if page >= total or len(prods) < 100:
            break
        page += 1
        time.sleep(2)
    print(f"Found {len(all_products)} products total")

    # Save for later
    out = Path(__file__).resolve().parents[1] / "raw" / "ercot_product_catalog.json"
    out.write_text(json.dumps(all_products, indent=2), encoding="utf-8")

    # Search AS-related
    as_pattern = re.compile(r"ancillary|capacity.*price|cleared.*price|reserve|sced|rtm|spinning|reg|frequency",
                            re.IGNORECASE)
    matches = []
    for p in all_products:
        name = p.get("name", "")
        desc = p.get("description", "")
        if as_pattern.search(name) or as_pattern.search(desc):
            matches.append(p)

    print(f"\nAS / SCED / RTM-related products ({len(matches)}):")
    for p in sorted(matches, key=lambda x: x.get("emilId","")):
        emil = p.get("emilId", "")
        name = p.get("name", "")
        gen = p.get("generationFrequency","")
        print(f"  [{emil:14s}] {name}  ({gen})")
    print(f"\nFull catalog saved -> {out}")


if __name__ == "__main__":
    main()
