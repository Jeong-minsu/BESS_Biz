"""
Adhoc AS-strategy backfill #02 — ERCOT Public API DAM AS Clearing Prices

Fetches hourly DAM AS clearing prices (MCPC) for 5 products:
  RegUp, RegDown, RRS (PFR/UFR/FFR), ECRS, NonSpin
2026-01-01 through 2026-03-06.

Endpoint: /np4-188-cd/dam_clear_price_for_cap

Output:
    raw/ercot_as_dam_mcpc_raw.json   (paginated raw)
    derived/as_dam_mcpc_hourly.parquet  (tidy long format)

Auth: OAuth B2C ROPC (id_token) + Subscription-Key header.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR    = ADHOC_ROOT / "raw"
DERIVED    = ADHOC_ROOT / "derived"
RAW_DIR.mkdir(parents=True, exist_ok=True)
DERIVED.mkdir(parents=True, exist_ok=True)

START = date(2026, 1, 1)
END   = date(2026, 3, 6)

ERCOT_API_BASE = "https://api.ercot.com/api/public-reports"
TOKEN_URL = ("https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/"
             "B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token")
CLIENT_ID = "fec253ea-0d06-4272-a5e6-b478baeecd70"

REPORT = "/np4-188-cd/dam_clear_price_for_cap"


def get_token(username: str, password: str) -> str:
    data = {
        "grant_type": "password",
        "username": username,
        "password": password,
        "scope": f"openid {CLIENT_ID} offline_access",
        "client_id": CLIENT_ID,
        "response_type": "id_token",
    }
    r = requests.post(TOKEN_URL, data=data, timeout=60)
    r.raise_for_status()
    return r.json()["id_token"]


def fetch_paginated(token: str, sub_key: str, params: dict, retries: int = 4):
    """Yield records from all pages."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Ocp-Apim-Subscription-Key": sub_key,
    }
    page = 1
    total_pages = None
    while True:
        p = {**params, "size": 1000, "page": page}
        for attempt in range(retries):
            try:
                r = requests.get(f"{ERCOT_API_BASE}{REPORT}", params=p,
                                 headers=headers, timeout=120)
                if r.status_code == 200:
                    break
                if r.status_code == 401:
                    sys.exit("ERCOT 401 - token rejected")
                print(f"  HTTP {r.status_code} page={page} try={attempt+1}/{retries}"
                      f" body[:200]={r.text[:200]!r}")
            except requests.RequestException as e:
                print(f"  {type(e).__name__}: {e} page={page} try={attempt+1}/{retries}")
            time.sleep([30, 60, 120, 300][min(attempt, 3)])
        else:
            sys.exit(f"ERCOT page {page} failed after retries")

        body = r.json()
        if total_pages is None:
            meta = body.get("_meta", {})
            total_pages = meta.get("totalPages", 1)
            print(f"  total pages: {total_pages}, total records (approx): {meta.get('totalRecords')}")
            field_names = [f["name"] for f in body.get("fields", [])]
            print(f"  fields: {field_names}")
            yield "FIELDS", field_names
        for row in body.get("data", []):
            yield "ROW", row
        if page >= total_pages:
            break
        page += 1
        time.sleep(3)  # be polite


def main() -> None:
    print(f"[02_fetch_as_history] {START} -> {END}")
    sec = load_env_sections(PROJECT_ROOT / ".env").get("ercot", {})
    user = sec.get("ERCOT_USERNAME")
    pwd  = sec.get("ERCOT_PASSWORD")
    sub  = sec.get("ERCOT_SUBSCRIPTION_KEY")
    if not all([user, pwd, sub]):
        sys.exit("Missing ERCOT credentials")

    print("  authenticating ...")
    token = get_token(user, pwd)
    print(f"  token acquired (len={len(token)})")

    # ERCOT API filter param naming for date is typically deliveryDateFrom / deliveryDateTo
    params = {
        "deliveryDateFrom": START.isoformat(),
        "deliveryDateTo":   END.isoformat(),
    }

    field_names = None
    rows = []
    for kind, payload in fetch_paginated(token, sub, params):
        if kind == "FIELDS":
            field_names = payload
        else:
            rows.append(payload)

    if not rows:
        sys.exit("No rows returned - check date param names or report id")

    print(f"  fetched {len(rows)} rows")
    raw_out = RAW_DIR / "ercot_as_dam_mcpc_raw.json"
    raw_out.write_text(json.dumps({"fields": field_names, "rows": rows[:5]}, indent=2),
                       encoding="utf-8")
    print(f"  saved sample raw -> {raw_out.name}")

    df = pd.DataFrame(rows, columns=field_names)
    print(f"  df shape: {df.shape}")
    print(f"  df head:\n{df.head(3)}")
    print(f"  df cols: {df.columns.tolist()}")

    out = DERIVED / "as_dam_mcpc_hourly.parquet"
    df.to_parquet(out, index=False)
    print(f"  saved tidy -> {out.name}  ({len(df)} rows)")


if __name__ == "__main__":
    main()
