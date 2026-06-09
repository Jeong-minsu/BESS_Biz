"""Build hourly wind+load panel + daily transmission-outage flags for the GKS POS deep-dive
window (2024-07-03 -> 2026-06-08). REAL Yes Energy datalake. Cached to derived/ parquet.

Wind (ercot/gen/wind_rti/{YYYYMMDD}.csv.gz): objid col0, value col4, hourly CST.
  GR_COASTAL=10004189446, GR_SOUTH=10004189447, GR_ERCOT=10004189442.
Load  (ercot/load/rtload_hourly/{YYYYMMDD}.csv.gz): ERCOT total = 10000712973, value col4, hourly.
Outage(ercot/transmission/outages/actual/{YYYYMMDD}23.csv.gz): one daily snapshot (HE23).
  col1=element name, col4=kv, col5/6=zones, col7=type, col8=Planned/Forced.
"""
import sys, io
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl

D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
WIND = {10004189446: "coastal", 10004189447: "south", 10004189442: "ercot_wind"}
LOAD_ID = 10000712973
dates = pd.date_range("2024-07-03", "2026-06-08", freq="D")

# ---- wind+load hourly panel ----
def wl_one(d):
    ds = d.strftime("%Y%m%d")
    out = []
    w = dl.try_read_csv(f"ercot/gen/wind_rti/{ds}.csv.gz", header=None)
    l = dl.try_read_csv(f"ercot/load/rtload_hourly/{ds}.csv.gz", header=None)
    if w is None or l is None:
        return None
    w = w[w[0].isin(WIND)].copy()
    w["dt"] = pd.to_datetime(w[2], format="%m/%d/%Y %H:%M:%S")
    w["reg"] = w[0].map(WIND)
    wp = w.pivot_table(index="dt", columns="reg", values=4, aggfunc="mean")
    l = l[l[0] == LOAD_ID].copy()
    l["dt"] = pd.to_datetime(l[2], format="%m/%d/%Y %H:%M:%S")
    lp = l.set_index("dt")[4].rename("load")
    df = wp.join(lp, how="outer")
    df["date"] = ds
    return df.reset_index()

def build_wl():
    fp = D / "panel_windload.parquet"
    if fp.exists():
        print("cached", fp); return pd.read_parquet(fp)
    rows = []
    with ThreadPoolExecutor(max_workers=32) as ex:
        for i, r in enumerate(ex.map(wl_one, dates)):
            if r is not None:
                rows.append(r)
            if i % 100 == 0:
                print("wl", i, "/", len(dates))
    df = pd.concat(rows, ignore_index=True)
    # MW -> GW for wind
    for c in ["coastal", "south", "ercot_wind"]:
        if c in df:
            df[c] = df[c] / 1000.0
    df.to_parquet(fp)
    print("saved", fp, df.shape)
    return df

# ---- daily 345kV LINE-level outage capture (South-TX coastal corridor) ----
# Station-name matching is undiscriminating (breakers/DSCs perpetually out). Match TYPE=LINE,
# kv=345, capture the actual corridor circuit names; derive boolean flags downstream.
CORR_TOKS = ["AJO", "REFORZAR", "ELM CREEK", "ELMCREEK", "BLESSING", "HILLJE", "LON HILL",
             "SAN MIGUEL", "SKYLINE", "STP-ELM", "STELLA", "MARION-ELM"]

def out_one(d):
    ds = d.strftime("%Y%m%d")
    df = dl.try_read_csv(f"ercot/transmission/outages/actual/{ds}23.csv.gz", header=None)
    if df is None:
        return {"date": ds, "lines345": None}
    sub = df[(df[4] == 345) & (df[7] == "LINE")]
    nm = sub[1].astype(str).str.upper()
    hit = sorted(nm[nm.str.contains("|".join(CORR_TOKS), regex=True, na=False)].unique())
    return {"date": ds, "lines345": ";".join(hit)}

def build_out():
    fp = D / "panel_outages.parquet"
    if fp.exists():
        print("cached", fp); return pd.read_parquet(fp)
    rows = []
    with ThreadPoolExecutor(max_workers=32) as ex:
        for i, r in enumerate(ex.map(out_one, dates)):
            rows.append(r)
            if i % 100 == 0:
                print("out", i, "/", len(dates))
    df = pd.DataFrame(rows)
    df.to_parquet(fp)
    print("saved", fp, df.shape, "coverage", df.lines345.notna().mean())
    return df

if __name__ == "__main__":
    wl = build_wl()
    print(wl.describe().to_string())
    od = build_out()
    print(od.drop(columns=["date"]).sum(numeric_only=True).to_string())
