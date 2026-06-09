"""Build full hourly panel 2023-01-01..2026-06-08 for trigger-threshold analysis.
Series (REAL Yes Energy datalake, no mock):
  COAST zone load (MW), Galveston/Hobby/Victoria drybulb (F),
  Coastal wind GR_COASTAL + GR_SOUTH (MW, wind_rti actual),
  South solar = SouthEast solar region (MW, generation_solar_rt actual),
  binding flag + lambda for MDOPHR99_A and STPWAP39_1 (DA).
"""
import concurrent.futures as cf
import pandas as pd
import dl

WZ_COAST = 10002211345
GR_COASTAL, GR_SOUTH = 10004189446, 10004189447       # wind_rti geographic regions
SOLAR_SE = 10017006228                                 # generation_solar_rt SouthEast region
START, END = "2023-01-01", "2026-06-08"
STATIONS = ["TX - Galveston/Scholes", "TX - Houston/William P. Hobby", "TX - Victoria/Regional Airport"]


def load_day(d):
    df = dl.try_read_csv(f"ercot/load/rtload_hourly_wz/{d:%Y%m%d}.csv.gz", header=None)
    if df is None: return None
    df.columns = ["OBJECTID","DATATYPEID","DATETIME","TIMEZONE","VALUE","LOADID"][:df.shape[1]]
    return df[df.OBJECTID == WZ_COAST][["DATETIME","VALUE"]].rename(columns={"VALUE":"coast_load"})


def wx_day(d):
    df = dl.try_read_csv(f"ercot/weather/actual/{d:%Y%m%d}.csv.gz", header=None)
    if df is None: return None
    df.columns = ["OBJECTID","DATETIME_UTC","DATETIME","TIMEZONE","NAME","WBAN","ISO","DRYBULB",
                  "WETBULB","DEWPT","WINDMPH","RH","PRESS","SKY","PRECIP"][:df.shape[1]]
    g = df[df.NAME.isin(STATIONS)][["DATETIME","NAME","DRYBULB"]].copy()
    g["NAME"] = g.NAME.map(lambda c: "galv_temp" if "Galveston" in c else "hobby_temp" if "Hobby" in c else "vict_temp")
    return g.pivot_table(index="DATETIME", columns="NAME", values="DRYBULB", aggfunc="mean").reset_index()


def wind_day(d):
    df = dl.try_read_csv(f"ercot/gen/wind_rti/{d:%Y%m%d}.csv.gz", header=None)
    if df is None: return None
    df.columns = ["OBJECTID","DATATYPEID","DATETIME","TIMEZONE","VALUE","SEQ"][:df.shape[1]]
    out = {}
    for oid, col in [(GR_COASTAL,"wind_coastal"),(GR_SOUTH,"wind_south")]:
        s = df[df.OBJECTID==oid].groupby("DATETIME")["VALUE"].mean().rename(col)
        out[col] = s
    if not out: return None
    return pd.concat(out.values(), axis=1).reset_index()


def solar_day(d):
    df = dl.try_read_csv(f"ercot/gen/generation_solar_rt/{d:%Y%m%d}.csv.gz", header=None)
    if df is None: return None
    df.columns = ["OBJECTID","DATATYPEID","DATETIME","TIMEZONE","VALUE","SEQ"][:df.shape[1]]
    s = df[df.OBJECTID==SOLAR_SE].groupby("DATETIME")["VALUE"].mean().rename("solar_se")
    return s.reset_index()


def gather(fn, days):
    with cf.ThreadPoolExecutor(max_workers=32) as ex:
        parts = [x for x in ex.map(fn, days) if x is not None and len(x)]
    return pd.concat(parts, ignore_index=True) if parts else None


def main():
    days = pd.date_range(START, END, freq="D")
    load = gather(load_day, days); print("load days done", load.DATETIME.nunique() if load is not None else 0)
    wx   = gather(wx_day, days);   print("wx done")
    wind = gather(wind_day, days); print("wind done", None if wind is None else wind.columns.tolist())
    solar= gather(solar_day, days);print("solar done", None if solar is None else len(solar))

    for df in (load, wx, wind, solar):
        if df is not None:
            df["dt"] = pd.to_datetime(df.DATETIME)

    panel = load.set_index("dt")[["coast_load"]]
    panel = panel.join(wx.set_index("dt").drop(columns=["DATETIME"]), how="left")
    if wind is not None:
        panel = panel.join(wind.set_index("dt").drop(columns=["DATETIME"]), how="left")
    if solar is not None:
        panel = panel.join(solar.set_index("dt")[["solar_se"]], how="left")

    b = pd.read_parquet("../derived/da_binding_mdophr_stpwap.parquet")
    b["dt"] = pd.to_datetime(b.DATETIME)
    for c in ["MDOPHR99_A","STPWAP39_1"]:
        lam = b[b.CONSTRAINTNAME==c].groupby("dt")["PRICE"].max()
        panel[c+"_bind"] = panel.index.isin(lam.index).astype(int)
        panel[c+"_lam"]  = lam.reindex(panel.index)

    panel = panel[(panel.index >= START) & (panel.index <= END+" 23:59")].copy()
    panel["year"]  = panel.index.year
    panel["month"] = panel.index.month
    panel["hour"]  = panel.index.hour
    panel["season"] = panel.month.map(lambda m: "summer" if m in (6,7,8) else
                                      "spring" if m in (3,4,5) else
                                      "fall" if m in (9,10,11) else "winter")
    panel.to_parquet("../derived/threshold_panel_2023_2026.parquet")
    cov = panel.notna().mean().round(3)
    print("\npanel rows", len(panel))
    print("coverage:\n", cov.to_string())
    print("\nbinding hrs: MDO", int(panel.MDOPHR99_A_bind.sum()), "STP", int(panel.STPWAP39_1_bind.sum()))
    print("MDO binding by year:\n", panel.groupby("year").MDOPHR99_A_bind.sum().to_string())
    print("STP binding by year:\n", panel.groupby("year").STPWAP39_1_bind.sum().to_string())


if __name__ == "__main__":
    main()
