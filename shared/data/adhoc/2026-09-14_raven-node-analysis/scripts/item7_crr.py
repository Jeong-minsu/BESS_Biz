"""ITEM 7 PART B.3 — CRR (FTR obligation) on South->Houston paths: auction clearing price vs realised DA congestion.
Source: ercot/ftr/auction/{YYYY_MM_monthly}/obligationmcp.csv.gz (headerless; ddl = ercot/ftr/auction/obligationmcp_ddl.json:
ISO, PRICENODEID, PEAKTYPE, AUCTIONTYPE, AUCTIONDATE, CONTRACTSTARTDATE, LMP(= monthly congestion price $/MW for the TOU block),
LOADID, ROUND, CONTRACTENDDATE, AUCTIONID). Path cost = MCP_sink - MCP_source ($/MW-block).
Realised payout (ERCOT CRR obligation settles on DA SPP congestion; ERCOT has no marginal-loss component, so
DA LMP difference = congestion difference) = sum over block hours of (DA_sink - DA_source), from derived/item7_price_panel.parquet.
TOU: WDPEAK = weekday HE7-22, WEPEAK = weekend/NERC-holiday HE7-22, OFFPEAK = HE1-6 & HE23-24 all days.
Monthly auctions 2024-08..2026-09 (GKS priced from 2024-08; RVN_RN priced only from 2026-09). Real data only.
"""
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl

R = Path(__file__).resolve().parents[1]; D = R / "derived"
NODES = {"RVN_RN": 10019925379, "GKS_BESS_RN": 10017907494, "HB_HOUSTON": 10000697077, "HB_SOUTH": 10000697079, "HB_BUSAVG": 10000698380}
COLS = ["ISO", "PRICENODEID", "PEAKTYPE", "AUCTIONTYPE", "AUCTIONDATE", "CONTRACTSTARTDATE", "MCP", "LOADID", "ROUND", "CONTRACTENDDATE", "AUCTIONID"]
MONTHS = pd.period_range("2024-08", "2026-09", freq="M")
PATHS = [("GKS_BESS_RN", "HB_HOUSTON"), ("GKS_BESS_RN", "RVN_RN"), ("HB_SOUTH", "HB_HOUSTON"), ("GKS_BESS_RN", "HB_SOUTH"), ("HB_BUSAVG", "HB_HOUSTON")]


def fetch(m):
    df = dl.try_read_csv(f"ercot/ftr/auction/{m.year}_{m.month:02d}_monthly/obligationmcp.csv.gz", header=None)
    if df is None: return None
    df.columns = COLS[:df.shape[1]]
    df = df[df.PRICENODEID.isin(NODES.values())].copy(); df["month"] = str(m); return df


with ThreadPoolExecutor(12) as ex: parts = [p for p in ex.map(fetch, MONTHS) if p is not None]
A = pd.concat(parts, ignore_index=True)
A["node"] = A.PRICENODEID.map({v: k for k, v in NODES.items()})
MCP = A.pivot_table(index=["month", "PEAKTYPE"], columns="node", values="MCP", aggfunc="first")
MCP.to_csv(D / "item7_crr_mcp_by_node.csv")
print("auction months", A.month.nunique(), "nodes", MCP.columns.tolist())

P = pd.read_parquet(D / "item7_price_panel.parquet")
hol = set(USFederalHolidayCalendar().holidays("2024-01-01", "2026-12-31").date)
fd = pd.to_datetime(P.FLOWDAY)
wkend = (fd.dt.dayofweek >= 5) | fd.dt.date.isin(hol)
peak = P.HE.between(7, 22)
P["tou"] = np.where(~peak, "OFFPEAK", np.where(wkend, "WEPEAK", "WDPEAK"))
P["month"] = fd.dt.to_period("M").astype(str)
DA = {"RVN_RN": P.DA_RVN, "GKS_BESS_RN": P.DA_GKS_BESS_RN, "HB_HOUSTON": P.DA_HB_HOUSTON, "HB_SOUTH": P.DA_HB_SOUTH, "HB_BUSAVG": P.DA_HB_BUSAVG}
rows = []
for src, snk in PATHS:
    diff = (DA[snk] - DA[src]).rename("d")
    real = pd.concat([diff, P[["month", "tou"]]], axis=1).groupby(["month", "tou"]).d.agg(["sum", "count"])
    for (m, tou), r in real.iterrows():
        if (m, tou) not in MCP.index: continue
        mc = MCP.loc[(m, tou)]
        if pd.isna(mc.get(src)) or pd.isna(mc.get(snk)): continue
        cost = float(mc[snk] - mc[src])
        rows.append(dict(path=f"{src}->{snk}", month=m, tou=tou, hours=int(r["count"]), auction_cost=cost, realised=float(r["sum"]),
                         pnl=float(r["sum"]) - cost, realised_per_mwh=float(r["sum"]) / r["count"], cost_per_mwh=cost / r["count"],
                         rvn_src="real" if m >= "2026-06" else "proxy"))
T = pd.DataFrame(rows)
T.to_csv(D / "item7_crr_path_pnl.csv", index=False)
summ = T.groupby(["path", "tou"]).agg(months=("month", "nunique"), cost_total=("auction_cost", "sum"), realised_total=("realised", "sum"),
                                      pnl_total=("pnl", "sum"), hit_rate=("pnl", lambda s: float((s > 0).mean())),
                                      pnl_mean=("pnl", "mean"), pnl_std=("pnl", "std"), pnl_min=("pnl", "min"), pnl_max=("pnl", "max"),
                                      realised_per_mwh=("realised_per_mwh", "mean"), cost_per_mwh=("cost_per_mwh", "mean")).round(1)
summ["pnl_per_mw_per_yr"] = (summ.pnl_total / summ.months * 12).round(0)
summ["sharpe_monthly"] = (summ.pnl_mean / summ.pnl_std * np.sqrt(12)).round(2)
summ.to_csv(D / "item7_crr_summary.csv")
print(summ.to_string())
by_path = T.groupby("path").agg(months=("month", "nunique"), cost=("auction_cost", "sum"), realised=("realised", "sum"), pnl=("pnl", "sum")).round(0)
by_path["pnl_per_mw_yr"] = (by_path.pnl / by_path.months * 12).round(0); print(by_path.to_string())
yr = T.assign(year=T.month.str[:4]).groupby(["path", "year"]).pnl.sum().round(0).unstack(); print(yr.to_string())
print(T[T.path == "GKS_BESS_RN->HB_HOUSTON"].pivot_table(index="month", columns="tou", values="pnl").round(0).to_string())
