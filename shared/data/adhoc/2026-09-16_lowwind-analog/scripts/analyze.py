"""Analog study: mid-day West+Coastal+South wind all low & net load slightly high.
Outcome = DA-RT spread (DA - RT) at HB_HUBAVG (ERCOT) and GKS_BESS_RN.
Season window: Jul 1 - Oct 31, 2021..2026 (actuals). Prices: HUBAVG 2021+, GKS 2024-07+.
"""
from __future__ import annotations
import glob
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAVEN = ROOT.parent / "2026-09-14_raven-node-analysis"
MID = list(range(11, 17))       # HE11..HE16 = 10:00-16:00 CT
EVE = list(range(17, 22))       # HE17..HE21
HUBAVG, GKS = 10000698382, 10017907494

# ---------- fundamentals ----------
wind = pd.read_parquet(ROOT / "raw" / "wind_region_hourly.parquet")
f1 = pd.read_parquet(RAVEN / "raw" / "item8" / "fundamentals.parquet")
f2 = pd.read_parquet(RAVEN / "raw" / "item6_fundamentals.parquet")
fund = pd.concat([f1, f2], ignore_index=True).drop_duplicates("hour_end").sort_values("hour_end")
fund["net_load"] = fund.load_mw - fund.wind_mw - fund.solar_mw

df = wind.merge(fund[["hour_end", "load_mw", "solar_mw", "net_load"]], on="hour_end", how="left")
df["HE"] = df.hour_end.dt.hour.replace(0, 24)
df["flowday"] = (df.hour_end - pd.Timedelta(hours=1)).dt.normalize()
df["year"] = df.flowday.dt.year
df = df[df.flowday.dt.month.isin([7, 8, 9, 10])]

# ---------- prices ----------
pp = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(RAVEN / "raw" / "price_panel" / "*.parquet")))])
pp = pp[pp.OBJECTID.isin([HUBAVG, GKS])].copy()
pp["hour_end"] = pd.to_datetime(pp.DATETIME, format="%m/%d/%Y %H:%M:%S")
pp["node"] = pp.OBJECTID.map({HUBAVG: "ERCOT", GKS: "GKS"})
pp = pp[["hour_end", "node", "DALMP", "RTLMP"]]
hb = pd.read_parquet(RAVEN / "raw" / "item8" / "hub_prices.parquet")
hb = hb[hb.node == "HB_HUBAVG"][["hour_end", "DALMP", "RTLMP"]].assign(node="ERCOT")
px = pd.concat([hb, pp], ignore_index=True).drop_duplicates(["hour_end", "node"])
px["spread"] = px.DALMP - px.RTLMP
px = px.pivot_table(index="hour_end", columns="node", values="spread")
px.columns = [f"sp_{c}" for c in px.columns]
df = df.merge(px, on="hour_end", how="left")

# ---------- daily mid-day features ----------
mid = df[df.HE.isin(MID)]
feat = mid.groupby(["flowday", "year"]).agg(
    w_west=("wind_west", "mean"), w_coast=("wind_coastal", "mean"),
    w_south=("wind_south", "mean"), w_tot=("wind_gr_ercot", "mean"),
    netload=("net_load", "mean"), load=("load_mw", "mean"),
).reset_index()

# percentile rank WITHIN the same Jul-Oct season-year (handles fleet growth / load growth)
for c in ["w_west", "w_coast", "w_south", "netload"]:
    feat[f"p_{c}"] = feat.groupby("year")[c].rank(pct=True) * 100

# ---------- tomorrow (2026-09-17 forecast) ----------
fc = pd.read_parquet(ROOT / "raw" / "fc_20260917.parquet").reset_index()
fc["HE"] = fc.hour_end.dt.hour.replace(0, 24)
fc["net_load"] = fc.load_fc - fc.wind_fc_gr_ercot - fc.solar_fc
fm = fc[fc.HE.isin(MID)]
tmr = dict(w_west=fm.wind_fc_west.mean(), w_coast=fm.wind_fc_coastal.mean(),
           w_south=fm.wind_fc_south.mean(), w_tot=fm.wind_fc_gr_ercot.mean(),
           netload=fm.net_load.mean(), load=fm.load_fc.mean())
