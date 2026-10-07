"""Join Tyba win-probabilities to GKS DA/RT LMP. spread = DA - RT."""
from __future__ import annotations
from pathlib import Path
import pandas as pd

A = Path(__file__).resolve().parents[1]
PROJ = Path(__file__).resolve().parents[5]

p = pd.read_csv(PROJ / "Inputs" / "GKS_BESS_RN_dart_win_probabilities.csv")
p["ft_utc"] = pd.to_datetime(p.forecast_time_utc, utc=True)
p["vt_utc"] = pd.to_datetime(p.vintage_utc, utc=True)
# DST artifact: 2026-03-09 00:00 CDT appears twice (lead-2 from 03-07 vintage + lead-1).
# Keep the latest vintage <= D-1, i.e. the lead-1 row.
p = p.sort_values("vt_utc").drop_duplicates("ft_utc", keep="last")

l = pd.read_csv(A / "raw" / "ye_gks_lmp.csv")
l["ft_ct"] = pd.to_datetime(l.DATETIME, format="%m/%d/%Y %H:%M:%S")
# Yes Energy DATETIME is CPT wall clock, hour-ending. Localize with DST inference.
l["ft_utc"] = l.ft_ct.dt.tz_localize("America/Chicago", ambiguous="infer",
                                     nonexistent="shift_forward").dt.tz_convert("UTC")
l = l.rename(columns={"GKS_BESS_RN (DALMP)": "da", "GKS_BESS_RN (RTLMP)": "rt"})
l = l[["ft_utc", "da", "rt", "HOURENDING", "PEAKTYPE"]]

m = p.merge(l, on="ft_utc", how="inner", validate="1:1")
m["ct"] = m.ft_utc.dt.tz_convert("America/Chicago")
m["date"] = m.ct.dt.date
m["he"] = m.HOURENDING
m["spread"] = m.da - m.rt          # DA - RT ; >0 => DA expensive => SHORT DA wins
m = m.sort_values("ft_utc").reset_index(drop=True)

print(f"prob rows {len(p)}  lmp rows {len(l)}  joined {len(m)}")
print("unmatched prob rows:", len(p) - len(m))
print(m[["da", "rt", "spread", "da_win_probability"]].describe())
# sanity: does da_win_probability actually predict spread>0 ?
print("\nrealized P(spread>0) by da_win decile:")
m["dec"] = pd.qcut(m.da_win_probability, 10, duplicates="drop")
print(m.groupby("dec", observed=True).agg(n=("spread", "size"),
                                          hit=("spread", lambda s: (s > 0).mean()),
                                          mean_spread=("spread", "mean")).round(3))
m.drop(columns=["dec"]).to_parquet(A / "derived" / "joined.parquet", index=False)
print("\nsaved ->", A / "derived" / "joined.parquet")
