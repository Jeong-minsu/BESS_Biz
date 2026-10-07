"""ITEM 8 - build the daily driver panel for the TB2 decomposition (2021-01-01 .. 2026-09-13).

Inputs (all real, already on disk):
  raw/item8/hub_prices.parquet      HB_HUBAVG / HB_HOUSTON hourly DA+RT, 2021-01..2023-08
  raw/price_panel/{YYYYMM}.parquet  all nodes hourly, 2023-09..2026-09  (filtered to the two hubs)
  raw/item8/fundamentals.parquet    system load/wind/solar hourly 2021-01..2023-11
  raw/item6_fundamentals.parquet    same, 2023-12..2026-09
  raw/item8/gas.parquet             Houston Ship Channel daily gas $/MMBtu (weekday only -> ffill)
  raw/item8/op_reserve.parquet      5-min RT operating reserves, daily min/p05/mean (2022-07-21+)
  raw/item8/storage.parquet         5-min ERCOT power-storage fuel-mix output, daily max (2023-01-24+)
  raw/item7_driver_panel.parquet    hourly temps (DFW/Hobby etc.) 2023-09+  (used only as robustness covariate)
  ../2026-07-15_capacity-outlook/actuals_2022_H1-2026.csv   YE nameplate anchors for ESS / solar (ERCOT CDR)

Output: derived/item8_panel_daily.parquet (+ .csv)
TB2 = mean(top-2 hours) - mean(bottom-2 hours) per flowday, DA and RT, for HB_HUBAVG (system) and HB_HOUSTON.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
OUT = ROOT / "derived"
CAP = ROOT.parent / "2026-07-15_capacity-outlook"
HUBS = {10000698382: "HB_HUBAVG", 10000697077: "HB_HOUSTON"}


def tb2(s: pd.Series) -> float:
    v = np.sort(s.dropna().values)
    if len(v) < 20:
        return np.nan
    return v[-2:].mean() - v[:2].mean()


def hub_hourly() -> pd.DataFrame:
    a = pd.read_parquet(RAW / "item8/hub_prices.parquet")
    parts = [a[["node", "hour_end", "DALMP", "RTLMP", "flowday"]]]
    for f in sorted((RAW / "price_panel").glob("*.parquet")):
        p = pd.read_parquet(f, columns=["OBJECTID", "DATETIME", "DALMP", "RTLMP", "FLOWDAY"])
        p = p[p.OBJECTID.isin(HUBS)]
        parts.append(pd.DataFrame({"node": p.OBJECTID.map(HUBS),
                                   "hour_end": pd.to_datetime(p.DATETIME, format="%m/%d/%Y %H:%M:%S"),
                                   "DALMP": p.DALMP, "RTLMP": p.RTLMP, "flowday": pd.to_datetime(p.FLOWDAY)}))
    h = pd.concat(parts, ignore_index=True)
    h["flowday"] = pd.to_datetime(h.flowday)
    return h.drop_duplicates(["node", "hour_end"]).sort_values(["node", "hour_end"])


def price_daily(h: pd.DataFrame) -> pd.DataFrame:
    rows = {}
    for node, tag in (("HB_HUBAVG", "sys"), ("HB_HOUSTON", "hou")):
        g = h[h.node == node].groupby("flowday")
        d = pd.DataFrame({
            f"tb2_da_{tag}": g.DALMP.apply(tb2),
            f"tb2_rt_{tag}": g.RTLMP.apply(tb2),
            f"rt_mean_{tag}": g.RTLMP.mean(),
            f"da_mean_{tag}": g.DALMP.mean(),
            f"rt_max_{tag}": g.RTLMP.max(),
            f"rt_hrs_gt500_{tag}": g.RTLMP.apply(lambda s: int((s > 500).sum())),
            f"rt_hrs_gt1000_{tag}": g.RTLMP.apply(lambda s: int((s > 1000).sum())),
            f"da_hrs_gt500_{tag}": g.DALMP.apply(lambda s: int((s > 500).sum())),
        })
        rows[tag] = d
    return rows["sys"].join(rows["hou"], how="outer")


def fundamentals_daily() -> pd.DataFrame:
    a = pd.read_parquet(RAW / "item8/fundamentals.parquet")
    b = pd.read_parquet(RAW / "item6_fundamentals.parquet")
    f = pd.concat([a, b], ignore_index=True).drop_duplicates("hour_end").sort_values("hour_end")
    f["flowday"] = pd.to_datetime(f.flowday)
    f["netload"] = f.load_mw - f.wind_mw.fillna(0) - f.solar_mw.fillna(0)
    g = f.groupby("flowday")

    def ramp3(s):  # largest 3-hour rise in net load (evening ramp)
        v = s.values
        return np.nanmax(v[3:] - v[:-3]) if len(v) > 4 else np.nan

    d = pd.DataFrame({
        "load_peak": g.load_mw.max(), "load_mean": g.load_mw.mean(), "load_min": g.load_mw.min(),
        "wind_mean": g.wind_mw.mean(), "wind_min": g.wind_mw.min(),
        "solar_peak": g.solar_mw.max(),
        "netload_peak": g.netload.max(), "netload_min": g.netload.min(),
        "netload_range": g.netload.max() - g.netload.min(),
        "netload_ramp3h": g.netload.apply(ramp3),
        "n_hours": g.load_mw.count(),
    })
    d["renew_share"] = (g.wind_mw.sum() + g.solar_mw.sum()) / g.load_mw.sum()
    return d


def gas_daily(idx) -> pd.Series:
    g = pd.read_parquet(RAW / "item8/gas.parquet").set_index("flowday").gas_hsc
    g = g.replace(0, np.nan)
    return g.reindex(idx).ffill(limit=5)


def opres_daily() -> pd.DataFrame:
    o = pd.read_parquet(RAW / "item8/op_reserve.parquet").set_index("flowday")
    # the feed contains occasional corrupt sentinels (e.g. -6.7e8); keep physically plausible MW only
    for c in ("opres_min", "opres_p05", "opres_mean"):
        o.loc[(o[c] < 0) | (o[c] > 60000), c] = np.nan
    return o[["opres_min", "opres_p05", "opres_mean"]]


def storage_daily() -> pd.Series:
    s = pd.read_parquet(RAW / "item8/storage.parquet").set_index("flowday").stor_max_mw
    return s


def installed_capacity(idx) -> pd.DataFrame:
    """Monthly-interpolated nameplate MW from ERCOT CDR year-end anchors (operational+synchronized, ex-PUN).
    YE2021 anchors are from ERCOT CDR Dec-2021 / EIA-860M (see item8_FINDINGS for source); all later
    anchors from ../2026-07-15_capacity-outlook/actuals_2022_H1-2026.csv."""
    a = pd.read_csv(CAP / "actuals_2022_H1-2026.csv", encoding="utf-8-sig").set_index("technology")
    ess = a.loc["ESS (power MW)"]
    sol = a.loc["Solar (utility-scale)"]
    anchors_ess = {"2021-12-31": YE2021_ESS, "2022-12-31": ess.YE2022, "2023-12-31": ess.YE2023,
                   "2024-12-31": ess.YE2024, "2025-12-31": ess.YE2025, "2026-06-30": ess.H1_2026}
    anchors_sol = {"2021-12-31": YE2021_SOLAR, "2022-12-31": sol.YE2022, "2023-12-31": sol.YE2023,
                   "2024-12-31": sol.YE2024, "2025-12-31": sol.YE2025, "2026-06-30": sol.H1_2026}

    def interp(anch):
        s = pd.Series({pd.Timestamp(k): float(v) for k, v in anch.items()}).sort_index()
        full = pd.Series(index=idx, dtype=float)
        full.loc[s.index.intersection(idx)] = s.loc[s.index.intersection(idx)]
        full = full.interpolate(method="time")
        # extrapolate linearly outside anchors using the adjacent segment slope
        first, last = s.index[0], s.index[-1]
        if idx[0] < first:
            slope = (s.iloc[1] - s.iloc[0]) / (s.index[1] - s.index[0]).days
            m = idx < first
            full.loc[m] = s.iloc[0] + slope * (idx[m] - first).days
        if idx[-1] > last:
            slope = (s.iloc[-1] - s.iloc[-2]) / (s.index[-1] - s.index[-2]).days
            m = idx > last
            full.loc[m] = s.iloc[-1] + slope * (idx[m] - last).days
        return full

    return pd.DataFrame({"ess_mw_installed": interp(anchors_ess), "solar_mw_installed": interp(anchors_sol)}, index=idx)


def temps_daily() -> pd.DataFrame:
    t = pd.read_parquet(RAW / "item7_driver_panel.parquet")
    t.index = pd.to_datetime(t.index)
    fd = (t.index - pd.Timedelta(seconds=1)).normalize()
    g = t.groupby(fd)
    d = pd.DataFrame({"tmax_dfw": g.temp_dfw.max(), "tmin_dfw": g.temp_dfw.min(),
                      "tmax_hou": g.temp_hobby.max(), "tmin_hou": g.temp_hobby.min()})
    tavg = (t[["temp_dfw", "temp_hobby", "temp_sanantonio", "temp_austin"]].mean(axis=1)).groupby(fd).mean()
    d["cdd"] = (tavg - 65).clip(lower=0)
    d["hdd"] = (65 - tavg).clip(lower=0)
    d.index.name = "flowday"
    return d


# ---- YE2021 anchors (nameplate MW) --------------------------------------------------------------
YE2021_ESS = float(sys.argv[1]) if len(sys.argv) > 1 else np.nan
YE2021_SOLAR = float(sys.argv[2]) if len(sys.argv) > 2 else np.nan

if __name__ == "__main__":
    h = hub_hourly()
    print("hub hourly", h.shape, h.flowday.min().date(), h.flowday.max().date())
    px = price_daily(h)
    fd = fundamentals_daily()
    panel = px.join(fd, how="left")
    idx = panel.index
    panel["gas_hsc"] = gas_daily(idx)
    panel = panel.join(opres_daily(), how="left").join(storage_daily().rename("stor_max_mw"), how="left")
    panel = panel.join(installed_capacity(idx), how="left").join(temps_daily(), how="left")
    panel["opres_min_pct_load"] = panel.opres_min / panel.load_peak * 100
    panel["year"] = idx.year
    panel["month"] = idx.month
    panel.index.name = "flowday"
    panel = panel[panel.index <= "2026-09-13"]
    panel.to_parquet(OUT / "item8_panel_daily.parquet")
    panel.round(3).to_csv(OUT / "item8_panel_daily.csv")
    print(panel.shape)
    print(panel.isna().sum().to_string())
    print(panel.groupby("year")[["tb2_da_sys", "tb2_rt_sys", "tb2_rt_hou", "gas_hsc", "load_peak", "netload_range",
                                 "opres_min", "ess_mw_installed", "solar_mw_installed", "stor_max_mw"]].mean().round(1).to_string())
