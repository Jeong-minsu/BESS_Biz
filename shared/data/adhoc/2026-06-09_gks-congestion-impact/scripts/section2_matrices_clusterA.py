"""Section2: P(bind) month x hour (12x24) matrices for HAINE__LA_PAL1_1 & 421__A, DA & RT.

Mirrors Houston analyze_rt_da_seasonality.py:
  - numerator = distinct binding intervals (distinct DATETIME) per (month, hour) for the constraint.
    (gks_msf_raw.parquet holds only BINDING rows -> SHADOWPRICE>0; RT 'PRICE>0' satisfied implicitly.)
  - denominator: DA = days_in_window_month ; RT = days_in_window_month * 12 (5-min SCED/hr).
  - hour = DATETIME hour 0..23 (== ERCOT HE per memory convention; same as Houston).
Window = node existence 2024-07-03..2026-06-08 (GKS_BESS_RN COD). REAL data only.
NOTE: 421__A is a growing 2025-onset constraint -> window-average P(bind) understates current."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
START, END = "2024-07-03", "2026-06-08"
TARGETS = ["HAINE__LA_PAL1_1", "421__A"]

raw = pd.read_parquet(D / "gks_msf_raw.parquet")
raw = raw[raw.SHADOWPRICE > 0].copy()
raw["dt"] = pd.to_datetime(raw.DATETIME, format="%m/%d/%Y %H:%M:%S")
raw["mon"] = raw.dt.dt.month
raw["hr"] = raw.dt.dt.hour

cal = pd.date_range(START, END, freq="D")
dcount = pd.Series(cal.month).value_counts().sort_index()  # days in window per month-of-year

out = {}
for c in TARGETS:
    rec = {}
    for mkt, perhr in [("DA", 1), ("RT", 12)]:
        sub = raw[(raw.CONSTRAINTNAME == c) & (raw.MARKET == mkt)]
        # distinct binding intervals per (mon,hr): dedupe on DATETIME (collapse multi-contingency rows)
        di = sub.drop_duplicates("dt")
        pbind = np.zeros((12, 24))
        medlam = np.full((12, 24), np.nan)
        for m in range(1, 13):
            denom = int(dcount.get(m, 0)) * perhr
            for h in range(24):
                cell = di[(di.mon == m) & (di.hr == h)]
                if denom:
                    pbind[m - 1, h] = round(len(cell) / denom, 4)
                if len(cell):
                    medlam[m - 1, h] = round(float(cell.SHADOWPRICE.median()), 1)
        rec[f"{mkt.lower()}_pbind"] = pbind.tolist()
        rec[f"{mkt.lower()}_medlam"] = [[None if np.isnan(v) else v for v in row] for row in medlam]
    out[c] = rec

meta = dict(window=f"{START}..{END}", source="Yes Energy Datalake yedatalake market_shift_factors @ GKS_BESS_RN (REAL)",
            rows="month_1_12", cols="hour_0_23_HE",
            numerator="distinct binding DATETIME per cell (SHADOWPRICE>0)",
            denominator="DA: days_in_window_month ; RT: days_in_window_month*12",
            note="421__A is 2025-onset/growing -> window-average P(bind) understates 2026 levels")
json.dump({"_meta": meta, **out}, open(D / "section2_matrices_clusterA.json", "w"), indent=1)

# quick sanity print
for c in TARGETS:
    da = np.array(out[c]["da_pbind"]); rt = np.array(out[c]["rt_pbind"])
    print(f"{c}: DA peak P(bind)={da.max():.2f} at m{da.argmax()//24+1}/h{da.argmax()%24}; "
          f"RT peak={rt.max():.2f} at m{rt.argmax()//24+1}/h{rt.argmax()%24}")
print("saved", D / "section2_matrices_clusterA.json")
