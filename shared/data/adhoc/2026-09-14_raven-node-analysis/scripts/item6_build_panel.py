"""ITEM 6 - hourly panel for conditional DART analysis at RVN_RN.
Rows: FLOWDAY x HE (1..24; HE25 on DST fall-back dropped). Window 2023-12-01..2026-09-13.
  spread_rvn  = DA - RT at RVN_RN: REAL from 2026-06-04, item2 NNLS proxy before (src column says which)
  spread_sys  = HB_BUSAVG spread; spread_hou = HB_HOUSTON spread; basis_spread = spread_rvn - spread_hou
  mcc_da / mcc_rt = total congestion $ at the Raven location that hour (from item2 panel, -SF*lambda, RT = duration-weighted)
  per-constraint DA-bind indicator columns  da_<C>  (1 if C bound in DA that hour) and mcc columns mccda_<C>, mccrt_<C>
  fundamentals (system load/wind/solar MW actuals) if raw/item6_fundamentals.parquet exists
Alignment of the congestion panel's `hour` to HE is chosen empirically (max corr between mcc_da and DA basis vs BUSAVG).
Output: derived/item6_panel.parquet
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; D = ROOT / "derived"
W0 = "2023-12-01"; REAL0 = "2026-06-04"
pdef = json.loads((D / "item2_proxy_definition.json").read_text()); W = dict(zip(pdef["nodes"], pdef["weights"])); C = pdef["intercept"]

panel = pd.read_parquet(D / "item3a_node_panel.parquet"); panel = panel[(panel.HE <= 24) & (panel.FLOWDAY >= W0)]
wide = panel.pivot_table(index=["FLOWDAY", "HE"], columns="NODE", values=["DALMP", "RTLMP"]).astype("float64")
prx_da = C + sum(W[n] * wide[("DALMP", n)] for n in W); prx_rt = C + sum(W[n] * wide[("RTLMP", n)] for n in W)
real = wide.index.get_level_values(0) >= REAL0
da = np.where(real, wide[("DALMP", "RVN_RN")], prx_da); rt = np.where(real, wide[("RTLMP", "RVN_RN")], prx_rt)
P = pd.DataFrame(index=wide.index)
P["da_rvn"] = da; P["rt_rvn"] = rt; P["spread_rvn"] = P.da_rvn - P.rt_rvn
P["src"] = np.where(real, "RVN", "proxy")
for tag, node in [("sys", "HB_BUSAVG"), ("hou", "HB_HOUSTON")]:
    P[f"da_{tag}"] = wide[("DALMP", node)]; P[f"rt_{tag}"] = wide[("RTLMP", node)]; P[f"spread_{tag}"] = P[f"da_{tag}"] - P[f"rt_{tag}"]
P["spread_gks"] = wide[("DALMP", "GKS_BESS_RN")] - wide[("RTLMP", "GKS_BESS_RN")]
P["basis_spread"] = P.spread_rvn - P.spread_hou            # congestion share of the node spread (vs Houston hub)
P["da_basis_sys"] = P.da_rvn - P.da_sys; P["rt_basis_sys"] = P.rt_rvn - P.rt_sys
P = P.dropna(subset=["spread_rvn", "spread_sys", "spread_hou"]).reset_index()
print("price rows", len(P), P.FLOWDAY.min().date(), "->", P.FLOWDAY.max().date(), "| real:", (P.src == "RVN").sum())

# ---- congestion panel -> hourly totals + per-constraint indicators ----
cg = pd.read_parquet(D / "item2_congestion_hourly_panel.parquet", columns=["CONSTRAINTNAME", "MARKET", "hour", "mcc_h", "lam_h", "bind_frac"])
cg = cg[cg.hour >= W0]
# top constraints = union of 3-yr top-10 (item2) + real-window top-12 (item2 overlap table) + next-in-rank names cited
top10 = list(json.loads((D / "item2_congestion_top10_profiles.json").read_text()).keys())
ov = pd.read_csv(D / "item2_congestion_rvn_overlap_top12.csv"); ovc = ov.iloc[:, 0].astype(str).tolist() if "constraint" not in ov.columns else ov.constraint.tolist()
TOP = list(dict.fromkeys(top10 + ovc + ["WESTEX", "35055__A", "ARROZ_EL_CAM1_1", "421__A", "FORTMA_YELWJC1_1"]))
TOP = [c for c in TOP if c in set(cg.CONSTRAINTNAME)]
print("constraints tracked:", len(TOP), TOP)

def hourly_from(cg, shift):
    """shift=+1: panel hour is hour-beginning -> HE = hour+1 ; shift=0: hour is hour-ending -> HE = hour (0 -> 24 of previous flowday)"""
    x = cg.copy()
    he_ts = x.hour + pd.Timedelta(hours=shift)          # period-ending timestamp
    x["FLOWDAY"] = (he_ts - pd.Timedelta(seconds=1)).dt.normalize(); x["HE"] = ((he_ts - pd.Timedelta(seconds=1)).dt.hour + 1)
    tot = x.pivot_table(index=["FLOWDAY", "HE"], columns="MARKET", values="mcc_h", aggfunc="sum").rename(columns={"DA": "mcc_da", "RT": "mcc_rt"})
    return x, tot

best = None
for shift in (1, 0):
    x, tot = hourly_from(cg, shift)
    m = P.merge(tot.reset_index(), on=["FLOWDAY", "HE"], how="left").fillna({"mcc_da": 0.0})
    r = m[m.src == "RVN"][["mcc_da", "da_basis_sys"]].corr().iloc[0, 1]
    print(f"alignment shift={shift}: corr(mcc_da, DA basis vs BUSAVG) on real window = {r:.3f}")
    if best is None or r > best[0]: best = (r, shift, x, tot)
r, shift, x, tot = best; print("chosen shift", shift)
P = P.merge(tot.reset_index(), on=["FLOWDAY", "HE"], how="left").fillna({"mcc_da": 0.0, "mcc_rt": 0.0})
xt = x[x.CONSTRAINTNAME.isin(TOP)]
for mk, pre in (("DA", "mccda_"), ("RT", "mccrt_")):
    piv = xt[xt.MARKET == mk].pivot_table(index=["FLOWDAY", "HE"], columns="CONSTRAINTNAME", values="mcc_h", aggfunc="sum")
    piv.columns = [pre + c for c in piv.columns]
    P = P.merge(piv.reset_index(), on=["FLOWDAY", "HE"], how="left")
lam = xt[xt.MARKET == "DA"].pivot_table(index=["FLOWDAY", "HE"], columns="CONSTRAINTNAME", values="lam_h", aggfunc="sum")
lam.columns = ["lamda_" + c for c in lam.columns]; P = P.merge(lam.reset_index(), on=["FLOWDAY", "HE"], how="left")
fill = {c: 0.0 for c in P.columns if c.startswith(("mccda_", "mccrt_", "lamda_"))}; P = P.fillna(fill)
for c in TOP:
    if f"lamda_{c}" in P: P[f"da_{c}"] = (P[f"lamda_{c}"] > 0).astype("int8")

fp = ROOT / "raw/item6_fundamentals.parquet"
if fp.exists():
    f = pd.read_parquet(fp); f["hour_end"] = pd.to_datetime(f.hour_end)
    f["FLOWDAY"] = (f.hour_end - pd.Timedelta(seconds=1)).dt.normalize(); f["HE"] = (f.hour_end - pd.Timedelta(seconds=1)).dt.hour + 1
    f = f.groupby(["FLOWDAY", "HE"], as_index=False)[["load_mw", "wind_mw", "solar_mw"]].mean()
    P = P.merge(f, on=["FLOWDAY", "HE"], how="left"); P["netload_mw"] = P.load_mw - P.wind_mw - P.solar_mw
    print("fundamentals merged; missing hours:", P.load_mw.isna().sum(), P.wind_mw.isna().sum(), P.solar_mw.isna().sum())
else:
    print("fundamentals file not found - regime features from fundamentals unavailable")

P.attrs["constraints"] = TOP
P.to_parquet(D / "item6_panel.parquet", index=False)
json.dump(dict(constraints=TOP, alignment_shift=int(shift), corr_mcc_da_vs_basis=round(float(r), 3), n_rows=int(len(P)),
               window=[str(P.FLOWDAY.min().date()), str(P.FLOWDAY.max().date())], n_real_hours=int((P.src == "RVN").sum())),
          open(D / "item6_panel_meta.json", "w"), indent=2)
print(P.shape); print(P[P.src == "RVN"][["spread_rvn", "spread_sys", "basis_spread", "mcc_da", "mcc_rt"]].describe().T)
print("var share basis (real):", round(P[P.src == "RVN"].basis_spread.var() / P[P.src == "RVN"].spread_rvn.var(), 4))
print("corr(basis_spread, mcc_da-mcc_rt) real:", round(P[P.src == "RVN"][["basis_spread", "mcc_da"]].assign(d=lambda d: d.mcc_da - P[P.src == "RVN"].mcc_rt)[["basis_spread", "d"]].corr().iloc[0, 1], 3))
