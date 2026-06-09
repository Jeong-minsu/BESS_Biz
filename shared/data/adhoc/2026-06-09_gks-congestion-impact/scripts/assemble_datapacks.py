"""Assemble per-constraint dashboard DATA PACKS for Cluster D LIVE constraints
into derived/datapack_<ID>.json per DATAPACK_SCHEMA.md.

Combines:
  - REUSED   : clusterD_stats.json (lambda summary, cum impact, contingencies, sf)
  - COMPUTED : clusterD_pbind_matrix.json   (section2)
               clusterD_wind_thresholds.json (section3)
               clusterD_outage_lift.json     (section5)
  - AUTHORED : narrative fields (drivers verdicts / rule-of-thumb / gks read /
               seasonality / caveats) sourced from the cluster-D deep-dive plan.
REAL data only. R&R = congestion (MCC) only.
"""
import json
from pathlib import Path

D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
stats = json.load(open(D / "clusterD_stats.json"))
pbind = json.load(open(D / "clusterD_pbind_matrix.json"))
wth = json.load(open(D / "clusterD_wind_thresholds.json"))
olift = json.load(open(D / "clusterD_outage_lift.json"))

GKS_SF_NOTE = "GKS_BESS_RN shift factor positive -> GKS injection aggravates Laredo/border through-flow -> lowers own LMP (charge-favorable)."


def dist_string(rows):
    """rows: [ [label, n, pbind, lam_med, lam_p90], ... ] -> compact P(bind) ladder."""
    parts = []
    for lab, n, pb, lm, l90 in rows:
        if pb is None:
            continue
        parts.append(f"{lab}GW:{round(pb*100)}%")
    return " -> ".join(parts)


def lambda_cond_string(rows):
    """summarize lambda in the two strongest-wind supported bins."""
    sup = [r for r in rows if r[2] is not None and r[3] is not None]
    if not sup:
        return None
    top = sup[-2:] if len(sup) >= 2 else sup
    seg = [f"{r[0]}GW: ${int(r[3])} med (${int(r[4])} P90)" for r in top]
    return "; ".join(seg)


def lam_summary(s):
    out = {}
    for mkt in ["da", "rt"]:
        m = s[mkt.upper()]
        out[mkt] = {"bind_hrs": int(m["binding_hours"]), "mean": m["lambda_mean"],
                    "median": m["lambda_median"], "p90": m["lambda_p90"],
                    "p99": m["lambda_p99"], "max": m["lambda_max"]}
    out["rt_cap"] = 3500
    da_c, rt_c = s["DA"]["cum_impact_$"], s["RT"]["cum_impact_$"]
    out["cum_impact_usd_per_mw"] = {"da": int(da_c), "rt": int(rt_c), "total": int(da_c + rt_c),
                                    "note": "per 1 MW continuous over full ~23-mo span (2024-07..2026-06); time-weighted (DA 1h, RT 1/12h)."}
    return out


def outage_section(oid):
    o = olift[oid]
    rows = []
    for r in o["rows"][:6]:
        rows.append({"facility": r["FROMSTATION"], "zone": r["FROMZONE"], "kv": r["kv"],
                     "out_days": r["days_out"], "co_bind": r["days_out_bind"],
                     "p_bind_given_out": round(r["p_bind_given_out"], 3),
                     "seas_lift": round(r["seas_lift"], 2),
                     "note": "SOUTH-zone planned/forced outage; not an identifiable FO-AV-LO member"})
    return {
        "informative": False,
        "base_pbind_per_day": round(o["base"], 3),
        "rows": rows,
        "caveat": ("NON-DISCRIMINATING. (1) Base P(bind/day) is high (BRUNI .64 / LOYOLA .49), structurally "
                   "compressing lift; many unrelated SOUTH-zone stations show near-identical seas_lift -> the "
                   "signal is planned-outage-season overlapping the wind-driven binding season, NOT a specific "
                   "real outage. (2) These constraints bind on a SIMULATED N-1 (FO-AV-LO family); the controlling "
                   "contingency is not a real facility-out event, so real-outage co-occurrence cannot attribute it. "
                   "(3) CRR Network Model (authoritative contingency membership) not accessible. "
                   "co-occurrence != causation."),
    }


