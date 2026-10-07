"""Is 'HE9-16 SHORT' and 'HE17-22 LONG' valid at every ERCOT node? 2024-07-04 .. 2026-09-22, 901 full-coverage nodes.

Per node: EV, win, payoff, robustness (ex best 5 hours), yearly & half-year sign stability,
node-specific excess vs HB_HUBAVG, and persistence of node ranking across periods.
"""
import sys, glob
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl

BASE = Path(__file__).resolve().parents[1]; DER = BASE / "derived"
PANEL = BASE.parent / "2026-09-14_raven-node-analysis" / "raw" / "price_panel"
W = pd.read_parquet(DER / "spread_wide_all_nodes.parquet"); W.columns = W.columns.astype("int64")
meta = dl.read_csv("ercot/metadata/objects/price_node.csv.gz").set_index("OBJECTID")[["OBJECTNAME", "ZONE", "SUBTYPE"]]
cov = W.notna().mean()
W = W.loc[:, cov >= 0.98]
HUBAVG = meta.index[meta.OBJECTNAME == "HB_HUBAVG"][0]; GKS = 10017907494

# DA wide (for DA-capped LONG variant)
fp = DER / "da_wide_all_nodes.parquet"
if not fp.exists():
    parts = [pd.read_parquet(f, columns=["OBJECTID", "DATETIME", "DALMP", "FLOWDAY"]) for f in sorted(glob.glob(str(PANEL / "*.parquet"))) if Path(f).stem >= "202407"]
    parts.append(pd.read_parquet(BASE / "raw" / "panel_20260914_20260922.parquet", columns=["OBJECTID", "DATETIME", "DALMP", "FLOWDAY"]))
    p = pd.concat(parts, ignore_index=True)
    p = p[(p.FLOWDAY >= "2024-07-04") & (p.FLOWDAY <= "2026-09-22")].drop_duplicates(["OBJECTID", "DATETIME"])
    DAw = p.pivot_table(index="DATETIME", columns="OBJECTID", values="DALMP", aggfunc="first")
    DAw.index = pd.to_datetime(DAw.index); DAw.sort_index().to_parquet(fp)
DAw = pd.read_parquet(fp); DAw.columns = DAw.columns.astype("int64"); DAw = DAw.reindex(index=W.index, columns=W.columns)

he = pd.Series(np.where(W.index.hour == 0, 24, W.index.hour), index=W.index)
fday = pd.Series((W.index - pd.Timedelta(hours=1)).normalize(), index=W.index)
year = fday.dt.year
half = fday.dt.year.astype(str) + np.where(fday.dt.month <= 6, "H1", "H2")

def evaluate(P, mask, label):
    """P: pnl matrix (hours x nodes), NaN where no trade."""
    X = P[mask]
    n = X.notna().sum(); tot = X.sum(); ev = tot / n
    win = (X > 0).sum() / n
    avgw = X.where(X > 0).mean(); avgl = -X.where(X < 0).mean()
    top5 = X.apply(lambda c: c.nlargest(5).sum()); bot5 = X.apply(lambda c: c.nsmallest(5).sum())
    Y = X.groupby(year[mask]).mean(); Hh = X.groupby(half[mask]).mean()
    r = pd.DataFrame({"hours": n, "EV": ev, "total": tot, "win": win, "payoff": avgw / avgl,
                      "total_ex_best5": tot - top5, "total_ex_worst5": tot - bot5,
                      "EV_2024": Y.loc[2024], "EV_2025": Y.loc[2025], "EV_2026": Y.loc[2026],
                      "halves_pos_share": (Hh > 0).mean(), "n_halves": Hh.notna().sum()})
    r["all_years_pos"] = (r[["EV_2024", "EV_2025", "EV_2026"]] > 0).all(axis=1)
    r["excess_vs_hubavg"] = r.EV - r.EV.loc[HUBAVG]
    r["label"] = label
    return r.join(meta)

SHORT = W.astype("float64")          # DA - RT
LONG = -SHORT
LONGcap = LONG.where(DAw <= 40)      # only clears if DA <= $40
res = {"HE9-16 SHORT": evaluate(SHORT, he.between(9, 16).values, "HE9-16 SHORT"),
       "HE17-22 LONG": evaluate(LONG, he.between(17, 22).values, "HE17-22 LONG"),
       "HE17-22 LONG DA<=40": evaluate(LONGcap, he.between(17, 22).values, "HE17-22 LONG DA<=40"),
       "HE17-22 SHORT": evaluate(SHORT, he.between(17, 22).values, "HE17-22 SHORT")}
