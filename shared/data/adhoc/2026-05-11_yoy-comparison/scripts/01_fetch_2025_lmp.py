"""
YoY comparison #01 — Yes Energy 2025 DA + RT LMP for GKS_BESS_RN (and HB_HOUSTON hub)
2025-02-14 .. 2025-04-30 (76 days, hourly).

Output:
    raw/ye_lmp_hourly_2025.csv
    derived/lmp_hourly_2025.parquet
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
START = date(2025, 2, 14)
END   = date(2025, 4, 30)
ITEMS = [
    "DALMP:GKS_BESS_RN",
    "RTLMP:GKS_BESS_RN",
    "DALMP:HB_HOUSTON",
    "RTLMP:HB_HOUSTON",
]


def fetch_ye_csv(user, pwd, items, start, end, retries=3):
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
                sys.exit("Yes Energy 401 - credentials rejected")
            print(f"  YE HTTP {r.status_code} (try {attempt+1}/{retries}) body[:200]={r.text[:200]!r}")
        except requests.RequestException as e:
            print(f"  YE {type(e).__name__}: {e} (try {attempt+1}/{retries})")
        time.sleep([5, 10, 15][min(attempt, 2)])
    sys.exit("Yes Energy fetch failed after retries")


def main():
    print(f"[01_fetch_2025_lmp] {START} -> {END}, items={ITEMS}")
    sec = load_env_sections(PROJECT_ROOT / ".env").get("yes_energy", {})
    user, pwd = sec.get("YES_ENERGY_USERNAME"), sec.get("YES_ENERGY_PASSWORD")
    if not user or not pwd:
        sys.exit("Missing YES_ENERGY credentials in [yes_energy] section")

    csv_text = fetch_ye_csv(user, pwd, ITEMS, START, END)
    raw_path = RAW_DIR / "ye_lmp_hourly_2025.csv"
    raw_path.write_text(csv_text, encoding="utf-8")
    print(f"  saved raw -> {raw_path.name} ({len(csv_text)} chars)")

    df = pd.read_csv(io.StringIO(csv_text))
    print(f"  columns: {df.columns.tolist()}")
    print(f"  shape: {df.shape}")
    print(f"  head:\n{df.head(3)}")

    if "HOURENDING" not in df.columns:
        sys.exit(f"Unexpected schema: {df.columns.tolist()[:10]}")

    id_cols   = [c for c in df.columns if c in ("DATETIME", "HOURENDING")]
    drop_cols = [c for c in df.columns if c in ("MARKETDAY", "PEAKTYPE", "MONTH", "YEAR")]
    val_cols  = [c for c in df.columns if c not in id_cols + drop_cols]

    long = df[id_cols + val_cols].melt(id_vars=id_cols, value_vars=val_cols,
                                        var_name="item_raw", value_name="price")
    long["price"] = pd.to_numeric(long["price"], errors="coerce")
    extracted = long["item_raw"].str.extract(r"^(?P<node>[^()]+?)\s*\((?P<data_type>[^)]+)\)\s*$")
    long["node"]      = extracted["node"].str.strip()
    long["data_type"] = extracted["data_type"].str.strip()
    long["he"]        = long["HOURENDING"].astype(int)
    long["datetime_ct"] = pd.to_datetime(long["DATETIME"], errors="coerce")
    long = long[["datetime_ct", "he", "data_type", "node", "price"]].dropna(subset=["price"])

    out = DERIVED / "lmp_hourly_2025.parquet"
    long.to_parquet(out, index=False)
    print(f"  saved tidy -> {out.name}  ({len(long)} rows)")
    print("\n  by node x type:")
    print(long.groupby(["node", "data_type"])["price"]
              .agg(["count", "mean", "min", "max"]).round(2))


if __name__ == "__main__":
    main()
