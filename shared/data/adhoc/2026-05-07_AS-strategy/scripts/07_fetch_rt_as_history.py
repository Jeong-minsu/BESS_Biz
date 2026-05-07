"""
Adhoc AS-strategy backfill #07 — ERCOT NP6-331-CD: RT 15-min AS Clearing Prices

Post-RTC+B (2025-12-05~) Real-Time Market clears AS in SCED. This report publishes
15-minute settlement-interval AS MCPCs for each product (RegUp/Dn, RRS, ECRS, NSpin).

Fetches 2026-01-01 ~ 2026-03-06.

Output:
  raw/ercot_rt_as_15min.parquet   (15-min settlement)
  derived/rt_as_hourly.parquet    (hourly mean MCPC)
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

ADHOC = Path(__file__).resolve().parents[1]
RAW = ADHOC / "raw"
DERIVED = ADHOC / "derived"
RAW.mkdir(parents=True, exist_ok=True)
DERIVED.mkdir(parents=True, exist_ok=True)

ERCOT_BASE = "https://api.ercot.com/api/public-reports"
TOKEN_URL = ("https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/"
             "B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token")
CLIENT_ID = "fec253ea-0d06-4272-a5e6-b478baeecd70"

REPORT = "/np6-331-cd/rt_clear_price_cap"
START = date(2026, 1, 1)
END   = date(2026, 3, 6)


def get_token(u, p):
    data = {"grant_type":"password","username":u,"password":p,
            "scope":f"openid {CLIENT_ID} offline_access","client_id":CLIENT_ID,
            "response_type":"id_token"}
    r = requests.post(TOKEN_URL, data=data, timeout=60); r.raise_for_status()
    return r.json()["id_token"]


def fetch_paginated(token, sub, start: date, end: date, retries=4):
    headers = {"Authorization": f"Bearer {token}", "Ocp-Apim-Subscription-Key": sub}
    page = 1
    total_pages = None
    field_names = None
    rows = []
    while True:
        params = {"size": 1000, "page": page,
                  "deliveryDateFrom": start.isoformat(),
                  "deliveryDateTo":   end.isoformat()}
        for attempt in range(retries):
            try:
                r = requests.get(f"{ERCOT_BASE}{REPORT}", params=params,
                                 headers=headers, timeout=120)
                if r.status_code == 200:
                    break
                if r.status_code == 401:
                    sys.exit("ERCOT 401 - re-auth needed")
                print(f"  HTTP {r.status_code} page={page} try={attempt+1}/{retries}"
                      f" body={r.text[:200]!r}")
            except requests.RequestException as e:
                print(f"  {type(e).__name__} {e} page={page}")
            time.sleep([30,60,120,300][min(attempt,3)])
        else:
            sys.exit(f"page {page} failed")
        body = r.json()
        if total_pages is None:
            meta = body.get("_meta", {})
            total_pages = meta.get("totalPages", 1)
            field_names = [f["name"] for f in body.get("fields", [])]
            print(f"  total pages: {total_pages}, total records: {meta.get('totalRecords')}")
            print(f"  fields: {field_names}")
        rows.extend(body.get("data", []))
        if page >= total_pages:
            break
        page += 1
        if page % 10 == 0:
            print(f"  ... page {page}/{total_pages} ({len(rows)} rows so far)")
        time.sleep(1.5)
    return field_names, rows


def main():
    print(f"[07_fetch_rt_as] {START} -> {END}")
    sec = load_env_sections(PROJECT_ROOT / ".env").get("ercot", {})
    token = get_token(sec["ERCOT_USERNAME"], sec["ERCOT_PASSWORD"])
    print(f"  authenticated")

    fields, rows = fetch_paginated(token, sec["ERCOT_SUBSCRIPTION_KEY"], START, END)
    df = pd.DataFrame(rows, columns=fields)
    print(f"  fetched {len(df)} rows")
    print(f"  head:\n{df.head(3)}")
    print(f"  cols: {df.columns.tolist()}")

    raw_out = RAW / "ercot_rt_as_15min.parquet"
    df.to_parquet(raw_out, index=False)
    print(f"  saved raw -> {raw_out.name}")

    # ============= Aggregate to hourly =============
    # 15-min settlement intervals -> hourly mean MCPC per product
    # Common ERCOT field names: deliveryDate, deliveryHour (1-24), deliveryInterval (1-4),
    # ancillaryType, MCPC. Adjust if different.
    print(f"\n  unique columns: {df.columns.tolist()}")
    print(f"  unique ancillaryType (if present): "
          f"{df.get('ancillaryType', pd.Series()).unique()[:10]}")

    # Try common time field names
    if "deliveryDate" in df.columns and "deliveryHour" in df.columns:
        df["hour"] = df["deliveryHour"].astype(int)  # HE 1-24
        df["delivery_date"] = pd.to_datetime(df["deliveryDate"]).dt.date
        df["datetime_ct"] = (
            pd.to_datetime(df["delivery_date"]) + pd.to_timedelta(df["hour"] - 1, unit="h")
        ).dt.tz_localize("America/Chicago", ambiguous="infer", nonexistent="shift_forward")
    else:
        print(f"  WARN: time fields not found in expected layout. Cannot pivot to hourly.")
        return

    # Find product field
    product_col = None
    for c in ["ASType", "ancillaryType", "AncillaryType", "ancillary_type", "asType"]:
        if c in df.columns:
            product_col = c
            break
    price_col = None
    for c in ["MCPC", "mcpc", "RTMCPC", "RT_MCPC", "price"]:
        if c in df.columns:
            price_col = c
            break
    print(f"  using product_col={product_col}, price_col={price_col}")
    if not product_col or not price_col:
        sys.exit("Cannot find product/price columns")

    df[price_col] = pd.to_numeric(df[price_col], errors="coerce")
    hourly = (df.groupby(["datetime_ct", product_col])[price_col]
                .mean()
                .reset_index()
                .rename(columns={product_col: "ancillary_type", price_col: "mcpc"}))
    hourly["he"] = hourly["datetime_ct"].dt.hour + 1
    hourly_pv = hourly.pivot_table(index="datetime_ct", columns="ancillary_type", values="mcpc")
    hourly_pv.columns = [f"RT_AS_MCPC_{c}" for c in hourly_pv.columns]
    hourly_pv = hourly_pv.reset_index()

    out = DERIVED / "rt_as_hourly.parquet"
    hourly_pv.to_parquet(out, index=False)
    print(f"  saved hourly -> {out.name}  ({hourly_pv.shape})")
    print(f"\n  RT AS mean by product:")
    for c in [col for col in hourly_pv.columns if col.startswith("RT_AS_MCPC_")]:
        s = hourly_pv[c].dropna()
        print(f"    {c:25s}  mean={s.mean():>7.2f}  median={s.median():>6.2f}  "
              f"max={s.max():>7.2f}  count={len(s)}")


if __name__ == "__main__":
    main()
