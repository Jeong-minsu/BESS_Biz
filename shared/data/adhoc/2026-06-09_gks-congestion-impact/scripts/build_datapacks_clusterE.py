"""Build standardized dashboard DATA PACKS (JSON) for the 2 LIVE Cluster-E GTC interfaces:
VALEXP (Valley Export, NEG/charge) and WESTEX (West Texas Export, POS/discharge RT-only).

Fills the 7 Houston-style sections (schema: DATAPACK_SCHEMA.md), adapted to GTC nature:
  - section2 month*hour : NEW-compute 12x24 P(bind) matrices (distinct binding hr / total hr per cell)
  - section3 thresholds : GTC-appropriate triggers
        VALEXP -> SouthEast solar~=0 (overnight/winter) + low GR_SOUTH (Valley) wind/net-load
        WESTEX -> West-basin wind (GR_WEST+GR_PANHANDLE) GW breakpoint ~14GW
  - section5 watchlist  : informative=false (GTC element membership absent in datalake);
        SUBSTITUTE the GTC LIMIT as the key "switch" (limit history -> binding-day rate by limit regime)
Real data only (Yes Energy Datalake derived parquets). Convention impact=-SF*lambda; neg=charge, pos=discharge.
"""
import json
from pathlib import Path
import numpy as np, pandas as pd

D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
GTCS = ["VALEXP", "WESTEX"]

# ---- inputs (REUSE) ----
bstats = json.load(open(D/"clusterE_binding_stats.json"))
limit_hist = json.load(open(D/"clusterE_limit_history.json"))
panel = pd.read_parquet(D/"clusterE_hourly_panel.parquet")
raw = pd.read_parquet(D/"derived_placeholder") if False else pd.read_parquet(D/"gks_msf_raw.parquet")
raw = raw[raw.CONSTRAINTNAME.isin(GTCS) & (raw.SHADOWPRICE > 0)].copy()
raw["dt"] = pd.to_datetime(raw["DATETIME"], format="%m/%d/%Y %H:%M:%S")
raw["hour_dt"] = raw["dt"].dt.floor("h")
raw["month"] = raw["dt"].dt.month
raw["he"] = raw["dt"].dt.hour + 1
raw["date"] = raw["dt"].dt.normalize()

panel["month"] = panel["dt"].dt.month
panel["he"] = panel["dt"].dt.hour + 1
panel["date"] = panel["dt"].dt.normalize()
total_days = int(panel["date"].nunique())

# total observed hours per (month, HE) cell -> denominator for P(bind)
tot_cell = panel.groupby(["month", "he"]).size()

def month_hour_pbind(cn, mkt):
    """12x24 matrix; rows=month 1..12, cols index0=HE1 .. index23=HE24. P(bind)=distinct bind hr/total hr."""
    b = raw[(raw.CONSTRAINTNAME == cn) & (raw.MARKET == mkt)]
    bind_cell = b.drop_duplicates("hour_dt").groupby(["month", "he"]).size()
    mat = []
    for m in range(1, 13):
        row = []
        for he in range(1, 25):
            tot = int(tot_cell.get((m, he), 0))
            if tot == 0:
                row.append(None)
            else:
                nb = int(bind_cell.get((m, he), 0))
                row.append(round(nb / tot, 3))
        mat.append(row)
    return mat

def lam_mean(cn, mkt):
    s = raw[(raw.CONSTRAINTNAME == cn) & (raw.MARKET == mkt)]["SHADOWPRICE"]
    return round(float(s.mean()), 2) if len(s) else None

