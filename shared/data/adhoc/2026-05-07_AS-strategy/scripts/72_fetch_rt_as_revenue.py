"""
Backfill #72 — Tenaska PTP Settlement-Charge-Details: GKS RT AS revenue (NS/RRS/ECRS)

Discovered via probe #71: RT AS revenue lives in `Settlement-Charge-Details` as ERCOT
charge codes RTNSIMBAMT / RTRRIMBAMT / RTECRIMBAMT (15-min settlement intervals),
ByIdentifier on the GKS ESR UUID.

Fetches 2026-01-01 .. 2026-05-10 in monthly chunks.

Output:
  raw/tenaska_rt_as_revenue_raw/<chunk>.json
  derived/rt_as_revenue_15min.parquet   (tidy: datetime_ct, charge_code, value)
"""
from __future__ import annotations
import base64, json, sys, time, urllib.parse
from datetime import date
from pathlib import Path
import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections, first  # noqa

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://api.ptp.energy"
ROOT = "ERCOTNodal"
ENDPOINT = "Settlement-Charge-Details"
GKS_ESR_UUID = "ef8d8d31-47c4-4212-b893-a2dbb2070a2f"
CODES = ["RTNSIMBAMT", "RTNSOAMT", "RTNSTOAMT",
         "RTRRIMBAMT", "RTRROAMT", "RTRRTOAMT",
         "RTECRIMBAMT", "RTECROAMT", "RTECRTOAMT"]

ADHOC = Path(__file__).resolve().parents[1]
RAWDIR = ADHOC / "raw" / "tenaska_rt_as_revenue_raw"
RAWDIR.mkdir(parents=True, exist_ok=True)
OUT = ADHOC / "derived" / "rt_as_revenue_15min.parquet"

CHUNKS = [  # (begin, end) flowday inclusive
    ("2026-01-01", "2026-01-31"),
    ("2026-02-01", "2026-02-28"),
    ("2026-03-01", "2026-03-31"),
    ("2026-04-01", "2026-04-30"),
    ("2026-05-01", "2026-05-10"),
]


def get_token(tk):
    u, p = first(tk, "TENASKA_USERNAME", "USERNAME"), first(tk, "TENASKA_PASSWORD", "PASSWORD")
    basic = base64.b64encode(f"{u}:{p}".encode()).decode()
    r = requests.get(f"{BASE}/authentication/token",
                     headers={"Authorization": f"Basic {basic}"}, timeout=30)
    r.raise_for_status()
    return r.json()["data"]


def flatten(j):
    rows = []
    for el in j.get("data", []) or []:
        for dp in el.get("dataPoints", []) or []:
            kn = dp.get("keyName")
            for v in dp.get("values", []) or []:
                for d in v.get("data", []) or []:
                    rows.append({"charge_code": kn,
                                 "interval_start_utc": v.get("intervalStartUtc"),
                                 "interval_end_utc": v.get("intervalEndUtc"),
                                 "value": d.get("value"),
                                 "sequence": d.get("sequence")})
    return rows


def main():
    tk = load_env_sections(PROJECT_ROOT / ".env").get("tenaska", {})
    tok = get_token(tk)
    H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    url = f"{BASE}/ptp/{ROOT}/{urllib.parse.quote(ENDPOINT)}/query"

    all_rows = []
    for begin, end in CHUNKS:
        payload = {"begin": begin, "end": end,
                   "elementQueryMode": "ByIdentifier",
                   "elementIdentifiers": [GKS_ESR_UUID],
                   "sequenceOptions": "GreatestEnabled",
                   "dataPoints": CODES}
        for attempt in range(4):
            try:
                r = requests.post(url, json=payload, headers=H, timeout=180)
                if r.status_code == 200:
                    break
                print(f"  HTTP {r.status_code} {begin}..{end} try{attempt+1}: {r.text[:200]}")
                if r.status_code == 401:
                    tok = get_token(tk); H["Authorization"] = f"Bearer {tok}"
            except requests.RequestException as e:
                print(f"  {type(e).__name__} {begin}..{end}: {e}")
            time.sleep([5, 15, 30, 60][attempt])
        else:
            sys.exit(f"chunk {begin}..{end} failed")
        j = r.json()
        (RAWDIR / f"{begin}_{end}.json").write_text(json.dumps(j, default=str), encoding="utf-8")
        for v in j.get("validations", []):
            print(f"  validation [{v.get('severity')} {v.get('code')}]: {v.get('message')}")
        rows = flatten(j)
        all_rows += rows
        nz = sum(1 for x in rows if isinstance(x["value"], (int, float)) and x["value"] != 0)
        print(f"  {begin}..{end}: {len(rows)} rows ({nz} nonzero)")
        time.sleep(1.3)  # rate limit

    df = pd.DataFrame(all_rows)
    df["interval_start_utc"] = pd.to_datetime(df["interval_start_utc"], utc=True)
    df["datetime_ct"] = df["interval_start_utc"].dt.tz_convert("America/Chicago")
    df = df.sort_values(["charge_code", "interval_start_utc"]).reset_index(drop=True)
    df.to_parquet(OUT, index=False)
    print(f"\nsaved -> {OUT}  ({len(df)} rows)")
    print("\nper charge_code: nonzero count + sum")
    g = df.assign(nz=df["value"].fillna(0) != 0).groupby("charge_code").agg(
        n=("value", "size"), nonzero=("nz", "sum"), total=("value", "sum"))
    print(g.to_string())


if __name__ == "__main__":
    main()
