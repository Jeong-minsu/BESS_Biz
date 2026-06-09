"""Full RT/SCED (NP6-86-CD) shadow-price history for MDOPHR99_A & STPWAP39_1.
Scans every hourly rt/ file 2023-01-01 00 .. 2026-06-08 23, keeps target-constraint
rows, saves long parquet. Real data only. CONTINGENCY text is blank in YE rt/ variant.
"""
import concurrent.futures as cf
from pathlib import Path
import pandas as pd
import dl

TARGETS = {"MDOPHR99_A", "STPWAP39_1"}
START, END = "2023-01-01", "2026-06-08"
OUT = Path(__file__).resolve().parents[1] / "derived" / "rt_binding_mdophr_stpwap.parquet"

def one(yyyymmddhh):
    df = dl.read_rt(yyyymmddhh)
    if df is None:
        return None
    sub = df[df["CONSTRAINTNAME"].isin(TARGETS)]
    if sub.empty:
        return None
    return sub[["CONSTRAINTNAME","DATETIME","CONTINGENCY","PRICE","LIMITMW",
                "VALUEMW","VIOLATEDMW","CONSTRAINT_TYPE"]].copy()

def main():
    days = pd.date_range(START, END, freq="D")
    hours = [f"{d.strftime('%Y%m%d')}{h:02d}" for d in days for h in range(24)]
    print("total hourly files to scan:", len(hours), flush=True)
    rows, done, hit = [], 0, 0
    with cf.ThreadPoolExecutor(max_workers=32) as ex:
        for r in ex.map(one, hours):
            done += 1
            if r is not None:
                rows.append(r); hit += 1
            if done % 2000 == 0:
                print(f"  scanned {done}/{len(hours)}  hit-files={hit}", flush=True)
    out = pd.concat(rows, ignore_index=True)
    out.to_parquet(OUT)
    print("DONE rows:", len(out), "->", OUT, flush=True)
    print(out.groupby("CONSTRAINTNAME").size().to_string())

if __name__ == "__main__":
    main()
