"""Hourly driver panel + daily Valley transmission-outage panel, 2024-07-03..2026-09-30 (Yes Energy datalake, real data).
Outputs raw/drivers_hourly.parquet, raw/outages_valley_daily.parquet
"""
import sys, pandas as pd, concurrent.futures as cf
sys.path.insert(0, "."); import dl

DAYS = pd.date_range("2024-07-03", "2026-09-30")
SER = {  # (prefix, objectid, column name)
    "load_south": ("ercot/load/rtload_hourly_wz/", 10002211351),
    "load_ercot": ("ercot/load/rtload_hourly_wz/", 10002211353),
    "wind_south": ("ercot/gen/wind_rti/", 10004189447),
    "wind_coastal": ("ercot/gen/wind_rti/", 10004189446),
    "wind_ercot": ("ercot/gen/wind_rti/", 10004189442),
    "solar_se": ("ercot/gen/generation_solar_rt/", 10017006228),
    "solar_ercot": ("ercot/gen/generation_solar_rt/", 10000712973),
}
KBRO = 10000355284

def hourly(d):
    ymd = d.strftime("%Y%m%d"); out = []
    for pre in sorted({p for p, _ in SER.values()}):
        x = dl.try_read_csv(f"{pre}{ymd}.csv.gz", header=None)
        if x is None: continue
        for name, (p, oid) in SER.items():
            if p != pre: continue
            s = x[x[0] == oid]
            out.append(pd.DataFrame({"dt": s[2].values, "var": name, "val": s[4].values}))
    w = dl.try_read_csv(f"ercot/weather/actual/{ymd}.csv.gz", header=None)
    if w is not None:
        s = w[w[0] == KBRO]
        out.append(pd.DataFrame({"dt": s[2].values, "var": "temp_bro", "val": s[7].values}))
        out.append(pd.DataFrame({"dt": s[2].values, "var": "dew_bro", "val": s[9].values}))
    return pd.concat(out) if out else None

OUT_COLS = ["ISO","FACILITY","FROMSTATION","TOSTATION","KV","FROMZONE","TOZONE","FACILITY_TYPE","TYPE","TYPE_DETAIL",
            "STATUS","STATUS_DETAIL","STARTDATE","ENDDATE","PLANNED_STARTDATE","PLANNED_ENDDATE","OPEN_CLOSE","TICKETID",
            "FACILITYID","LASTCHANGEDATE","PUBLISHDATE","REPORTED_NAME","FROMSTATIONID","TOSTATIONID"]

def outages(d):
    ymd = d.strftime("%Y%m%d"); rows = []
    for hh in ("12", "17"):  # midday + evening-peak snapshots
        df = dl.try_read_csv(f"ercot/transmission/outages/actual/{ymd}{hh}.csv.gz", header=None)
        if df is None: continue
        df.columns = OUT_COLS[:df.shape[1]]
        df = df[(df.STATUS.astype(str).str.upper() == "ACTIVE") & ((df.FROMZONE == "SOUTH") | (df.TOZONE == "SOUTH"))]
        df = df[df.FACILITY_TYPE.isin(["LINE", "XFMR", "SVC", "CAP", "SR", "SC"]) & (pd.to_numeric(df.KV, errors="coerce") >= 69)]
        df = df[["FACILITY","FROMSTATION","TOSTATION","KV","FACILITY_TYPE","TYPE","STARTDATE","ENDDATE","FACILITYID"]].copy()
        df["date"] = d; df["snap"] = hh; rows.append(df)
    return pd.concat(rows) if rows else None

if __name__ == "__main__":
    with cf.ThreadPoolExecutor(24) as ex:
        h = [x for x in ex.map(hourly, DAYS) if x is not None]
    h = pd.concat(h); h["dt"] = pd.to_datetime(h.dt)
    h = h.pivot_table(index="dt", columns="var", values="val", aggfunc="mean").sort_index()
    h.to_parquet("../raw/drivers_hourly.parquet"); print("drivers", h.shape, h.index.min(), h.index.max()); print(h.describe().round(0).to_string())
    with cf.ThreadPoolExecutor(24) as ex:
        o = [x for x in ex.map(outages, DAYS) if x is not None]
    o = pd.concat(o); o.to_parquet("../raw/outages_valley_daily.parquet"); print("outages", o.shape, o.date.nunique())
