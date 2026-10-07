"""
Build #73 — RT AS quantities for GKS from imbalance revenue / RT MCPC.

ERCOT RTC+B RT AS Imbalance.  15-min settlement interval = 0.25 h; MCPC is $/MW-h:
  RT{P}IMBAMT = (DA_qty - RT_qty) * RT_MCPC * 0.25      per 15-min interval
  => buyback_qty = RT{P}IMBAMT / (RT_MCPC * 0.25) = 4 * RT{P}IMBAMT / RT_MCPC
       (>0 = bought back in RT, <0 = sold extra in RT)
  => RT_qty (delivered) = DA_qty - buyback_qty
Validation: buyback_qty/DA_qty caps at exactly 1.0 (physical "can't buy back more than sold");
the 0.25-h factor is what makes that cap land at 1.0 instead of 0.25.

Inputs:
  derived/rt_as_revenue_15min.parquet  (charge_code, datetime_ct, value)   [script 72]
  raw/ercot_rt_as_15min.parquet        (deliveryDate/Hour/Int, ASType, MCPC) [script 07]
  derived/master_hourly.parquet        (GKS_Gen_*_Qty hourly DA AS award)

Output:
  derived/gks_rt_as_15min.parquet  (per 15-min: product, DA_qty, RT_MCPC, imb_amt, deviation_qty, RT_qty, buyback_qty, extra_sale_qty)
  derived/gks_as_hourly_full.parquet (hourly roll-up, all 3 products wide)
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ADHOC = Path(__file__).resolve().parents[1]
DERIVED = ADHOC / "derived"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROD = {  # product -> (imb charge code, ASType in price file, master DA award col)
    "NSPIN": ("RTNSIMBAMT",  "NSPIN", "GKS_Gen_NS_Qty"),
    "RRS":   ("RTRRIMBAMT",  "RRS",   "GKS_Gen_RRS_Qty"),
    "ECRS":  ("RTECRIMBAMT", "ECRS",  "GKS_Gen_ECRS_Qty"),
}
CAP = 100.0

# --- 1. RT AS imbalance revenue (15-min) ---
rev = pd.read_parquet(DERIVED / "rt_as_revenue_15min.parquet")
rev = rev[["charge_code", "datetime_ct", "value"]].copy()
rev["datetime_ct"] = pd.to_datetime(rev["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
# 15-min interval -> owning hour (interval start)
rev["hour_ct"] = rev["datetime_ct"].dt.floor("h")

# --- 2. RT AS MCPC (15-min) ---
px = pd.read_parquet(ADHOC / "raw" / "ercot_rt_as_15min.parquet")
# deliveryHour 1-24 hour-ending; deliveryInt 1-4. interval start = date + (DH-1)h + (DI-1)*15m
px["datetime_ct"] = (pd.to_datetime(px["deliveryDate"]).dt.tz_localize("America/Chicago", ambiguous=False, nonexistent="shift_forward")
                     + pd.to_timedelta(px["deliveryHour"] - 1, unit="h")
                     + pd.to_timedelta((px["deliveryInt"] - 1) * 15, unit="m"))
px["hour_ct"] = px["datetime_ct"].dt.floor("h")

# --- 3. DA AS award (hourly) ---
m = pd.read_parquet(DERIVED / "master_hourly.parquet")
m["hour_ct"] = pd.to_datetime(m["datetime_ct"], utc=True).dt.tz_convert("America/Chicago").dt.floor("h")

frames = []
for p, (code, astype, da_col) in PROD.items():
    r = rev[rev["charge_code"] == code][["datetime_ct", "hour_ct", "value"]].rename(columns={"value": "imb_amt"})
    pp = px[px["ASType"] == astype][["datetime_ct", "MCPC"]].rename(columns={"MCPC": "rt_mcpc"})
    da = m[["hour_ct", da_col]].rename(columns={da_col: "da_qty"})
    da["da_qty"] = da["da_qty"].fillna(0.0)

    d = r.merge(pp, on="datetime_ct", how="inner").merge(da, on="hour_ct", how="left")
    d["product"] = p
    d["imb_amt"] = d["imb_amt"].fillna(0.0)
    d["da_qty"] = d["da_qty"].fillna(0.0)
    # buyback_qty = IMB / (RT_MCPC * 0.25) ; only meaningful where rt_mcpc > 0
    d["buyback_qty"] = np.where(d["rt_mcpc"] > 0, d["imb_amt"] / (d["rt_mcpc"] * 0.25), 0.0)
    d["rt_qty"] = (d["da_qty"] - d["buyback_qty"]).clip(lower=0.0, upper=CAP)
    frames.append(d)

q15 = pd.concat(frames, ignore_index=True)

# --- validation: buyback_qty/DA_qty should cap at ~1.0 (can't buy back more than sold) ---
print("=== VALIDATION  (buyback_qty / DA_qty should cap at ~1.0) ===")
for p in PROD:
    s = q15[(q15["product"] == p) & (q15["da_qty"] > 0)]
    r = s["buyback_qty"] / s["da_qty"]
    rt = s["da_qty"] - s["buyback_qty"]
    print(f"  {p:6s}  buyback/DA  p90={r.quantile(.9):.3f}  p99={r.quantile(.99):.3f}  max={r.max():.3f}"
          f"   |  RT_qty in[0,100]: {((rt>=-1e-6)&(rt<=CAP+1e-6)).mean()*100:5.1f}%")
print()

# buyback (>0) vs extra RT sale (<0)
q15["extra_sale_qty"] = (-q15["buyback_qty"]).clip(lower=0.0)
q15["buyback_qty"]    = q15["buyback_qty"].clip(lower=0.0)
q15["deviation_qty"]  = q15["buyback_qty"] - q15["extra_sale_qty"]   # net (>0 buyback)
q15.to_parquet(DERIVED / "gks_rt_as_15min.parquet", index=False)
print(f"saved -> derived/gks_rt_as_15min.parquet  ({len(q15)} rows)")

# --- hourly roll-up ---  (15-min qty -> hourly mean MW; amt -> hourly sum $)
hr = (q15.groupby(["product", "hour_ct"])
      .agg(da_qty=("da_qty", "mean"),
           rt_qty=("rt_qty", "mean"),
           deviation_qty=("deviation_qty", "mean"),
           buyback_qty=("buyback_qty", "mean"),
           extra_sale_qty=("extra_sale_qty", "mean"),
           rt_mcpc=("rt_mcpc", "mean"),
           imb_amt=("imb_amt", "sum"))
      .reset_index())
hr.to_parquet(DERIVED / "gks_as_hourly_full.parquet", index=False)
print(f"saved -> derived/gks_as_hourly_full.parquet  ({len(hr)} rows)\n")

print("=== HOURLY MEANS (over all hours in window) ===")
for p in PROD:
    s = hr[hr["product"] == p]
    print(f"  {p:6s}  DA_qty={s.da_qty.mean():6.2f}  RT_qty={s.rt_qty.mean():6.2f}  "
          f"deviation={s.deviation_qty.mean():+6.2f}  buyback={s.buyback_qty.mean():5.2f}  "
          f"extra_sale={s.extra_sale_qty.mean():5.2f}  RT_MCPC={s.rt_mcpc.mean():5.2f}  "
          f"RT_imb_total=${s.imb_amt.sum():>11,.0f}")
