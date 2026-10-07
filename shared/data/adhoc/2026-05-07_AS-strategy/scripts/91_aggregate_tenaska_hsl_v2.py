"""
#91 — Aggregate Tenaska HSL from raw files (proper Elements.DataPoints parser).
"""
from __future__ import annotations
import json, sys, glob
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC = Path(__file__).resolve().parents[1]
RAW = ADHOC / "raw" / "tenaska_hsl_raw"
DERIVED = ADHOC / "derived"

files = sorted(glob.glob(str(RAW / "2026-*.json")))
print(f"Raw HSL files: {len(files)}")

all_rows = []
empty_dates = []
for fp in files:
    date_str = Path(fp).stem
    with open(fp, encoding="utf-8") as f:
        j = json.load(f)
    data = j.get("data", {})
    starts = data.get("IntervalStartUtc", [])
    elements = data.get("Elements", [])
    if not starts or not elements:
        empty_dates.append(date_str)
        continue
    elem = elements[0]
    dps = elem.get("DataPoints", {})
    for dp_name, vals in dps.items():
        if not isinstance(vals, list):
            continue
        for i, v in enumerate(vals):
            if v is None or i >= len(starts):
                continue
            try: v = float(v)
            except (TypeError, ValueError): continue
            all_rows.append({
                "interval_start_utc": starts[i],
                "datapoint": dp_name,
                "value": v,
            })

print(f"  Empty dates: {len(empty_dates)}")
if empty_dates:
    print(f"    {empty_dates[:5]} ... (truncated)")
print(f"  Parsed rows total: {len(all_rows):,}")

df = pd.DataFrame(all_rows)
df["datetime_utc"] = pd.to_datetime(df["interval_start_utc"], utc=True)
df["hour_ct"] = df["datetime_utc"].dt.tz_convert("America/Chicago").dt.floor("h")

# Hourly aggregation (mean of 5-min telemetered or 15-min predictive within hour)
hourly_frames = []
for dp, short in [("Telemetered_HSL_5_Min",  "tenaska_hsl_telemetered"),
                  ("Predictive_HSL_15_Min",  "tenaska_hsl_predictive")]:
    sub = df[df["datapoint"] == dp]
    if sub.empty:
        continue
    agg = sub.groupby("hour_ct")["value"].mean().reset_index()
    agg = agg.rename(columns={"value": short, "hour_ct": "datetime_ct"})
    hourly_frames.append(agg)

if not hourly_frames:
    print("No HSL data parsed.")
    sys.exit(1)

hourly = hourly_frames[0]
for fr in hourly_frames[1:]:
    hourly = hourly.merge(fr, on="datetime_ct", how="outer")
hourly = hourly.sort_values("datetime_ct").reset_index(drop=True)

print()
print(f"Hourly aggregation: {len(hourly)} hours")
print(f"  range: {hourly['datetime_ct'].min()} ~ {hourly['datetime_ct'].max()}")
for c in ["tenaska_hsl_telemetered", "tenaska_hsl_predictive"]:
    if c in hourly:
        s = hourly[c].dropna()
        print(f"  {c}: n={len(s)}, mean={s.mean():.2f}, min={s.min():.2f}, max={s.max():.2f}")

# Compare against Smartbidder
m = pd.read_parquet(DERIVED / "master_hourly.parquet")
m["datetime_ct"] = pd.to_datetime(m["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
mm = m[["datetime_ct","avail_discharge_mw","GKS_Gen_NS_Qty"]].merge(hourly, on="datetime_ct", how="inner")
print()
print(f"Merged with master: {len(mm)} hours")
print(f'  Smartbidder avg:        {mm["avail_discharge_mw"].fillna(100).mean():.2f}')
print(f'  Tenaska Telemetered avg: {mm["tenaska_hsl_telemetered"].mean():.2f}')
print(f'  Tenaska Predictive avg:  {mm["tenaska_hsl_predictive"].mean():.2f}')
print(f'  GKS NSPIN bid avg (>0):  {mm[mm["GKS_Gen_NS_Qty"].fillna(0)>0]["GKS_Gen_NS_Qty"].mean():.2f}')

# Correlation
corr_tel_sb = mm["tenaska_hsl_telemetered"].corr(mm["avail_discharge_mw"])
corr_pred_sb = mm["tenaska_hsl_predictive"].corr(mm["avail_discharge_mw"])
print(f'  Corr (Telemetered HSL vs Smartbidder):  {corr_tel_sb:.3f}')
print(f'  Corr (Predictive HSL vs Smartbidder):   {corr_pred_sb:.3f}')

out = DERIVED / "tenaska_hsl_hourly.parquet"
hourly.to_parquet(out, index=False)
print(f"\nsaved -> {out.name}")
