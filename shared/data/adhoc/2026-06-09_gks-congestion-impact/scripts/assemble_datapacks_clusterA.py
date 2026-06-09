"""Assemble per-constraint dashboard datapacks for HAINE__LA_PAL1_1 & 421__A per DATAPACK_SCHEMA.md.
Reuses already-computed section1/3/4/6/7 (deepdive_clusterA_stats.json, drivers_clusterA.json) and
NEW section2 (section2_matrices_clusterA.json) + section5 (clusterA_outage_lift.json). REAL data only."""
import json
from pathlib import Path

D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
stats = json.load(open(D / "deepdive_clusterA_stats.json"))
mtx = json.load(open(D / "section2_matrices_clusterA.json"))
olift = json.load(open(D / "clusterA_outage_lift.json"))


def s1(c):
    da, rt = stats[c]["DA"], stats[c]["RT"]
    tot = round(da["cum_usd"] + rt["cum_usd"])
    return {
        "da": {"bind_hrs": da["binding_hours"], "mean": da["lam_mean"], "median": da["lam_median"],
               "p90": da["lam_p90"], "p99": da["lam_p99"], "max": da["lam_max"]},
        "rt": {"bind_hrs": rt["binding_hours"], "mean": rt["lam_mean"], "median": rt["lam_median"],
               "p90": rt["lam_p90"], "p99": rt["lam_p99"], "max": rt["lam_max"]},
        "rt_cap": 3500,
        "cum_impact_usd_per_mw": {"da": round(da["cum_usd"]), "rt": round(rt["cum_usd"]), "total": tot,
                                  "note": "POS/discharge: binding RAISES GKS_BESS_RN LMP. cum = time-weighted $/MWh*h per 1MW continuous discharge position."},
    }


def s2(c):
    m = mtx[c]
    return {"rt_pbind": m["rt_pbind"], "da_pbind": m["da_pbind"],
            "rt_medlam": m["rt_medlam"], "da_medlam": m["da_medlam"],
            "_meta": mtx["_meta"]}


def s5(c, informative, base, rows, caveat):
    return {"informative": informative, "base_pbind_per_day": base, "rows": rows, "caveat": caveat}


