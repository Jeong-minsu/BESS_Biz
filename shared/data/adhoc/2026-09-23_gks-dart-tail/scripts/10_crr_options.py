"""CRR PTP options (DA-settled, payout = sum max(0, DA_sink - DA_source), loss capped at premium) on hub/GKS paths."""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl
BASE = Path(__file__).resolve().parents[1]; DER = BASE / "derived"
NODES = {"GKS": 10017907494, "SOUTH": 10000697079, "NORTH": 10000697078, "WEST": 10000697080, "HOUSTON": 10000697077, "PAN": 10015999590}
ID2 = {v: k for k, v in NODES.items()}
C = ["ISO", "SOURCEID", "SINKID", "PEAKTYPE", "AUCTIONTYPE", "AUCTIONDATE", "CONTRACTSTARTDATE", "MCP", "LOADID", "ROUND", "CONTRACTENDDATE", "AUCTIONID"]
def fetch(mo):
    df = dl.try_read_csv(f"ercot/ftr/auction/{mo.year}_{mo.month:02d}_monthly/optionmcp.csv.gz", header=None)
    if df is None: return None
    df.columns = C[:df.shape[1]]
    df = df[df.SOURCEID.isin(NODES.values()) & df.SINKID.isin(NODES.values())].copy(); df["month"] = str(mo); return df
with ThreadPoolExecutor(12) as ex:
    O = pd.concat([x for x in ex.map(fetch, pd.period_range("2024-08", "2026-09", freq="M")) if x is not None], ignore_index=True)
O["path"] = O.SOURCEID.map(ID2) + "->" + O.SINKID.map(ID2)
print("option paths found:", O.groupby("path").month.nunique().to_dict())
p = pd.read_parquet(DER / "hub_gks_prices.parquet"); p["dt"] = pd.to_datetime(p.DATETIME)
DA = p.pivot_table(index="dt", columns="node", values="DALMP", aggfunc="first").dropna()
he = pd.Series(np.where(DA.index.hour == 0, 24, DA.index.hour), index=DA.index)
fday = pd.Series((DA.index - pd.Timedelta(hours=1)).normalize(), index=DA.index)
hol = set(USFederalHolidayCalendar().holidays("2024-01-01", "2026-12-31").date)
wk = (fday.dt.dayofweek >= 5) | fday.dt.date.isin(hol)
tou = pd.Series(np.where(~he.between(7, 22), "OFFPEAK", np.where(wk, "WEPEAK", "WDPEAK")), index=DA.index)
mon = fday.dt.to_period("M").astype(str)
rows = []
for (pth, mo, t), g in O.groupby(["path", "month", "PEAKTYPE"]):
    s, k = pth.split("->")
    m = (mon == mo) & (tou == t)
    d = (DA.loc[m, k] - DA.loc[m, s])
    if len(d) == 0: continue
    pay = d.clip(lower=0).sum(); cost = g.MCP.iloc[0]
    rows.append(dict(path=pth, month=mo, tou=t, hours=len(d), premium=cost, payout=pay, pnl=pay - cost))
T = pd.DataFrame(rows); T.to_csv(DER / "crr_option_pnl.csv", index=False)
pd.set_option("display.width", 250, "display.float_format", "{:,.1f}".format)
S = T.groupby("path").agg(blocks=("pnl", "size"), months=("month", "nunique"), premium=("premium", "sum"), payout=("payout", "sum"),
                          pnl=("pnl", "sum"), hit=("pnl", lambda x: (x > 0).mean()), worst_block=("pnl", "min"), best_block=("pnl", "max"))
S["payout/premium"] = S.payout / S.premium
S["pnl_ex_best3_blocks"] = [g.pnl.sum() - g.pnl.nlargest(3).sum() for _, g in T.groupby("path")]
S["prem_per_mwh"] = S.premium / T.groupby("path").hours.sum()
print(S.to_string())