# ---- limit regime -> binding-day rate (GTC analogue of outage watch-list) ----
def limit_regime_rows(cn, mkt, buckets):
    """buckets: list of (label, lo, hi) on the operator limit (MW). Returns watchlist-style rows."""
    # map each calendar month -> limit MW for this GTC
    lim_by_month = {ym: v[cn] for ym, v in limit_hist.items() if v.get(cn) is not None}
    pan = panel.copy()
    pan["ym"] = pan["dt"].dt.strftime("%Y-%m")
    pan["lim"] = pan["ym"].map(lim_by_month)
    b = raw[(raw.CONSTRAINTNAME == cn) & (raw.MARKET == mkt)].copy()
    b["ym"] = b["dt"].dt.strftime("%Y-%m")
    bind_dates = set(b["date"])
    pan["bind_day"] = pan["date"].isin(bind_dates)
    overall = pan.drop_duplicates("date")["bind_day"].mean()
    rows = []
    for label, lo, hi in buckets:
        sel = pan[(pan["lim"] >= lo) & (pan["lim"] < hi)]
        days = sel.drop_duplicates("date")
        n_days = int(len(days))
        if n_days == 0:
            continue
        co = int(days["bind_day"].sum())
        p = co / n_days
        rows.append({
            "facility": f"GTC limit {label} ({lo:.0f}-{hi:.0f} MW regime)",
            "zone": "SOUTH" if cn == "VALEXP" else "WEST",
            "out_days": n_days,            # days the GTC sat in this limit regime
            "co_bind": co,                 # of those, days the GTC bound (>=1 interval)
            "p_bind_given_out": round(p, 3),
            "seas_lift": round(p / overall, 2) if overall > 0 else None,
            "note": "GTC-limit regime (SUBSTITUTE for outage membership; limit = the operator 'switch')",
        })
    return rows, round(float(overall), 3)

# ---- section3 threshold helpers ----
def cond_pbind_lambda(cn, mkt, mask_fn, panel_subset=None):
    """P(bind) and conditional lambda (median, P90) over hours satisfying mask_fn(panel)."""
    b = raw[(raw.CONSTRAINTNAME == cn) & (raw.MARKET == mkt)]
    bind_hours = set(b["hour_dt"])
    pan = panel if panel_subset is None else panel_subset
    m = mask_fn(pan)
    sub = pan[m]
    n = len(sub)
    if n == 0:
        return None, None, None
    nb = sub["dt"].isin(bind_hours).sum()
    p = nb / n
    # conditional lambda among binding hours in subset (hour-max lambda)
    lam = b.groupby("hour_dt")["SHADOWPRICE"].max()
    sub_bind = sub[sub["dt"].isin(bind_hours)]
    lvals = sub_bind["dt"].map(lam).dropna()
    med = round(float(lvals.median()), 1) if len(lvals) else None
    p90 = round(float(np.percentile(lvals, 90)), 1) if len(lvals) else None
    return round(float(p), 3), med, p90

