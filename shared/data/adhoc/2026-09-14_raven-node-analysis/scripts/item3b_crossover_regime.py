"""item3b: Raven energy-arbitrage vs AS-parking crossover (hour by hour) + regime conditioning
(system tightness x Raven congestion sign). Real data only:
  - derived/item3b_hourly_prices_2026.parquet  (Yes Energy datalake nodal DA/RT LMP)
  - derived/item3b_rt_as_mcpc_hourly_2026.parquet (datalake rtc_mcpc_*, system-wide)
  - derived/item3b_da_as_mcpc_hourly_2026.parquet (ERCOT DAM-ESR disclosure, system-wide)
  - shared/data/pnl/all_bess/energy_as/chunks/revenue_hourly_* (fleet actual mix, if present for window)
AS MCPC has NO nodal component -> never scaled. Round-trip efficiency ETA stated explicitly.
Usage: python item3b_crossover_regime.py --start 2026-06-04 --end 2026-08-31 --tag summer
"""
import argparse, numpy as np, pandas as pd
from pathlib import Path
A = Path(__file__).resolve().parents[1]; CH = A.parents[3]/"shared/data/pnl/all_bess/energy_as/chunks"
ap = argparse.ArgumentParser(); ap.add_argument("--start", required=True); ap.add_argument("--end", required=True); ap.add_argument("--tag", required=True)
ap.add_argument("--node", default="RVN_RN"); ap.add_argument("--eta", type=float, default=0.85)
a = ap.parse_args(); S, E, ETA = pd.Timestamp(a.start), pd.Timestamp(a.end), a.eta
PRODS = ["regup","regdn","rrs","ecrs","nspin"]; UP = ["regup","rrs","ecrs","nspin"]   # products a discharging/idle ESR can stack
pd.set_option("display.width", 320); pd.set_option("display.max_columns", 40)

px = pd.read_parquet(A/"derived/item3b_hourly_prices_2026.parquet"); px = px[(px.FLOWDAY>=S)&(px.FLOWDAY<=E)]
px["flowday"] = px.FLOWDAY.dt.strftime("%Y-%m-%d")
rt = pd.read_parquet(A/"derived/item3b_rt_as_mcpc_hourly_2026.parquet"); rt["he"] = pd.to_datetime(rt.he_ts).dt.hour.replace(0,24)
rt = rt[(rt.flowday>=a.start)&(rt.flowday<=a.end)].drop(columns="he_ts")
da = pd.read_parquet(A/"derived/item3b_da_as_mcpc_hourly_2026.parquet"); da = da[(da.flowday>=a.start)&(da.flowday<=a.end)]
print(f"window {a.start}..{a.end}: price days={px.flowday.nunique()}  RT-MCPC days={rt.flowday.nunique()}  DA-MCPC days={da.flowday.nunique()}")
rt["best_up_rt"] = rt[UP].max(axis=1); rt["best_prod_rt"] = rt[UP].idxmax(axis=1)
da["best_up_da"] = da[UP].max(axis=1); da["best_prod_da"] = da[UP].idxmax(axis=1)

node = px[px.node==a.node][["flowday","he","DALMP","RTLMP"]].rename(columns={"DALMP":"da","RTLMP":"rt"})
hub = px[px.node=="HB_HOUSTON"][["flowday","he","DALMP","RTLMP"]].rename(columns={"DALMP":"hub_da","RTLMP":"hub_rt"})
sysm = px[px.node=="HB_BUSAVG"][["flowday","he","RTLMP","DALMP"]].rename(columns={"RTLMP":"sys_rt","DALMP":"sys_da"})
h = node.merge(hub, on=["flowday","he"]).merge(sysm, on=["flowday","he"]).merge(rt, on=["flowday","he"], how="left").merge(da, on=["flowday","he"], how="left", suffixes=("_rt","_da"))

# ── daily features ──
def daily(g):
    r = {}
    for c in ("da","rt"):
        s = g[c].dropna().sort_values()
        if len(s) < 20: r[f"tb2_{c}"] = np.nan; continue
        r[f"tb2_{c}"] = s.tail(2).mean()-s.head(2).mean(); r[f"top2_{c}"] = s.tail(2).mean(); r[f"bot2_{c}"] = s.head(2).mean()
        r[f"top2_he_{c}"] = tuple(sorted(g.loc[s.tail(2).index,"he"])); r[f"bot2_he_{c}"] = tuple(sorted(g.loc[s.head(2).index,"he"]))
    s = g.hub_rt.sort_values(); r["hub_tb2_rt"] = s.tail(2).mean()-s.head(2).mean()
    s = g.sys_rt.sort_values(); r["sys_top2_rt"] = s.tail(2).mean(); r["sys_mean_rt"] = g.sys_rt.mean()
    r["basis_rt"] = (g.rt-g.hub_rt).mean(); r["basis_da"] = (g.da-g.hub_da).mean()
    r["basis_sys_rt"] = (g.rt-g.sys_rt).mean()
    if "top2_he_rt" in r:
        r["basis_rt_dis"] = (g.rt-g.hub_rt)[g.he.isin(r["top2_he_rt"])].mean(); r["basis_rt_chg"] = (g.rt-g.hub_rt)[g.he.isin(r["bot2_he_rt"])].mean()
    # AS parking value ($/MW-day): best up-product over the 4 cycling hours vs all 24h
    cyc = list(r.get("top2_he_rt",()))+list(r.get("bot2_he_rt",()))
    r["as4_rt"] = g.loc[g.he.isin(cyc),"best_up_rt"].sum(); r["as24_rt"] = g.best_up_rt.sum(); r["as20_rt"] = r["as24_rt"]-r["as4_rt"]
    r["as4_da"] = g.loc[g.he.isin(cyc),"best_up_da"].sum(); r["as24_da"] = g.best_up_da.sum()
    r["nspin24_rt"] = g.nspin_rt.sum(); r["rrs24_rt"] = g.rrs_rt.sum(); r["ecrs24_rt"] = g.ecrs_rt.sum()
    return pd.Series(r)
