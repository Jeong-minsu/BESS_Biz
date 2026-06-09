"""Build hourly panel Apr-Sep 2025: COAST load + coastal temps + binding flags.
Then conditional binding frequency / correlation per lens."""
import concurrent.futures as cf
import numpy as np
import pandas as pd
import dl

WZ_COAST = 10002211345
START, END = "2025-04-01", "2025-09-30"
STATIONS = ["TX - Galveston/Scholes", "TX - Houston/William P. Hobby", "TX - Victoria/Regional Airport"]

def load_day(d):
    ymd = d.strftime("%Y%m%d")
    df = dl.try_read_csv(f"ercot/load/rtload_hourly_wz/{ymd}.csv.gz", header=None)
    if df is None: return None
    df.columns = ["OBJECTID","DATATYPEID","DATETIME","TIMEZONE","VALUE","LOADID"]
    g = df[df.OBJECTID == WZ_COAST][["DATETIME","VALUE"]].rename(columns={"VALUE":"coast_load"})
    return g

def wx_day(d):
    ymd = d.strftime("%Y%m%d")
    df = dl.try_read_csv(f"ercot/weather/actual/{ymd}.csv.gz", header=None)
    if df is None: return None
    df.columns = ["OBJECTID","DATETIME_UTC","DATETIME","TIMEZONE","NAME","WBAN","ISO","DRYBULB",
                  "WETBULB","DEWPT","WINDMPH","RH","PRESS","SKY","PRECIP"]
    g = df[df.NAME.isin(STATIONS)][["DATETIME","NAME","DRYBULB","WINDMPH"]]
    return g

def main():
    days = pd.date_range(START, END, freq="D")
    with cf.ThreadPoolExecutor(max_workers=24) as ex:
        load = pd.concat([x for x in ex.map(load_day, days) if x is not None], ignore_index=True)
        wx = pd.concat([x for x in ex.map(wx_day, days) if x is not None], ignore_index=True)
    load["dt"] = pd.to_datetime(load.DATETIME)
    wx["dt"] = pd.to_datetime(wx.DATETIME)
    # pivot temps
    temp = wx.pivot_table(index="dt", columns="NAME", values="DRYBULB", aggfunc="mean")
    temp.columns = ["galv_temp" if "Galveston" in c else "hobby_temp" if "Hobby" in c else "vict_temp" for c in temp.columns]
    panel = load.set_index("dt")[["coast_load"]].join(temp, how="outer")
    # binding flags from DA parquet
    b = pd.read_parquet("../derived/da_binding_mdophr_stpwap.parquet")
    b["dt"] = pd.to_datetime(b.DATETIME)
    for c in ["MDOPHR99_A","STPWAP39_1"]:
        lam = b[b.CONSTRAINTNAME==c].groupby("dt")["PRICE"].max()
        panel[c+"_bind"] = panel.index.isin(lam.index).astype(int)
        panel[c+"_lam"] = lam.reindex(panel.index)
    panel = panel[(panel.index >= START) & (panel.index <= END + " 23:59")]
    panel.to_parquet("../derived/panel_2025_apr_sep.parquet")
    print("panel rows", len(panel), "| binding hrs MDO", panel.MDOPHR99_A_bind.sum(), "STP", panel.STPWAP39_1_bind.sum())
    print("coverage: coast_load nonnull", panel.coast_load.notna().mean().round(2),
          "galv", panel.galv_temp.notna().mean().round(2), "vict", panel.vict_temp.notna().mean().round(2))

    for c in ["MDOPHR99_A","STPWAP39_1"]:
        print(f"\n############ {c} ############")
        p = panel.dropna(subset=["coast_load"])
        # DEMAND: binding freq by coast-load decile
        p = p.copy(); p["ld_dec"] = pd.qcut(p.coast_load, 10, labels=False)
        bf = p.groupby("ld_dec")[c+"_bind"].mean()
        print("P(bind) by COAST-load decile (0=low..9=high):")
        print((bf*100).round(1).to_string())
        print("corr(coast_load, lambda | binding) =",
              round(p.loc[p[c+"_bind"]==1, ["coast_load", c+"_lam"]].corr().iloc[0,1], 3))
        # TEMP
        pt = panel.dropna(subset=["galv_temp"]).copy()
        pt["t_dec"] = pd.qcut(pt.galv_temp, 10, labels=False, duplicates="drop")
        tf = pt.groupby("t_dec")[c+"_bind"].mean()
        print("P(bind) by Galveston-temp decile:")
        print((tf*100).round(1).to_string())

if __name__ == "__main__":
    main()