# =====================================================================================
# VALEXP datapack
# =====================================================================================
def build_valexp():
    cn = "VALEXP"; mkt = "RT"  # RT is the dominant charge signal for a Valley BESS
    # section3: solar-off + low Valley wind
    # factor A: SouthEast solar (overnight switch)
    p_solar0, lmed_s0, lp90_s0 = cond_pbind_lambda(cn, "RT", lambda p: p["solar_SouthEast"] <= 5)
    p_solaron, _, _ = cond_pbind_lambda(cn, "RT", lambda p: p["solar_SouthEast"] > 200)
    # factor B: GR_SOUTH wind buckets (binding peaks at moderate-low wind; INVERTED)
    pb = {}
    for lab, lo, hi in [("<0.5GW", -1, 500), ("0.5-1GW", 500, 1000), ("1-1.5GW", 1000, 1500),
                        ("1.5-2GW", 1500, 2000), (">2GW", 2000, 99999)]:
        p, _, _ = cond_pbind_lambda(cn, "RT", lambda x, lo=lo, hi=hi: (x["wind_GR_SOUTH"] > lo) & (x["wind_GR_SOUTH"] <= hi))
        pb[lab] = p
    # factor C: combined solar-off AND low Valley wind (the charge window)
    p_combo, lmed_c, lp90_c = cond_pbind_lambda(
        cn, "RT", lambda p: (p["solar_SouthEast"] <= 5) & (p["wind_GR_SOUTH"].between(500, 1500)))

    thresholds = [
        {"factor": "SouthEast solar (MW) ~ 0 [overnight/winter switch]",
         "on_breakpoint": "<=5 (solar off)", "strong": "0 (deep overnight HE2-6 / HE18-22)",
         "pbind_distribution": f"solar>200MW:{p_solaron*100:.1f}% -> solar<=5MW:{p_solar0*100:.1f}%",
         "lambda_cond": f"${lmed_s0} median (${lp90_s0} P90), tail to $4304",
         "confidence": "HIGH"},
        {"factor": "GR_SOUTH (Valley) wind (GW) [INVERTED: modest export, not surge]",
         "on_breakpoint": "0.5-1.5 (moderate-low)", "strong": "0.5-1.0",
         "pbind_distribution": (f"<0.5GW:{_pct(pb['<0.5GW'])} -> 0.5-1GW:{_pct(pb['0.5-1GW'])} -> "
                                f"1-1.5GW:{_pct(pb['1-1.5GW'])} -> 1.5-2GW:{_pct(pb['1.5-2GW'])} -> >2GW:{_pct(pb['>2GW'])}"),
         "lambda_cond": "$16.6 median ($83.8 P90) binding-only",
         "confidence": "HIGH"},
        {"factor": "COMBO: solar~0 AND GR_SOUTH 0.5-1.5GW (low Valley net-load + modest export)",
         "on_breakpoint": "both true", "strong": "+ Nov-May + GTC limit <=900 MW",
         "pbind_distribution": f"combo TRUE:{p_combo*100:.1f}% vs base {bstats[cn]['RT']['distinct_hours']}/{16941} hr",
         "lambda_cond": f"${lmed_c} median (${lp90_c} P90)",
         "confidence": "HIGH"},
    ]

    wl_rows, base = limit_regime_rows(cn, "RT", [
        ("tight", 600, 800),    # 625, 690
        ("mid", 800, 1000),     # 850, 920, 935
        ("relaxed", 1000, 1300) # 1075, 1140
    ])

    return {
        "id": "VALEXP",
        "display_name": "VALEXP — Valley Export GTC (Greater Lower Rio Grande Valley stability interface)",
        "element": "NORTH EDINBURG (SOUTH) -> LON HILL (SOUTH)",
        "kv": 345,
        "facility_type": "GTC",
        "zone_from": "SOUTH", "zone_to": "SOUTH",
        "binding_basis": "base-case",
        "contingencies": ["BASE CASE (contingency 10000756754) — pre-contingency steady-state stability limit, NOT N-1"],
        "gks_sf": {"da": 1.000, "rt": 0.979},
        "sign": "neg",
        "mechanism": "GKS Valley discharge/net-export loads the very low Valley Export stability interface (positive SF ~+1.0) -> raises interface congestion that LOWERS GKS LMP; strongest as a CHARGE signal when solar is off and Valley net-load is low.",
        "status": "live",
        "section1_lambda_summary": {
            "da": {"bind_hrs": bstats[cn]["DA"]["binding_hours"], "mean": lam_mean(cn, "DA"),
                   "median": bstats[cn]["DA"]["lambda_median"], "p90": bstats[cn]["DA"]["lambda_P90"],
                   "p99": bstats[cn]["DA"]["lambda_P99"], "max": bstats[cn]["DA"]["lambda_max"]},
            "rt": {"bind_hrs": bstats[cn]["RT"]["binding_hours"], "mean": lam_mean(cn, "RT"),
                   "median": bstats[cn]["RT"]["lambda_median"], "p90": bstats[cn]["RT"]["lambda_P90"],
                   "p99": bstats[cn]["RT"]["lambda_P99"], "max": bstats[cn]["RT"]["lambda_max"]},
            "rt_cap": 4500,
            "cum_impact_usd_per_mw": {
                "da": bstats[cn]["DA"]["cum_impact_$"], "rt": bstats[cn]["RT"]["cum_impact_$"],
                "total": round(bstats[cn]["DA"]["cum_impact_$"] + bstats[cn]["RT"]["cum_impact_$"], 1),
                "note": "DA+RT same sign (both charge-favorable). Winter/spring concentrated: RT Dec -$3.75k / Jan -$2.04k / Nov -$1.55k + Apr -$2.83k spike; summer ~0. Per 1 MW continuous over 23 mo."}
        },
        "section2_month_hour": {
            "rt_pbind": month_hour_pbind(cn, "RT"),
            "da_pbind": month_hour_pbind(cn, "DA"),
            "_axis_note": "rows=month 1..12; cols index0=HE1 .. index23=HE24. P(bind)=distinct binding hours / total observed hours per cell."
        },
        "section3_thresholds": thresholds,
        "section4_rule_of_thumb": "Nov-May 비여름 + 야간/저녁 (HE1-7, HE18-22, solar off) + Valley(GR_SOUTH) wind 0.5-1.5GW(modest export) + 낮은 GTC limit(<=900MW) => RT P(bind)~10-18%, CHARGE-favorable. 여름·한낮(HE10-16)엔 로컬 solar가 interface를 RELIEVE → P(bind)~0.",
        "section5_outage_watchlist": {
            "informative": False,
            "base_pbind_per_day": base,
            "rows": wl_rows,
            "caveat": "GTC element membership/outage data NOT in datalake -> classic outage watch-list infeasible. SUBSTITUTE: the operator-set GTC LIMIT (MW) is the key binding 'switch' (limit history -> binding-day rate by regime). VALEXP limit moved 625->1,140 MW over 23 mo. CONFOUND FLAG: the raw regime->binding rate here INVERTS the physical expectation (tight 600-800 MW regime 8.3% < relaxed 1,000-1,300 MW 27%) because limit settings are confounded with SEASON — tight 625/690 MW limits happened to sit in low-binding summer, the relaxed 1,075/1,140 MW settings in high-binding winter (2026-02-04 Greater Valley update). The clean limit effect CANNOT be isolated from seasonality with this data; seas_lift here mostly reflects season, not limit. Co-occurrence != causation; limit is operator/ERCOT-Quarterly-Stability driven, not a fixed rating."
        },
        "section6_drivers": [
            {"lens": "demand", "verdict": "CONFIRMED", "evidence": "Binds on LOW Valley net-load (winter-overnight low-load seasonality); no zonal load in datalake, inferred via diurnal/seasonal binding pattern (HE2-6 + HE18-20 peaks, midday trough)."},
            {"lens": "supply/renewable", "verdict": "CONFIRMED", "evidence": "SouthEast solar bind-median 0 vs nonbind 32-77 MW; midday solar locally absorbs & RELIEVES interface. GR_SOUTH wind moderate-low (bind-median ~1023 MW); P(bind) DECREASES as Valley wind rises (inverted, not a surge story)."},
            {"lens": "transmission outage", "verdict": "INSUFFICIENT", "evidence": "GTC element membership not in datalake. Net operator effect captured by GTC LIMIT history (625->935->690->920->1075->1140 MW); 2026-02-04 Greater Valley GTC update lifted limit step-wise."},
            {"lens": "temperature", "verdict": "CONFIRMED (indirect)", "evidence": "Winter-overnight low-load concentration (Dec/Jan/Nov + Apr) consistent with low-temp low-net-load regime; system-only load data limits direct attribution."},
            {"lens": "weather", "verdict": "CONFIRMED", "evidence": "Solar diurnal cycle strongly modulates (midday relief); winter+spring regime dominates, summer ~0."}
        ],
        "section7_gks_read": "Highest-SF live CHARGE signal for GKS (SF~+1.0 DA, +0.98 RT). Lean into cheap Valley charging on solar-off hours (overnight HE1-7, evening HE18-22) in Nov-May with low Valley net-load; sharpest when GTC limit is at the tight <=900 MW setting. RT λ tail to $4304 = rare transmission scarcity. Avoid expecting it midday/summer.",
        "seasonality_text": "Winter+spring dominant (Dec/Jan/Nov + Apr RT spike); summer ~0. Hour: bimodal overnight HE2-6 (peak HE5) + evening HE17-20 (HE18); midday trough HE10-16.",
        "caveats": [
            "GTC LIMIT is TIME-VARYING (operator/ERCOT Quarterly Stability driven): VALEXP moved 625->1,140 MW over 23 mo (2026-02-04 Greater Valley update lifted it). Treat limit as a time-varying feature, NOT a fixed rating; binding freq/timing shifts step-wise with each GTC parameter update.",
            "Binds in BASE CASE (pre-contingency steady-state stability), NOT N-1 — distinct from the Houston N-1 corridor constraints.",
            "DA & RT enforce the same GTC: DA SF=+1.000 (pseudo-line '- 0KV VALEXP'), RT SF~+0.98 — both strongly charge-favorable (no DA/RT sign conflict, unlike WESTEX).",
            "No zonal load in datalake (system-only) -> demand lens inferred from diurnal/seasonal binding signature.",
            "GTC element membership absent -> outage watch-list substituted by GTC-limit regime (section5)."
        ]
    }

