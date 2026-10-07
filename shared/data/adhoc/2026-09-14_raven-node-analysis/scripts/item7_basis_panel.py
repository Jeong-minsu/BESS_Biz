"""ITEM 7 — build the RVN-vs-GKS basis panels (PART B inputs).
1. GKS_BESS_RN hourly constraint panel from raw/msf_gks/*.parquet, aggregated exactly like item2's monthly_panel
   (mcc_h = -SF x lambda x dur, DA row = 1 h, RT row = 1/12 h, RT binding = lambda > 0).
   -> derived/item7_gks_congestion_hourly_panel.parquet
2. Constraint-level basis panel: outer join of RVN-location (item2) and GKS panels on (constraint, market, hour)
   over the GKS window 2024-07-03..2026-09-13; missing node row = SF below reporting threshold = 0 MCC.
   basis_h = mcc_rvn - mcc_gks  (positive = raises RVN relative to GKS)
   -> derived/item7_basis_constraint_panel.parquet
3. Hourly price panel for RVN (real from 2026-06-04, item2 proxy before), GKS, HB_HOUSTON, HB_SOUTH, HB_BUSAVG,
   from raw/price_panel (no re-download). -> derived/item7_price_panel.parquet
Real data only. Memory-safe (monthly chunks).
"""
import json
from pathlib import Path
import numpy as np, pandas as pd

R = Path(__file__).resolve().parents[1]; D = R / "derived"
GKS_RAW = R / "raw" / "msf_gks"
WIN0, WIN1 = pd.Timestamp("2024-07-03"), pd.Timestamp("2026-09-13 23:00")
NODES = {"RVN_RN": 10019925379, "GKS_BESS_RN": 10017907494, "HB_HOUSTON": 10000697077, "HB_SOUTH": 10000697079,
         "HB_BUSAVG": 10000698380, "CBEC_ALL": 10001765766, "RBN_BESS1": 10017290064, "TAV_RN": 10016969364}
PROXY = json.load(open(D / "item2_proxy_definition.json"))
RVN_REAL_FROM = pd.Timestamp("2026-06-04")


def gks_monthly_panel(fp):
    m = pd.read_parquet(fp)
    m = m[m.SHADOWPRICE > 0].copy()
    m["dt"] = pd.to_datetime(m.DATETIME, format="%m/%d/%Y %H:%M:%S")
    m["dur"] = np.where(m.MARKET == "DA", 1.0, 1 / 12)
    m["hour"] = m.dt.dt.floor("h")
    m["mcc_h"] = -m.SHIFTFACTOR * m.SHADOWPRICE * m.dur
    m["lam_h"] = m.SHADOWPRICE * m.dur
    g = m.groupby(["CONSTRAINTNAME", "MARKET", "hour"])
    h = g.agg(mcc_h=("mcc_h", "sum"), lam_h=("lam_h", "sum"), lam_max=("SHADOWPRICE", "max"),
              sf_mean=("SHIFTFACTOR", "mean"), n_int=("SHIFTFACTOR", "size"), limit=("LIMIT", "median"),
              fac=("FACILITYID", "first"), ctg=("CONTINGENCYID", "first")).reset_index()
    h["bind_frac"] = np.where(h.MARKET == "DA", 1.0, np.minimum(h.n_int / 12, 1.0))
    return h


def build_gks_panel():
    fp = D / "item7_gks_congestion_hourly_panel.parquet"
    if fp.exists(): return pd.read_parquet(fp)
    parts = [gks_monthly_panel(f) for f in sorted(GKS_RAW.glob("*.parquet"))]
    P = pd.concat(parts, ignore_index=True); P.to_parquet(fp, index=False); return P


