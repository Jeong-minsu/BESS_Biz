"""ITEM 7 — daily transmission-outage snapshot (HE23) 2023-09-01..2026-09-13, for the outage lens of the
top-10 driver analysis (same source/approach as 2026-06-09_gks-congestion-impact/scripts/fetch_panel.py).
ercot/transmission/outages/actual/{YYYYMMDD}23.csv.gz, headerless: col1 element name, col2 from-station,
col3 to-station, col4 kV, col5/6 zones, col7 type, col8 Planned/Forced. Keep LINE / XFMR / AUTO >= 138 kV.
Output raw/item7_outages_daily.parquet (date, element, kv, zone_from, zone_to, type, cause). Real data only.
"""
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl

R = Path(__file__).resolve().parents[1]
OUT = R / "raw" / "item7_outages_daily.parquet"
DAYS = pd.date_range("2023-09-01", "2026-09-13", freq="D")
KEEP = {"LINE", "XFMR", "AUTO", "TRANSFORMER"}


def one(d):
    ds = d.strftime("%Y%m%d")
    df = dl.try_read_csv(f"ercot/transmission/outages/actual/{ds}23.csv.gz", header=None)
    if df is None: return None
    kv = pd.to_numeric(df[4], errors="coerce")
    sub = df[(kv >= 138) & (df[7].astype(str).str.upper().isin(KEEP))]
    if sub.empty: return None
    return pd.DataFrame({"date": ds, "element": sub[1].astype(str), "kv": kv[sub.index].astype(int),
                         "zone_from": sub[5].astype(str), "zone_to": sub[6].astype(str),
                         "type": sub[7].astype(str), "cause": sub[8].astype(str)})


def main():
    if OUT.exists():
        print("cached", OUT); return
    rows = []
    with ThreadPoolExecutor(24) as ex:
        for i, r in enumerate(ex.map(one, DAYS)):
            if r is not None: rows.append(r)
            if i % 100 == 0: print("day", i, "/", len(DAYS), flush=True)
    df = pd.concat(rows, ignore_index=True).drop_duplicates()
    df.to_parquet(OUT, index=False)
    print("saved", OUT, df.shape, "days", df.date.nunique(), "elements", df.element.nunique())


if __name__ == "__main__":
    main()
