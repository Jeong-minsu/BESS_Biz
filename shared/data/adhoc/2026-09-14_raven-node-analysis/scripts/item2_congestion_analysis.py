"""ITEM 2 Part B — 3-year constraint attribution at the Raven location (RVN_RN / proxy).
Input : raw/msf_nodes/YYYYMM.parquet (market_shift_factors rows for RVN + proxy nodes, DA + RT 5-min).
Location shift factor SF_loc(k,t) = RVN_RN SF where RVN exists (>=2026-06), else proxy blend
  sum(w_i * SF_i) with weights from derived/item2_proxy_definition.json (TAV_RN fallback pre-2023-12).
  MCC is linear in SF, so the price-proxy weights carry over to the SF exactly (intercept drops out).
MCC contribution = -SF_loc x lambda (project convention). Positive = raises Raven LMP (discharge-favorable).
Time weight: DA row = 1 h, RT row = 1/12 h. RT binding = lambda > 0.
Aggregation is done month-by-month to an hourly constraint panel (memory-safe), then all stats derive from it.
Outputs derived/item2_congestion_*.json / .parquet.  Real data only.
"""
import json
from pathlib import Path
import numpy as np, pandas as pd

R = Path(__file__).resolve().parents[1]
D = R / "derived"; RAW = R / "raw" / "msf_nodes"
RVN = 10019925379
defn = json.load(open(D / "item2_proxy_definition.json"))
W_MAIN = dict(zip(defn["objectids"], defn["weights"]))
W_FALL = dict(zip(defn["fallback"]["objectids"], defn["fallback"]["weights"]))
FALL_BEFORE = pd.Timestamp("2023-12-01")
EPS = 1e-9

# --- metadata decode ---
obj = pd.read_parquet(R / "raw/objects_all.parquet")
fac = obj[obj.OBJECTTYPE == "facility"].set_index("OBJECTID")
facname, faczone, facsub = fac.OBJECTNAME.to_dict(), fac.ZONE.to_dict(), fac.SUBTYPE.to_dict()
con = pd.read_parquet(R / "raw/objects_contingency.parquet")
conname = dict(zip(con["OBJECTID"], con["CONTINGENCYNAME"]))


def location_sf(m: pd.DataFrame) -> pd.DataFrame:
    """rows keyed (FACILITYID,CONTINGENCYID,DATETIME,MARKET,CONSTRAINTNAME) -> SF_loc, lambda, LIMIT, source."""
    key = ["FACILITYID", "CONTINGENCYID", "DATETIME", "MARKET", "CONSTRAINTNAME"]
    piv = m.pivot_table(index=key, columns="PRICENODEID", values="SHIFTFACTOR", aggfunc="first")
    lam = m.groupby(key)[["SHADOWPRICE", "LIMIT"]].first()
    dt = pd.to_datetime(piv.index.get_level_values("DATETIME"), format="%m/%d/%Y %H:%M:%S")
    out = lam.copy(); out["dt"] = dt.values
    # missing node row for a binding => SF below reporting threshold => 0
    w = W_FALL if dt[0] < FALL_BEFORE else W_MAIN
    prox = sum(piv[c].fillna(0.0) * wt for c, wt in w.items() if c in piv.columns)
    if RVN in piv.columns:
        has = piv[RVN].notna()
        out["sf"] = np.where(has, piv[RVN], prox); out["src"] = np.where(has, "RVN", "proxy")
        out["sf_proxy"] = prox.values; out["sf_rvn"] = piv[RVN].values
    else:
        out["sf"] = prox.values; out["src"] = "proxy"; out["sf_proxy"] = prox.values; out["sf_rvn"] = np.nan
    return out.reset_index()


def monthly_panel(fp: Path) -> pd.DataFrame:
    m = pd.read_parquet(fp)
    m = m[m.SHADOWPRICE > 0]
    loc = location_sf(m)
    loc["mcc"] = -loc["sf"] * loc["SHADOWPRICE"]
    loc["dur"] = np.where(loc.MARKET == "DA", 1.0, 1 / 12)
    loc["hour"] = loc.dt.dt.floor("h")
    # hourly per constraint x market: cum $ (=mcc*dur), lambda stats, sf, interval count, dominant facility/ctg
    loc["mcc_h"] = loc.mcc * loc.dur; loc["lam_h"] = loc.SHADOWPRICE * loc.dur
    g = loc.groupby(["CONSTRAINTNAME", "MARKET", "hour"])
    h = g.agg(mcc_h=("mcc_h", "sum"), lam_h=("lam_h", "sum"), lam_max=("SHADOWPRICE", "max"),
              sf_mean=("sf", "mean"), sf_rvn_mean=("sf_rvn", "mean"), sf_proxy_mean=("sf_proxy", "mean"),
              n_int=("sf", "size"), limit=("LIMIT", "median"), fac=("FACILITYID", "first"),
              ctg=("CONTINGENCYID", "first"), src=("src", "first")).reset_index()
    h["bind_frac"] = np.where(h.MARKET == "DA", 1.0, np.minimum(h.n_int / 12, 1.0))  # share of the hour binding
    return h