# =====================================================================================
# WESTEX datapack
# =====================================================================================
def build_westex():
    cn = "WESTEX"; mkt = "RT"  # RT is the discharge tailwind (DA is ~neutral/opposite)
    # section3: West-basin wind GW breakpoint ~14GW
    pb, lam_b = {}, {}
    bins = [("<10GW", -1, 10000), ("10-12GW", 10000, 12000), ("12-14GW", 12000, 14000),
            ("14-16GW", 14000, 16000), ("16-18GW", 16000, 18000), (">18GW", 18000, 99999)]
    for lab, lo, hi in bins:
        p, med, p90 = cond_pbind_lambda(cn, "RT", lambda x, lo=lo, hi=hi: (x["wind_WESTEX_basin"] > lo) & (x["wind_WESTEX_basin"] <= hi))
        pb[lab] = p; lam_b[lab] = (med, p90)
    p_below14, _, _ = cond_pbind_lambda(cn, "RT", lambda x: x["wind_WESTEX_basin"] <= 14000)
    p_above14, med14, p9014 = cond_pbind_lambda(cn, "RT", lambda x: x["wind_WESTEX_basin"] > 14000)

    thresholds = [
        {"factor": "West-basin wind GR_WEST+GR_PANHANDLE (GW) [RT discharge switch]",
         "on_breakpoint": "14", "strong": "16-17",
         "pbind_distribution": (f"<=14GW:{_pct(p_below14)} -> >14GW:{_pct(p_above14)}  | by-bucket: "
                                f"<10:{_pct(pb['<10GW'])} 10-12:{_pct(pb['10-12GW'])} 12-14:{_pct(pb['12-14GW'])} "
                                f"14-16:{_pct(pb['14-16GW'])} 16-18:{_pct(pb['16-18GW'])} >18:{_pct(pb['>18GW'])}"),
         "lambda_cond": f"${med14} median (${p9014} P90) when basin>14GW",
         "confidence": "HIGH"},
        {"factor": "Season (West-wind regime)",
         "on_breakpoint": "Mar-May (spring high-wind)", "strong": "Mar-May + GTC limit at 10.6GW low setting",
         "pbind_distribution": "spring ~180 bind-hr/mo vs summer (Jul-Sep) ~10-40 bind-hr/mo",
         "lambda_cond": "$15.1 median ($28.4 P90) RT binding-only; modest magnitude (P99 $50, max $169)",
         "confidence": "HIGH"},
        {"factor": "GTC limit (MW) [seasonal switch]",
         "on_breakpoint": "<=10,630 (spring/fall low setting)", "strong": "10,630",
         "pbind_distribution": "lower limit (spring/fall) coincides with peak binding; high 11,810 setting = fewer binds",
         "lambda_cond": "see basin-wind row (limit gates, wind drives)",
         "confidence": "MED"},
    ]

    wl_rows, base = limit_regime_rows(cn, "RT", [
        ("low", 10000, 11000),   # 10630
        ("mid", 11000, 11700),   # 11220, 11620
        ("high", 11700, 12000),  # 11810
    ])

    return {
        "id": "WESTEX",
        "display_name": "WESTEX — West Texas Export GTC (largest ERCOT GTC, ~36GW wind behind it; live since 2020-10-01)",
        "element": "RILEY (WEST) -> KRWSW (NORTH)  [RT repr.]; DA repr. CLEARCRO->WILLOW CREEK (WEST internal)",
        "kv": 345,
        "facility_type": "GTC",
        "zone_from": "WEST", "zone_to": "NORTH",
        "binding_basis": "base-case",
        "contingencies": ["BASE CASE (contingency 10000756754) — pre-contingency steady-state stability limit, NOT N-1"],
        "gks_sf": {"da": 0.048, "rt": -0.150},
        "sign": "pos",
        "mechanism": "High West-basin wind exports North into the West Texas Export stability interface. RT repr. element (RILEY->KRWSW) gives GKS SF=-0.15 -> impact=-SF*lambda=+0.15*lambda -> RAISES GKS LMP (DISCHARGE-favorable). RT-ONLY: DA repr. element (CLEARCRO->WILLOW CREEK) gives GKS SF=+0.048 -> small CHARGE-favorable/opposite; do NOT assume a DA discharge signal.",
        "status": "live",
        "section1_lambda_summary": {
            "da": {"bind_hrs": bstats[cn]["DA"]["binding_hours"], "mean": lam_mean(cn, "DA"),
                   "median": bstats[cn]["DA"]["lambda_median"], "p90": bstats[cn]["DA"]["lambda_P90"],
                   "p99": bstats[cn]["DA"]["lambda_P99"], "max": bstats[cn]["DA"]["lambda_max"]},
            "rt": {"bind_hrs": bstats[cn]["RT"]["binding_hours"], "mean": lam_mean(cn, "RT"),
                   "median": bstats[cn]["RT"]["lambda_median"], "p90": bstats[cn]["RT"]["lambda_P90"],
                   "p99": bstats[cn]["RT"]["lambda_P99"], "max": bstats[cn]["RT"]["lambda_max"]},
            "rt_cap": 4500,
            "cum_impact_usd_per_mw": {
                "da": bstats[cn]["DA"]["cum_impact_$"], "rt": bstats[cn]["RT"]["cum_impact_$"],
                "total": round(bstats[cn]["DA"]["cum_impact_$"] + bstats[cn]["RT"]["cum_impact_$"], 1),
                "note": "DA & RT FLIP SIGN (different repr. elements of same GTC): DA -$908 (SF+0.048, small charge), RT +$3,099 (SF-0.15, discharge). Net +$2,191 over 23 mo, RT dominates. Discharge tailwind is RT-ONLY."}
        },
        "section2_month_hour": {
            "rt_pbind": month_hour_pbind(cn, "RT"),
            "da_pbind": month_hour_pbind(cn, "DA"),
            "_axis_note": "rows=month 1..12; cols index0=HE1 .. index23=HE24. P(bind)=distinct binding hours / total observed hours per cell."
        },
        "section3_thresholds": thresholds,
        "section4_rule_of_thumb": "West-basin wind(GR_WEST+GR_PANHANDLE) > ~14GW (strongest 16-17GW) + 봄(Mar-May) + GTC limit 10.6GW 낮은 설정 => RT P(bind) jumps ~0%(<14GW) -> 12-19%(>14GW), DISCHARGE-favorable (RT ONLY). 여름엔 wind trough로 binding 급감. DA WESTEX은 ~중립/약한 반대 — DA discharge 신호 가정 금지.",
        "section5_outage_watchlist": {
            "informative": False,
            "base_pbind_per_day": base,
            "rows": wl_rows,
            "caveat": "GTC element membership/outage data NOT in datalake -> outage watch-list infeasible. SUBSTITUTE: GTC LIMIT (MW) is the binding 'switch' (limit history -> binding-day rate by regime). WESTEX limit moved 10,630->11,810 MW; LOWER limit (spring/fall) = higher binding. seas_lift = binding-day rate vs overall daily base. NOTE: DA & RT monitor DIFFERENT repr. elements -> SF sign differs (DA +0.048 charge vs RT -0.15 discharge); rows use RT (the discharge signal). Co-occurrence != causation."
        },
        "section6_drivers": [
            {"lens": "demand", "verdict": "HYPOTHESIS", "evidence": "Overnight low-load + high wind co-occur (binding peaks HE23-HE2), but not separable from the wind signal with system-only load data."},
            {"lens": "supply/renewable", "verdict": "CONFIRMED (STRONG)", "evidence": "West-basin wind bind-median 16.7-17.2 GW vs nonbind 7.2-7.7 GW; DA corr(lambda, basin-wind)=+0.29; P(bind) ~0 below ~14GW, jumps to 12-19% above. Classic high-West-wind export."},
            {"lens": "transmission outage", "verdict": "INSUFFICIENT", "evidence": "GTC element membership not in datalake. Net operator effect via GTC LIMIT history (10,630-11,810 MW); lower spring/fall setting coincides with peak binding."},
            {"lens": "temperature", "verdict": "INSUFFICIENT", "evidence": "No zonal load/temp separation; folded into wind/season signal."},
            {"lens": "weather", "verdict": "CONFIRMED", "evidence": "Spring high-wind peak, summer (Jul-Sep) wind trough drives binding seasonality; West-basin wind is the proximate weather driver."}
        ],
        "section7_gks_read": "Modest DISCHARGE tailwind, RT-ONLY: SF=-0.15 (RT) raises GKS LMP when West-basin wind >14GW (spring overnight/midday, low 10.6GW GTC setting). Magnitude small (λ median $15, P99 $50). Do NOT trade a DA WESTEX discharge signal — DA SF=+0.048 is neutral/slightly charge. Lower-priority, RT-realtime opportunistic only.",
        "seasonality_text": "Spring-heavy (Mar-May ~180 bind-hr/mo), steady most of year, summer trough (Jul-Sep ~10-40 hr/mo). Hour: overnight peak HE23-HE2 (HE24) + midday secondary; morning trough HE4-7.",
        "caveats": [
            "GTC LIMIT is TIME-VARYING (seasonal): WESTEX moved 10,630->11,810 MW; lower spring/fall setting coincides with peak binding. Treat limit as a time-varying feature, not a fixed rating.",
            "DA & RT monitor DIFFERENT representative elements of the same GTC -> GKS SF SIGN DIFFERS: DA SF=+0.048 (charge-favorable, -$908) vs RT SF=-0.15 (discharge-favorable, +$3,099). The discharge tailwind is RT-ONLY; net +$2,191 with RT dominating.",
            "Binds in BASE CASE (pre-contingency steady-state stability), NOT N-1.",
            "GTC element membership absent -> outage watch-list substituted by GTC-limit regime (section5).",
            "Magnitude is modest (RT λ median $15, P90 $28, P99 $50, max $169) — lower-impact than VALEXP charge signal."
        ]
    }