pd.concat(res.values()).to_csv(DER / "rule_all_nodes.csv")

pd.set_option("display.width", 250, "display.max_columns", 40, "display.float_format", "{:,.2f}".format)
summ = {}
for k, r in res.items():
    rn = r[r.SUBTYPE == "GENERATOR"]
    summ[k] = {"nodes": len(rn), "EV>0 %": (rn.EV > 0).mean() * 100, "EV median": rn.EV.median(),
               "EV p10": rn.EV.quantile(.1), "EV p90": rn.EV.quantile(.9),
               "ex-best5 >0 %": (rn.total_ex_best5 > 0).mean() * 100, "all 3 yrs >0 %": rn.all_years_pos.mean() * 100,
               "2024>0 %": (rn.EV_2024 > 0).mean() * 100, "2025>0 %": (rn.EV_2025 > 0).mean() * 100, "2026>0 %": (rn.EV_2026 > 0).mean() * 100,
               ">=4 of 5 halves >0 %": (rn.halves_pos_share >= 0.8).mean() * 100,
               "payoff median": rn.payoff.median(), "win median": rn.win.median(),
               "HUBAVG EV": r.EV.loc[HUBAVG], "GKS EV": r.EV.loc[GKS]}
S = pd.DataFrame(summ); print(S.to_string())
S.to_csv(DER / "rule_all_nodes_summary.csv")

for k in ["HE9-16 SHORT", "HE17-22 LONG", "HE17-22 LONG DA<=40"]:
    rn = res[k][res[k].SUBTYPE == "GENERATOR"]
    print(f"\n--- {k}: by zone ---")
    print(rn.groupby("ZONE").agg(nodes=("EV", "size"), EV_med=("EV", "median"), pos=("EV", lambda s: (s > 0).mean() * 100),
                                 all3=("all_years_pos", lambda s: s.mean() * 100), ex5pos=("total_ex_best5", lambda s: (s > 0).mean() * 100),
                                 excess_sd=("excess_vs_hubavg", "std")).to_string())
    # persistence of node-specific excess: 2025 vs 2026 rank corr, and top/bottom quintile stay
    ex = rn[["EV_2024", "EV_2025", "EV_2026"]].sub(res[k].loc[HUBAVG, ["EV_2024", "EV_2025", "EV_2026"]])
    print("rank corr of node excess vs HUBAVG: 24-25 %.2f  25-26 %.2f  24-26 %.2f" % (
        ex.EV_2024.corr(ex.EV_2025, method="spearman"), ex.EV_2025.corr(ex.EV_2026, method="spearman"), ex.EV_2024.corr(ex.EV_2026, method="spearman")))
    q25 = pd.qcut(ex.EV_2025, 5, labels=False); q26 = pd.qcut(ex.EV_2026, 5, labels=False)
    print("top-quintile 2025 still top-quintile 2026: %.0f%%   bottom stays bottom: %.0f%%   top->bottom: %.0f%%" % (
        ((q25 == 4) & (q26 == 4)).sum() / (q25 == 4).sum() * 100, ((q25 == 0) & (q26 == 0)).sum() / (q25 == 0).sum() * 100,
        ((q25 == 4) & (q26 == 0)).sum() / (q25 == 4).sum() * 100))
    # variance decomposition: how much of node EV dispersion is system (hubavg) vs local, hourly
    print("worst 5 nodes:\n", rn.nsmallest(5, "EV")[["OBJECTNAME", "ZONE", "EV", "total", "EV_2024", "EV_2025", "EV_2026"]].to_string())
    print("best 5 nodes:\n", rn.nlargest(5, "EV")[["OBJECTNAME", "ZONE", "EV", "total", "total_ex_best5", "EV_2024", "EV_2025", "EV_2026"]].to_string())

# hourly: share of node-hour pnl variance explained by HUBAVG (system) per node, for each window
for k, m in [("HE9-16", he.between(9, 16).values), ("HE17-22", he.between(17, 22).values)]:
    X = SHORT[m]; h = X[HUBAVG]
    r2 = X.corrwith(h) ** 2
    print(f"\n{k}: R2 node spread ~ HUBAVG spread: median {r2.median():.2f}, p10 {r2.quantile(.1):.2f}, p90 {r2.quantile(.9):.2f}, GKS {r2.loc[GKS]:.2f}")