def build_panel() -> pd.DataFrame:
    fp = D / "item2_congestion_hourly_panel.parquet"
    if fp.exists():
        return pd.read_parquet(fp)
    parts = []
    for f in sorted(RAW.glob("*.parquet")):
        parts.append(monthly_panel(f)); print("panel", f.name, len(parts[-1]), flush=True)
    P = pd.concat(parts, ignore_index=True)
    P.to_parquet(fp, index=False); return P


P = build_panel()
P["year"] = P.hour.dt.year; P["month"] = P.hour.dt.month; P["he"] = P.hour.dt.hour + 1
hours_total = pd.date_range(P.hour.min(), P.hour.max(), freq="h")
n_hours = len(hours_total)
hours_by_year = pd.Series(hours_total.year).value_counts().sort_index()
hours_by_month = pd.Series(hours_total.month).value_counts().sort_index()
hours_by_he = pd.Series(hours_total.hour + 1).value_counts().sort_index()
print("panel rows", len(P), "hours", n_hours, P.hour.min(), "->", P.hour.max())

# ---------------- ranking ----------------
tot = P.pivot_table(index="CONSTRAINTNAME", columns="MARKET", values="mcc_h", aggfunc="sum").fillna(0)
tot["total"] = tot.sum(axis=1); tot["abs_total"] = tot.total.abs()
tot["abs_da_plus_rt"] = P.groupby("CONSTRAINTNAME").mcc_h.apply(lambda s: s.abs().sum())
rank = tot.sort_values("abs_total", ascending=False)
rank.to_csv(D / "item2_congestion_ranking_all.csv")
TOP = list(rank.head(10).index)
print("\nTOP-10 by |cum MCC contribution| (DA+RT, $/MWh-h per MW, 2023-09..2026-09):")
print(rank.head(15).round(0).to_string())


