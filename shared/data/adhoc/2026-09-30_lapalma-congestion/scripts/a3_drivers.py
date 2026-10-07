"""Hourly driver analysis for La Palma family. Outputs derived/panel_hourly.parquet + derived/a3_drivers.json"""
import json, pandas as pd, numpy as np
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
D = "../derived/"
h = pd.read_parquet("../raw/drivers_hourly.parquet")
h["net_south"] = h.load_south - h.wind_south - h.solar_se
da = pd.read_parquet(D + "da_family_hourly.parquet"); rt = pd.read_parquet(D + "rt_family_hourly.parquet")
grp = {"XF": ["LA_PALMA_XF1A", "LA_PALMA_XF1B"], "HAINE": ["HAINE__LA_PAL1_1"], "VCAV": ["LA_PAL_VCAVAZ1_1"]}
for k, names in grp.items():
    h[f"da_{k}"] = da[da.CONSTRAINTNAME.isin(names)].groupby("he_end").PRICE.max().reindex(h.index).fillna(0)
    r = rt[rt.CONSTRAINTNAME.isin(names)].groupby("he_end").agg(p=("rt_px", "max"), n=("rt_n", "sum"))
    h[f"rt_{k}"] = r.p.reindex(h.index).fillna(0); h[f"rtn_{k}"] = r.n.reindex(h.index).fillna(0)
h["he"] = (h.index - pd.Timedelta(minutes=1)).hour + 1
h["month"] = h.index.month
h.to_parquet(D + "panel_hourly.parquet")
out = {}

def cond(df, col, var, bins):
    c = pd.cut(df[var], bins)
    g = df.groupby(c, observed=True).agg(n=(col, "size"), p_bind=(col, lambda s: (s > 0).mean()), mean_px=(col, "mean"))
    return g.round(3)

# ---------- XF regime: 2026-08-01 .. 09-30 ----------
x = h.loc["2026-08-01":"2026-09-30 23:00"].copy()
x["post916"] = x.index >= "2026-09-17"
x["bind"] = ((x.da_XF > 0) | (x.rt_XF > 0)).astype(int)
print("XF bind share by regime:", x.groupby("post916").bind.mean().round(3).to_dict())
print("\nXF by HE (post 9/17):"); print(x[x.post916].groupby("he").agg(p=("bind", "mean"), da=("da_XF", "mean"), rt=("rt_XF", "mean")).round(2).T.to_string())
print("\nXF by HE (Aug1-Sep16):"); print(x[~x.post916].groupby("he").agg(p=("bind", "mean")).round(2).T.to_string())
xe = x[x.he.between(12, 21)]
for var, bins in [("load_south", [0, 5500, 6000, 6300, 6600, 6900, 9000]), ("temp_bro", [0, 86, 89, 91, 93, 110]),
                  ("wind_south", [-1, 800, 1300, 1800, 2500, 5000]), ("solar_se", [-1, 300, 800, 1300, 1800, 5000]),
                  ("net_south", [0, 2500, 3500, 4000, 4500, 5000, 9000])]:
    for reg, g in xe.groupby("post916"):
        t = cond(g, "bind", var, bins); print(f"\n[XF HE12-21 post916={reg}] {var}\n", t.to_string())
        out[f"XF_{var}_post{int(reg)}"] = t.reset_index().astype(str).to_dict("records")
print("\nAug vs Sep driver means HE16-20:"); print(x[x.he.between(16, 20)].groupby([x[x.he.between(16, 20)].index.month, "post916"])[["load_south", "temp_bro", "wind_south", "solar_se", "net_south", "bind"]].mean().round(2).to_string())

# ---------- HAINE & VCAV long history (2024-07 .. ) ----------
for k in ["HAINE", "VCAV"]:
    y = h.copy(); y["bind"] = ((y[f"da_{k}"] > 0) | (y[f"rt_{k}"] > 0)).astype(int)
    mh = y.pivot_table(index="month", columns="he", values="bind", aggfunc="mean").round(2)
    print(f"\n==== {k}: P(bind) month x HE (all years)"); print(mh.to_string())
    out[f"{k}_month_he"] = mh.to_dict()
    yy = y[y.index >= "2025-01-01"]
    for var, bins in [("load_south", [0, 3500, 4000, 4500, 5000, 5500, 6000, 9000]), ("wind_south", [-1, 500, 1000, 1500, 2000, 2500, 5000]),
                      ("solar_se", [-1, 100, 500, 1000, 1500, 2000, 5000]), ("temp_bro", [0, 60, 70, 80, 88, 93, 110])]:
        t = cond(yy, "bind", var, bins); print(f"\n[{k} 2025+] {var}\n", t.to_string())
        out[f"{k}_{var}"] = t.reset_index().astype(str).to_dict("records")
    print(f"\n[{k}] yearly bind share:", y.groupby(y.index.year).bind.mean().round(3).to_dict())
json.dump(out, open(D + "a3_drivers.json", "w"), indent=1)