def build_basis_panel(G):
    fp = D / "item7_basis_constraint_panel.parquet"
    if fp.exists(): return pd.read_parquet(fp)
    Rv = pd.read_parquet(D / "item2_congestion_hourly_panel.parquet",
                         columns=["CONSTRAINTNAME", "MARKET", "hour", "mcc_h", "lam_h", "lam_max", "sf_mean", "sf_rvn_mean",
                                  "sf_proxy_mean", "bind_frac", "src"])
    Rv = Rv[(Rv.hour >= WIN0) & (Rv.hour <= WIN1)]
    G = G[(G.hour >= WIN0) & (G.hour <= WIN1)]
    key = ["CONSTRAINTNAME", "MARKET", "hour"]
    B = Rv.rename(columns={"mcc_h": "mcc_rvn", "sf_mean": "sf_loc", "lam_h": "lam_h_rvn", "lam_max": "lam_max_rvn", "bind_frac": "bf_rvn"}) \
          .merge(G.rename(columns={"mcc_h": "mcc_gks", "sf_mean": "sf_gks", "lam_h": "lam_h_gks", "lam_max": "lam_max_gks", "bind_frac": "bf_gks"})
                 [key + ["mcc_gks", "sf_gks", "lam_h_gks", "lam_max_gks", "bf_gks"]], on=key, how="outer")
    # lambda is node-independent: take whichever side has it
    B["lam_h"] = B.lam_h_rvn.fillna(B.lam_h_gks); B["lam_max"] = B.lam_max_rvn.fillna(B.lam_max_gks)
    B["bind_frac"] = B.bf_rvn.fillna(B.bf_gks)
    B["mcc_rvn"] = B.mcc_rvn.fillna(0.0); B["mcc_gks"] = B.mcc_gks.fillna(0.0)
    B["basis_h"] = B.mcc_rvn - B.mcc_gks
    B = B.drop(columns=["lam_h_rvn", "lam_h_gks", "lam_max_rvn", "lam_max_gks", "bf_rvn", "bf_gks"])
    B.to_parquet(fp, index=False); return B


def build_price_panel():
    fp = D / "item7_price_panel.parquet"
    if fp.exists(): return pd.read_parquet(fp)
    ids = set(NODES.values()); parts = []
    for f in sorted((R / "raw" / "price_panel").glob("*.parquet")):
        if f.stem < "202407": continue
        p = pd.read_parquet(f, columns=["OBJECTID", "DATETIME", "DALMP", "RTLMP", "FLOWDAY"])
        p = p[p.OBJECTID.isin(ids)].copy()
        p["dt"] = pd.to_datetime(p.DATETIME, format="%m/%d/%Y %H:%M:%S")
        parts.append(p.drop(columns=["DATETIME"]))
    p = pd.concat(parts, ignore_index=True)
    inv = {v: k for k, v in NODES.items()}; p["node"] = p.OBJECTID.map(inv)
    da = p.pivot_table(index="dt", columns="node", values="DALMP", aggfunc="first")
    rt = p.pivot_table(index="dt", columns="node", values="RTLMP", aggfunc="first")
    fd = p.groupby("dt").FLOWDAY.first()
    w = dict(zip(PROXY["nodes"], PROXY["weights"])); icpt = PROXY["intercept"]
    out = pd.DataFrame(index=da.index)
    for mk, X in (("DA", da), ("RT", rt)):
        prox = icpt + sum(X[n] * wt for n, wt in w.items())
        real = X["RVN_RN"] if "RVN_RN" in X else pd.Series(np.nan, index=X.index)
        use_real = (X.index >= RVN_REAL_FROM) & real.notna()
        out[f"{mk}_RVN"] = np.where(use_real, real, prox)
        out[f"{mk}_RVN_proxy"] = prox
        out[f"{mk}_RVN_src"] = np.where(use_real, "real", "proxy")
        for n in ("GKS_BESS_RN", "HB_HOUSTON", "HB_SOUTH", "HB_BUSAVG"):
            out[f"{mk}_{n}"] = X[n]
    out["FLOWDAY"] = fd; out["HE"] = out.index.hour.where(out.index.hour > 0, 24)
    out = out[(out.index >= WIN0) & (out.index <= WIN1 + pd.Timedelta(hours=1))]
    out = out.dropna(subset=["DA_GKS_BESS_RN", "RT_GKS_BESS_RN", "DA_RVN", "RT_RVN"])
    out.to_parquet(fp); return out


if __name__ == "__main__":
    G = build_gks_panel(); print("GKS panel", G.shape, G.hour.min(), "->", G.hour.max())
    B = build_basis_panel(G); print("basis panel", B.shape, "constraints", B.CONSTRAINTNAME.nunique())
    P = build_price_panel(); print("price panel", P.shape, P.index.min(), "->", P.index.max())
    print(P[["DA_RVN", "DA_GKS_BESS_RN", "RT_RVN", "RT_GKS_BESS_RN"]].describe().round(1).to_string())
    print((P.DA_RVN_src == "real").sum(), "real RVN hours")
