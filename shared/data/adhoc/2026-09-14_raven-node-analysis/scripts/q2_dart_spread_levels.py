"""Q2: Is Raven's average DA-RT spread materially lower than GKS's, and does that
mean DART virtual has less merit at Raven?

spread = DA - RT. Positive => selling DA (virtual short) wins.
Raven pre-2026-06 uses the item2 NNLS proxy; real RVN_RN used where it exists.
Real data only.
"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd

BASE = Path(__file__).resolve().parents[1]; D = BASE / "derived"
N = {"RVN": 10019925379, "GKS": 10017907494, "CBEC_ALL": 10001765766,
     "RBN_BESS1": 10017290064, "TAV_RN": 10016969364,
     "HB_HOU": 10000697077, "HB_SOU": 10000697079, "HB_AVG": 10000698380}
inv = {v: k for k, v in N.items()}
W, B = {"CBEC_ALL": 0.4148, "RBN_BESS1": 0.5407, "TAV_RN": 0.0445}, -0.065

parts = []
for f in sorted(glob.glob(str(BASE / "raw/price_panel/*.parquet"))):
    d = pd.read_parquet(f)
    parts.append(d[d.OBJECTID.isin(N.values())])
df = pd.concat(parts, ignore_index=True)
df["node"] = df.OBJECTID.map(inv)
df["dt"] = pd.to_datetime(df.DATETIME)

da = df.pivot_table(index="dt", columns="node", values="DALMP")
rt = df.pivot_table(index="dt", columns="node", values="RTLMP")
ix = da.index.intersection(rt.index)
da, rt = da.loc[ix], rt.loc[ix]

for p in (da, rt):
    have = [k for k in W if k in p.columns]
    ok = p[have].notna().all(axis=1)
    p["PROXY"] = np.nan
    p.loc[ok, "PROXY"] = B + sum(W[k] * p.loc[ok, k] for k in have)
    fb = (~ok) & p["TAV_RN"].notna()
    p.loc[fb, "PROXY"] = p.loc[fb, "TAV_RN"]

sp = pd.DataFrame(index=ix)
sp["RAVEN"] = (da.RVN - rt.RVN).fillna(da.PROXY - rt.PROXY)
sp["GKS"] = da.GKS - rt.GKS
sp["HUB_SYS"] = da.HB_AVG - rt.HB_AVG
sp["HUB_HOU"] = da.HB_HOU - rt.HB_HOU
sp["HUB_SOU"] = da.HB_SOU - rt.HB_SOU
sp["year"] = sp.index.year
sp["he"] = sp.index.hour.where(sp.index.hour != 0, 24)

out = {}
print("=" * 104)
print("Q2. DA-RT spread level: Raven vs GKS   (spread = DA - RT, $/MWh; + => virtual SHORT wins)")
print("=" * 104)

rows = []
for y in sorted(sp.year.unique()):
    s = sp[sp.year == y]
    r = {"year": int(y), "n_hours": int(s.RAVEN.notna().sum())}
    for c in ["RAVEN", "GKS", "HUB_SYS"]:
        v = s[c].dropna()
        if len(v) < 100:
            r[c] = None; continue
        # "harvest" = always take the profitable side of the mean, in $/MWh
        r[c] = {"mean": v.mean(), "std": v.std(),
                "abs_mean": abs(v.mean()),
                "t": v.mean() / (v.std() / np.sqrt(len(v))),
                "share_pos": (v > 0).mean(),
                "mean_over_std": v.mean() / v.std()}
    rows.append(r)

print(f"\n{'year':>6} {'Raven mean':>12} {'GKS mean':>11} {'System mean':>12} "
      f"{'|Raven|/|GKS|':>14} {'Raven std':>11} {'GKS std':>9}")
for r in rows:
    if not r.get("GKS") or not r.get("RAVEN"):
        print(f"{r['year']:>6} {r['RAVEN']['mean'] if r.get('RAVEN') else float('nan'):>12.2f} "
              f"{'—':>11} {r['HUB_SYS']['mean']:>12.2f}")
        continue
    ratio = r["RAVEN"]["abs_mean"] / r["GKS"]["abs_mean"] if r["GKS"]["abs_mean"] else np.nan
    print(f"{r['year']:>6} {r['RAVEN']['mean']:>12.2f} {r['GKS']['mean']:>11.2f} "
          f"{r['HUB_SYS']['mean']:>12.2f} {ratio:>14.2f} "
          f"{r['RAVEN']['std']:>11.1f} {r['GKS']['std']:>9.1f}")

# full-period
print("\n--- full period (2023-09 .. 2026-09) ---")
full = {}
for c in ["RAVEN", "GKS", "HUB_SYS", "HUB_HOU", "HUB_SOU"]:
    v = sp[c].dropna()
    full[c] = {"mean": v.mean(), "std": v.std(), "t": v.mean() / (v.std() / np.sqrt(len(v))),
               "share_pos": (v > 0).mean(), "mean_over_std": v.mean() / v.std(), "n": len(v)}
    print(f"  {c:9s} mean {v.mean():+7.3f}  std {v.std():7.2f}  "
          f"t {full[c]['t']:+7.2f}  P(+) {100*(v>0).mean():5.1f}%  "
          f"mean/std {full[c]['mean_over_std']:+.4f}")

# node-specific component: spread minus the system spread
print("\n--- node-specific spread component (node spread - system hub spread) ---")
for c in ["RAVEN", "GKS"]:
    v = (sp[c] - sp["HUB_SYS"]).dropna()
    tot = sp[c].dropna()
    print(f"  {c:6s} own-component mean {v.mean():+7.3f}  std {v.std():7.2f}  "
          f"share of total variance {v.var()/tot.var():6.1%}")

# harvestable structural bias: always-one-side by hour, sized 1 MW
print("\n--- structural bias by hour: |mean| and its t-stat ---")
print(f"{'HE':>3} {'Raven mean':>11} {'t':>7} | {'GKS mean':>10} {'t':>7} | {'GKS/Raven |mean|':>17}")
hr = []
for he in range(1, 25):
    s = sp[sp.he == he]
    a, g = s.RAVEN.dropna(), s.GKS.dropna()
    ta = a.mean() / (a.std() / np.sqrt(len(a)))
    tg = g.mean() / (g.std() / np.sqrt(len(g)))
    rat = abs(g.mean()) / abs(a.mean()) if a.mean() else np.nan
    hr.append(dict(he=he, raven_mean=a.mean(), raven_t=ta, gks_mean=g.mean(), gks_t=tg))
    print(f"{he:>3} {a.mean():>11.2f} {ta:>7.2f} | {g.mean():>10.2f} {tg:>7.2f} | {rat:>17.2f}")

n_sig_r = sum(1 for h in hr if abs(h["raven_t"]) > 2)
n_sig_g = sum(1 for h in hr if abs(h["gks_t"]) > 2)
print(f"\n  hours with a statistically clear directional bias (|t|>2): "
      f"Raven {n_sig_r}/24, GKS {n_sig_g}/24")

json.dump({"by_year": rows, "full": full, "by_hour": hr,
           "note": "spread = DA - RT; Raven uses real RVN_RN where available, item2 NNLS proxy before 2026-06"},
          open(D / "q2_dart_spread_levels.json", "w"), indent=1, default=float)
print("\nwrote q2_dart_spread_levels.json")
