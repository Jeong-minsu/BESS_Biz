"""DART 3-year extension — fetch LEAKAGE-FREE day-ahead forecasts for the ERCOT system.

For each operating day D, take the ERCOT forecast vintage published on D-1 at 13:30 GMT (load MTLF)
and 13:55 GMT (wind STWPF, solar STPPF). PUBLISHDATE in these files is GMT, so that is
08:30/08:55 CDT or 07:30/07:55 CST — always BEFORE the DAM bid close (D-1 10:00 CT).
If that exact vintage is missing, walk back hour by hour (never forward).

Source: Yes Energy datalake ercot/vintage/{load_forecast, wind_stwpf, solar_stppf}, object ERCOT (10000712973).
Output: raw/dart3y_forecasts.parquet — one row per (D, hour-ending CT): load_fc, wind_fc, solar_fc, vintage stamps.
Idempotent (cached). Real data only.
"""
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "raw" / "dart3y_forecasts.parquet"
SYS = 10000712973
COLS = ["OBJECTID", "DATATYPEID", "DATETIME", "TIMEZONE", "VALUE", "LOADID", "PUBLISHDATE", "HISTORYID", "PUBTZ"]
SERIES = {"load_fc": ("load_forecast", 30), "wind_fc": ("wind_stwpf", 55), "solar_fc": ("solar_stppf", 55)}
TARGET_GMT_HOUR = 13


CUTOFF_GMT = (13, 59)   # D-1 13:59 GMT = 08:59 CDT / 07:59 CST, always before the 10:00 CT bid close


def fetch_vintage(table, minute, d_op):
    """Latest vintage published at or before D-1 13:59 GMT (file minute stamps vary by era: :00/:30/:55).
    Lists the actual keys for D-1 instead of guessing the minute; walks back within D-1 only."""
    d1 = datetime(d_op.year, d_op.month, d_op.day) - timedelta(days=1)
    cutoff = d1 + timedelta(hours=CUTOFF_GMT[0], minutes=CUTOFF_GMT[1])
    keys = [k for k, _ in dl.ls(f"ercot/vintage/{table}/{d1:%Y%m%d}", max_keys=200)]
    stamps = []
    for k in keys:
        name = k.rsplit("/", 1)[-1].split(".")[0]
        try:
            ts = datetime.strptime(name, "%Y%m%d%H%M")
        except ValueError:
            continue
        if ts <= cutoff:
            stamps.append((ts, k))
    for ts, key in sorted(stamps, reverse=True)[:12]:
        t = ts
        df = dl.try_read_csv(key, header=None)
        if df is None:
            continue
        df.columns = COLS[:df.shape[1]]
        df = df[df.OBJECTID == SYS].copy()
        if df.empty:
            continue
        df["dt"] = pd.to_datetime(df.DATETIME)
        # keep the operating day D in CT: period-ending HE1 (D 01:00) .. HE24 (D+1 00:00)
        lo = pd.Timestamp(d_op) + pd.Timedelta(hours=1)
        hi = pd.Timestamp(d_op) + pd.Timedelta(hours=24)
        df = df[(df.dt >= lo) & (df.dt <= hi)]
        min_rows = 8 if table == "solar_stppf" else 20     # solar file only carries daylight hours
        if len(df) < min_rows:
            continue
        df = df.drop_duplicates("dt", keep="last")
        return df[["dt", "VALUE"]].assign(vintage=f"{t:%Y%m%d%H%M}")
    return None


def one_day(d_op):
    parts = {}
    for name, (table, minute) in SERIES.items():
        r = fetch_vintage(table, minute, d_op)
        if r is None:
            return d_op, None
        parts[name] = r.set_index("dt")
    hours = pd.date_range(pd.Timestamp(d_op) + pd.Timedelta(hours=1), periods=24, freq="h")
    out = pd.DataFrame({k: v.VALUE for k, v in parts.items()}).reindex(hours)
    out.index.name = "dt"
    out["solar_fc"] = out["solar_fc"].fillna(0.0)                 # night hours absent from STPPF = 0 MW
    if out[["load_fc", "wind_fc"]].isna().sum().sum() > 2:
        return d_op, None
    out[["load_fc", "wind_fc"]] = out[["load_fc", "wind_fc"]].interpolate(limit=2)
    for k, v in parts.items():
        out[k.replace("_fc", "_vintage")] = v.vintage.iloc[0]
    out["day"] = pd.Timestamp(d_op)
    return d_op, out.reset_index()


if __name__ == "__main__":
    have = pd.read_parquet(OUT) if OUT.exists() else None
    done = set(have.day.dt.date) if have is not None else set()
    days, d = [], date(2023, 12, 1)
    while d <= date(2026, 9, 13):
        if d not in done:
            days.append(d)
        d += timedelta(days=1)
    print(f"days to fetch: {len(days)} (cached {len(done)})", flush=True)
    got, miss = [], []
    with ThreadPoolExecutor(16) as ex:
        for d_op, df in ex.map(one_day, days):
            (got if df is not None else miss).append(df if df is not None else d_op)
    new = pd.concat(got, ignore_index=True) if got else pd.DataFrame()
    allf = pd.concat([have, new], ignore_index=True) if have is not None else new
    allf.to_parquet(OUT, index=False)
    print(f"wrote {OUT.name}: {allf.day.nunique()} days, {len(allf):,} rows; missing days: {len(miss)} {miss[:10]}")
    print("vintage check (sample):", allf[["day", "load_vintage", "wind_vintage", "solar_vintage"]].drop_duplicates("day").tail(3).to_string(index=False))