D = h.groupby("flowday").apply(daily).reset_index()
# energy value per MW-day of one 2h cycle at the node, with efficiency: discharge top2 - charge bot2/ETA
D["energy2h_rt"] = 2*(D.top2_rt - D.bot2_rt/ETA); D["energy2h_da"] = 2*(D.top2_da - D.bot2_da/ETA)
D["crossover_tb2_rt"] = D.as4_rt/2       # TB2 at which 2h arbitrage == parking the same MW in best AS for those 4h
D["ratio_e_as4_rt"] = D.energy2h_rt/D.as4_rt.replace(0,np.nan)
D.to_csv(A/f"derived/item3b_daily_regime_features_{a.tag}.csv", index=False)

print("\n== Daily means ==")
print(D[["tb2_da","tb2_rt","top2_rt","bot2_rt","hub_tb2_rt","basis_rt","basis_rt_dis","basis_rt_chg","energy2h_rt","as4_rt","as24_rt","as4_da","as24_da","crossover_tb2_rt"]].mean().round(2).to_string())
print("share of days energy2h_rt > as4_rt:", (D.energy2h_rt>D.as4_rt).mean().round(3), "| > as24_rt:", (D.energy2h_rt>D.as24_rt).mean().round(3))
print("crossover TB2 (as4/2) percentiles $/MWh:", D.crossover_tb2_rt.quantile([.5,.75,.9,.95,.99]).round(2).to_dict())

# ── hour by hour ──
Dm = D.set_index("flowday")
h = h.join(Dm[["bot2_rt","top2_rt","bot2_da","top2_da"]], on="flowday")
h["dis_margin_rt"] = h.rt - h.bot2_rt/ETA          # $/MWh if this hour is used to discharge energy bought at the day's bottom-2
h["chg_margin_rt"] = h.top2_rt*ETA - h.rt          # $/MWh if this hour is used to charge for the day's top-2
h["dis_margin_da"] = h.da - h.bot2_da/ETA; h["chg_margin_da"] = h.top2_da*ETA - h.da
H = h.groupby("he").agg(rt=("rt","mean"), da=("da","mean"), hub_rt=("hub_rt","mean"), basis_rt=("basis_rt","mean") if "basis_rt" in h else ("rt","mean"),
    dis_margin_rt=("dis_margin_rt","mean"), chg_margin_rt=("chg_margin_rt","mean"), dis_margin_da=("dis_margin_da","mean"),
    best_up_rt=("best_up_rt","mean"), best_up_da=("best_up_da","mean"), nspin_rt=("nspin_rt","mean"), rrs_rt=("rrs_rt","mean"), ecrs_rt=("ecrs_rt","mean"), regup_rt=("regup_rt","mean"),
    nspin_da=("nspin_da","mean"), rrs_da=("rrs_da","mean"), ecrs_da=("ecrs_da","mean"), regup_da=("regup_da","mean"),
    p_dis_beats_as_rt=("dis_margin_rt", lambda s: np.nan), p_top2=("he", lambda s: np.nan))
H["basis_rt"] = h.assign(b=h.rt-h.hub_rt).groupby("he").b.mean()
H["p_dis_beats_as_rt"] = h.assign(x=h.dis_margin_rt>h.best_up_rt).groupby("he").x.mean()
H["p_dis_beats_as_da"] = h.assign(x=h.dis_margin_da>h.best_up_da).groupby("he").x.mean()
top2 = pd.Series([x for t in D.top2_he_rt.dropna() for x in t]).value_counts(normalize=True); bot2 = pd.Series([x for t in D.bot2_he_rt.dropna() for x in t]).value_counts(normalize=True)
H["p_top2"] = top2.reindex(H.index).fillna(0); H["p_bot2"] = bot2.reindex(H.index).fillna(0)
H["best_prod_rt"] = h.groupby("he").best_prod_rt.agg(lambda s: s.value_counts().index[0])
H.round(2).to_csv(A/f"derived/item3b_hourly_crossover_{a.tag}.csv")
print("\n== Hour-by-hour (means, $/MWh; margins net of ETA) =="); print(H.round(2).to_string())