def profile(cn: str) -> dict:
    s = P[P.CONSTRAINTNAME == cn]
    da, rt = s[s.MARKET == "DA"], s[s.MARKET == "RT"]
    out = {"constraint": cn}
    f = s.fac.value_counts().index[0]; c = s.ctg.value_counts().index[0]
    out["element"] = facname.get(f, str(f)); out["element_zone"] = faczone.get(f); out["element_type"] = facsub.get(f)
    out["dominant_contingency"] = conname.get(c, str(c))
    out["n_distinct_contingencies"] = int(s.ctg.nunique())
    out["sf_mean"] = {"da": round(float(da.sf_mean.mean()), 4) if len(da) else None,
                      "rt": round(float(rt.sf_mean.mean()), 4) if len(rt) else None}
    out["sign_at_raven"] = "pos (raises RVN LMP / discharge-favorable)" if s.mcc_h.sum() > 0 else "neg (lowers RVN LMP / charge-favorable)"
    out["cum_mcc"] = {"da": round(float(da.mcc_h.sum()), 1), "rt": round(float(rt.mcc_h.sum()), 1), "total": round(float(s.mcc_h.sum()), 1)}
    # per year: total & mean-per-binding-hour, DA / RT
    py = {}
    for y in sorted(s.year.unique()):
        sy = s[s.year == y]; dy, ry = sy[sy.MARKET == "DA"], sy[sy.MARKET == "RT"]
        py[int(y)] = {"da_total": round(float(dy.mcc_h.sum()), 1), "da_bind_hours": int(len(dy)),
                      "da_mean_per_bind_hour": round(float(dy.mcc_h.mean()), 2) if len(dy) else None,
                      "rt_total": round(float(ry.mcc_h.sum()), 1), "rt_bind_hours": round(float(ry.bind_frac.sum()), 1),
                      "rt_mean_per_bind_hour": round(float(ry.mcc_h.sum() / ry.bind_frac.sum()), 2) if len(ry) else None,
                      "hours_in_year_covered": int(hours_by_year.get(y, 0))}
    out["per_year"] = py
    # seasonality: month x contribution (DA, RT) + bind months
    mm = s.pivot_table(index="month", columns="MARKET", values="mcc_h", aggfunc="sum").reindex(range(1, 13)).fillna(0)
    out["month_matrix"] = {"da": [round(float(v), 1) for v in mm.get("DA", pd.Series(0, index=mm.index))],
                           "rt": [round(float(v), 1) for v in mm.get("RT", pd.Series(0, index=mm.index))]}
    mb = s.groupby("month").apply(lambda x: (x.mcc_h.abs().sum()), include_groups=False).reindex(range(1, 13)).fillna(0)
    out["binding_months"] = [int(m) for m in mb[mb > 0.05 * mb.sum()].index]
    # hourly profile: HE x P(bind) and mean lambda (binding-conditional), DA & RT
    hp = {}
    for mk, sub in (("da", da), ("rt", rt)):
        pb = (sub.groupby("he").bind_frac.sum() / hours_by_he * 24 / 24).reindex(range(1, 25)).fillna(0)
        lam = (sub.groupby("he").lam_h.sum() / sub.groupby("he").bind_frac.sum()).reindex(range(1, 25))
        hp[mk] = {"p_bind": [round(float(v), 4) for v in pb], "mean_lambda": [None if pd.isna(v) else round(float(v), 1) for v in lam]}
    out["hourly_profile"] = hp
    # DA vs RT strength
    da_bind_h = float(len(da)); rt_bind_h = float(rt.bind_frac.sum())
    out["da_vs_rt"] = {
        "da_bind_hours": da_bind_h, "da_bind_freq": round(da_bind_h / n_hours, 4),
        "da_mean_lambda": round(float(da.lam_h.sum() / da_bind_h), 1) if da_bind_h else None,
        "da_p90_lambda": round(float(da.lam_h.quantile(0.9)), 1) if da_bind_h else None,
        "rt_bind_hours_equiv": round(rt_bind_h, 1), "rt_bind_freq": round(rt_bind_h / n_hours, 4),
        "rt_mean_lambda": round(float(rt.lam_h.sum() / rt_bind_h), 1) if rt_bind_h else None,
        "rt_p90_lambda_interval_max": round(float(rt.lam_max.quantile(0.9)), 1) if rt_bind_h else None,
        "rt_max_lambda": round(float(rt.lam_max.max()), 1) if rt_bind_h else None,
        "harder_in": "DA" if da.mcc_h.abs().sum() > rt.mcc_h.abs().sum() else "RT",
        "abs_contrib_ratio_da_over_rt": round(float(da.mcc_h.abs().sum() / max(rt.mcc_h.abs().sum(), EPS)), 2),
    }
    # DA-vs-RT sign agreement on hours where both bind; plus DART lean (spread = MCC_DA - MCC_RT)
    hda = da.set_index("hour").mcc_h; hrt = rt.set_index("hour").mcc_h
    both = pd.concat([hda, hrt], axis=1, keys=["da", "rt"]).fillna(0)
    b2 = both[(both.da.abs() > EPS) & (both.rt.abs() > EPS)]
    spread = both.da - both.rt
    out["da_rt_agreement"] = {
        "hours_both_bind": int(len(b2)), "hours_da_only": int(((both.da.abs() > EPS) & (both.rt.abs() <= EPS)).sum()),
        "hours_rt_only": int(((both.rt.abs() > EPS) & (both.da.abs() <= EPS)).sum()),
        "sign_agree_when_both": round(float((np.sign(b2.da) == np.sign(b2.rt)).mean()), 3) if len(b2) else None,
        "cum_spread_da_minus_rt": round(float(spread.sum()), 1),
        "dart_lean": "short (DA congestion richer)" if spread.sum() > 0 else "long (RT congestion richer)",
        "pct_active_hours_short": round(float((spread > EPS).sum() / max((spread.abs() > EPS).sum(), 1)), 3),
    }
    # forward relevance diagnostics
    days = s.groupby(s.hour.dt.date).mcc_h.apply(lambda x: x.abs().sum())
    by_ym = s.groupby(s.hour.dt.to_period("M")).mcc_h.apply(lambda x: x.abs().sum())
    last12 = by_ym[by_ym.index >= (by_ym.index.max() - 11)].sum()
    out["forward_relevance"] = {
        "first_bind": str(s.hour.min().date()), "last_bind": str(s.hour.max().date()),
        "months_with_binding": int(by_ym[by_ym > 0].shape[0]),
        "share_abs_contrib_last_12m": round(float(last12 / by_ym.sum()), 3),
        "share_abs_contrib_2026": round(float(s[s.year == 2026].mcc_h.abs().sum() / s.mcc_h.abs().sum()), 3),
        "top3_days_share": round(float(days.nlargest(3).sum() / days.sum()), 3),
        "top3_days": [str(d) for d in days.nlargest(3).index],
        "limit_median_by_year": {int(y): round(float(v), 0) for y, v in s.groupby("year")["limit"].median().items()},
        "src_share_rvn": round(float((s.src == "RVN").mean()), 3),
    }
    # proxy-vs-RVN SF check in overlap
    ov = s[s.sf_rvn_mean.notna()]
    if len(ov):
        out["sf_check_overlap"] = {"n_hours": int(len(ov)), "sf_rvn": round(float(ov.sf_rvn_mean.mean()), 4),
                                   "sf_proxy": round(float(ov.sf_proxy_mean.mean()), 4)}
    return out


