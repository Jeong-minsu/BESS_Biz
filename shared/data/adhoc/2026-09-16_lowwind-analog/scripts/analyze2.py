"""v2 - analog cut re-centred on the ACTUAL 2026-09-17 shape
(coastal/south wind low, west ~median, net load high-ish). NN matching on percentile vector.
"""
from __future__ import annotations
import glob
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAVEN = ROOT.parent / "2026-09-14_raven-node-analysis"
MID, EVE = list(range(11, 17)), list(range(17, 22))
HUBAVG, GKS = 10000698382, 10017907494

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

mid = df[df.HE.isin(MID)]
feat = mid.groupby(["flowday", "year"]).agg(
    w_west=("wind_west", "mean"), w_coast=("wind_coastal", "mean"),
    w_south=("wind_south", "mean"), w_tot=("wind_gr_ercot", "mean"),
    netload=("net_load", "mean")).reset_index()
FCOLS = ["w_west", "w_coast", "w_south", "w_tot", "netload"]
for c in FCOLS:
    feat[f"p_{c}"] = feat.groupby("year")[c].rank(pct=True) * 100

fc = pd.read_parquet(ROOT / "raw" / "fc_20260917.parquet").reset_index()
fc["HE"] = fc.hour_end.dt.hour.replace(0, 24)
fc["net_load"] = fc.load_fc - fc.wind_fc_gr_ercot - fc.solar_fc
fm = fc[fc.HE.isin(MID)]
tmr = dict(w_west=fm.wind_fc_west.mean(), w_coast=fm.wind_fc_coastal.mean(),
           w_south=fm.wind_fc_south.mean(), w_tot=fm.wind_fc_gr_ercot.mean(),
           netload=fm.net_load.mean())
cur = feat[feat.year == 2026]
tp = {c: float((cur[c] < tmr[c]).mean() * 100) for c in FCOLS}
print("=== 2026-09-17 D+1 (leakage-free vintage), mid-day HE11-16 mean ===")
for c in FCOLS:
    print(f"  {c:8s} {tmr[c]:8,.0f} MW   pctile vs 2026 Jul-Sep: {tp[c]:.0f}")

# --- NN match on percentile vector (weights: coastal/south emphasised, west & netload) ---
W = dict(p_w_west=1.0, p_w_coast=1.2, p_w_south=1.2, p_netload=1.0)
d2 = sum(w * (feat[c] - tp[c.replace("p_", "")]) ** 2 for c, w in W.items())
feat["dist"] = np.sqrt(d2 / sum(W.values()))
nn = feat.nsmallest(25, "dist")

# --- rule cut ---
rule = feat[(feat.p_w_coast <= 30) & (feat.p_w_south <= 30) &
            (feat.p_w_west.between(25, 70)) & (feat.p_netload >= 70)]

print(f"\n=== rule cut (coastal&south <=p30, west p25-70, netload >=p70): n={len(rule)} ===")
print(rule[["flowday"] + FCOLS + ["p_w_west", "p_w_coast", "p_w_south", "p_netload"]]
      .round(0).to_string(index=False))
print(f"\n=== nearest-neighbour top25 (mean dist {nn.dist.mean():.1f} pctile-pts) ===")
print(nn[["flowday", "dist"] + FCOLS + ["p_w_west", "p_w_coast", "p_w_south", "p_netload"]]
      .round(0).to_string(index=False))


def tmean(v, q=0.05):
    lo, hi = v.quantile(q), v.quantile(1 - q)
    return v.clip(lo, hi).mean()


def stats(days, label):
    d = df[df.flowday.isin(days)]
    rows = []
    for name, hrs in [("mid HE11-16", MID), ("eve HE17-21", EVE), ("all 24h", list(range(1, 25)))]:
        s = d[d.HE.isin(hrs)]
        for node in ["ERCOT", "GKS"]:
            v = s[f"sp_{node}"].dropna()
            if not len(v):
                continue
            rows.append(dict(set=label, block=name, node=node, n_day=s.flowday.nunique(), n_hr=len(v),
                             mean=v.mean(), win_mean=tmean(v), median=v.median(),
                             pct_pos=(v > 0).mean() * 100, p10=v.quantile(.1), p90=v.quantile(.9)))
    return pd.DataFrame(rows)


res = pd.concat([stats(rule.flowday, "RULE"), stats(nn.flowday, "NN25"),
                 stats(feat.flowday, "BASE JulOct"),
                 stats(feat[feat.flowday.dt.month == 9].flowday, "BASE Sep")], ignore_index=True)
print("\n=== DA-RT spread (DA - RT, $/MWh). +=DA rich => short DA / long RT ===")
print(res.round(2).to_string(index=False))

for lab, days in [("RULE", rule.flowday), ("NN25", nn.flowday)]:
    hp = df[df.flowday.isin(days)].groupby("HE")[["sp_ERCOT", "sp_GKS"]].agg(["median", "mean", "count"])
    print(f"\n=== {lab}: hourly DA-RT spread ===")
    print(hp.round(1).to_string())

det = (df[df.flowday.isin(nn.flowday) & df.HE.isin(MID)].groupby("flowday")[["sp_ERCOT", "sp_GKS"]].mean()
       .rename(columns={"sp_ERCOT": "mid_ERCOT", "sp_GKS": "mid_GKS"}))
det = det.join(df[df.flowday.isin(nn.flowday) & df.HE.isin(EVE)].groupby("flowday")[["sp_ERCOT", "sp_GKS"]]
               .mean().rename(columns={"sp_ERCOT": "eve_ERCOT", "sp_GKS": "eve_GKS"}))
det = det.join(nn.set_index("flowday")[["w_tot", "netload", "dist"]])
print("\n=== NN25 per-day ===")
print(det.sort_values("dist").round(1).to_string())

feat.to_csv(ROOT / "derived" / "daily_features_v2.csv", index=False)
res.to_csv(ROOT / "derived" / "spread_stats_v2.csv", index=False)
det.to_csv(ROOT / "derived" / "nn25_days.csv")

# ---- regime-consistent slice: 2025-2026 only (GKS live, post-RTC fleet) ----
recent = feat[feat.year >= 2025].nsmallest(15, "dist")
print("\n=== NN15 within 2025-2026 only ===")
print(recent[["flowday", "dist", "w_west", "w_coast", "w_south", "w_tot", "netload",
              "p_w_coast", "p_w_south", "p_netload"]].round(0).to_string(index=False))
print(pd.concat([stats(recent.flowday, "NN15 25-26"),
                 stats(feat[feat.year >= 2025].flowday, "BASE 25-26")]).round(2).to_string(index=False))
hp = df[df.flowday.isin(recent.flowday)].groupby("HE")[["sp_ERCOT", "sp_GKS"]].agg(["median", "mean"])
print("\n=== NN15 25-26 hourly ===")
print(hp.round(1).to_string())
d2 = (df[df.flowday.isin(recent.flowday) & df.HE.isin(MID)].groupby("flowday")[["sp_ERCOT","sp_GKS"]].mean()
      .rename(columns={"sp_ERCOT":"mid_E","sp_GKS":"mid_G"}))
d2 = d2.join(df[df.flowday.isin(recent.flowday) & df.HE.isin(EVE)].groupby("flowday")[["sp_ERCOT","sp_GKS"]]
             .mean().rename(columns={"sp_ERCOT":"eve_E","sp_GKS":"eve_G"}))
print(d2.round(1).to_string())
