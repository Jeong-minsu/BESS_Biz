# -*- coding: utf-8 -*-
"""
DART regime analysis #06b — RT AS MCPC gap fill via NP6-332-CD (SCED 5-min).

np6-331-cd (15-min settlement) stopped publishing 2026-07-30 14:00; np6-332-cd
(same MCPCs, per SCED run) is live. Fetch 2026-07-30 .. 2026-08-23, aggregate
to hourly mean per product, merge into raw/as_rt_hourly.parquet.
"""
from __future__ import annotations

import sys
import time
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


def get_token(u, p):
    data = {"grant_type": "password", "username": u, "password": p,
            "scope": f"openid {CLIENT_ID} offline_access", "client_id": CLIENT_ID,
            "response_type": "id_token"}
    r = requests.post(TOKEN_URL, data=data, timeout=60)
    r.raise_for_status()
    return r.json()["id_token"]


def main():
    sec = load_env_sections(PROJECT_ROOT / ".env").get("ercot", {})
    token = get_token(sec["ERCOT_USERNAME"], sec["ERCOT_PASSWORD"])
    h = {"Authorization": f"Bearer {token}",
         "Ocp-Apim-Subscription-Key": sec["ERCOT_SUBSCRIPTION_KEY"]}

    page, total_pages, fields, rows = 1, None, None, []
    while True:
        params = {"size": 1000, "page": page,
                  "SCEDTimestampFrom": "2026-07-30T00:00:00",
                  "SCEDTimestampTo": "2026-08-24T00:00:00"}
        for attempt in range(4):
            try:
                r = requests.get(f"{ERCOT_BASE}/np6-332-cd/rt_clear_price_cap_sced",
                                 params=params, headers=h, timeout=120)
                if r.status_code == 200:
                    break
                print(f"  HTTP {r.status_code} page={page} body={r.text[:150]!r}")
            except requests.RequestException as e:
                print(f"  {type(e).__name__} {e}")
            time.sleep([15, 30, 60, 120][min(attempt, 3)])
        else:
            sys.exit(f"page {page} failed")
        b = r.json()
        if total_pages is None:
            total_pages = b["_meta"]["totalPages"]
            fields = [f["name"] for f in b.get("fields", [])]
            print(f"  pages={total_pages} records={b['_meta']['totalRecords']} fields={fields}")
        rows.extend(b.get("data", []))
        if page >= total_pages:
            break
        page += 1
        if page % 10 == 0:
            print(f"  page {page}/{total_pages}")
        time.sleep(1.2)

    df = pd.DataFrame(rows, columns=fields)
    df["MCPC"] = pd.to_numeric(df["MCPC"], errors="coerce")
    ts = pd.to_datetime(df["SCEDTimestamp"])
    df["date"] = ts.dt.date.astype(str)
    df["he"] = ts.dt.hour + 1
    pv = df.pivot_table(index=["date", "he"], columns="ASType",
                        values="MCPC", aggfunc="mean").reset_index()
    pv = pv[(pv["date"] >= "2026-07-30") & (pv["date"] <= "2026-08-23")]

    old = pd.read_parquet(RAW / "as_rt_hourly.parquet")
    comb = (pd.concat([old[old["date"] < "2026-07-30"], pv])
            .drop_duplicates(subset=["date", "he"]).sort_values(["date", "he"]))
    comb.to_parquet(RAW / "as_rt_hourly.parquet", index=False)
    cnt = comb.groupby("date").size()
    print(f"combined: {comb.shape}, {comb['date'].min()}..{comb['date'].max()}, "
          f"days={comb['date'].nunique()}, incomplete={cnt[cnt < 24].to_dict()}")


if __name__ == "__main__":
    main()
