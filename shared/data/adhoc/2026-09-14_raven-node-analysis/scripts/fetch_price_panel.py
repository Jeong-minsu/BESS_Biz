"""Fetch ERCOT hourly nodal DA/RT LMP panel (all price_nodes) from Yes Energy datalake.
Writes one parquet per month to raw/price_panel/YYYYMM.parquet (monthly chunking to
avoid the OOM seen on whole-range loads). Idempotent: skips months already written.
"""
import sys, io, calendar
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl

OUT = Path(__file__).resolve().parents[1] / "raw" / "price_panel"
OUT.mkdir(parents=True, exist_ok=True)
COLS = ["OBJECTID","DATETIME","TIMEZONE","DALMP","DACONG","DALOSS","RTLMP","RTCONG",
        "RTLOSS","RTFINAL","LOADID","HALMP","HACONG","HALOSS","ISO","ALT"]
KEEP = ["OBJECTID","DATETIME","TIMEZONE","DALMP","RTLMP","RTFINAL"]

START, END = date(2023, 9, 1), date(2026, 9, 13)

def one_day(d: date):
    key = f"ercot/prices/lmp/hourly/{d:%Y%m%d}.csv.gz"
    df = dl.try_read_csv(key, header=None)
    if df is None:
        print(f"  MISSING {d}", flush=True); return None
    df.columns = COLS[:df.shape[1]]
    df = df[[c for c in KEEP if c in df.columns]].copy()
    df["FLOWDAY"] = pd.Timestamp(d)
    return df

def main():
    m = date(START.year, START.month, 1)
    while m <= END:
        tag = f"{m:%Y%m}"
        fp = OUT / f"{tag}.parquet"
        if fp.exists():
            print(f"skip {tag} (exists)", flush=True)
        else:
            last = date(m.year, m.month, calendar.monthrange(m.year, m.month)[1])
            days = []
            d = max(m, START)
            while d <= min(last, END):
                days.append(d); d += timedelta(days=1)
            with ThreadPoolExecutor(10) as ex:
                parts = [p for p in ex.map(one_day, days) if p is not None]
            if parts:
                out = pd.concat(parts, ignore_index=True)
                for c in ("DALMP", "RTLMP"):
                    out[c] = pd.to_numeric(out[c], errors="coerce").astype("float32")
                out["OBJECTID"] = out["OBJECTID"].astype("int64")
                out.to_parquet(fp, index=False)
                print(f"wrote {tag}: {len(out):,} rows", flush=True)
        m = date(m.year + (m.month == 12), (m.month % 12) + 1, 1)

if __name__ == "__main__":
    main()
