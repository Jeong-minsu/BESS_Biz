"""
boto3 S3 client factory and helpers for the Yes Energy datalake.

Bucket: yedatalake
Auth: YES_ENERGY_ACCESS_KEY / YES_ENERGY_SECRET_KEY from .env [yes_energy_s3] section.
"""
from __future__ import annotations

import gzip
import io
import json
import sys
from pathlib import Path
from typing import List

import boto3
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared" / "scripts"))
from _env_loader import load_env_sections

BUCKET = "yedatalake"


def get_s3_client():
    creds = load_env_sections().get("yes_energy_s3", {})
    access_key = creds.get("YES_ENERGY_ACCESS_KEY")
    secret_key = creds.get("YES_ENERGY_SECRET_KEY")
    if not access_key or not secret_key:
        raise RuntimeError("yes_energy_s3 credentials missing in .env")
    return boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def read_csv_gz(bucket: str, key: str, col_names: list[str] | None = None) -> pd.DataFrame:
    """Download a .csv.gz from S3 and return a DataFrame.

    If col_names is provided, the file is assumed headerless and those names are
    applied. Otherwise pandas infers headers from the first row.
    """
    client = get_s3_client()
    obj = client.get_object(Bucket=bucket, Key=key)
    raw = obj["Body"].read()
    with gzip.open(io.BytesIO(raw)) as f:
        if col_names:
            return pd.read_csv(f, header=None, names=col_names, low_memory=False)
        return pd.read_csv(f, low_memory=False)


def read_ddl(folder_prefix: str) -> list[dict]:
    """Fetch ddl.json from the given S3 folder prefix and return the columns list.

    Each entry is a dict with at least: colName, colType, colDesc.
    Returns empty list if ddl.json does not exist at that prefix.
    """
    key = folder_prefix.rstrip("/") + "/ddl.json"
    client = get_s3_client()
    try:
        obj = client.get_object(Bucket=BUCKET, Key=key)
        data = json.loads(obj["Body"].read().decode("utf-8"))
        return data.get("columns", [])
    except client.exceptions.NoSuchKey:
        return []
    except Exception:
        return []