# ---------------- HAINE ----------------
hl = olift["HAINE__LA_PAL1_1"]
haine = {
    "id": "HAINE__LA_PAL1_1",
    "display_name": "HAINE__LA_PAL1_1 — LA PALMA–HAINE DRIVE 138 (RGV local)",
    "element": "LA PALMA → HAINE DRIVE",
    "kv": 138,
    "facility_type": "line",
    "zone_from": "SOUTH", "zone_to": "SOUTH",
    "binding_basis": "post-contingency-N1",
    "contingencies": ["MHARNED5 (dominant, 23211 rows, λ̄$155)", "SRAYRI38 (3361, $159)", "SN_SAJO5", "SRAYRI28", "SRAYHAR8", "DBONRIO5"],
    "gks_sf": {"da": stats["HAINE__LA_PAL1_1"]["DA"]["sf_mean"], "rt": stats["HAINE__LA_PAL1_1"]["RT"]["sf_mean"]},
    "sign": "pos",
    "mechanism": "GKS injection relieves local Valley 138 loading (SF≈−0.03 <0) → binding RAISES GKS_BESS_RN LMP → discharge-favorable. Small |SF| (local line) but binds constantly: high local RGV solar+wind overloads the LA PALMA–HAINE 138.",
    "status": "live",
    "section1_lambda_summary": s1("HAINE__LA_PAL1_1"),
    "section2_month_hour": s2("HAINE__LA_PAL1_1"),
    "section3_thresholds": [
        {"factor": "Hour-of-day (HE)", "on_breakpoint": "HE12", "strong": "HE17-19",
         "pbind_distribution": "HE6-9:~42% -> HE12:71% -> HE15-16:84% -> HE17-18:90-94% -> HE19:~100%",
         "lambda_cond": "rises into evening; DA med $16 / p90 $125, RT med $155 / p90 $364",
         "confidence": "HIGH"},
        {"factor": "South-zone load (GW)", "on_breakpoint": "4.0", "strong": "4.6",
         "pbind_distribution": "<3.5GW:44% -> 3.5-4.0:69% -> 4.0-4.6:80% -> >4.6:80%",
         "lambda_cond": "λ̄ scales $37 -> $103 -> $127 when binding", "confidence": "MEDIUM"},
        {"factor": "South/coastal solar (GW)", "on_breakpoint": "1.1", "strong": "1.1-2.3",
         "pbind_distribution": "0GW:52% -> 0-1.1:68% -> 1.1-2.3:88% -> >2.3:60% (non-monotonic tail)",
         "lambda_cond": "λ̄ $54 -> $88", "confidence": "MEDIUM"},
        {"factor": "GR_SOUTH wind (GW)", "on_breakpoint": "2.2", "strong": "2.8",
         "pbind_distribution": "<1.1GW:51% -> 1.1-2.2:59% -> 2.2-2.8:82% -> >2.8:88%",
         "lambda_cond": "λ̄ $69 -> $98", "confidence": "MEDIUM"},
    ],
    "section4_rule_of_thumb": "봄(Feb–May) 오후 HE12–19, 특히 HE17–19 + South load >4GW + 로컬 RGV solar>1.1GW 또는 GR_SOUTH wind>2.2GW ⇒ P(bind)~80–94%, discharge-favorable. 빈도형(per-MWh 작지만 시간수 압도적); |SF| 작아 per-MW 레버리지는 낮음.",
    "section5_outage_watchlist": s5(
        "HAINE__LA_PAL1_1", False, hl["meta"]["base_pbind_per_day"],
        [{"facility": r["station"], "zone": r["zone"], "out_days": r["out_days"], "co_bind": r["co_bind"],
          "p_bind_given_out": r["p_bind_given_out"], "seas_lift": r["seas_lift"], "note": "top by seas_lift but ≈1.0–1.3, non-discriminating"}
         for r in hl["stations"][:3]],
        "OUTAGE-UNDISCRIMINATED at day level: HAINE binds ~72% of all days (base 0.72), so daily outage-state adds ~no lift "
        "(max seas_lift ~1.3, from non-local stations = spurious co-occurrence). Outages act on INTENSITY not frequency: deep-dive "
        "found LA_PALMA 138/345 planned outage (Feb–Mar 2026) amplified the RT λ=$3500 spike. Driver is renewable+load, not a contingency-membership outage signal."),
    "section6_drivers": [
        {"lens": "demand", "verdict": "CONFIRMED", "evidence": "South load bind 3944 vs nonbind 3559 MW; P(bind) 0.44(low)→0.80(high), λ̄ $37→$127."},
        {"lens": "supply/renewable", "verdict": "CONFIRMED", "evidence": "South solar bind 897 vs 493 (P(bind)→0.88); GR_SOUTH wind bind 1841 vs 1272 (P(bind)→0.88 top-decile). High local Valley solar+wind overloads the 138."},
        {"lens": "transmission outage", "verdict": "CONFIRMED (intensity only)", "evidence": "LA_PALMA 138/345 + LA_PALMA–KNGFSHER 345 planned outage Feb–Mar 2026 amplified RT λ to $3500; but base bind-rate 0.72 means no daily-frequency lift."},
        {"lens": "temperature", "verdict": "HYPOTHESIS", "evidence": "load proxy only; no direct temp series pulled (spring-afternoon pattern consistent with cooling/irradiance)."},
        {"lens": "weather", "verdict": "HYPOTHESIS", "evidence": "irradiance/wind via the renewable lens; no separate weather feature."},
    ],
    "section7_gks_read": "Highest-FREQUENCY live discharge signal (7207 DA bind-hrs, ~100% N-1). Small per-MWh ($16 DA median) but binds nearly every spring afternoon. Lean into discharge HE17–19 spring days with high RGV solar/wind + South load >4GW. Low |SF| (~0.03) ⇒ modest per-MW $; a volume/frequency play, not a severity play.",
    "seasonality_text": "Spring peak (Feb–May; Mar/Apr biggest), trough Aug–Oct. Hour HE12–19, P(bind) peaks HE17–19, λ peaks HE17–18.",
    "caveats": ["RT λ source = market_shift_factors MARKET='RT' @ GKS pricenode (validated on 1710__C sample); SCED resource-level cross-check recommended.",
                "Window = node existence 2024-07-03..2026-06-08 (~23mo).",
                "Thresholds from a single representative month (2025-03, base 0.65) — directionally consistent with full-window stats but not full-window fitted.",
                "Outage watchlist non-informative at day level (base 0.72)."],
}

