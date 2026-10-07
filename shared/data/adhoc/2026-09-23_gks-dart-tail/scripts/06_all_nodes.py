"""DA-RT spread stats for every ERCOT price node vs GKS, 2024-07-04 .. 2026-09-22.

Source: Yes Energy datalake ercot/prices/lmp/hourly (same DALMP/RTLMP as YE REST).
Reuses the Raven project's monthly panel (through 2026-09-13) and fetches 09-14..09-22 here.
"""
import sys, glob
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl

BASE = Path(__file__).resolve().parents[1]
PANEL = BASE.parent / "2026-09-14_raven-node-analysis" / "raw" / "price_panel"
COLS = ["OBJECTID", "DATETIME", "TIMEZONE", "DALMP", "DACONG", "DALOSS", "RTLMP", "RTCONG",
        "RTLOSS", "RTFINAL", "LOADID", "HALMP", "HACONG", "HALOSS", "ISO", "ALT"]
START, END = pd.Timestamp("2024-07-04"), pd.Timestamp("2026-09-22")
GKS = 10017907494

# --- extra days
extra_fp = BASE / "raw" / "panel_20260914_20260922.parquet"
if not extra_fp.exists():
    def one(d):
        df = dl.try_read_csv(f"ercot/prices/lmp/hourly/{d:%Y%m%d}.csv.gz", header=None)
        if df is None:
            print("MISSING", d); return None
        df.columns = COLS[:df.shape[1]]
        df = df[["OBJECTID", "DATETIME", "DALMP", "RTLMP", "RTFINAL"]].copy(); df["FLOWDAY"] = pd.Timestamp(d)
        return df
    days = [date(2026, 9, 14) + timedelta(i) for i in range(9)]
    with ThreadPoolExecutor(9) as ex:
        x = pd.concat([p for p in ex.map(one, days) if p is not None], ignore_index=True)
    for c in ("DALMP", "RTLMP"): x[c] = pd.to_numeric(x[c], errors="coerce").astype("float32")
    x.to_parquet(extra_fp, index=False)

parts = []
for f in sorted(glob.glob(str(PANEL / "*.parquet"))):
    if Path(f).stem < "202407": continue
    parts.append(pd.read_parquet(f, columns=["OBJECTID", "DATETIME", "DALMP", "RTLMP", "RTFINAL", "FLOWDAY"]))
parts.append(pd.read_parquet(extra_fp))
p = pd.concat(parts, ignore_index=True)
p = p[(p.FLOWDAY >= START) & (p.FLOWDAY <= END)]
p = p.drop_duplicates(["OBJECTID", "DATETIME"])
p["spread"] = (p.DALMP - p.RTLMP).astype("float32")
print("rows", len(p), "nodes", p.OBJECTID.nunique(), "RT non-final rows", (p.RTFINAL != "Y").sum())
W = p.pivot_table(index="DATETIME", columns="OBJECTID", values="spread", aggfunc="first")
W.index = pd.to_datetime(W.index); W = W.sort_index()
W.to_parquet(BASE / "derived" / "spread_wide_all_nodes.parquet")
print("matrix", W.shape)
