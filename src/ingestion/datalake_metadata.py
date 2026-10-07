"""
Fetch ERCOT network metadata tables from the Yes Energy datalake.

Tables: facility, contingency, ercot_plant, ercot_unit
Source: yedatalake://ercot/metadata/objects/{name}.csv.gz
Output: data/raw/ercot/metadata/objects/{name}.parquet
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from _datalake_client import BUCKET, read_csv_gz

METADATA_TABLES = ["facility", "contingency", "ercot_plant", "ercot_unit"]
OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "ercot" / "metadata" / "objects"


def fetch_metadata_table(name: str) -> pd.DataFrame:
    key = f"ercot/metadata/objects/{name}.csv.gz"
    df = read_csv_gz(BUCKET, key)
    return df


def run():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = {}
    for name in METADATA_TABLES:
        print(f"  Fetching {name}...")
        df = fetch_metadata_table(name)
        out_path = OUT_DIR / f"{name}.parquet"
        df.to_parquet(out_path, index=False)
        results[name] = df
        print(f"    Saved {len(df):,} rows → {out_path}")
    return results


if __name__ == "__main__":
    run()