# ---------------- 421__A ----------------
ol = olift["421__A"]
disc = [r for r in ol["stations"] if r["seas_lift"] and r["seas_lift"] >= 1.15 and r["out_days"] < 520][:8]
c421 = {
    "id": "421__A",
    "display_name": "421__A — BCESW–SANDOW SWITCH 345 (Central-TX North↔South seam)",
    "element": "BCESW → SANDOW SWITCH",
    "kv": 345,
    "facility_type": "line",
    "zone_from": "NORTH", "zone_to": "SOUTH",
    "binding_basis": "post-contingency-N1",
    "contingencies": ["DSALHUT5 (2428 rows, λ̄$90)", "MSSNDBG5 (1623, $100)", "SBCESND5", "SSNDBGR5", "MSBCEBG5", "DFRYTM58"],
    "gks_sf": {"da": stats["421__A"]["DA"]["sf_mean"], "rt": stats["421__A"]["RT"]["sf_mean"]},
    "sign": "pos",
    "mechanism": "GKS discharge in the deep South displaces North→South import on this 345 seam (SF≈−0.19, |SF| up to 0.32 — strongest bulk coupling of Cluster A) → reduces flow → binding RAISES GKS_BESS_RN LMP → discharge-favorable. Onset gated by parallel-345 (BGRSW/BCESW/YARSW/SANDOW) outage state.",
    "status": "live",
    "section1_lambda_summary": s1("421__A"),
    "section2_month_hour": s2("421__A"),
    "section3_thresholds": [
        {"factor": "Parallel-345 outage state (BGRSW/BCESW/YARSW/SANDOW corridor)", "on_breakpoint": "431_B/455_A/3425_B forced out",
         "strong": "multiple segments out (Apr–May 2025 onward)",
         "pbind_distribution": "corridor intact (pre-Apr2025): ~0%/day -> corridor forced-out (Apr2025+): ~23%/day (regime base); months Oct–Dec & Apr 50–68%/day",
         "lambda_cond": "RT med $48 / p90 $197 / max $2417", "confidence": "MEDIUM-HIGH"},
        {"factor": "GR_SOUTH wind (GW, INVERSE)", "on_breakpoint": "<1.7", "strong": "<1.0",
         "pbind_distribution": "low South wind ⇒ more North→South import ⇒ binds: <1.7GW:5% vs >2.4GW:0% (thin Apr-2025 sample, base 2%)",
         "lambda_cond": "λ̄ ~$12 when binding (sample)", "confidence": "LOW"},
        {"factor": "SouthCentral load (GW)", "on_breakpoint": "8.9", "strong": "10.2",
         "pbind_distribution": "weak-positive: <7.3GW:0% -> 8.9-10.2:3% -> >10.2:3% (thin sample)",
         "lambda_cond": "λ̄ $8→$17", "confidence": "LOW"},
        {"factor": "Hour-of-day (HE)", "on_breakpoint": "HE10", "strong": "HE13-16",
         "pbind_distribution": "overnight ~0% -> HE10:rises -> HE13-16 peak -> evening tapers; DA peak m4/HE15, RT peak m4/HE16",
         "lambda_cond": "λ peaks HE17-18 ($121-140)", "confidence": "MEDIUM"},
    ],
    "section4_rule_of_thumb": "Sandow/BCESW 345 병렬경로(431_B/455_A/3425_B)가 outage 상태일 때만 의미 있게 binding. 그 조건에서 봄(Apr 최대)·늦가을/겨울(Oct–Dec) 오후 HE13–16 + 낮은 South wind ⇒ discharge-favorable. |SF| 최대 0.32로 Cluster A 중 per-MW 레버리지 1위, 2026 유일 성장 제약.",
    "section5_outage_watchlist": s5(
        "421__A", True, ol["meta"]["base_pbind_per_day"],
        [{"facility": r["station"], "zone": r["zone"], "out_days": r["out_days"], "co_bind": r["co_bind"],
          "p_bind_given_out": r["p_bind_given_out"], "seas_lift": r["seas_lift"],
          "note": "RGV-South area facility; daily-discriminating co-bind"} for r in disc],
        "informative=true (regime 2025-01-01+, base 0.23/day). KEY NUANCE: the headline parallel-345 outages (BGRSW/BCESW/YARSW/SANDOW: "
        "BGRSW–BCESW 431_B, BGRSW–SNDSW 455_A, BCESW–YARSW 3425_B — Forced since Apr/May 2025) are PERSISTENTLY out across the whole 2025+ "
        "regime (out_days ≈ all 522 days) → they show seas_lift≈1.0 (no daily discrimination) because they are the STRUCTURAL regime shift: "
        "P(bind) ~0/day in 2024 → 0.23/day in 2025+. The daily-discriminating outages are RGV-South area facilities (KNGFSHER, SE EDINBURG, "
        "CLOSNER, STEWART ROAD, LA PALMA, GDLSW–YARSW 3436_A) seas_lift 1.2–2.4, co-moving with the South-import/solar conditions that tighten the seam. "
        "co-occurrence != causation; lift = weakening-outage signature, not NMMS contingency membership."),
    "section6_drivers": [
        {"lens": "transmission outage", "verdict": "CONFIRMED (structural)", "evidence": "Parallel 345 BGRSW–BCESW 431_B / BGRSW–SNDSW 455_A / BCESW–YARSW 3425_B Forced-out since Apr–May 2025; binding ramped 2024:160 → 2025:2983 → 2026:3023 rows. Persistent outage = the regime onset, not a daily lift."},
        {"lens": "demand", "verdict": "INSUFFICIENT (weak-positive)", "evidence": "SouthCentral load bind 9022 vs nonbind 8222 MW; thin Apr-2025 sample (base 2%) — directionally North→South-import consistent but underpowered."},
        {"lens": "supply/renewable", "verdict": "HYPOTHESIS (inverse-wind)", "evidence": "GR_SOUTH wind bind 993 vs nonbind 1908 MW — low South wind ⇒ more southbound import ⇒ binds; same import story as 1710__C, sample thin."},
        {"lens": "temperature", "verdict": "INSUFFICIENT", "evidence": "no direct temp series; sample too thin to separate from load."},
        {"lens": "weather", "verdict": "INSUFFICIENT", "evidence": "captured only via inverse-wind hypothesis; no separate weather feature."},
    ],
    "section7_gks_read": "Most forward-relevant Cluster-A discharge signal: ONLY constraint growing into 2026 and the largest |SF| (~0.19 mean, up to 0.32) ⇒ highest per-MW discharge leverage. Conditional on the Sandow/BCESW 345 parallel-corridor outage state — when that corridor is out (current regime), lean into discharge spring (Apr) + late-fall/winter (Oct–Dec) afternoons HE13–16, especially low-South-wind hours. Recommend a parallel-345 outage-state feature for Stage-2.",
    "seasonality_text": "Spring (Apr biggest) + late-fall/winter (Nov/Dec/Oct); afternoon HE10–18, P(bind) peaks HE13–16, λ peaks HE17–18. 2025-onset & growing (gated by parallel-345 outages).",
    "caveats": ["2025-onset/growing constraint — window-average section2 P(bind) UNDERSTATES current (2026) levels; outage regime window = 2025-01-01+.",
                "Driver thresholds from a thin month (2025-04, only 15 binding hrs, base 2%) → LOW confidence on load/wind/solar; primary switch is the outage-state gate.",
                "RT λ source = market_shift_factors MARKET='RT' @ GKS pricenode.",
                "Parallel-345 outages persistent ⇒ visible as regime base-rate jump, not daily lift."],
}

json.dump(haine, open(D / "datapack_HAINE__LA_PAL1_1.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
json.dump(c421, open(D / "datapack_421__A.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("saved datapack_HAINE__LA_PAL1_1.json + datapack_421__A.json")
for k in ["section1_lambda_summary", "section2_month_hour", "section3_thresholds", "section4_rule_of_thumb",
          "section5_outage_watchlist", "section6_drivers", "section7_gks_read"]:
    print("HAINE has", k, "->", bool(haine.get(k)), "| 421 has", k, "->", bool(c421.get(k)))
