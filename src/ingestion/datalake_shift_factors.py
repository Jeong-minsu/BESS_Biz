"""
Backfill the 4 DA shift factor variants from the Yes Energy datalake.

Variants (in execution order):
  shift_factors            — pricenode + QUALITY_METRIC         (0.42 GB gz, tiny)
  settle_shift_factors_ercot — SP-level settlement PTDF          (~17 GB gz)
  market_shift_factors     — pricenode DAM/RT PTDF + SHADOWPRICE (~31 GB gz)
  ercot_sced_shift_factors — resource-level SCED PTDF            (~27 GB gz)

Window: 2020-02-01 through 2026-05-26 (settle_shift_factors starts 2020-02;
all others have earlier history but we cap at the same start for alignment).

Output: data/raw/ercot/transmission/constraints/{variant}/year=YYYY/part.parquet

Column pruning decision (2026-05-26):
  Redundant columns dropped to fit within available disk (~30 GB):
    LOADID       — batch process ID, not analytically useful
    TIMEZONE     — derivable from DATETIME + ERCOT CT zone rule
    CONSTRAINTNAME — join from contingency metadata
    CONTINGENCY  (ercot_sced, settle) — same as CONSTRAINTNAME; in metadata
    SHADOWPRICE  (market) — redundant with PRICE in DA constraints
    LIMIT        (market) — redundant with LIMITMW in DA constraints

  Retained per variant:
    market_shift_factors:     PRICENODEID, FACILITYID, CONTINGENCYID, DATETIME, MARKET, SHIFTFACTOR
    ercot_sced_shift_factors: DATETIME, CONSTRAINTID, RESOURCENAME, SETTLEMENTPOINT, SHIFTFACTOR
    settle_shift_factors:     DATETIME, CONSTRAINTID, SETTLEMENTPOINT, SHIFTFACTOR
    shift_factors:            all 10 columns (dataset is tiny, ~0.2 GB)

Streaming write: uses pyarrow.parquet.ParquetWriter for incremental per-day appends
so peak memory stays bounded to one parallel batch (16 workers × ~800K rows ≈ ~0.5 GB).
"""
from __future__ import annotations

import gzip
import io
import json
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import threading

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

_INGESTION_DIR = Path(__file__).resolve().parents[0]
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "shared" / "scripts"
sys.path.insert(0, str(_INGESTION_DIR))
sys.path.insert(0, str(_SCRIPTS_DIR))
from _datalake_client import BUCKET, read_ddl
from _env_loader import load_env_sections

# Thread-local boto3 clients — boto3 clients must not be shared across threads
_thread_local = threading.local()


def _get_thread_client():
    if not hasattr(_thread_local, "client"):
        creds = load_env_sections().get("yes_energy_s3", {})
        _thread_local.client = boto3.client(
            "s3",
            aws_access_key_id=creds["YES_ENERGY_ACCESS_KEY"],
            aws_secret_access_key=creds["YES_ENERGY_SECRET_KEY"],
        )
    return _thread_local.client

START_DATE = date(2020, 2, 1)
END_DATE = date(2026, 5, 26)
BASE_PREFIX = "ercot/transmission/constraints"
OUT_BASE = Path(__file__).resolve().parents[2] / "data" / "raw" / "ercot" / "transmission" / "constraints"

MAX_WORKERS = 8
# Bounded batch size: never hold more than MAX_WORKERS DataFrames in memory at once.
# Submitting all days upfront causes OOM when downloads complete faster than parquet writes.
BATCH_SIZE = MAX_WORKERS
RETRY_BACKOFF = [2, 4, 8]

# Columns to retain per variant (None = all columns)
KEEP_COLS: dict[str, list[str] | None] = {
    "market_shift_factors": [
        "PRICENODEID", "FACILITYID", "CONTINGENCYID", "DATETIME", "MARKET", "SHIFTFACTOR",
    ],
    "ercot_sced_shift_factors": [
        "DATETIME", "CONSTRAINTID", "RESOURCENAME", "SETTLEMENTPOINT", "SHIFTFACTOR",
    ],
    "settle_shift_factors_ercot": [
        "DATETIME", "CONSTRAINTID", "SETTLEMENTPOINT", "SHIFTFACTOR",
    ],
    "shift_factors": None,  # keep all — tiny dataset
}

# Processing order: smallest first, W2 exit gate (market) before largest (sced)
VARIANT_ORDER = [
    "shift_factors",
    "settle_shift_factors_ercot",
    "market_shift_factors",
    "ercot_sced_shift_factors",
]


def _get_col_names(variant: str) -> list[str] | None:
    cols = read_ddl(f"{BASE_PREFIX}/{variant}")
    return [c["colName"] for c in cols] if cols else None


def _fetch_one(
    d: date, variant: str, col_names: list[str] | None,
    keep: list[str] | None,
) -> Optional[pd.DataFrame]:
    key = f"{BASE_PREFIX}/{variant}/{d.strftime('%Y%m%d')}.csv.gz"
    client = _get_thread_client()
    for attempt in range(3):
        try:
            obj = client.get_object(Bucket=BUCKET, Key=key)
            raw = obj["Body"].read()
            with gzip.open(io.BytesIO(raw)) as f:
                if col_names:
                    df = pd.read_csv(f, header=None, names=col_names, low_memory=False)
                else:
                    df = pd.read_csv(f, low_memory=False)
            if keep:
                present = [c for c in keep if c in df.columns]
                df = df[present]
            return df
        except client.exceptions.NoSuchKey:
            return None
        except Exception as e:
            if attempt < 2:
                time.sleep(RETRY_BACKOFF[attempt])
            else:
                print(f"  WARN: {variant} {d} failed: {e}")
                return None
    return None