cur = feat[feat.year == 2026]
tmr_p = {c: float((cur[c] < tmr[c]).mean() * 100) for c in ["w_west", "w_coast", "w_south", "netload"]}

print("=== 2026-09-17 D+1 forecast, mid-day HE11-16 mean (leakage-free vintage) ===")
for c in ["w_west", "w_coast", "w_south", "w_tot", "netload", "load"]:
    p = f"  (2026 Jul-Sep pctile {tmr_p[c]:.0f})" if c in tmr_p else ""
    print(f"  {c:9s} {tmr[c]:8,.0f} MW{p}")
print(f"  evening HE17-21 net load {fc[fc.HE.isin(EVE)].net_load.mean():,.0f} MW  "
      f"wind {fc[fc.HE.isin(EVE)].wind_fc_gr_ercot.mean():,.0f} MW")

# ---------- analog selection ----------
WIND_P, NL_LO, NL_HI = 30, 50, 85
sel = feat[(feat.p_w_west <= WIND_P) & (feat.p_w_coast <= WIND_P) & (feat.p_w_south <= WIND_P) &
           (feat.p_netload.between(NL_LO, NL_HI))]
print(f"\n=== analog days: all 3 regions mid-day wind <= p{WIND_P} of own season-year, "
      f"net load p{NL_LO}-{NL_HI}  ->  n={len(sel)} ===")
print(sel[["flowday", "w_west", "w_coast", "w_south", "w_tot", "netload",
           "p_w_west", "p_w_coast", "p_w_south", "p_netload"]]
      .round(0).to_string(index=False))

# looser: wind low only (no net-load filter), and all-days baseline
sel_wind = feat[(feat.p_w_west <= WIND_P) & (feat.p_w_coast <= WIND_P) & (feat.p_w_south <= WIND_P)]


def spread_stats(days, label):
    d = df[df.flowday.isin(days)]
    rows = []
    for name, hrs in [("mid HE11-16", MID), ("eve HE17-21", EVE), ("all 24h", list(range(1, 25)))]:
        s = d[d.HE.isin(hrs)]
        for node in ["ERCOT", "GKS"]:
            v = s[f"sp_{node}"].dropna()
            if len(v) == 0:
                continue
            rows.append(dict(set=label, block=name, node=node, n_hr=len(v),
                             mean=v.mean(), median=v.median(),
                             p_pos=(v > 0).mean() * 100, p10=v.quantile(.1), p90=v.quantile(.9)))
    return pd.DataFrame(rows)


base = feat.flowday
out = pd.concat([spread_stats(sel.flowday, "ANALOG(wind+NL)"),
                 spread_stats(sel_wind.flowday, "wind-low only"),
                 spread_stats(base, "Jul-Oct baseline")], ignore_index=True)
print("\n=== DA-RT spread (DA - RT, $/MWh); positive = DA rich = short DA ===")
print(out.round(2).to_string(index=False))

# hourly profile on analog days
hp = df[df.flowday.isin(sel.flowday)].groupby("HE")[["sp_ERCOT", "sp_GKS"]].agg(["mean", "median", "count"])
print("\n=== analog-day hourly mean/median DA-RT spread ===")
print(hp.round(2).to_string())

# per-day mid-day detail
det = df[df.flowday.isin(sel.flowday) & df.HE.isin(MID)].groupby("flowday")[["sp_ERCOT", "sp_GKS"]].mean()
det = det.join(sel.set_index("flowday")[["w_tot", "netload"]])
det["eve_ERCOT"] = df[df.flowday.isin(sel.flowday) & df.HE.isin(EVE)].groupby("flowday")["sp_ERCOT"].mean()
det["eve_GKS"] = df[df.flowday.isin(sel.flowday) & df.HE.isin(EVE)].groupby("flowday")["sp_GKS"].mean()
print("\n=== per analog day (mid-day & evening mean spread) ===")
print(det.round(1).to_string())

ROOT.joinpath("derived").mkdir(exist_ok=True)
feat.to_csv(ROOT / "derived" / "daily_features.csv", index=False)
out.to_csv(ROOT / "derived" / "spread_stats.csv", index=False)
det.to_csv(ROOT / "derived" / "analog_days.csv")
