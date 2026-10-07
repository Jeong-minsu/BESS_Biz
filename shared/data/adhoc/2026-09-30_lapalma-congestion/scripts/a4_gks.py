import pandas as pd, numpy as np, json
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
old = pd.read_parquet("../../2026-06-09_gks-congestion-impact/derived/gks_msf_raw.parquet")
new = pd.read_parquet("../raw/gks_msf_2026Q3.parquet").drop(columns=["PNODE"])
m = pd.concat([old[old.day < "20260609"], new.assign(day=new.day.astype(str))])
m = m[m.CONSTRAINTNAME.astype(str).str.contains("LA_PAL")]
m["ts"] = pd.to_datetime(m.DATETIME, format="%m/%d/%Y %H:%M:%S")
m["mcc"] = -m.SHIFTFACTOR * m.SHADOWPRICE
# DA rows hourly (hour-ending stamp); RT rows 5-min -> hourly mean contribution
m["he_end"] = np.where(m.MARKET == "DA", m.ts, m.ts.dt.floor("h") + pd.Timedelta(hours=1))
m["he_end"] = pd.to_datetime(m.he_end)
da = m[m.MARKET == "DA"].groupby(["CONSTRAINTNAME", "he_end"]).mcc.sum()
# RT: sum per SCED interval then average per hour (non-binding intervals = 0 -> use 12 intervals/hr)
rt = m[m.MARKET == "RT"].groupby(["CONSTRAINTNAME", "he_end"]).mcc.sum() / 12
t = pd.concat([da.rename("da"), rt.rename("rt")], axis=1).fillna(0).reset_index()
t["m"] = t.he_end.dt.to_period("M")
print("GKS SF on XF (recent):", m[m.CONSTRAINTNAME.str.startswith("LA_PALMA_XF")].groupby(["CONSTRAINTNAME","MARKET"]).SHIFTFACTOR.agg(["mean","min","max"]).round(3).to_string())
mm = t.groupby(["m", "CONSTRAINTNAME"])[["da", "rt"]].sum().unstack().fillna(0).round(0)
print("\nGKS congestion $/MW (sum over hours of MCC, $/MWh*h) by month:\n", mm.loc["2025-01":].to_string())
x = t[t.CONSTRAINTNAME.str.startswith("LA_PALMA_XF")].groupby("he_end")[["da", "rt"]].sum()
x = x.loc["2026-09-01":]; x["date"] = (x.index - pd.Timedelta(minutes=1)).normalize(); x["he"] = (x.index - pd.Timedelta(minutes=1)).hour + 1
print("\nXF-driven GKS MCC by day (sum $/MW-day):\n", x.groupby("date")[["da", "rt"]].sum().round(0).to_string())
print("\nXF-driven GKS MCC post 9/17 by HE (mean $/MWh):\n", x.loc["2026-09-17":].groupby("he")[["da", "rt"]].mean().round(1).T.to_string())
t.to_parquet("../derived/gks_mcc_lapalma_hourly.parquet")