def _date_range(start: date, end: date) -> list[date]:
    days, d = [], start
    while d <= end:
        days.append(d)
        d += timedelta(days=1)
    return days


def _check_disk_gb(path: Path) -> float:
    usage = shutil.disk_usage(path)
    return usage.free / 1024**3


def run_variant(
    variant: str,
    start: date = START_DATE,
    end: date = END_DATE,
    chunk_suffix: str | None = None,
):
    """Download one variant for the given date range.

    chunk_suffix: if set, writes to year=YYYY/part-{chunk_suffix}.parquet so
    multiple non-overlapping chunks (e.g. H1/H2) can coexist in the same year
    directory and be read together with pd.read_parquet(year_dir).
    """
    print(f"\n{'='*60}")
    print(f"Variant: {variant}  ({start} → {end})  chunk={chunk_suffix or 'full'}")
    print(f"{'='*60}")

    free_gb = _check_disk_gb(OUT_BASE.parent)
    print(f"Disk free before start: {free_gb:.1f} GB")
    if free_gb < 2.0:
        raise RuntimeError(f"Insufficient disk space ({free_gb:.1f} GB). Aborting {variant}.")

    keep = KEEP_COLS[variant]
    col_names = _get_col_names(variant)
    print(f"  ddl columns: {col_names}")
    print(f"  retaining: {keep or 'all'}")

    days = _date_range(start, end)

    # Group days by year for year-level parquet files
    from itertools import groupby
    from operator import attrgetter
    years: dict[int, list[date]] = {}
    for d in days:
        years.setdefault(d.year, []).append(d)

    total_rows = 0
    total_success = 0
    total_missing = 0

    for yr, yr_days in sorted(years.items()):
        out_dir = OUT_BASE / variant / f"year={yr}"
        out_dir.mkdir(parents=True, exist_ok=True)
        fname = f"part-{chunk_suffix}.parquet" if chunk_suffix else "part.parquet"
        out_path = out_dir / fname

        if out_path.exists():
            try:
                existing = pq.read_metadata(out_path).num_rows
                print(f"  {yr}: already exists ({existing:,} rows), skipping")
                total_rows += existing
                total_success += len(yr_days)
                continue
            except Exception:
                print(f"  {yr}: corrupt parquet found, re-downloading")
                out_path.unlink()

        writer: pq.ParquetWriter | None = None
        yr_rows = 0
        yr_success = 0

        # Process in fixed batches of BATCH_SIZE to bound peak memory.
        # Submitting all days at once causes OOM when fast downloads accumulate
        # many DataFrames before the single-threaded parquet writer can drain them.
        for batch_start in range(0, len(yr_days), BATCH_SIZE):
            batch = yr_days[batch_start:batch_start + BATCH_SIZE]
            with ThreadPoolExecutor(max_workers=len(batch)) as pool:
                futs = [pool.submit(_fetch_one, d, variant, col_names, keep)
                        for d in batch]
                for future in as_completed(futs):
                    df = future.result()
                    if df is None:
                        total_missing += 1
                        continue
                    yr_success += 1
                    total_success += 1
                    yr_rows += len(df)
                    total_rows += len(df)
                    table = pa.Table.from_pandas(df, preserve_index=False)
                    if writer is None:
                        writer = pq.ParquetWriter(out_path, table.schema, compression="zstd")
                    writer.write_table(table)

        if writer:
            writer.close()

        free_after = _check_disk_gb(OUT_BASE.parent)
        print(f"  {yr}: {yr_success}/{len(yr_days)} files | {yr_rows:,} rows | "
              f"disk free: {free_after:.1f} GB → {out_path}")

        if free_after < 1.5:
            print(f"  WARNING: disk nearly full ({free_after:.1f} GB). Stopping {variant}.")
            break

    print(f"  DONE: {total_success} files | {total_rows:,} rows | missing: {total_missing}")
    return total_rows


def run(
    variants: list[str] = VARIANT_ORDER,
    start: date = START_DATE,
    end: date = END_DATE,
    chunk_suffix: str | None = None,
):
    results = {}
    for variant in variants:
        free = _check_disk_gb(OUT_BASE.parent)
        print(f"\nDisk free before {variant}: {free:.1f} GB")
        if free < 2.0:
            print(f"STOPPING: insufficient disk for {variant} ({free:.1f} GB free)")
            results[variant] = "SKIPPED (disk full)"
            continue
        rows = run_variant(variant, start=start, end=end, chunk_suffix=chunk_suffix)
        results[variant] = rows
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default=None, help="Run a single variant")
    parser.add_argument("--smoke", action="store_true", help="Last 7 days only")
    parser.add_argument("--start", default="2020-02-01")
    parser.add_argument("--end", default="2026-05-26")
    parser.add_argument(
        "--chunk-suffix", default=None,
        help="Output filename suffix (e.g. H1 → part-H1.parquet). "
             "Use with narrow --start/--end to chunk large years.",
    )
    args = parser.parse_args()

    if args.smoke:
        smoke_end = date(2026, 5, 26)
        smoke_start = smoke_end - timedelta(days=6)
        variants = [args.variant] if args.variant else VARIANT_ORDER
        results = run(variants=variants, start=smoke_start, end=smoke_end,
                      chunk_suffix=args.chunk_suffix)
    else:
        s = date.fromisoformat(args.start)
        e = date.fromisoformat(args.end)
        variants = [args.variant] if args.variant else VARIANT_ORDER
        results = run(variants=variants, start=s, end=e,
                      chunk_suffix=args.chunk_suffix)

    print("\n=== Summary ===")
    for variant, rows in results.items():
        print(f"  {variant}: {rows}")
