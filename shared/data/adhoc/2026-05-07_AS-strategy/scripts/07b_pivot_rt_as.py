"""Re-pivot RT AS 15-min raw to hourly without re-fetching."""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC = Path(__file__).resolve().parents[1]
RAW = ADHOC / "raw"
DERIVED = ADHOC / "derived"

df = pd.read_parquet(RAW / "ercot_rt_as_15min.parquet")
print(f"Loaded {len(df)} rows; cols: {df.columns.tolist()}")
print(f"ASType values: {df['ASType'].unique()}")
print(f"Date range: {df['deliveryDate'].min()} ~ {df['deliveryDate'].max()}")

df["hour"] = df["deliveryHour"].astype(int)
df["delivery_date"] = pd.to_datetime(df["deliveryDate"]).dt.date
df["datetime_ct"] = (
    pd.to_datetime(df["delivery_date"]) + pd.to_timedelta(df["hour"] - 1, unit="h")
).dt.tz_localize("America/Chicago", ambiguous="infer", nonexistent="shift_forward")
df["MCPC"] = pd.to_numeric(df["MCPC"], errors="coerce")

# Hourly mean across 4 settlement intervals
hourly = df.groupby(["datetime_ct", "ASType"])["MCPC"].mean().reset_index()
pv = hourly.pivot_table(index="datetime_ct", columns="ASType", values="MCPC")
pv.columns = [f"RT_AS_MCPC_{c}" for c in pv.columns]
pv = pv.reset_index().sort_values("datetime_ct")

print(f"\nHourly pivot: {pv.shape}")
print(f"  cols: {pv.columns.tolist()}")
print(f"  range: {pv['datetime_ct'].min()} ~ {pv['datetime_ct'].max()}")

out = DERIVED / "rt_as_hourly.parquet"
pv.to_parquet(out, index=False)
print(f"\nSaved -> {out.name}")

print(f"\nRT AS mean by product:")
for c in [col for col in pv.columns if col.startswith("RT_AS_MCPC_")]:
    s = pv[c].dropna()
    print(f"  {c:25s}  mean={s.mean():>7.2f}  median={s.median():>6.2f}  "
          f"p95={s.quantile(0.95):>7.2f}  max={s.max():>8.2f}  n={len(s)}")
