"""
Adhoc AS-strategy backfill #03 — Yes Energy forecast (D-1 vintage) + actual

Fetches hourly:
- D-1 bidclose vintage forecasts: load, net-load, wind, solar
- Real-time actuals: load, wind, solar
2026-01-01 through 2026-03-06.

Output:
    raw/ye_forecast_actual_hourly.csv
    derived/forecast_actual_hourly.parquet  (long format)

Note: ERCOT bidclose forecasts are snapshot at DAM bid close (10:00 CT D-1).
For D-1 08:30 CT feasibility, this is the closest YE-exposed vintage; treat
as approximation (~1.5h after the user's actual decision time).
"""
from __future__ import annotations

import io
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

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

YES_BASE = "https://services.yesenergy.com/PS/rest"

START = date(2026, 1, 1)
END   = date(2026, 3, 6)

# Yes Energy items.
# LOAD_FORECAST_BID_CLOSE:* was retired (per fetch_market_data.py 2026-05-04 note);
# we use LOAD_FORECAST:ERCOT as the "basic" fallback. Wind/solar/net-load BIDCLOSE work.
ITEMS = [
    # Forecasts (D-1 vintage where possible)
    "LOAD_FORECAST:ERCOT",                     # basic load FC (latest model)
    "NET_LOAD_FORECAST_BID_CLOSE:ERCOT",       # net-load bidclose
    "WIND_STWPF_BIDCLOSE:ERCOT",               # wind STWPF bidclose
    "WIND_COPHSL_BIDCLOSE:ERCOT",              # wind COPHSL bidclose
    "SOLAR_COPHSL_BIDCLOSE:ERCOT",             # solar COPHSL bidclose
    # Actuals (real-time aggregated)
    "RTLOAD:ERCOT",                            # actual load
    "WIND_RTI:ERCOT",                          # actual wind
    # SOLAR_RTI:ERCOT does not exist in YE catalog; try alternatives below
    "SOLAR_GENERATION:ERCOT",                  # try this first
]


def fetch_ye_csv(user: str, pwd: str, items: list[str], start: date, end: date,
                 retries: int = 3) -> str:
    params = {
        "items":     ",".join(items),
        "startdate": start.isoformat(),
        "enddate":   end.isoformat(),
        "agglevel":  "hour",
    }
    url = f"{YES_BASE}/timeseries/multiple.csv"
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, auth=HTTPBasicAuth(user, pwd), timeout=180)
            if r.status_code == 200:
                return r.text
            if r.status_code == 401:
                sys.exit("YE 401 - credentials rejected")
            print(f"  YE HTTP {r.status_code} (try {attempt+1}/{retries}) body[:200]={r.text[:200]!r}")
        except requests.RequestException as e:
            print(f"  YE {type(e).__name__}: {e} (try {attempt+1}/{retries})")
        time.sleep([5, 10, 15][min(attempt, 2)])
    sys.exit("YE fetch failed")


def main() -> None:
    print(f"[03_fetch_forecast_actual] {START} -> {END}, {len(ITEMS)} items")
    sec = load_env_sections(PROJECT_ROOT / ".env").get("yes_energy", {})
    user, pwd = sec.get("YES_ENERGY_USERNAME"), sec.get("YES_ENERGY_PASSWORD")
    if not user or not pwd:
        sys.exit("Missing YE creds")

    csv_text = fetch_ye_csv(user, pwd, ITEMS, START, END)
    raw_path = RAW_DIR / "ye_forecast_actual_hourly.csv"
    raw_path.write_text(csv_text, encoding="utf-8")
    print(f"  saved raw -> {raw_path.name} ({len(csv_text)} chars)")

    df = pd.read_csv(io.StringIO(csv_text))
    print(f"  shape: {df.shape}")
    print(f"  columns: {df.columns.tolist()}")

    if "HOURENDING" not in df.columns:
        sys.exit("Bad schema")
    drop_cols = [c for c in df.columns if c in ("MARKETDAY", "PEAKTYPE", "MONTH", "YEAR")]
    id_cols = ["DATETIME", "HOURENDING"]
    val_cols = [c for c in df.columns if c not in id_cols + drop_cols]

    long = df[id_cols + val_cols].melt(id_vars=id_cols, value_vars=val_cols,
                                        var_name="item_raw", value_name="value")
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    extracted = long["item_raw"].str.extract(
        r"^(?P<node>[^()]+?)\s*\((?P<data_type>[^)]+)\)\s*$"
    )
    long["node"] = extracted["node"].str.strip()
    long["data_type"] = extracted["data_type"].str.strip()
    long["he"] = long["HOURENDING"].astype(int)
    long["datetime_ct"] = pd.to_datetime(long["DATETIME"], errors="coerce")
    long = long[["datetime_ct", "he", "data_type", "node", "value"]].dropna(subset=["value"])

    out = DERIVED / "forecast_actual_hourly.parquet"
    long.to_parquet(out, index=False)
    print(f"  saved tidy -> {out.name}  ({len(long)} rows)")

    print("\n  by data_type:")
    print(long.groupby("data_type")["value"].agg(["count", "mean", "min", "max"]).round(0))


if __name__ == "__main__":
    main()
