"""Alternatives to hourly DART for tail control, 2024-07-04 .. 2026-09-22 (real data).

A) CRR monthly obligations between hubs/GKS: DA-settled basis. P&L = sum_block(DA_sink - DA_source) - auction MCP path cost.
B) Evening (HE17-22) virtual LONG with DA bid cap = call-like payoff (loss bounded by DA price paid).
C) Diversification: equal-weight DART SHORT across hubs + GKS.
D) Aggregation: hourly vs daily vs monthly DART - does the tail wash out?
"""
import sys, glob
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl

BASE = Path(__file__).resolve().parents[1]; DER = BASE / "derived"
PANEL = BASE.parent / "2026-09-14_raven-node-analysis" / "raw" / "price_panel"
NODES = {"GKS": 10017907494, "SOUTH": 10000697079, "NORTH": 10000697078, "WEST": 10000697080,
         "HOUSTON": 10000697077, "PAN": 10015999590}
ID2 = {v: k for k, v in NODES.items()}
pd.set_option("display.width", 250, "display.max_columns", 40, "display.float_format", "{:,.2f}".format)

# ---------- prices (DA, RT) for selected nodes
fp = DER / "hub_gks_prices.parquet"
if not fp.exists():
    parts = [pd.read_parquet(f, columns=["OBJECTID", "DATETIME", "DALMP", "RTLMP", "FLOWDAY"],
                             filters=[("OBJECTID", "in", list(NODES.values()))])
             for f in sorted(glob.glob(str(PANEL / "*.parquet"))) if Path(f).stem >= "202407"]
    parts.append(pd.read_parquet(BASE / "raw" / "panel_20260914_20260922.parquet").query("OBJECTID in @NODES.values()"))
    p = pd.concat(parts, ignore_index=True)
    p = p[(p.FLOWDAY >= "2024-07-04") & (p.FLOWDAY <= "2026-09-22")].drop_duplicates(["OBJECTID", "DATETIME"])
    p["node"] = p.OBJECTID.map(ID2)
    p.to_parquet(fp, index=False)
p = pd.read_parquet(fp)
p["dt"] = pd.to_datetime(p.DATETIME)
DA = p.pivot_table(index="dt", columns="node", values="DALMP", aggfunc="first")
RT = p.pivot_table(index="dt", columns="node", values="RTLMP", aggfunc="first")
ok = DA.notna().all(axis=1) & RT.notna().all(axis=1)
DA, RT = DA[ok], RT[ok]
he = pd.Series(np.where(DA.index.hour == 0, 24, DA.index.hour), index=DA.index)
fday = pd.Series((DA.index - pd.Timedelta(hours=1)).normalize(), index=DA.index)
SP = DA - RT  # SHORT pnl
print("hours", len(DA))

def dstats(x, per=None):
    x = pd.Series(x).dropna(); w, l = x[x > 0], x[x < 0]
    return dict(n=len(x), win=len(w) / len(x), payoff=w.mean() / -l.mean() if len(l) else np.nan, mean=x.mean(), sd=x.std(),
                kurt=x.kurt(), worst=x.min(), best=x.max(), total=x.sum())

# ---------- D) aggregation: DART SHORT per MWh at hourly / daily / monthly horizon (GKS, SOUTH, NORTH)
print("\n=== D) DART SHORT: does aggregation wash out the tail? ($/MWh basis) ===")
rows = {}
for n in ["GKS", "SOUTH", "NORTH", "HOUSTON", "WEST"]:
    h = SP[n]; d = h.groupby(fday).mean(); w = h.groupby(fday.dt.to_period("W")).mean(); m = h.groupby(fday.dt.to_period("M")).mean()
    for lab, x in [("hour", h), ("day", d), ("week", w), ("month", m)]:
        s = dstats(x); rows[(n, lab)] = dict(win=s["win"], mean=s["mean"], sd=s["sd"], kurt=s["kurt"], worst=s["worst"],
                                             worst_over_median_win=-s["worst"] / x[x > 0].median())
D_ = pd.DataFrame(rows).T; print(D_.to_string())