# ---- authored narrative per constraint --------------------------------------
NARR = {
    "BRUNI_69_1": dict(
        display_name="BRUNI_69_1 — BRUNI 138/69 kV autotransformer (Webb Co., Laredo area)",
        element="BRUNI 138 kV station (138/69 autotransformer; '_69_1' = low-side tag)",
        kv=138, facility_type="xfmr",
        contingencies=["MFOAVLO5", "DFOAVLO5", "MLOBFOR5", "MLOFOAV5", "DLOFOAV5 (FO-AV-LO Laredo N-1/N-2 group)"],
        mechanism="GKS deep-South injection adds to South-Texas export through the BRUNI 138/69 autotransformer; positive SF -> post-contingency overload aggravated -> own LMP pushed down (charge-favorable).",
        s3_factor="South wind (GW), overnight HE22-07",
        s3_on="1.0", s3_strong="2.5", s3_conf="HIGH",
        s3_note="Clean monotonic: P(bind) 2%@<0.5GW -> 57%@>2.5GW in the overnight window; lambda also scales with wind.",
        rule="Overnight HE22-07 + GR_SOUTH wind >2 GW + FO-AV-LO Laredo contingency active => P(bind)~44-57%, charge-favorable; tiny SF (~0.013) but very high lambda (transformer cap-outs, RT to $3500).",
        drivers=[
            {"lens": "supply/renewable", "verdict": "CONFIRMED", "evidence": "GR_SOUTH wind 2266 vs 1486 MW binding/non (Apr-2025, 1.52x); P(bind) overnight 2%->57% across wind bins <0.5GW->>2.5GW."},
            {"lens": "transmission outage", "verdict": "CONFIRMED (structural) / INSUFFICIENT (specific)", "evidence": "100% post-contingency (FO-AV-LO group); no base-case binding. Specific outage attribution blocked (no CRR Network Model); real-outage lift non-discriminating (sec5)."},
            {"lens": "demand", "verdict": "HYPOTHESIS", "evidence": "Overnight peak not isolated from the overnight South-wind surge."},
            {"lens": "temperature", "verdict": "INSUFFICIENT", "evidence": "Apr/Dec/Jan peaks; Jan-2026 winter event coincident but temp not isolated from wind."},
            {"lens": "weather", "verdict": "HYPOTHESIS", "evidence": "Spring/cool-season high-wind low-solar windows; not separately tested vs wind."},
        ],
        gks_read="Highest-RT-severity live charge signal of cluster D (RT mean lambda $978). Overnight HE22-07 high-South-wind days = cheap charging; SF small so per-event $ modest, value comes from binding frequency + cap-out lambda.",
        seasonality="Spring (Apr biggest, -$3.96k DA) + Dec/Jan secondary. Overnight-dominant HE22-07; midday trough.",
        caveats=["section2 columns = HE1..HE24 (index0=HE1).",
                 "SF tiny (~0.013) -> small $/MWh per event; material only because it binds thousands of DA hrs.",
                 "BRUNI & LASCRU_MILO share the DFOAVLO5 contingency -> electrically coupled around the same FO-AV-LO outage.",
                 "RT transmission cap observed = $3500."],
    ),
    "LOYOLA_69_1": dict(
        display_name="LOYOLA_69_1 — LOYOLA 138/69 kV transformer (Loyola switchyard, SOUTH)",
        element="LOYOLA switchyard 138/69 kV transformer (two windings; '_69_1' = low-side tag)",
        kv=138, facility_type="xfmr",
        contingencies=["SN_SLON5", "SKLELOY8", "SKINKLE8", "SN_SAJO5 (single-element N-1 at Loyola)"],
        mechanism="GKS injection loads South-Texas export through the LOYOLA 138/69 transformer; positive SF -> post-contingency overload aggravated -> own LMP pushed down (charge-favorable).",
        s3_factor="South wind (GW), evening HE18-21",
        s3_on="0.5", s3_strong="2.0", s3_conf="HIGH",
        s3_note="Monotonic: P(bind) 11%@<0.5GW -> 44%@>2GW in evening window; lambda median 5->189 across bins.",
        rule="Evening HE18-21 + GR_SOUTH wind >1.5-2 GW + single-element Loyola N-1 (SN_SLON5/SKLELOY8) => P(bind)~34-44%, charge-favorable; small SF (~0.012-0.015), high lambda (cap-outs to $3500 RT).",
        drivers=[
            {"lens": "supply/renewable", "verdict": "CONFIRMED", "evidence": "GR_SOUTH wind 1854 vs 977 MW binding/non (May-2025, 1.90x); P(bind) evening 11%->44% across wind bins."},
            {"lens": "transmission outage", "verdict": "CONFIRMED (structural) / INSUFFICIENT (specific)", "evidence": "100% post-contingency (SN_SLON5/SKLELOY8 single-element N-1); real-outage lift non-discriminating (sec5)."},
            {"lens": "demand", "verdict": "HYPOTHESIS", "evidence": "Evening HE18-21 aligns with local load peak but co-incident with evening wind ramp; not isolated."},
            {"lens": "temperature", "verdict": "INSUFFICIENT", "evidence": "May/Apr/Nov peaks; temp not isolated from wind/seasonality."},
            {"lens": "weather", "verdict": "HYPOTHESIS", "evidence": "Shoulder-season high-wind windows; not separately tested."},
        ],
        gks_read="Most-frequent DA binder of cluster D (4435 DA hrs). Evening HE18-21 high-South-wind days = charge-favorable; steady DA depression + episodic RT cap-outs.",
        seasonality="Spring (May biggest -$1.59k DA / -$1.79k RT, Apr) + Nov. Evening-dominant HE18-21.",
        caveats=["section2 columns = HE1..HE24 (index0=HE1).",
                 "rt/ LIMITMW ~38 MW (small element) -> saturates fast -> RT lambda slams $3500 cap.",
                 "SF tiny (~0.012-0.015); value from binding frequency, not per-event size.",
                 "Loyola contingencies (SN_SLON5/SKLELOY8) are distinct from BRUNI/LASCRU FO-AV-LO group."],
    ),
    "LASCRU_MILO1_1": dict(
        display_name="LASCRU_MILO1_1 — LASCRUCE–MILO 138 kV line (SOUTH, Laredo/border)",
        element="LASCRUCE -> MILO 138 kV line (genuine line; highest cluster-D SF)",
        kv=138, facility_type="line",
        contingencies=["DFOAVLO5 (dominant, 3666/3895 RT rows)", "DLOFOAV5 (FO-AV-LO Laredo group)"],
        mechanism="GKS injection adds to South-Texas export on the LASCRUCE-MILO 138 kV line path; large positive SF (~0.09, ~7x the transformers) -> post-contingency overload aggravated -> own LMP pushed down (charge-favorable).",
        s3_factor="South wind (GW), evening/overnight cool-season (HE18-23)",
        s3_on="1.0", s3_strong="2.5", s3_conf="MED",
        s3_note="Wind sensitivity is strongest in COOL-SEASON OVERNIGHT (Jan-2026 1815 vs 769 MW, 2.36x). In the evening HE18-23 window the wind ladder is weak/non-monotonic (P(bind) 3%->18%) because binding concentrates Oct-Jan overnight; treat the GW breakpoint as conditional on cool season.",
        rule="Cool season (Oct-Jan) evening/overnight + GR_SOUTH wind >1.5-2 GW + DFOAVLO5 active => binding; largest per-event swing of cluster D (SF ~0.09). Near-zero binding when South wind <~0.9 GW or in warm months (Mar-Sep ~0).",
        drivers=[
            {"lens": "supply/renewable", "verdict": "CONFIRMED (cool-season)", "evidence": "GR_SOUTH wind 1815 vs 769 MW binding/non (Jan-2026, 2.36x = most wind-sensitive of cluster); binding vanishes Mar-Sep."},
            {"lens": "transmission outage", "verdict": "CONFIRMED (structural) / INSUFFICIENT (specific)", "evidence": "100% post-contingency, dominated by DFOAVLO5 (same FO-AV-LO outage as BRUNI). Specific outage non-discriminating (sec5)."},
            {"lens": "temperature", "verdict": "HYPOTHESIS", "evidence": "Fall/winter dominance (Nov/Jan/Oct), biggest RT month Jan-2026 (-$2.37k) on a winter event; cold-load not isolated from high wind."},
            {"lens": "demand", "verdict": "HYPOTHESIS", "evidence": "Evening HE19-23 peak aligns with local load but co-incident with wind ramp."},
            {"lens": "solar", "verdict": "HYPOTHESIS", "evidence": "Midday binding trough consistent with South-solar export relief; not directly tested."},
        ],
        gks_read="Largest per-event charge swing of cluster D (SF ~0.09). Lean into cool-season (Oct-Jan) evening/overnight high-South-wind days for cheap charging; warm-month value ~0.",
        seasonality="Fall/Winter only (Nov biggest -$2.31k DA, Jan/Oct); Jan-2026 biggest RT month (-$2.37k). Evening/overnight HE19-23. Effectively dormant Mar-Sep.",
        caveats=["section2 columns = HE1..HE24 (index0=HE1); months Mar-Sep are genuine 0 (dormant), not null.",
                 "BRUNI & LASCRU_MILO share the DFOAVLO5 contingency -> electrically coupled.",
                 "Largest SF of cluster (~0.09) but fewest binding hours; RT value episodic (Jan/Nov cool-season events).",
                 "Evening-window wind threshold is conditional on cool season; overnight cool-season is the true trigger."],
    ),
}

