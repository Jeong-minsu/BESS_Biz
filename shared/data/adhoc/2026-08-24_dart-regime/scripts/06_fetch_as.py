# -*- coding: utf-8 -*-
"""
DART regime analysis #06 — ERCOT DAM + RT AS MCPC, 2026-07-01 .. 2026-08-23.

DAM: np4-188-cd/dam_clear_price_for_cap  (hourly per product)
RT : np6-331-cd/rt_clear_price_cap       (15-min -> hourly mean)

Outputs: raw/as_dam_hourly.parquet, raw/as_rt_hourly.parquet
"""
from __future__ import annotations

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

ADHOC = Path(__file__).resolve().parents[1]
RAW = ADHOC / "raw"

ERCOT_BASE = "https://api.ercot.com/api/public-reports"
TOKEN_URL = ("https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/"
             "B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token")
CLIENT_ID = "fec253ea-0d06-4272-a5e6-b478baeecd70"
START, END = date(2026, 7, 1), date(2026, 8, 23)


def get_token(u, p):
    data = {"grant_type": "password", "username": u, "password": p,
            "scope": f"openid {CLIENT_ID} offline_access", "client_id": CLIENT_ID,
            "response_type": "id_token"}
    r = requests.post(TOKEN_URL, data=data, timeout=60)
    r.raise_for_status()
    return r.json()["id_token"]


def fetch_report(token, sub, report, retries=4):
    headers = {"Authorization": f"Bearer {token}", "Ocp-Apim-Subscription-Key": sub}
    page, total_pages, fields, rows = 1, None, None, []
    while True:
        params = {"size": 1000, "page": page,
                  "deliveryDateFrom": START.isoformat(),
                  "deliveryDateTo": END.isoformat()}
        for attempt in range(retries):
            try:
                r = requests.get(f"{ERCOT_BASE}{report}", params=params,
                                 headers=headers, timeout=120)
                if r.status_code == 200:
                    break
                if r.status_code == 401:
                    sys.exit("ERCOT 401")
                print(f"  HTTP {r.status_code} page={page} body={r.text[:150]!r}")
            except requests.RequestException as e:
                print(f"  {type(e).__name__} {e}")
            time.sleep([15, 30, 60, 120][min(attempt, 3)])
        else:
            sys.exit(f"page {page} failed")
        body = r.json()
        if total_pages is None:
            total_pages = body.get("_meta", {}).get("totalPages", 1)
            fields = [f["name"] for f in body.get("fields", [])]
            print(f"  {report}: pages={total_pages} fields={fields}")
        rows.extend(body.get("data", []))
        if page >= total_pages:
            break
        page += 1
        time.sleep(1.5)
    return pd.DataFrame(rows, columns=fields)


def main():
    sec = load_env_sections(PROJECT_ROOT / ".env").get("ercot", {})
    token = get_token(sec["ERCOT_USERNAME"], sec["ERCOT_PASSWORD"])
    sub = sec["ERCOT_SUBSCRIPTION_KEY"]

    # ---- DAM hourly ----
    dam = fetch_report(token, sub, "/np4-188-cd/dam_clear_price_for_cap")
    dam["MCPC"] = pd.to_numeric(dam["MCPC"], errors="coerce")
    dam["he"] = dam["hourEnding"].astype(str).str.split(":").str[0].astype(int)
    dam["date"] = pd.to_datetime(dam["deliveryDate"]).dt.date.astype(str)
    dam_pv = dam.pivot_table(index=["date", "he"], columns="ancillaryType",
                             values="MCPC", aggfunc="mean").reset_index()
    dam_pv.to_parquet(RAW / "as_dam_hourly.parquet", index=False)
    print(f"DAM hourly: {dam_pv.shape}, products={[c for c in dam_pv.columns if c not in ('date','he')]}")

    # ---- RT 15-min -> hourly mean ----
    rt = fetch_report(token, sub, "/np6-331-cd/rt_clear_price_cap")
    pcol = next(c for c in ["MCPC", "mcpc", "RTMCPC"] if c in rt.columns)
    prod = next(c for c in ["ancillaryType", "ASType", "asType"] if c in rt.columns)
    rt[pcol] = pd.to_numeric(rt[pcol], errors="coerce")
    rt["he"] = rt["deliveryHour"].astype(int)
    rt["date"] = pd.to_datetime(rt["deliveryDate"]).dt.date.astype(str)
    rt_pv = rt.pivot_table(index=["date", "he"], columns=prod,
                           values=pcol, aggfunc="mean").reset_index()
    rt_pv.to_parquet(RAW / "as_rt_hourly.parquet", index=False)
    print(f"RT hourly: {rt_pv.shape}, products={[c for c in rt_pv.columns if c not in ('date','he')]}")


if __name__ == "__main__":
    main()
