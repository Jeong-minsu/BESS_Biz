"""Assemble derived/datapack_E_PASP.json per DATAPACK_SCHEMA.md.
REUSE: seasonality_clusterC.json (month x hour), gks-deepdive plan (lambda summary, drivers,
rule-of-thumb, gks read). NEW-COMPUTE: section2 P(bind) matrices, section3 evening-window
thresholds (driver_panel_clusterC.parquet), section5 outage watch-list (cached SOUTH-345
outage panel + E_PASP daily binding). REAL data only.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]                       # .../2026-06-09_gks-congestion-impact
DERIVED = ROOT / "derived"
HOUSTON_DERIVED = ROOT.parent / "2026-06-09_houston-constraint-validation" / "derived"

panel = pd.read_parquet(DERIVED / "driver_panel_clusterC.parquet")          # hourly, dt index
seas = json.loads((DERIVED / "seasonality_clusterC.json").read_text())

# ---- n_days per calendar month (denominator for P(bind)) -------------------
panel = panel.copy()
panel["date"] = pd.to_datetime(panel.index).normalize()
ndays = panel.groupby("month")["date"].nunique().reindex(range(1, 13)).fillna(0).astype(int)

def grid(constraint, market, metric):
    for g in seas["grids"]:
        if g["constraint"] == constraint and g["market"] == market and g["metric"] == metric:
            return np.array(g["matrix"], dtype=float)
    raise KeyError((constraint, market, metric))

def pbind_matrix(constraint, market):
    hrs = grid(constraint, market, "hrs")            # rows month1..12, cols hour0..23 (HE)
    den = ndays.values.reshape(-1, 1).astype(float)
    den[den == 0] = np.nan
    p = hrs / den
    return np.round(np.clip(p, 0, 1), 3).tolist()

da_pbind = pbind_matrix("E_PASP", "DA")
rt_pbind = pbind_matrix("E_PASP", "RT")

# ---- section3 thresholds: evening HE17-21 conditional P(bind)+lambda --------
# panel 'hour' is HE 1..24 ; evening peak window HE17-21
ev = panel[panel["hour"].between(17, 21)].copy()
b = ev["E_PASP_bind"].astype(int)
lam = ev["E_PASP_lam"]

def cond(mask):
    n = int(mask.sum())
    if n == 0:
        return None, None, 0
    sub_b = b[mask]
    p = float(sub_b.mean())
    lm = lam[mask & (b == 1)]
    med = float(lm.median()) if len(lm) else None
    return round(p, 3), (round(med, 1) if med is not None else None), n

# southwind / coastalwind in MW; load in MW -> express GW
sw = ev["wind_south"]; cw = ev["wind_coastal"]; ld = ev["load_south"]

def dist_str(series, bins, labels):
    parts = []
    for (lo, hi), lab in zip(bins, labels):
        p, med, n = cond((series >= lo) & (series < hi))
        parts.append(f"{lab}:{'' if p is None else str(round(p*100))+'%'}")
    return " -> ".join(parts)

# South wind breakpoints
sw_dist = dist_str(sw, [(0, 1000), (1000, 1500), (1500, 2500), (2500, 1e9)],
                   ["<1.0GW", "1.0-1.5", "1.5-2.5", ">2.5"])
sw_p15, sw_l15, _ = cond(sw >= 1500)
# Coastal wind
cw_dist = dist_str(cw, [(0, 500), (500, 1000), (1000, 1500), (1500, 1e9)],
                   ["<0.5GW", "0.5-1.0", "1.0-1.5", ">1.5"])
cw_p10, cw_l10, _ = cond(cw >= 1000)
# South load
ld_dist = dist_str(ld, [(0, 4000), (4000, 5000), (5000, 6000), (6000, 1e9)],
                   ["<4GW", "4-5", "5-6", ">6"])
ld_p5, ld_l5, _ = cond(ld >= 5000)
# combined evening high setup
combo_mask = (sw >= 1500) & (ld >= 5000)
combo_p, combo_l, combo_n = cond(combo_mask)
ev_base_p, ev_base_l, ev_n = cond(pd.Series(True, index=ev.index))

# detect whether panel lambda is DA or RT scale (DA med ~13.6, RT med ~61)
lam_med_bind = float(lam[b == 1].median())

thresholds = [
    {"factor": "South wind (GW), evening HE17-21", "on_breakpoint": "1.5", "strong": "2.5",
     "pbind_distribution": sw_dist, "lambda_cond": f"${sw_l15} med @>=1.5GW",
     "confidence": "HIGH"},
    {"factor": "Coastal wind (GW), evening HE17-21", "on_breakpoint": "1.0", "strong": "1.5",
     "pbind_distribution": cw_dist, "lambda_cond": f"${cw_l10} med @>=1.0GW",
     "confidence": "HIGH"},
    {"factor": "South load (GW), evening HE17-21", "on_breakpoint": "5.0", "strong": "6.0",
     "pbind_distribution": ld_dist, "lambda_cond": f"${ld_l5} med @>=5GW",
     "confidence": "MEDIUM"},
    {"factor": "Combined: South wind>=1.5GW AND South load>=5GW, evening HE17-21",
     "on_breakpoint": "both", "strong": "both",
     "pbind_distribution": f"evening-base:{round(ev_base_p*100)}% -> combo:{round(combo_p*100)}% (n={combo_n})",
     "lambda_cond": f"${combo_l} med", "confidence": "MEDIUM"},
]

# ---- section5 outage watch-list: SOUTH 345 outage -> E_PASP binding lift ----
opanel = pd.read_parquet(HOUSTON_DERIVED / "outage_panel_345_houston_south.parquet")
opanel = opanel[opanel["FROMZONE"] == "SOUTH"].copy()
opanel["date"] = pd.to_datetime(opanel["date"]).dt.normalize()

# E_PASP daily binding flag (regime = node window)
daily = panel.groupby("date")["E_PASP_bind"].max()        # any-hour bind that day
daily_cum = panel.groupby("date").apply(
    lambda d: float((d["E_PASP_lam"].fillna(0)).sum()), include_groups=False)  # daily DA lambda-hours (severity proxy)
lo = daily.index.min(); hi = daily.index.max()
have = set(opanel["date"].unique())
universe = pd.DatetimeIndex([d for d in daily.index if d in have])
bind_day = (daily.reindex(universe) > 0).astype(int)
base = float(bind_day.mean())
# seasonality (month) base
mon = pd.Series(universe.month, index=universe)
month_base = bind_day.groupby(mon).mean()
day_exp = mon.map(month_base)
# severe-day flag = top-decile daily lambda-hours (weakening signature, not frequency)
sev_thresh = float(daily_cum.reindex(universe).quantile(0.90))
sev_day = (daily_cum.reindex(universe) >= sev_thresh).astype(int)
base_sev = float(sev_day.mean())
sev_exp = mon.map(sev_day.groupby(mon).mean())

p = opanel[opanel["date"].isin(universe)].copy()
p["bind"] = p["date"].map(bind_day.to_dict()).astype(int)
p["exp"] = p["date"].map(day_exp.to_dict()).astype(float)
p["sev"] = p["date"].map(sev_day.to_dict()).astype(int)
p["sev_exp"] = p["date"].map(sev_exp.to_dict()).astype(float)

# station-level (dedupe equipment within station-day)
sd = p.drop_duplicates(["FROMSTATION", "date"])
agg = sd.groupby("FROMSTATION").agg(
    out_days=("date", "nunique"),
    co_bind=("bind", "sum"),
    exp_bind=("exp", "sum"),
    co_sev=("sev", "sum"),
    exp_sev=("sev_exp", "sum"),
).reset_index()
agg["p_bind_given_out"] = agg.co_bind / agg.out_days
agg["seas_lift"] = agg.co_bind / agg.exp_bind.replace(0, np.nan)
agg["p_sev_given_out"] = agg.co_sev / agg.out_days
agg["sev_seas_lift"] = agg.co_sev / agg.exp_sev.replace(0, np.nan)
agg = agg[agg.out_days >= 15]

# Jan-2026 episode (Jan 24-26): which SOUTH 345 stations were OUT
epi = pd.to_datetime(["2026-01-24", "2026-01-25", "2026-01-26"])
epi_out = sorted(opanel[opanel["date"].isin(epi)]["FROMSTATION"].unique().tolist())

print("=== E_PASP outage-lift diagnostics ===")
print(f"regime {lo.date()}..{hi.date()}  universe days={len(universe)}  base P(bind/day)={base:.3f}  base P(severe/day)={base_sev:.3f}")
print(f"panel lambda median (bind, evening) = {lam_med_bind:.1f}  (DA-scale ~13.6 / RT-scale ~61)")
print(f"evening base P(bind)={ev_base_p}  combo P(bind)={combo_p} n={combo_n}")
print("\n-- SEVERITY-lift top (P(severe-day|out)/seasonal, min 15 out-days, min 4 co-sev) --")
sv = agg[agg.co_sev >= 4].sort_values("sev_seas_lift", ascending=False).head(12)
print(sv[["FROMSTATION", "out_days", "co_bind", "p_bind_given_out", "seas_lift", "co_sev", "p_sev_given_out", "sev_seas_lift"]].to_string(index=False))
print("\n-- FREQUENCY-lift top --")
fr = agg[agg.co_bind >= 10].sort_values("seas_lift", ascending=False).head(10)
print(fr[["FROMSTATION", "out_days", "co_bind", "p_bind_given_out", "seas_lift"]].to_string(index=False))
print(f"\nJan 24-26 2026 SOUTH-345 stations OUT ({len(epi_out)}): {epi_out}")

# assemble outage rows (severity-lift ranked; honest informative flag)
sv_rows = []
for _, r in agg[agg.co_sev >= 4].sort_values("sev_seas_lift", ascending=False).head(6).iterrows():
    sv_rows.append({
        "facility": r.FROMSTATION, "zone": "SOUTH",
        "out_days": int(r.out_days), "co_bind": int(r.co_bind),
        "p_bind_given_out": round(float(r.p_bind_given_out), 3),
        "seas_lift": round(float(r.seas_lift), 2),
        "p_severe_given_out": round(float(r.p_sev_given_out), 3),
        "severity_seas_lift": round(float(r.sev_seas_lift), 2),
        "note": "severity-lift = P(top-decile-lambda day | out)/seasonal-expected"
    })

# informative if any severity-lift meaningfully >1.3 with support
informative = bool((agg[agg.co_sev >= 4]["sev_seas_lift"] > 1.3).any())

section5 = {
    "informative": informative,
    "base_pbind_per_day": round(base, 3),
    "base_severe_per_day": round(base_sev, 3),
    "method": "SOUTH-345 outage daily snapshot (HE13) x E_PASP daily DA binding; freq-lift AND severity-lift (top-decile daily lambda-hours, captures weakening parallel-345 derate, not frequency).",
    "rows": sv_rows,
    "jan2026_episode": {
        "dates": ["2026-01-24", "2026-01-25", "2026-01-26"],
        "south_345_stations_out": epi_out,
        "note": "candidate parallel-345 standing derate(s) co-incident with the 3-day 24/24-hr lambda->$4.5k episode (=31% of DA cum). Co-occurrence, NOT confirmed contingency membership; E_PASP is a BASE-CASE interface so a derate is a standing parallel-345 outage, not an N-1 member."
    },
    "caveat": "E_PASP binds most days (base P(bind/day) high) -> frequency-lift is near-uninformative by construction; severity-lift (top-decile lambda days) is the discriminating signal. Co-occurrence != causation; lift = weakening-outage signature, not NMMS contingency membership.",
}

# ---- assemble datapack -----------------------------------------------------
dp = {
    "id": "E_PASP",
    "display_name": "E_PASP — PAWNEE-CALAVERAS 345 interface",
    "element": "PAWNEE -> CALAVERAS",
    "kv": 345,
    "facility_type": "interface",
    "zone_from": "SOUTH", "zone_to": "SOUTH",
    "binding_basis": "base-case",
    "contingencies": ["E_PASP (RTI base-case interface)"],
    "gks_sf": {"da": 0.244, "rt": 0.223},
    "sign": "neg",
    "mechanism": "GKS Valley/South-TX export flows north over PAWNEE->CALAVERAS, loading the San-Antonio-import interface (positive SF) -> aggravates -> prices GKS node DOWN (charge-favorable). Highest SF of the GKS NEG cluster.",
    "status": "live",
    "section1_lambda_summary": {
        "da": {"bind_hrs": 4539, "mean": 54.2, "median": 13.6, "p90": 98, "p99": 633, "max": 4566},
        "rt": {"bind_hrs": 776, "mean": 140, "median": 61, "p90": 259, "p99": 1286, "max": 3665},
        "rt_cap": 4500,
        "cum_impact_usd_per_mw": {"da": -56360, "rt": -22983, "total": -79343,
                                  "note": "DA ex-Jan2026-episode = -38858 (Jan 24-26 2026 episode = -17502 = 31% of DA cum). RT max: single $15,341 msf value is an uncorroborated outlier; rt/-corroborated peak ~$3,665."}
    },
    "section2_month_hour": {
        "rows": "month 1..12", "cols": "hour HE0..23",
        "denominator": {int(m): int(n) for m, n in ndays.items()},
        "rt_pbind": rt_pbind,
        "da_pbind": da_pbind
    },
    "section3_thresholds": thresholds,
    "section4_rule_of_thumb": "Evening HE17-21 + South/coastal wind >1.5GW + South load >5GW => P(bind)~45-56%, charge-favorable (most-negative MCC when wind AND evening load both high). Rare multi-day winter export events push lambda->$1k+.",
    "section5_outage_watchlist": section5,
    "section6_drivers": [
        {"lens": "demand", "verdict": "CONFIRMED",
         "evidence": "P(bind) 10%->47% as South load 3->7 GW; corr +0.29. Export-TO-LOAD interface: high evening San-Antonio/South load pulls South-TX gen north over PAWNEE->CALAVERAS."},
        {"lens": "supply/renewable", "verdict": "CONFIRMED",
         "evidence": "Primary driver. P(bind) 7%->40% across South wind 0->2500 MW; coastal-wind corr +0.45 (highest single driver), south-wind +0.26. >3000 MW South wind P(bind) falls (whole-region surplus). Solar corr +0.06 = INSUFFICIENT."},
        {"lens": "transmission outage", "verdict": "HYPOTHESIS",
         "evidence": "Jan 24-26 2026 = 24/24-hr 3-day bind, lambda med $206/$1061/$314, max $4,566 (=31% of DA cum). Base-case interface => signature of a STANDING parallel-345 derate on the SA-import corridor, not an N-1. See section5 episode-out list; not confirmed (co-occurrence)."},
        {"lens": "temperature", "verdict": "HYPOTHESIS",
         "evidence": "Load is the channel (San-Antonio summer/winter peaks); not separately isolated from load in this panel."},
        {"lens": "weather", "verdict": "CONFIRMED (via wind)",
         "evidence": "Coastal+South wind injection (the supply channel) is the dominant weather driver; coastal-wind corr +0.45. Solar negligible (+0.06)."}
    ],
    "section7_gks_read": "LIVE, highest-SF (+0.244 DA) charge signal of the GKS NEG cluster. Lean into cheap evening HE17-21 charging on high South/coastal-wind days; most-negative MCC when wind AND evening South load both high. Rare multi-day winter export events (lambda->$1k+) = exceptional charge value. Durable forward signal (binds continuously through 2026-06-08).",
    "seasonality_text": "Month: Jan-2026 episode-dominated, then Aug/Jul (summer wind+load); ex-episode summer-heavy. RT: May/Jan/Aug/Jul. Hour: EVENING PEAK HE17-21 (P(bind) 45-56%), overnight trough (13-17%) = South-TX wind evening-diurnal + solar gone + SA load peak.",
    "caveats": [
        "Jan-2026 -$17.5k 3-day episode (Jan 24-26) = 31% of DA cum; report ex-episode DA = -$38.9k.",
        "RTI BASE-CASE interface (GTC-like), NOT a single monitored line N-1 — different binding physics; embed interface-vs-N1 as a feature.",
        "Single $15,341 RT msf value is an uncorroborated outlier; use rt/-corroborated severity (~$3,665 peak).",
        "section5 outage lift: E_PASP binds most days -> frequency-lift near-uninformative; severity-lift used. Co-occurrence != causation, not NMMS membership.",
        "panel lambda is DA-scale (median bind/evening = %.1f); section3 lambda_cond are DA medians, not RT." % lam_med_bind
    ]
}

out = DERIVED / "datapack_E_PASP.json"
out.write_text(json.dumps(dp, indent=2))
print(f"\nwrote {out}  ({out.stat().st_size} bytes)")
