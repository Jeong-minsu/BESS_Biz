"""
#89 — Aggregate Tenaska HSL (Generator-Performance) to hourly + integrate into master.

Datapoints from Tenaska Generator-Performance endpoint:
  Telemetered_HSL_5_Min   — real-time telemetered High Sustained Limit (5-min)
  Predictive_HSL_15_Min   — predictive HSL (forward-looking, what was forecast)
  Telemetered_LSL_5_Min   — telemetered Low Sustained Limit (typically negative for charging)
  Predictive_LSL_15_Min   — predictive LSL
  Telemetered_Generation_15_Min  — actual generation

We use Telemetered_HSL_5_Min aggregated to hourly mean as the "true HSL" GKS could
have used for AS bidding. This is what GKS committed to in DA via Tenaska submission.

Output:
  derived/tenaska_hsl_hourly.parquet  — hourly Telemetered & Predictive HSL
"""
from __future__ import annotations
import json, sys, glob
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[5]
PNL_DIR = ROOT / "shared" / "data" / "pnl" / "gks" / "hourly"
ADHOC = Path(__file__).resolve().parents[1]
DERIVED = ADHOC / "derived"

# Load all 2026 HSL files
files = sorted(glob.glob(str(PNL_DIR / "2026-*_hsl.json")))
print(f"Found {len(files)} HSL files")

all_rows = []
empty = 0
for fp in files:
    with open(fp, encoding="utf-8") as f:
        d = json.load(f)
    if not d:
        empty += 1
        continue
    all_rows.extend(d)
print(f"  Empty: {empty}")
print(f"  Non-empty rows total: {len(all_rows)}")

df = pd.DataFrame(all_rows)
print(f"  Datapoints found: {sorted(df['datapoint'].unique())}")

# Convert and pivot
df["datetime_utc"] = pd.to_datetime(df["interval_start_utc"], utc=True)
df["hour_ct"] = df["datetime_utc"].dt.tz_convert("America/Chicago").dt.floor("h")
df["value"] = pd.to_numeric(df["value"], errors="coerce")

# Aggregate each HSL datapoint to hourly mean
key_dps = ["Telemetered_HSL_5_Min", "Predictive_HSL_15_Min",
           "Telemetered_LSL_5_Min", "Predictive_LSL_15_Min",
           "Telemetered_Generation_15_Min"]
hourly = pd.DataFrame()
for dp in key_dps:
    sub = df[df["datapoint"] == dp]
    if sub.empty:
        continue
    agg = sub.groupby("hour_ct")["value"].mean().reset_index()
    short = {"Telemetered_HSL_5_Min": "tenaska_hsl_telemetered",
             "Predictive_HSL_15_Min": "tenaska_hsl_predictive",
             "Telemetered_LSL_5_Min": "tenaska_lsl_telemetered",
             "Predictive_LSL_15_Min": "tenaska_lsl_predictive",
             "Telemetered_Generation_15_Min": "tenaska_gen_actual"}[dp]
    agg = agg.rename(columns={"value": short, "hour_ct": "datetime_ct"})
    if hourly.empty:
        hourly = agg
    else:
        hourly = hourly.merge(agg, on="datetime_ct", how="outer")

print()
print(f"Hourly aggregation: {len(hourly)} hours")
print(f"  Date range: {hourly['datetime_ct'].min()} ~ {hourly['datetime_ct'].max()}")
print()
print("Summary stats:")
for c in hourly.columns:
    if c == "datetime_ct": continue
    s = hourly[c].dropna()
    if len(s):
        print(f"  {c:32s}: n={len(s):>4d}  mean={s.mean():>7.2f}  min={s.min():>7.2f}  max={s.max():>7.2f}")

out = DERIVED / "tenaska_hsl_hourly.parquet"
hourly.to_parquet(out, index=False)
print(f"\nsaved -> {out.name}")
