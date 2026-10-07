"""ITEM 1 — Raven (RVN_RN) vs GKS (GKS_BESS_RN) TB2 comparison, summer 2026 (6/1–8/31).

Source: raw/price_panel/{202606,202607,202608}.parquet (real Yes Energy datalake data, no mock).
DATETIME is period-ending CT; HE = hour-ending 1..24 (00:00 -> HE24 of FLOWDAY).
TB2 = mean(top-2 hours) - mean(bottom-2 hours), $/MWh, per flowday, DA and RT separately.
Revenue proxy = TB2 x 200 MWh (100 MW / 2h), before round-trip efficiency (no RTE applied).

Outputs (derived/):
  item1_daily_tb2.csv        per node/day/market TB2 + top/bottom hours & prices
  item1_hourly_prices.csv    hourly DA/RT for the 5 nodes (for dashboard drill-down)
  item1_summary.json         daily series + summary blocks (dashboard-ready)
  item1_tables.md            markdown tables (pasted into item1_FINDINGS.md)
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "raw" / "price_panel"
OUT = ROOT / "derived"

NODES = {
    10019925379: "RVN_RN",
    10017907494: "GKS_BESS_RN",
    10000697077: "HB_HOUSTON",
    10000697079: "HB_SOUTH",
    10000698380: "HB_BUSAVG",
}
HUB_OF = {"RVN_RN": "HB_HOUSTON", "GKS_BESS_RN": "HB_SOUTH"}
START, END = pd.Timestamp("2026-06-01"), pd.Timestamp("2026-08-31")
MWH = 200  # 100 MW x 2 h

# ---------------------------------------------------------------- load (filter early)
parts = []
for ym in ("202606", "202607", "202608"):
    d = pd.read_parquet(PANEL / f"{ym}.parquet", columns=["OBJECTID", "DATETIME", "DALMP", "RTLMP", "FLOWDAY"])
    parts.append(d[d.OBJECTID.isin(NODES)])
px = pd.concat(parts, ignore_index=True)
px["node"] = px.OBJECTID.map(NODES)
px["FLOWDAY"] = pd.to_datetime(px.FLOWDAY)
px = px[(px.FLOWDAY >= START) & (px.FLOWDAY <= END)].copy()
ts = pd.to_datetime(px.DATETIME, format="%m/%d/%Y %H:%M:%S")
px["HE"] = ts.dt.hour.replace(0, 24)
px = px.drop(columns=["OBJECTID", "DATETIME"]).sort_values(["node", "FLOWDAY", "HE"]).reset_index(drop=True)
assert not px.duplicated(["node", "FLOWDAY", "HE"]).any()
px.rename(columns={"FLOWDAY": "flowday", "DALMP": "DA", "RTLMP": "RT"}).to_csv(OUT / "item1_hourly_prices.csv", index=False)

# coverage: which node/day/market has a full 24h of non-null prices
cov = px.groupby(["node", "FLOWDAY"]).agg(DA=("DALMP", "count"), RT=("RTLMP", "count")).reset_index()
all_days = pd.date_range(START, END, freq="D")
missing = {}
for n in ("RVN_RN", "GKS_BESS_RN"):
    for m in ("DA", "RT"):
        ok = set(cov[(cov.node == n) & (cov[m] == 24)].FLOWDAY)
        missing[f"{n}_{m}"] = [d.strftime("%Y-%m-%d") for d in all_days if d not in ok]
print("missing full-24h days:", {k: v for k, v in missing.items()})

# ---------------------------------------------------------------- TB2 per node/day/market
def tb2_rows(g: pd.DataFrame, col: str) -> dict | None:
    g = g.dropna(subset=[col])
    if len(g) < 24:
        return None
    s = g.sort_values(col)
    bot, top = s.iloc[:2], s.iloc[-2:]
    return dict(
        top_mean=float(top[col].mean()), bot_mean=float(bot[col].mean()),
        tb2=float(top[col].mean() - bot[col].mean()),
        top_he=[int(x) for x in top.HE], top_px=[round(float(x), 2) for x in top[col]],
        bot_he=[int(x) for x in bot.HE], bot_px=[round(float(x), 2) for x in bot[col]],
        day_mean=float(g[col].mean()),
    )

rows = []
for (n, d), g in px.groupby(["node", "FLOWDAY"]):
    for m, col in (("DA", "DALMP"), ("RT", "RTLMP")):
        r = tb2_rows(g, col)
        if r:
            rows.append(dict(node=n, flowday=d, market=m, **r))
tb = pd.DataFrame(rows)
tb["month"] = tb.flowday.dt.strftime("%Y-%m")
tb.assign(flowday=tb.flowday.dt.strftime("%Y-%m-%d")).to_csv(OUT / "item1_daily_tb2.csv", index=False)

# wide: one row per (flowday, market) with all nodes
W = {}
for m in ("DA", "RT"):
    t = tb[tb.market == m]
    w = t.pivot(index="flowday", columns="node", values=["tb2", "top_mean", "bot_mean", "day_mean"])
    w.columns = [f"{a}__{b}" for a, b in w.columns]
    # common window = days where BOTH RVN and GKS have full 24h
    w = w.dropna(subset=["tb2__RVN_RN", "tb2__GKS_BESS_RN"])
    w["month"] = w.index.strftime("%Y-%m")
    W[m] = w
    print(f"{m}: common days {len(w)}  {w.index.min().date()} .. {w.index.max().date()}")

# ---------------------------------------------------------------- stats helpers
def stats(s: pd.Series) -> dict:
    s = s.dropna()
    return dict(n=int(len(s)), mean=round(s.mean(), 2), median=round(s.median(), 2),
                p10=round(s.quantile(.10), 2), p90=round(s.quantile(.90), 2),
                min=round(s.min(), 2), max=round(s.max(), 2), sum=round(s.sum(), 2))

summary = {"meta": dict(
    window_requested="2026-06-01..2026-08-31",
    effective_window={m: f"{W[m].index.min().date()}..{W[m].index.max().date()} ({len(W[m])} common days)" for m in W},
    missing_full_days=missing,
    tb2_def="mean(top-2 hourly LMP) - mean(bottom-2 hourly LMP) per flowday; hourly period-ending CT (HE1..HE24)",
    revenue_proxy="TB2 x 200 MWh (100MW/2h), before round-trip efficiency; no RTE applied",
    hubs_used={"RVN_RN": "HB_HOUSTON (10000697077)", "GKS_BESS_RN": "HB_SOUTH (10000697079)", "system": "HB_BUSAVG (10000698380)"},
    source="raw/price_panel/2026{06,07,08}.parquet (Yes Energy datalake, real data)",
)}

# 1) TB2 stats + monthly + cumulative
summary["tb2_stats"] = {}
summary["tb2_monthly_mean"] = {}
summary["cumulative_usd_per_100MW"] = {}
for m in ("DA", "RT"):
    w = W[m]
    summary["tb2_stats"][m] = {n: stats(w[f"tb2__{n}"]) for n in NODES.values()}
    summary["tb2_stats"][m]["RVN_minus_GKS"] = stats(w["tb2__RVN_RN"] - w["tb2__GKS_BESS_RN"])
    summary["tb2_monthly_mean"][m] = {
        n: {k: round(v, 2) for k, v in w.groupby("month")[f"tb2__{n}"].mean().items()} for n in NODES.values()}
    summary["cumulative_usd_per_100MW"][m] = {
        n: round(float(w[f"tb2__{n}"].sum() * MWH)) for n in ("RVN_RN", "GKS_BESS_RN")}
    summary["cumulative_usd_per_100MW"][m]["RVN_minus_GKS"] = (
        summary["cumulative_usd_per_100MW"][m]["RVN_RN"] - summary["cumulative_usd_per_100MW"][m]["GKS_BESS_RN"])
    summary["cumulative_usd_per_100MW"][m]["win_rate_RVN_gt_GKS"] = round(float((w["tb2__RVN_RN"] > w["tb2__GKS_BESS_RN"]).mean()), 3)

# 2) Decomposition of daily delta: dTB2 = d(top_mean) - d(bot_mean)
summary["delta_decomposition"] = {}
for m in ("DA", "RT"):
    w = W[m]
    d_top = w["top_mean__RVN_RN"] - w["top_mean__GKS_BESS_RN"]        # discharge-side contribution
    d_bot = -(w["bot_mean__RVN_RN"] - w["bot_mean__GKS_BESS_RN"])     # charge-side contribution (cheaper charge => +)
    d_tb2 = w["tb2__RVN_RN"] - w["tb2__GKS_BESS_RN"]
    assert np.allclose(d_top + d_bot, d_tb2)
    W[m]["d_tb2"], W[m]["d_top"], W[m]["d_bot"] = d_tb2, d_top, d_bot
    blk = {"overall": dict(delta_tb2=round(d_tb2.mean(), 2), discharge_contrib=round(d_top.mean(), 2),
                           charge_contrib=round(d_bot.mean(), 2),
                           discharge_share=round(float(d_top.mean() / d_tb2.mean()), 3) if d_tb2.mean() else None,
                           dominant="discharge" if abs(d_top.mean()) > abs(d_bot.mean()) else "charge")}
    for mo, g in W[m].groupby("month"):
        blk[mo] = dict(delta_tb2=round(g.d_tb2.mean(), 2), discharge_contrib=round(g.d_top.mean(), 2),
                       charge_contrib=round(g.d_bot.mean(), 2),
                       dominant="discharge" if abs(g.d_top.mean()) > abs(g.d_bot.mean()) else "charge")
    summary["delta_decomposition"][m] = blk

# 3) Hub / basis decomposition of TB2 gap
#    dTB2_nodal = [TB2(HB_HOUSTON) - TB2(HB_SOUTH)]  (zonal hub component)
#               + [TB2(RVN) - TB2(HB_HOUSTON)]        (Raven local basis)
#               - [TB2(GKS) - TB2(HB_SOUTH)]          (GKS local basis)
#    and vs system: TB2(node) - TB2(HB_BUSAVG) = zone + node local component
summary["hub_decomposition"] = {}
for m in ("DA", "RT"):
    w = W[m]
    hub_gap = w["tb2__HB_HOUSTON"] - w["tb2__HB_SOUTH"]
    rvn_loc = w["tb2__RVN_RN"] - w["tb2__HB_HOUSTON"]
    gks_loc = w["tb2__GKS_BESS_RN"] - w["tb2__HB_SOUTH"]
    assert np.allclose(hub_gap + rvn_loc - gks_loc, w["d_tb2"])
    blk = {}
    for label, g, hg, rl, gl in [("overall", w, hub_gap, rvn_loc, gks_loc)] + [
            (mo, g, hub_gap[g.index], rvn_loc[g.index], gks_loc[g.index]) for mo, g in w.groupby("month")]:
        blk[label] = dict(
            delta_tb2=round(g.d_tb2.mean(), 2),
            hub_houston_minus_south=round(hg.mean(), 2),
            rvn_local_basis_contrib=round(rl.mean(), 2),
            gks_local_basis_contrib=round(gl.mean(), 2),
            net_local=round((rl - gl).mean(), 2),
            tb2_busavg=round(g["tb2__HB_BUSAVG"].mean(), 2),
            tb2_hb_houston=round(g["tb2__HB_HOUSTON"].mean(), 2),
            tb2_hb_south=round(g["tb2__HB_SOUTH"].mean(), 2),
            rvn_vs_busavg=round((g["tb2__RVN_RN"] - g["tb2__HB_BUSAVG"]).mean(), 2),
            gks_vs_busavg=round((g["tb2__GKS_BESS_RN"] - g["tb2__HB_BUSAVG"]).mean(), 2),
        )
    summary["hub_decomposition"][m] = blk

# 3b) hour-of-day basis profile (node - own hub) and RVN - GKS, mean over common days
hp = px.pivot_table(index=["FLOWDAY", "HE"], columns="node", values=["DALMP", "RTLMP"])
hp.columns = [f"{'DA' if a == 'DALMP' else 'RT'}__{b}" for a, b in hp.columns]
summary["hourly_profile"] = {}
summary["basis_in_dispatch_hours"] = {}
for m in ("DA", "RT"):
    h = hp.loc[hp.index.get_level_values(0).isin(W[m].index)].copy()
    h["basis_RVN"] = h[f"{m}__RVN_RN"] - h[f"{m}__HB_HOUSTON"]
    h["basis_GKS"] = h[f"{m}__GKS_BESS_RN"] - h[f"{m}__HB_SOUTH"]
    h["hub_diff"] = h[f"{m}__HB_HOUSTON"] - h[f"{m}__HB_SOUTH"]
    h["rvn_minus_gks"] = h[f"{m}__RVN_RN"] - h[f"{m}__GKS_BESS_RN"]
    prof = h.groupby(level="HE")[[f"{m}__RVN_RN", f"{m}__GKS_BESS_RN", f"{m}__HB_HOUSTON", f"{m}__HB_SOUTH", f"{m}__HB_BUSAVG",
                                  "basis_RVN", "basis_GKS", "hub_diff", "rvn_minus_gks"]].mean().round(2)
    prof.columns = [c.replace(f"{m}__", "") for c in prof.columns]
    summary["hourly_profile"][m] = {"HE": prof.index.tolist(), **{c: prof[c].tolist() for c in prof.columns}}
    # basis of each node in ITS OWN top-2 (discharge) and bottom-2 (charge) hours
    blk = {}
    for n, bcol in (("RVN_RN", "basis_RVN"), ("GKS_BESS_RN", "basis_GKS")):
        t = tb[(tb.market == m) & (tb.node == n) & tb.flowday.isin(W[m].index)]
        dis = [(d, he) for d, hes in zip(t.flowday, t.top_he) for he in hes]
        chg = [(d, he) for d, hes in zip(t.flowday, t.bot_he) for he in hes]
        bd, bc = h.loc[dis, bcol], h.loc[chg, bcol]
        blk[n] = dict(basis_discharge_hours_mean=round(bd.mean(), 2), basis_discharge_pos_share=round(float((bd > 0).mean()), 3),
                      basis_charge_hours_mean=round(bc.mean(), 2), basis_charge_neg_share=round(float((bc < 0).mean()), 3),
                      basis_all_hours_mean=round(h[bcol].mean(), 2))
    summary["basis_in_dispatch_hours"][m] = blk
    # hour-ending frequency of top-2 / bottom-2 by node
    freq = {}
    for n in ("RVN_RN", "GKS_BESS_RN"):
        t = tb[(tb.market == m) & (tb.node == n) & tb.flowday.isin(W[m].index)]
        freq[n] = dict(top_he=pd.Series([x for l in t.top_he for x in l]).value_counts().sort_index().to_dict(),
                       bot_he=pd.Series([x for l in t.bot_he for x in l]).value_counts().sort_index().to_dict())
    summary.setdefault("dispatch_hour_frequency", {})[m] = freq

# 3c) DA vs RT per node
summary["da_vs_rt"] = {}
for n in ("RVN_RN", "GKS_BESS_RN", "HB_HOUSTON", "HB_SOUTH", "HB_BUSAVG"):
    da = W["DA"][f"tb2__{n}"]; rt = W["RT"][f"tb2__{n}"]
    idx = da.index.intersection(rt.index)
    summary["da_vs_rt"][n] = dict(days=len(idx), da_mean=round(da[idx].mean(), 2), rt_mean=round(rt[idx].mean(), 2),
                                 rt_minus_da_mean=round((rt[idx] - da[idx]).mean(), 2),
                                 rt_over_da_ratio=round(float(rt[idx].mean() / da[idx].mean()), 3),
                                 rt_gt_da_share=round(float((rt[idx] > da[idx]).mean()), 3),
                                 rt_tb2_std=round(rt[idx].std(), 2), da_tb2_std=round(da[idx].std(), 2))

# 4) Tails: LMP < 0 and LMP > 500 (hours), on common-day window per market
summary["tails"] = {}
for m, col in (("DA", "DALMP"), ("RT", "RTLMP")):
    sub = px[px.FLOWDAY.isin(W[m].index)]
    blk = {}
    for n in NODES.values():
        s = sub[sub.node == n][col].dropna()
        neg, spk, spk1k = s[s < 0], s[s > 500], s[s > 1000]
        blk[n] = dict(hours=int(len(s)),
                      neg_hours=int(len(neg)), neg_sum=round(float(neg.sum()), 1), neg_min=round(float(s.min()), 2),
                      spike500_hours=int(len(spk)), spike500_sum=round(float(spk.sum()), 1), spike1000_hours=int(len(spk1k)),
                      max=round(float(s.max()), 2), mean=round(float(s.mean()), 2))
    summary["tails"][m] = blk
    # monthly tail counts for the two nodes
    summary["tails"][f"{m}_monthly"] = {
        n: {mo: dict(neg=int((g[col] < 0).sum()), spike500=int((g[col] > 500).sum()))
            for mo, g in sub[sub.node == n].groupby(sub.FLOWDAY.dt.strftime("%Y-%m"))} for n in ("RVN_RN", "GKS_BESS_RN")}

# daily series (dashboard)
summary["daily"] = {}
for m in ("DA", "RT"):
    w = W[m]
    t = tb[(tb.market == m) & tb.flowday.isin(w.index)]
    hours = {n: t[t.node == n].set_index("flowday") for n in ("RVN_RN", "GKS_BESS_RN")}
    summary["daily"][m] = dict(
        flowday=[d.strftime("%Y-%m-%d") for d in w.index],
        **{f"tb2_{n}": w[f"tb2__{n}"].round(2).tolist() for n in NODES.values()},
        delta_tb2=w.d_tb2.round(2).tolist(), discharge_contrib=w.d_top.round(2).tolist(), charge_contrib=w.d_bot.round(2).tolist(),
        hub_gap=(w["tb2__HB_HOUSTON"] - w["tb2__HB_SOUTH"]).round(2).tolist(),
        rvn_local=(w["tb2__RVN_RN"] - w["tb2__HB_HOUSTON"]).round(2).tolist(),
        gks_local=(w["tb2__GKS_BESS_RN"] - w["tb2__HB_SOUTH"]).round(2).tolist(),
        **{f"{n}_{k}": hours[n].loc[w.index, k].tolist() for n in hours for k in ("top_he", "top_px", "bot_he", "bot_px")},
    )

(OUT / "item1_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")

# ---------------------------------------------------------------- markdown tables
L = []
def table(df: pd.DataFrame, title: str):
    L.append(f"\n**{title}**\n"); L.append(df.to_markdown()); L.append("")

for m in ("DA", "RT"):
    st = pd.DataFrame(summary["tb2_stats"][m]).T
    table(st, f"{m} TB2 daily stats ($/MWh), {summary['meta']['effective_window'][m]}")
    table(pd.DataFrame(summary["tb2_monthly_mean"][m]), f"{m} TB2 monthly mean ($/MWh)")
    table(pd.DataFrame(summary["delta_decomposition"][m]).T, f"{m} RVN−GKS daily TB2 delta decomposition ($/MWh): discharge (top-2) vs charge (bottom-2) contribution")
    table(pd.DataFrame(summary["hub_decomposition"][m]).T, f"{m} hub/basis decomposition of RVN−GKS TB2 gap ($/MWh)")
    table(pd.DataFrame(summary["basis_in_dispatch_hours"][m]).T, f"{m} node−hub basis in each node's own top-2 (discharge) / bottom-2 (charge) hours ($/MWh)")
    hpf = pd.DataFrame(summary["hourly_profile"][m]).set_index("HE")
    table(hpf, f"{m} hour-ending mean price / basis profile ($/MWh, common days)")
    table(pd.DataFrame(summary["tails"][m]).T, f"{m} tail hours (common-day window)")
table(pd.DataFrame(summary["cumulative_usd_per_100MW"]).T, "Cumulative TB2 revenue proxy, $ per 100MW/200MWh, before RTE")
table(pd.DataFrame(summary["da_vs_rt"]).T, "DA vs RT TB2 by node ($/MWh, days with both)")
(OUT / "item1_tables.md").write_text("\n".join(L), encoding="utf-8")
print("wrote", sorted(p.name for p in OUT.glob("item1_*")))
