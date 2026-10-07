"""Per-node spread stats (same table as GKS) + GKS rank vs all ERCOT nodes + hubs."""
from pathlib import Path
import numpy as np, pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl

BASE = Path(__file__).resolve().parents[1]
W = pd.read_parquet(BASE / "derived" / "spread_wide_all_nodes.parquet")
W.columns = W.columns.astype("int64")
meta = dl.read_csv("ercot/metadata/objects/price_node.csv.gz")[["OBJECTID", "OBJECTNAME", "ZONE", "SUBTYPE"]]
meta = meta.set_index("OBJECTID")
GKS = 10017907494
HUBS = ["HB_NORTH", "HB_SOUTH", "HB_WEST", "HB_HOUSTON", "HB_PAN", "HB_HUBAVG", "HB_BUSAVG"]
N = len(W)
years = W.index.to_series().dt.year.values  # DATETIME is hour-ending; HE24 of 12/31 lands on 1/1 (negligible)

def st(x: np.ndarray) -> dict:
    x = x[~np.isnan(x)]
    if len(x) < 100: return {}
    med = np.median(x); q1, q99 = np.quantile(x, [0.01, 0.99])
    s = pd.Series(x)
    a = np.sort(np.abs(x))[::-1]; k = max(1, int(len(x) * 0.01))
    return dict(n=len(x), mean=x.mean(), sd=x.std(ddof=1), median=med,
                robust_sd=np.median(np.abs(x - med)) * 1.4826, sd_trim1=np.clip(x, q1, q99).std(ddof=1),
                kurt=s.kurt(), skew=s.skew(), worst_short=x.min(), worst_long=-x.max(),
                short_loss100_yr=(x <= -100).sum() / (len(x) / 8766), long_loss100_yr=(x >= 100).sum() / (len(x) / 8766),
                top1pct_share=a[:k].sum() / a.sum(), sd_ratio=x.std(ddof=1) / max(np.median(np.abs(x - med)) * 1.4826, 1e-9))

rows = {}
for oid in W.columns:
    v = W[oid].to_numpy(dtype="float64")
    r = st(v)
    if not r: continue
    for y in (2024, 2025, 2026):
        xv = v[years == y]; xv = xv[~np.isnan(xv)]
        r[f"mean_{y}"] = xv.mean() if len(xv) else np.nan
        r[f"sd_{y}"] = xv.std(ddof=1) if len(xv) > 1 else np.nan
    rows[oid] = r
T = pd.DataFrame(rows).T
T.index = T.index.astype("int64")
T = T.join(meta, how="left")
T["coverage"] = T.n / N
T.to_csv(BASE / "derived" / "node_spread_stats.csv")

full = T[T.coverage >= 0.98].copy()
print("nodes total", len(T), "full-coverage (>=98%)", len(full), "subtypes", full.SUBTYPE.value_counts().to_dict())
cols = ["mean", "sd", "median", "robust_sd", "sd_trim1", "kurt", "skew", "worst_short", "worst_long",
        "short_loss100_yr", "long_loss100_yr", "top1pct_share", "sd_ratio",
        "mean_2024", "mean_2025", "mean_2026", "sd_2024", "sd_2025", "sd_2026"]
pd.set_option("display.width", 260, "display.max_columns", 40, "display.float_format", "{:,.2f}".format)

name = full.OBJECTNAME
sel = full[name.isin(HUBS) | (full.index == GKS)].set_index("OBJECTNAME").loc[lambda d: ["GKS_BESS_RN"] + [h for h in HUBS if h in d.index]]
dist = full[cols].quantile([0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]).rename(index=lambda q: f"all nodes p{int(q*100)}")
rank = full[cols].rank(pct=True).loc[GKS].rename("GKS percentile (0=lowest)")
print("\n=== GKS vs hubs ===\n", sel[cols].T.to_string())
print("\n=== all full-coverage nodes distribution ===\n", dist.T.to_string())
print("\n", rank.to_string())
zone = full[full.SUBTYPE == "GENERATOR"].groupby("ZONE")[["mean", "sd", "robust_sd", "sd_trim1", "kurt", "worst_short", "worst_long", "short_loss100_yr"]].median()
print("\n=== resource nodes median by zone ===\n", zone.to_string())
print("\nworst_short most negative 10:\n", full.nsmallest(10, "worst_short")[["OBJECTNAME", "ZONE", "worst_short", "sd", "robust_sd"]].to_string())
print("\nsd highest 10:\n", full.nlargest(10, "sd")[["OBJECTNAME", "ZONE", "sd", "robust_sd", "kurt", "worst_short", "worst_long"]].to_string())

# system vs local: GKS worst hours vs hubs same hour
nm = meta.OBJECTNAME.to_dict()
H = W[[GKS] + [o for o in W.columns if nm.get(o) in HUBS]].rename(columns=nm)
wh = H.nsmallest(12, "GKS_BESS_RN")
print("\n=== GKS worst 12 hours: same-hour hub spreads ===\n", wh.to_string())
bh = H.nlargest(8, "GKS_BESS_RN")
print("\n=== GKS best 8 hours (LONG worst) ===\n", bh.to_string())
print("\ncorr GKS spread vs hubs:\n", H.corr()["GKS_BESS_RN"].round(3).to_string())
basis = (H["GKS_BESS_RN"] - H["HB_SOUTH"]).dropna()
print("\nGKS - HB_SOUTH spread basis: mean %.2f sd %.2f robust_sd %.2f worst %.1f best %.1f" % (
    basis.mean(), basis.std(), (basis - basis.median()).abs().median() * 1.4826, basis.min(), basis.max()))
# variance share explained by HB_SOUTH / HB_BUSAVG
for h in ["HB_SOUTH", "HB_BUSAVG"]:
    b = H[["GKS_BESS_RN", h]].dropna(); r2 = b.corr().iloc[0, 1] ** 2
    print(f"R2 GKS~{h}: {r2:.3f}")
with pd.ExcelWriter(BASE / "derived" / "node_spread_compare.xlsx") as xw:
    sel[cols].T.to_excel(xw, sheet_name="GKS_vs_hubs")
    dist.T.to_excel(xw, sheet_name="all_nodes_dist")
    rank.to_excel(xw, sheet_name="GKS_percentile")
    zone.to_excel(xw, sheet_name="zone_median")
    full.to_excel(xw, sheet_name="all_nodes")
    wh.to_excel(xw, sheet_name="GKS_worst_hours_vs_hubs")
