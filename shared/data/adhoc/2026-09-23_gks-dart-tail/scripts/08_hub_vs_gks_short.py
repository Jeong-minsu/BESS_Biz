"""SHORT strategy stats: GKS node vs hubs, same metrics as 02_tail_analysis."""
from pathlib import Path
import numpy as np, pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl
BASE = Path(__file__).resolve().parents[1]
W = pd.read_parquet(BASE / "derived" / "spread_wide_all_nodes.parquet"); W.columns = W.columns.astype("int64")
nm = dl.read_csv("ercot/metadata/objects/price_node.csv.gz").set_index("OBJECTID").OBJECTNAME.to_dict()
names = ["GKS_BESS_RN", "HB_SOUTH", "HB_NORTH", "HB_WEST", "HB_HOUSTON", "HB_HUBAVG"]
H = W[[o for o in W.columns if nm.get(o) in names]].rename(columns=nm)[names].dropna()
he = H.index.hour.where(H.index.hour != 0, 24)
day = (H.index - pd.Timedelta(hours=1)).normalize()

def st(x):
    x = x.to_numpy(); w, l = x[x > 0], x[x < 0]; R = w.mean() / -l.mean()
    cum = np.cumsum(x); mdd = (cum - np.maximum.accumulate(np.r_[0, cum])[1:]).min()
    q = np.quantile(x, .01)
    return dict(win=len(w)/len(x), payoff=R, be=1/(1+R), EV=x.mean(), total=x.sum(), CVaR1=x[x <= q].mean(),
                worst=x.min(), MDD=mdd, k_wipe=int(np.searchsorted(-np.cumsum(np.sort(l)), x.sum()) + 1) if x.sum() > 0 else 0)
pd.set_option("display.width", 250, "display.float_format", "{:,.2f}".format)
for lab, m in [("hourly 24h", np.ones(len(H), bool)), ("hourly HE9-16", (he >= 9) & (he <= 16)), ("hourly HE17-22", (he >= 17) & (he <= 22))]:
    print(f"\n=== SHORT {lab} ===\n", pd.DataFrame({c: st(H.loc[m, c]) for c in names}).T.to_string())
D = H.groupby(day).sum()
print("\n=== SHORT 24h per day ===\n", pd.DataFrame({c: st(D[c]) for c in names}).T.to_string())
print("\nworst 5 days per column:\n", pd.DataFrame({c: D[c].nsmallest(5).round(0).astype(int).astype(str).values + " (" + D[c].nsmallest(5).index.strftime("%y-%m-%d") + ")" for c in names}).to_string())
Y = H.groupby(H.index.year).mean(); print("\nEV by year:\n", Y.to_string())
# diversification: GKS + HUB 50/50
mix = (H.GKS_BESS_RN + H.HB_SOUTH) / 2
print("\n50/50 GKS+HB_SOUTH:", {k: round(v, 2) for k, v in st(mix).items()})
print("corr daily GKS vs hubs:", D.corr().GKS_BESS_RN.round(2).to_dict())