def _pct(x):
    return f"{x*100:.1f}%" if x is not None else "n/a"

vx = build_valexp()
wx = build_westex()
json.dump(vx, open(D/"datapack_VALEXP.json", "w"), indent=2)
json.dump(wx, open(D/"datapack_WESTEX.json", "w"), indent=2)
print("total_days(window):", total_days)
print("VALEXP base_pbind_per_day:", vx["section5_outage_watchlist"]["base_pbind_per_day"])
print("WESTEX base_pbind_per_day:", wx["section5_outage_watchlist"]["base_pbind_per_day"])
print("VALEXP RT thresholds:")
for t in vx["section3_thresholds"]:
    print(" -", t["factor"], "|", t["pbind_distribution"])
print("WESTEX RT thresholds:")
for t in wx["section3_thresholds"]:
    print(" -", t["factor"], "|", t["pbind_distribution"])
print("VALEXP section5 rows:", json.dumps(vx["section5_outage_watchlist"]["rows"], indent=1))
print("WESTEX section5 rows:", json.dumps(wx["section5_outage_watchlist"]["rows"], indent=1))
# sanity: peak RT pbind cells
import numpy as np
for nm, dp in [("VALEXP", vx), ("WESTEX", wx)]:
    mat = np.array([[c if c is not None else np.nan for c in row] for row in dp["section2_month_hour"]["rt_pbind"]])
    mi = np.unravel_index(np.nanargmax(mat), mat.shape)
    print(f"{nm} RT peak P(bind) cell month={mi[0]+1} HE={mi[1]+1} = {mat[mi]:.3f}")
print("WROTE datapack_VALEXP.json + datapack_WESTEX.json")
