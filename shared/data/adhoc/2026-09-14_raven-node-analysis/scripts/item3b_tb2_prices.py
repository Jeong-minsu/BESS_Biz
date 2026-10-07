"""item3b: daily TB2 (DA & RT) + absolute top-2 / bottom-2 levels for Raven, Houston ESS peers, GKS, hubs.
Source: raw/price_panel/*.parquet (real Yes Energy datalake ercot/prices/lmp/hourly; no mock).
TB2 per BRIEF: mean(top-2 hrs) - mean(bottom-2 hrs), unordered (no charge-before-discharge constraint)."""
import pandas as pd, numpy as np
from pathlib import Path
A = Path(__file__).resolve().parents[1]
NODES = {"RVN_RN":10019925379,"RBN_BESS1":10017290064,"TAV_RN":10016969364,"GKS_BESS_RN":10017907494,
         "HB_HOUSTON":10000697077,"HB_BUSAVG":10000698380,"HB_SOUTH":10000697079,"HB_NORTH":10000697078,"HB_WEST":10000697080}
months = ["202601","202602","202603","202604","202605","202606","202607","202608","202609"]
fr = []
for m in months:
    p = A/f"raw/price_panel/{m}.parquet"
    if not p.exists(): continue
    d = pd.read_parquet(p, columns=["OBJECTID","DATETIME","DALMP","RTLMP","FLOWDAY"])
    fr.append(d[d.OBJECTID.isin(NODES.values())])
df = pd.concat(fr); inv = {v:k for k,v in NODES.items()}
df["node"] = df.OBJECTID.map(inv)
df["he"] = pd.to_datetime(df.DATETIME, format="%m/%d/%Y %H:%M:%S").dt.hour.replace(0,24)
df["FLOWDAY"] = pd.to_datetime(df.FLOWDAY)
# hourly panel
df.to_parquet(A/"derived/item3b_hourly_prices_2026.parquet", index=False)
rows = []
for (n, fd), g in df.groupby(["node","FLOWDAY"]):
    r = {"node":n,"flowday":fd,"n_hrs":len(g)}
    for col, tag in (("DALMP","da"),("RTLMP","rt")):
        s = g.dropna(subset=[col]).sort_values(col)
        if len(s) < 20: r[f"tb2_{tag}"]=np.nan; continue
        lo, hi = s.head(2), s.tail(2)
        r[f"tb2_{tag}"] = hi[col].mean()-lo[col].mean()
        r[f"top2_{tag}"] = hi[col].mean(); r[f"bot2_{tag}"] = lo[col].mean()
        r[f"top2_he_{tag}"] = ",".join(map(str,sorted(hi.he))); r[f"bot2_he_{tag}"] = ",".join(map(str,sorted(lo.he)))
        r[f"mean_{tag}"] = s[col].mean(); r[f"max_{tag}"] = s[col].max()
    rows.append(r)
tb = pd.DataFrame(rows); tb.to_csv(A/"derived/item3b_daily_tb2.csv", index=False)
# summer window summary (Raven has data 6/4+ DA, 6/2+ RT)
w = tb[(tb.flowday>="2026-06-04")&(tb.flowday<="2026-08-31")]
agg = w.groupby("node").agg(days=("flowday","count"), tb2_da=("tb2_da","mean"), tb2_rt=("tb2_rt","mean"),
      top2_da=("top2_da","mean"), bot2_da=("bot2_da","mean"), top2_rt=("top2_rt","mean"), bot2_rt=("bot2_rt","mean"),
      mean_da=("mean_da","mean"), mean_rt=("mean_rt","mean"), tb2_rt_med=("tb2_rt","median")).round(2)
print("Summer 2026-06-04..08-31"); print(agg.sort_values("tb2_rt", ascending=False).to_string())
# top-2 / bottom-2 hour-of-day distribution for Raven vs peers (RT)
for n in ["RVN_RN","RBN_BESS1","TAV_RN","GKS_BESS_RN","HB_HOUSTON"]:
    x = w[w.node==n]
    hs = pd.Series(",".join(x.top2_he_rt.dropna()).split(",")).value_counts().head(4).to_dict()
    ls = pd.Series(",".join(x.bot2_he_rt.dropna()).split(",")).value_counts().head(4).to_dict()
    print(n, "top2 HE:", hs, "bot2 HE:", ls)
agg.to_csv(A/"derived/item3b_summer_tb2_summary.csv")