# ---------- C) diversification across locations (daily SHORT 24h, 1MW each, equal weight = 1MW total)
print("\n=== C) Diversification: daily SHORT 24h, $/MW-day ===")
day = SP.groupby(fday).sum()
day["EQW_4HUBS"] = day[["SOUTH", "NORTH", "WEST", "HOUSTON"]].mean(axis=1)
day["EQW_ALL6"] = day[list(NODES)].mean(axis=1)
C = pd.DataFrame({c: dstats(day[c]) for c in ["GKS", "SOUTH", "NORTH", "WEST", "HOUSTON", "EQW_4HUBS", "EQW_ALL6"]}).T
C["worst5_sum"] = [day[c].nsmallest(5).sum() for c in C.index]
print(C.to_string())
w20 = {c: set(day[c].nsmallest(20).index) for c in ["GKS", "SOUTH", "NORTH", "WEST", "HOUSTON"]}
print("worst-20-day overlap with HB_NORTH:", {c: len(w20[c] & w20["NORTH"]) for c in w20})
print("daily corr:\n", day[["GKS", "SOUTH", "NORTH", "WEST", "HOUSTON"]].corr().round(2).to_string())

# ---------- B) evening virtual LONG with DA bid cap (call-like)
print("\n=== B) HE17-22 virtual LONG with DA bid cap (clears only if DA <= cap), $/MWh ===")
ev = he.between(17, 22)
rowsB = []
for n in ["GKS", "SOUTH", "NORTH", "HOUSTON", "WEST"]:
    for cap in [None, 100, 60, 40, 30]:
        m = ev & ((DA[n] <= cap) if cap else True)
        x = (RT[n] - DA[n])[m]
        wins = x[x > 0].sort_values(ascending=False)
        mon = x.groupby(fday[m].dt.to_period("M")).sum()
        rowsB.append(dict(node=n, cap=cap or "none", hours=len(x), win=(x > 0).mean(), EV=x.mean(), total=x.sum(),
                          max_loss_hr=x.min(), premium_paid=-x[x < 0].sum(), payout=wins.sum(),
                          top5_share_of_payout=wins.head(5).sum() / wins.sum(), total_ex_top5=x.sum() - wins.head(5).sum(),
                          losing_months=(mon < 0).mean(), worst_month=mon.min()))
B = pd.DataFrame(rowsB); print(B.to_string(index=False))

# ---------- A) CRR monthly obligations (DA basis, auction cost)
print("\n=== A) CRR obligations: monthly TOU-block P&L, 1MW ===")
COLS = ["ISO", "PRICENODEID", "PEAKTYPE", "AUCTIONTYPE", "AUCTIONDATE", "CONTRACTSTARTDATE", "MCP", "LOADID", "ROUND", "CONTRACTENDDATE", "AUCTIONID"]
MONTHS = pd.period_range("2024-08", "2026-09", freq="M")
def fetch(mo):
    df = dl.try_read_csv(f"ercot/ftr/auction/{mo.year}_{mo.month:02d}_monthly/obligationmcp.csv.gz", header=None)
    if df is None: return None
    df.columns = COLS[:df.shape[1]]
    df = df[df.PRICENODEID.isin(NODES.values())].copy(); df["month"] = str(mo); return df
with ThreadPoolExecutor(12) as ex: A = pd.concat([x for x in ex.map(fetch, MONTHS) if x is not None], ignore_index=True)
A["node"] = A.PRICENODEID.map(ID2)
MCP = A.pivot_table(index=["month", "PEAKTYPE"], columns="node", values="MCP", aggfunc="first")
hol = set(USFederalHolidayCalendar().holidays("2024-01-01", "2026-12-31").date)
wk = (fday.dt.dayofweek >= 5) | fday.dt.date.isin(hol)
tou = pd.Series(np.where(~he.between(7, 22), "OFFPEAK", np.where(wk, "WEPEAK", "WDPEAK")), index=DA.index)
mon = fday.dt.to_period("M").astype(str)
PATHS = [("WEST", "NORTH"), ("SOUTH", "NORTH"), ("NORTH", "HOUSTON"), ("SOUTH", "HOUSTON"), ("WEST", "HOUSTON"),
         ("PAN", "NORTH"), ("GKS", "SOUTH"), ("GKS", "HOUSTON"), ("GKS", "NORTH")]
