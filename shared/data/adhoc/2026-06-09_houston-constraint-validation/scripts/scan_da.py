"""Pass 1: scan DA daily binding-constraint files for MDOPHR99_A & STPWAP39_1.
Outputs a long table of every hour these two constraints appear (binding) in DAM.
"""
import sys, concurrent.futures as cf
from pathlib import Path
import pandas as pd
import dl

TARGETS = {"MDOPHR99_A", "STPWAP39_1"}
START, END = "2023-01-01", "2026-06-08"

def one(d):
    ymd = d.strftime("%Y%m%d")
    df = dl.read_da(ymd)
    if df is None:
        return None
    sub = df[df["CONSTRAINTNAME"].isin(TARGETS)]
    if sub.empty:
        return None
    return sub[["CONSTRAINTNAME","DATETIME","CONTINGENCY","PRICE","LIMITMW","VALUEMW","VIOLATEDMW","REPORTED_NAME","CONTINGENCYID"]].copy()

def main():
    days = pd.date_range(START, END, freq="D")
    rows = []
    done = 0
    with cf.ThreadPoolExecutor(max_workers=24) as ex:
        for r in ex.map(one, days):
            done += 1
            if r is not None:
                rows.append(r)
            if done % 200 == 0:
                print(f"  scanned {done}/{len(days)}  hits-days={len(rows)}", flush=True)
    if not rows:
        print("NO HITS")
        return
    out = pd.concat(rows, ignore_index=True)
    out.to_parquet(Path(__file__).resolve().parents[1] / "derived" / "da_binding_mdophr_stpwap.parquet")
    print("TOTAL binding-hours:", len(out))
    for c, g in out.groupby("CONSTRAINTNAME"):
        print(f"\n=== {c} ===  binding-hours={len(g)}")
        print("  PRICE stats:", g["PRICE"].describe()[["mean","50%","max"]].round(2).to_dict())
        print("  distinct contingencies:")
        print(g["CONTINGENCY"].fillna("(blank)").value_counts().head(8).to_string())

if __name__ == "__main__":
    main()