# ── regime 2x2: tightness (system top-2 RT price, median split) x Raven congestion sign (daily RT basis vs HB_HOUSTON) ──
D["tight"] = np.where(D.sys_top2_rt >= D.sys_top2_rt.median(), "TIGHT", "LOOSE")
D["cong"] = np.where(D.basis_rt >= 0, "POS(node>hub)", "NEG(node<hub)")
D["tight_q"] = pd.qcut(D.sys_top2_rt, 3, labels=["loose","mid","tight"])
cell = D.groupby(["tight","cong"]).agg(days=("flowday","count"), sys_top2_rt=("sys_top2_rt","mean"), tb2_rt=("tb2_rt","mean"), tb2_da=("tb2_da","mean"), top2_rt=("top2_rt","mean"), bot2_rt=("bot2_rt","mean"),
    hub_tb2_rt=("hub_tb2_rt","mean"), basis_rt=("basis_rt","mean"), basis_dis=("basis_rt_dis","mean"), basis_chg=("basis_rt_chg","mean"),
    energy2h_rt=("energy2h_rt","mean"), as4_rt=("as4_rt","mean"), as24_rt=("as24_rt","mean"), as4_da=("as4_da","mean"), as24_da=("as24_da","mean"),
    nspin24_rt=("nspin24_rt","mean"), ecrs24_rt=("ecrs24_rt","mean"), rrs24_rt=("rrs24_rt","mean"), xover=("crossover_tb2_rt","mean"), ratio=("ratio_e_as4_rt","median"))
print("\n== Regime 2x2 (means; $/MW-day for energy2h/as*) =="); print(cell.round(2).to_string())
cell.round(3).to_csv(A/f"derived/item3b_regime_2x2_{a.tag}.csv")
ter = D.groupby("tight_q", observed=True).agg(days=("flowday","count"), sys_top2_rt=("sys_top2_rt","mean"), tb2_rt=("tb2_rt","mean"), energy2h_rt=("energy2h_rt","mean"), as4_rt=("as4_rt","mean"), as24_rt=("as24_rt","mean"), as24_da=("as24_da","mean"))
print("\n== Tightness terciles =="); print(ter.round(2).to_string())

# ── fleet actual mix under the same regimes (if chunk revenue exists in window) ──
def win(p):
    s, e = p.stem.split("_")[-2:]; return pd.Timestamp(s), pd.Timestamp(e)
chunks = [p for p in CH.glob("revenue_hourly_*.parquet") if not (win(p)[1] < S or win(p)[0] > E)]
if chunks:
    rev = pd.concat([pd.read_parquet(p) for p in chunks]); rev["flowday"] = pd.to_datetime(rev._operating_date).dt.strftime("%Y-%m-%d")
    rev = rev[(rev.flowday>=a.start)&(rev.flowday<=a.end)]
    peers = ["RBN_ESR1","WAL_ESR1","CLO_ESR1","CLO_ESR2","LON_ESR1","JAR_ESR1","JAR_ESR2","PHO_ESR1","PHO_ESR2","HLY_ESR1","HLY_ESR2","GKS_BESS_ESR1","RVN_ESR1"]
    rev = rev[rev.resource_name.isin(peers)]
    rev["energy"] = rev.da_energy_rev+rev.rt_energy_rev; rev["as"] = rev[["regup_rev","regdn_rev","rrs_rev","ecrs_rev","nonspin_rev"]].sum(axis=1)
    dd = rev.groupby(["resource_name","flowday"])[["energy","as","total_rev","rrs_rev","ecrs_rev","nonspin_rev"]].sum().reset_index().merge(D[["flowday","tight","cong","tb2_rt"]], on="flowday")
    grp = dd.groupby(["tight","cong"]).agg(days=("flowday","nunique"), energy=("energy","sum"), as_=("as","sum"), total=("total_rev","sum"), rrs=("rrs_rev","sum"), ecrs=("ecrs_rev","sum"), nspin=("nonspin_rev","sum"))
    grp["energy_share"] = grp.energy/grp.total; grp["as_share"] = grp.as_/grp.total
    print("\n== Houston 2h-class peers + GKS: actual mix by regime (fleet sums) =="); print(grp.round(3).to_string())
    per = dd.groupby(["resource_name","tight","cong"]).agg(energy=("energy","sum"), total=("total_rev","sum")).reset_index(); per["energy_share"] = per.energy/per.total
    piv = per.pivot_table(index="resource_name", columns=["tight","cong"], values="energy_share"); print("\n energy share by resource x regime"); print(piv.round(2).to_string())
    grp.round(3).to_csv(A/f"derived/item3b_regime_fleet_mix_{a.tag}.csv"); piv.round(3).to_csv(A/f"derived/item3b_regime_fleet_mix_by_resource_{a.tag}.csv")
    print("fleet days in window:", rev.flowday.nunique(), rev.flowday.min(), rev.flowday.max())
else:
    print("\n[no chunk revenue in window yet — fleet regime mix skipped]")