rowsA = []
for src, snk in PATHS:
    diff = DA[snk] - DA[src]
    rt_diff = RT[snk] - RT[src]
    g = pd.DataFrame({"d": diff, "r": rt_diff, "m": mon, "t": tou}).groupby(["m", "t"]).agg(real=("d", "sum"), rtreal=("r", "sum"), h=("d", "size"))
    for (mo, t), r in g.iterrows():
        if (mo, t) not in MCP.index: continue
        mc = MCP.loc[(mo, t)]
        if pd.isna(mc.get(src)) or pd.isna(mc.get(snk)): continue
        cost = float(mc[snk] - mc[src])
        rowsA.append(dict(path=f"{src}->{snk}", month=mo, tou=t, hours=int(r.h), cost=cost, realised=r.real,
                          pnl=r.real - cost, pnl_mwh=(r.real - cost) / r.h, ptp_rt_pnl_mwh=(r.rtreal - r.real) / r.h))
TA = pd.DataFrame(rowsA); TA.to_csv(DER / "crr_path_pnl.csv", index=False)
# long (sink-source) and short (reverse) are symmetric in pnl sign; report the direction with positive total as "best side"
agg = []
for pth, g in TA.groupby("path"):
    for side, sgn in [("buy", 1), ("sell", -1)]:
        x = sgn * g.pnl; xm = sgn * g.pnl_mwh
        agg.append(dict(path=pth, side=side, blocks=len(g), hit=(x > 0).mean(), total=x.sum(), per_mw_yr=x.sum() / g.month.nunique() * 12,
                        mean_mwh=xm.mean(), sd_mwh=xm.std(), worst_block=x.min(), worst_block_mwh=xm.min(),
                        worst_month_all_tou=(sgn * g.groupby("month").pnl.sum()).min()))
AG = pd.DataFrame(agg); print(AG.sort_values(["path", "side"]).to_string(index=False))
# hourly basis distribution (DA vs RT) vs DART
print("\n=== hourly distribution: DA basis vs RT basis vs DART ($/MWh) ===")
H = {}
for src, snk in PATHS[:7]:
    H[f"DA basis {src}->{snk}"] = dstats(DA[snk] - DA[src]); H[f"RT basis {src}->{snk}"] = dstats(RT[snk] - RT[src])
for n in ["GKS", "SOUTH", "NORTH"]:
    H[f"DART {n}"] = dstats(SP[n])
HH = pd.DataFrame(H).T[["mean", "sd", "kurt", "worst", "best"]]; print(HH.to_string())
# monthly-block comparison per MWh: CRR vs DART same TOU
print("\n=== per-MWh monthly-block risk: CRR vs DART SHORT (same months/blocks) ===")
dart_blk = pd.DataFrame({n: SP[n] for n in ["GKS", "SOUTH", "NORTH"]}).assign(m=mon, t=tou).groupby(["m", "t"]).mean()
cmp = {f"DART SHORT {n}": dict(sd_mwh=dart_blk[n].std(), worst_mwh=dart_blk[n].min(), mean_mwh=dart_blk[n].mean(), hit=(dart_blk[n] > 0).mean()) for n in dart_blk}
for pth, g in TA.groupby("path"):
    cmp[f"CRR {pth}"] = dict(sd_mwh=g.pnl_mwh.std(), worst_mwh=min(g.pnl_mwh.min(), (-g.pnl_mwh).min()), mean_mwh=g.pnl_mwh.mean(), hit=(g.pnl > 0).mean())
print(pd.DataFrame(cmp).T.to_string())
with pd.ExcelWriter(DER / "alternatives.xlsx") as xw:
    D_.to_excel(xw, sheet_name="D_aggregation"); C.to_excel(xw, sheet_name="C_diversification")
    B.to_excel(xw, sheet_name="B_evening_long_cap", index=False); AG.to_excel(xw, sheet_name="A_crr_paths", index=False)
    HH.to_excel(xw, sheet_name="A_hourly_basis_vs_dart"); pd.DataFrame(cmp).T.to_excel(xw, sheet_name="A_block_risk")
