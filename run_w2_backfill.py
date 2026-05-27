"""
W2 full backfill runner — all 4 shift factor variants, 2020-02-01 to 2026-05-26.
Designed to run as a background process; writes progress to run_w2_backfill.log.
Resume-safe: skips already-completed year parquets, deletes and re-downloads corrupt ones.
"""
import gzip
import io
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).parent / "shared" / "scripts"))
sys.path.insert(0, str(Path(__file__).parent / "src" / "ingestion"))
from _env_loader import load_env_sections

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[
        logging.FileHandler("run_w2_backfill.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

BUCKET = "yedatalake"
BASE = "ercot/transmission/constraints"
OUT_BASE = Path("data/raw/ercot/transmission/constraints")
START = date(2020, 2, 1)
END = date(2026, 5, 26)
MAX_WORKERS = 8

VARIANTS = {
    "shift_factors": (
        ["CONSTRAINT_DAY", "DATETIME", "FACILITYID", "CONTINGENCYID", "ISO",
         "PNODEID", "PNODENAME", "SHIFT_FACTOR", "QUALITY_METRIC", "SHADOWPRICE"],
        None,
    ),
    "settle_shift_factors_ercot": (
        ["DATETIME", "TIMEZONE", "CONSTRAINTID", "CONSTRAINTNAME", "CONTINGENCY",
         "SETTLEMENTPOINT", "SHIFTFACTOR", "LOADID"],
        ["DATETIME", "CONSTRAINTID", "SETTLEMENTPOINT", "SHIFTFACTOR"],
    ),
    "market_shift_factors": (
        ["PRICENODEID", "FACILITYID", "CONTINGENCYID", "DATETIME", "TIMEZONE",
         "MARKET", "SHIFTFACTOR", "SHADOWPRICE", "LIMIT", "CONSTRAINTID",
         "CONSTRAINTNAME", "LOADID"],
        ["PRICENODEID", "FACILITYID", "CONTINGENCYID", "DATETIME", "MARKET", "SHIFTFACTOR"],
    ),
    "ercot_sced_shift_factors": (
        ["DATETIME", "TIMEZONE", "CONSTRAINTID", "CONSTRAINTNAME", "CONTINGENCY",
         "RESOURCENAME", "SETTLEMENTPOINT", "SHIFTFACTOR", "LOADID"],
        ["DATETIME", "CONSTRAINTID", "RESOURCENAME", "SETTLEMENTPOINT", "SHIFTFACTOR"],
    ),
}

_creds = load_env_sections().get("yes_energy_s3", {})
_local = threading.local()


def get_client():
    if not hasattr(_local, "c"):
        _local.c = boto3.client(
            "s3",
            aws_access_key_id=_creds["YES_ENERGY_ACCESS_KEY"],
            aws_secret_access_key=_creds["YES_ENERGY_SECRET_KEY"],
        )
    return _local.c


def fetch_one(d: date, variant: str, col_names: list, keep: list | None) -> pd.DataFrame | None:
    key = f"{BASE}/{variant}/{d.strftime('%Y%m%d')}.csv.gz"
    cl = get_client()
    for attempt in range(3):
        try:
            obj = cl.get_object(Bucket=BUCKET, Key=key)
            raw = obj["Body"].read()
            with gzip.open(io.BytesIO(raw)) as f:
                df = pd.read_csv(f, header=None, names=col_names, low_memory=False)
            if keep:
                df = df[[c for c in keep if c in df.columns]]
            return df
        except cl.exceptions.NoSuchKey:
            return None
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                log.warning(f"  WARN {variant} {d}: {e}")
                return None
    return None


def process_year(variant: str, yr: int, yr_days: list[date], col_names: list, keep: list | None):
    out_dir = OUT_BASE / variant / f"year={yr}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "part.parquet"

    if out_path.exists():
        try:
            n = pq.read_metadata(out_path).num_rows
            log.info(f"  {variant} year={yr}: already done ({n:,} rows), skipping")
            return n
        except Exception:
            log.info(f"  {variant} year={yr}: corrupt parquet, re-downloading")
            out_path.unlink()

    writer = None
    success = 0
    missing = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_one, d, variant, col_names, keep): d for d in yr_days}
        for i, fut in enumerate(as_completed(futures), 1):
            df = fut.result()
            if df is None:
                missing += 1
                continue
            success += 1
            t = pa.Table.from_pandas(df, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(str(out_path), t.schema, compression="zstd")
            writer.write_table(t)

    if writer:
        writer.close()

    if out_path.exists():
        n = pq.read_metadata(out_path).num_rows
        sz = out_path.stat().st_size / 1024 ** 2
        import shutil
        free = shutil.disk_usage(out_path.parent).free / 1024 ** 3
        log.info(f"  {variant} year={yr}: {success}/{len(yr_days)} files | {n:,} rows | "
                 f"{sz:.0f} MB parquet | disk free: {free:.1f} GB")
        return n
    return 0


def main():
    log.info("=== W2 Backfill Start ===")

    # Group dates by year
    days_by_year: dict[int, list[date]] = {}
    d = START
    while d <= END:
        days_by_year.setdefault(d.year, []).append(d)
        d += timedelta(days=1)

    summary: dict[str, int] = {}

    for variant, (col_names, keep) in VARIANTS.items():
        log.info(f"\n{'='*60}\nVariant: {variant}\n{'='*60}")
        total_rows = 0
        for yr in sorted(days_by_year.keys()):
            rows = process_year(variant, yr, days_by_year[yr], col_names, keep)
            total_rows += rows
        summary[variant] = total_rows
        log.info(f"{variant} TOTAL: {total_rows:,} rows")

    log.info("\n=== W2 Backfill Complete ===")
    for v, r in summary.items():
        log.info(f"  {v}: {r:,} rows")


if __name__ == "__main__":
    main()