for oid in ["BRUNI_69_1", "LOYOLA_69_1", "LASCRU_MILO1_1"]:
    s = stats[oid]
    n = NARR[oid]
    wrows = wth[oid]
    pack = {
        "id": oid,
        "display_name": n["display_name"],
        "element": n["element"],
        "kv": n["kv"],
        "facility_type": n["facility_type"],
        "zone_from": "SOUTH", "zone_to": "SOUTH",
        "binding_basis": "post-contingency-N1",
        "contingencies": n["contingencies"],
        "gks_sf": {"da": s["DA"]["sf_median"], "rt": s["RT"]["sf_median"]},
        "sign": "neg",
        "mechanism": n["mechanism"],
        "status": "live",
        "section1_lambda_summary": lam_summary(s),
        "section2_month_hour": {"rt_pbind": pbind[oid]["rt_pbind"], "da_pbind": pbind[oid]["da_pbind"]},
        "section3_thresholds": [{
            "factor": n["s3_factor"],
            "on_breakpoint": n["s3_on"],
            "strong": n["s3_strong"],
            "pbind_distribution": dist_string(wrows),
            "lambda_cond": lambda_cond_string(wrows),
            "confidence": n["s3_conf"],
            "note": n["s3_note"],
        }],
        "section4_rule_of_thumb": n["rule"],
        "section5_outage_watchlist": outage_section(oid),
        "section6_drivers": n["drivers"],
        "section7_gks_read": n["gks_read"],
        "seasonality_text": n["seasonality"],
        "caveats": n["caveats"],
    }
    out = D / f"datapack_{oid}.json"
    json.dump(pack, open(out, "w"), indent=2)
    print("wrote", out.name)
