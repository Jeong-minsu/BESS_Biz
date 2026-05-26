"""
Backfill DA binding constraint history from Yes Energy datalake.

Source: yedatalake://ercot/transmission/constraints/da/{YYYYMMDD}.csv.gz
Range:  2020-02-01 through 2026-05-26 (today)
Output: data/interim/constraint_binding_history.parquet

Schema (output):
  date            DATE      - calendar date of the constraint record
  hour_ending     int       - hour ending (1-24, ERCOT convention)
  FACILITYID      int       - facility object ID
  facility_name   str       - FACILITYNAME from facility metadata
  CONTINGENCYID   int       - contingency object ID
  contingency_name str      - CONTINGENCYNAME from contingency metadata
  DATETIME        str       - original timestamp string from file
  TIMEZONE        str       - CDT or CST
  PRICE           float     - shadow price in $/MWh
  CONSTRAINTID    int       - constraint ID as reported by ERCOT
  CONSTRAINTNAME  str       - constraint name string
  LIMITMW         float     - thermal limit MW
  VALUEMW         float     - actual flow MW
  VIOLATEDMW      float     - violation amount MW
  REPORTED_NAME   str       - monitored element description
"""
from __future__ import annotations

import gzip
import io
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import boto3
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from _datalake_client import BUCKET, get_s3_client, read_ddl

START_DATE = date(2020, 2, 1)
END_DATE = date(2026, 5, 26)
DA_PREFIX = "ercot/transmission/constraints/da"
OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "interim" / "constraint_binding_history.parquet"
FACILITY_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "ercot" / "metadata" / "objects" / "facility.parquet"
CONTINGENCY_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "ercot" / "metadata" / "objects" / "contingency.parquet"

MAX_WORKERS = 16
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = [2, 4, 8]


def _get_col_names() -> list[str]:
    cols = read_ddl(DA_PREFIX)
    if cols:
        return [c["colName"] for c in cols]
    # Fallback from known schema if ddl.json unavailable
    return [
        "FACILITYID", "CONTINGENCYID", "DATETIME", "TIMEZONE", "CONTINGENCY",
        "ISO", "PRICE", "LOADID", "CONSTRAINTID", "CONSTRAINTNAME",
        "LIMITMW", "VALUEMW", "VIOLATEDMW", "REPORTED_NAME",
    ]


def _date_range(start: date, end: date) -> list[date]:
    days = []
    d = start
    while d <= end:
        days.append(d)
        d += timedelta(days=1)
    return days


def _fetch_one(d: date, col_names: list[str], s3_client) -> Optional[pd.DataFrame]:
    key = f"{DA_PREFIX}/{d.strftime('%Y%m%d')}.csv.gz"
    for attempt in range(RETRY_ATTEMPTS):
        try:
            obj = s3_client.get_object(Bucket=BUCKET, Key=key)
            raw = obj["Body"].read()
            with gzip.open(io.BytesIO(raw)) as f:
                df = pd.read_csv(f, header=None, names=col_names, low_memory=False)
            df["date"] = d
            # Parse hour from DATETIME (Period Ending convention)
            df["hour_ending"] = pd.to_datetime(df["DATETIME"], errors="coerce").dt.hour
            # hour=0 means midnight = HE24; keep as-is (HE convention: hour in file is HE value 0-23)
            return df
        except s3_client.exceptions.NoSuchKey:
            return None  # file simply doesn't exist for this date
        except Exception as e:
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_BACKOFF[attempt])
            else:
                print(f"  WARN: failed {d} after {RETRY_ATTEMPTS} attempts: {e}")
                return None
    return None


def _load_metadata_maps() -> tuple[dict, dict]:
    fac = pd.read_parquet(FACILITY_PATH)[["OBJECTID", "FACILITYNAME"]]
    fac_map = dict(zip(fac["OBJECTID"].astype("Int64"), fac["FACILITYNAME"]))

    cont = pd.read_parquet(CONTINGENCY_PATH)[["OBJECTID", "CONTINGENCYNAME"]]
    cont_map = dict(zip(cont["OBJECTID"].astype("Int64"), cont["CONTINGENCYNAME"]))
    return fac_map, cont_map


def run(start: date = START_DATE, end: date = END_DATE) -> pd.DataFrame:
    print(f"Loading column schema from ddl.json...")
    col_names = _get_col_names()
    print(f"  Columns ({len(col_names)}): {col_names}")

    print("Loading metadata join maps...")
    fac_map, cont_map = _load_metadata_maps()
    print(f"  facility map: {len(fac_map):,} entries")
    print(f"  contingency map: {len(cont_map):,} entries")

    days = _date_range(start, end)
    print(f"Fetching {len(days):,} daily files ({start} → {end}) with {MAX_WORKERS} workers...")

    s3 = get_s3_client()
    frames: list[pd.DataFrame] = []
    success = 0
    missing = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_fetch_one, d, col_names, s3): d for d in days}
        for i, future in enumerate(as_completed(futures), 1):
            df = future.result()
            if df is not None:
                frames.append(df)
                success += 1
            else:
                missing += 1
            if i % 200 == 0 or i == len(days):
                print(f"  Progress: {i}/{len(days)} | success={success} missing={missing}")

    print(f"Download complete. {success} files fetched, {missing} missing.")

    if not frames:
        raise RuntimeError("No data downloaded — cannot proceed.")

    print("Concatenating frames...")
    all_df = pd.concat(frames, ignore_index=True)

    # Apply metadata joins
    print("Joining facility and contingency names...")
    all_df["FACILITYID"] = pd.to_numeric(all_df["FACILITYID"], errors="coerce").astype("Int64")
    all_df["CONTINGENCYID"] = pd.to_numeric(all_df["CONTINGENCYID"], errors="coerce").astype("Int64")
    all_df["facility_name"] = all_df["FACILITYID"].map(fac_map)
    all_df["contingency_name"] = all_df["CONTINGENCYID"].map(cont_map)

    # Select and order output columns
    keep_cols = [
        "date", "hour_ending", "FACILITYID", "facility_name",
        "CONTINGENCYID", "contingency_name", "DATETIME", "TIMEZONE",
        "PRICE", "CONSTRAINTID", "CONSTRAINTNAME", "LIMITMW", "VALUEMW",
        "VIOLATEDMW", "REPORTED_NAME",
    ]
    all_df = all_df[[c for c in keep_cols if c in all_df.columns]]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Saving {len(all_df):,} rows → {OUT_PATH}")
    all_df.to_parquet(OUT_PATH, index=False)
    print("Done.")
    return all_df


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2020-02-01")
    parser.add_argument("--end", default="2026-05-26")
    parser.add_argument("--smoke", action="store_true", help="Smoke test: last 7 days only")
    args = parser.parse_args()

    if args.smoke:
        smoke_end = date(2026, 5, 26)
        smoke_start = smoke_end - timedelta(days=6)
        print(f"SMOKE TEST: {smoke_start} → {smoke_end}")
        df = run(start=smoke_start, end=smoke_end)
    else:
        start = date.fromisoformat(args.start)
        end = date.fromisoformat(args.end)
        df = run(start=start, end=end)

    print(f"\nResult shape: {df.shape}")
    print(f"Date range in data: {df['date'].min()} → {df['date'].max()}")
    print(f"PRICE stats: min={df['PRICE'].min():.3f}, max={df['PRICE'].max():.3f}, mean={df['PRICE'].mean():.3f}")
