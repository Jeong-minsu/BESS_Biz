"""Yes Energy Datalake (S3 yedatalake) helper — Raven node analysis.
Same as 2026-06-09_houston-constraint-validation/scripts/dl.py but with verify=False
(corporate MITM proxy presents a self-signed chain; established repo workaround).
Real data only — no mock.
"""
from __future__ import annotations
import io, sys
from pathlib import Path
import pandas as pd
import boto3, urllib3
from botocore.config import Config

urllib3.disable_warnings()
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "shared" / "scripts"))
from _env_loader import load_env_sections  # noqa: E402

_BUCKET = "yedatalake"
_cli = None

def cli():
    global _cli
    if _cli is None:
        s = load_env_sections().get("yes_energy_s3", {})
        _cli = boto3.client(
            "s3",
            aws_access_key_id=s["YES_ENERGY_ACCESS_KEY"],
            aws_secret_access_key=s["YES_ENERGY_SECRET_KEY"],
            verify=False,
            config=Config(connect_timeout=15, read_timeout=180, retries={"max_attempts": 4}),
        )
    return _cli

def raw(key: str) -> bytes:
    return cli().get_object(Bucket=_BUCKET, Key=key)["Body"].read()

def read_csv(key: str, **kw) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(raw(key)), compression="gzip", **kw)

def try_read_csv(key: str, **kw):
    try:
        return read_csv(key, **kw)
    except Exception as e:
        if "NoSuchKey" in type(e).__name__ or "NoSuchKey" in str(e):
            return None
        raise

DA_COLS = ["FACILITYID","CONTINGENCYID","DATETIME","TIMEZONE","CONTINGENCY","ISO",
           "PRICE","LOADID","CONSTRAINTID","CONSTRAINTNAME","LIMITMW","VALUEMW",
           "VIOLATEDMW","REPORTED_NAME"]
RT_COLS = ["ISO","FACILITYID","DATETIME","TIMEZONE","CONTINGENCY","CONTROLLINGACTION",
           "PRICE","LOADID","CONTINGENCYID","CONSTRAINTID","CONSTRAINTNAME","LIMITMW",
           "MAXPRICE","VALUEMW","VIOLATEDMW","REPORTED_NAME","CONSTRAINT_TYPE"]

def read_da(yyyymmdd: str):
    df = try_read_csv(f"ercot/transmission/constraints/da/{yyyymmdd}.csv.gz", header=None)
    if df is None: return None
    df.columns = DA_COLS[:df.shape[1]]
    return df

def read_rt(yyyymmddhh: str):
    df = try_read_csv(f"ercot/transmission/constraints/rt/{yyyymmddhh}.csv.gz", header=None)
    if df is None: return None
    df.columns = RT_COLS[:df.shape[1]]
    return df

def ls(prefix: str, max_keys: int = 1000):
    out, tok = [], None
    while True:
        kw = dict(Bucket=_BUCKET, Prefix=prefix, MaxKeys=1000)
        if tok: kw["ContinuationToken"] = tok
        r = cli().list_objects_v2(**kw)
        out += [(o["Key"], o["Size"]) for o in r.get("Contents", [])]
        if r.get("IsTruncated") and len(out) < max_keys:
            tok = r["NextContinuationToken"]
        else:
            break
    return out