profiles = {cn: profile(cn) for cn in TOP}
json.dump(profiles, open(D / "item2_congestion_top10_profiles.json", "w"), indent=2, default=str)

# overlap validation of proxy SF vs RVN SF for constraints ranked top-30 by |MCC at RVN| (2026-06..09 only)
ov = P[P.sf_rvn_mean.notna()].copy()
ov["mcc_rvn"] = -ov.sf_rvn_mean * ov.lam_h; ov["mcc_proxy"] = -ov.sf_proxy_mean * ov.lam_h
chk = ov.groupby("CONSTRAINTNAME").agg(hours=("lam_h", "size"), sf_rvn=("sf_rvn_mean", "mean"), sf_proxy=("sf_proxy_mean", "mean"),
                                       mcc_rvn=("mcc_rvn", "sum"), mcc_proxy=("mcc_proxy", "sum"))
if len(chk):
    chk["abs_mcc_rvn"] = chk.mcc_rvn.abs(); chk = chk.sort_values("abs_mcc_rvn", ascending=False)
    chk.head(30).to_csv(D / "item2_congestion_proxy_sf_check.csv")
    c30 = chk.head(30)
    print("\nOverlap SF check (2026-06..09), top-30 constraints by |MCC at RVN|: corr(sf_rvn, sf_proxy)=%.3f, sign agree=%.2f, sum|mcc| rvn=%.0f proxy=%.0f"
          % (np.corrcoef(c30.sf_rvn, c30.sf_proxy)[0, 1], (np.sign(c30.sf_rvn) == np.sign(c30.sf_proxy)).mean(), c30.abs_mcc_rvn.sum(), c30.mcc_proxy.abs().sum()))
    print(c30.round(3).head(12).to_string())
else:
    print("\n(no RVN overlap rows in panel - SF check skipped)")

# yearly totals summary
yr = P.pivot_table(index="year", columns="MARKET", values="mcc_h", aggfunc="sum").round(0)
yr_abs = P.groupby(["year", "MARKET"]).mcc_h.apply(lambda s: s.abs().sum()).unstack().round(0)
print("\nNet MCC by year (DA/RT):"); print(yr.to_string()); print("gross |MCC| by year:"); print(yr_abs.to_string())
json.dump({"net_by_year": yr.to_dict(), "gross_by_year": yr_abs.to_dict(), "n_hours": n_hours,
           "window": [str(P.hour.min()), str(P.hour.max())]}, open(D / "item2_congestion_totals.json", "w"), indent=2, default=str)

for cn in TOP:
    p = profiles[cn]
    print(f"\n### {cn} | {p['element']} [{p['element_zone']}/{p['element_type']}] ctg={p['dominant_contingency']} sign={p['sign_at_raven'][:3]} "
          f"cum DA={p['cum_mcc']['da']} RT={p['cum_mcc']['rt']} sf={p['sf_mean']}")
    print("  per_year:", {y: (v['da_total'], v['rt_total']) for y, v in p['per_year'].items()})
    print("  binding months:", p['binding_months'], "| harder in", p['da_vs_rt']['harder_in'], "ratio", p['da_vs_rt']['abs_contrib_ratio_da_over_rt'],
          "| DA freq %.3f λ %s | RT freq %.3f λ %s" % (p['da_vs_rt']['da_bind_freq'], p['da_vs_rt']['da_mean_lambda'], p['da_vs_rt']['rt_bind_freq'], p['da_vs_rt']['rt_mean_lambda']))
    print("  agreement:", p['da_rt_agreement'])
    print("  forward:", p['forward_relevance'])
    print("  sf_check:", p.get("sf_check_overlap"))
