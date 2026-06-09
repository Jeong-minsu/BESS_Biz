"""Build per-constraint dashboard data packs for BLESSING_1382 and STPELM27_1 (Cluster B POS).
REUSE section1/4/6/7/seasonality from clusterB_pos_deepdive (deep-dive plan); NEW-compute
section2 (month x hour P(bind)), section3 (wind/load/outage thresholds), section5 (outage watchlist).
REAL Yes Energy datalake. impact = -SF*lambda (POS raises GKS LMP -> discharge-favorable).
"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))

D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")

# ---------- load binding events ----------
raw = pd.read_parquet(D / "gks_msf_raw.parquet")
raw = raw[raw.SHADOWPRICE > 0].copy()
raw["dt"] = pd.to_datetime(raw.DATETIME, format="%m/%d/%Y %H:%M:%S")
raw["date"] = raw.dt.dt.normalize()
raw["month"] = raw.dt.dt.month
raw["hour"] = raw.dt.dt.hour

# window day-counts per month (calendar, for P(bind) denominators)
WIN = pd.date_range("2024-07-03", "2026-06-08", freq="D")
days_per_month = pd.Series(WIN.month).value_counts().to_dict()  # {month: #days in window}

# ---------- panels ----------
wl = pd.read_parquet(D / "panel_windload.parquet")
wl["dt"] = pd.to_datetime(wl["dt"])
wl["cs_wind"] = wl["coastal"] + wl["south"]          # coastal+south wind GW
wl["load_gw"] = wl["load"] / 1000.0
wl["month"] = wl.dt.dt.month
wl["hour"] = wl.dt.dt.hour
wl["date"] = wl.dt.dt.normalize()

od = pd.read_parquet(D / "panel_outages.parquet")
od["date"] = pd.to_datetime(od.date, format="%Y%m%d")
od["ajo_ref_out"] = od.lines345.fillna("").str.contains("AJO_REFORZ").astype(int)
od["reforzar_corr_out"] = od.lines345.fillna("").str.contains("REFORZ").astype(int)
od["elmcreek_other_out"] = od.lines345.fillna("").str.contains("E5_P4|E5_G6|SMG_ELMCRK|MARN_ELMCRK|E5_LIBRA").astype(int)


def month_hour_pbind(cname, mkt):
    """12x24 P(bind) % matrix. DA: rows/day-per-month. RT: 5min-rows/(day-per-month*12)."""
    s = raw[(raw.CONSTRAINTNAME == cname) & (raw.MARKET == mkt)]
    cnt = s.groupby(["month", "hour"]).size().unstack(fill_value=0).reindex(
        index=range(1, 13), columns=range(24), fill_value=0)
    mat = []
    for m in range(1, 13):
        den = days_per_month.get(m, 0) * (1 if mkt == "DA" else 12)
        row = [round(100.0 * cnt.loc[m, h] / den, 2) if den else None for h in range(24)]
        mat.append(row)
    return mat


def thresholds(cname, season_months, hours, wind_bins, load_bins):
    """Conditional P(bind in DA hour) within (season, hours) vs coastal+south wind & ERCOT load,
    plus AJO-REFORZAR outage. Binding indicator = DA row exists at that (date,HE)."""
    bind_keys = set(zip(raw[(raw.CONSTRAINTNAME == cname) & (raw.MARKET == "DA")].date,
                        raw[(raw.CONSTRAINTNAME == cname) & (raw.MARKET == "DA")].hour))
    p = wl[wl.month.isin(season_months) & wl.hour.isin(hours)].copy()
    p["bind"] = [(d, h) in bind_keys for d, h in zip(p.date, p.hour)]
    p = p.merge(od[["date", "ajo_ref_out"]], on="date", how="left")
    n_all = len(p)
    base = round(100 * p.bind.mean(), 1)
    lam = raw[(raw.CONSTRAINTNAME == cname) & (raw.MARKET == "DA")].SHADOWPRICE

    def dist(series, bins, labels):
        out = []
        b = pd.cut(series, bins=bins, labels=labels, include_lowest=True)
        for lab in labels:
            mask = b == lab
            n = int(mask.sum())
            pb = round(100 * p.bind[mask].mean(), 1) if n else None
            out.append((lab, pb, n))
        return out

    def mono_up(d):   # increasing P with bin? (supports positive-driver hypothesis)
        v = [b for _, b, c in d if b is not None and c >= 30]
        return len(v) >= 2 and all(x <= y for x, y in zip(v, v[1:]))
    def mono_dn(d):
        v = [b for _, b, c in d if b is not None and c >= 30]
        return len(v) >= 2 and all(x >= y for x, y in zip(v, v[1:]))

    wlab = [f"<{wind_bins[1]}", f"{wind_bins[1]}-{wind_bins[2]}", f">{wind_bins[2]}"]
    llab = [f"<{load_bins[1]}", f"{load_bins[1]}-{load_bins[2]}", f">{load_bins[2]}"]
    rows = []
    # wind (marginal)
    wl_dist = dist(p.cs_wind, wind_bins, wlab)
    rows.append({
        "factor": "Coastal+South wind (GW), marginal",
        "on_breakpoint": str(wind_bins[1]), "strong": str(wind_bins[2]),
        "pbind_distribution": " -> ".join(f"{a}GW:{b}%(n{c})" for a, b, c in wl_dist),
        "lambda_cond": f"DA med ${round(lam.median(),1)} (P90 ${round(lam.quantile(.9),1)})",
        "confidence": "MED" if mono_up(wl_dist) else "LOW",
        "note": ("higher-wind -> higher P(bind) (supports export driver)" if mono_up(wl_dist)
                 else "marginal wind sign NOT positive (negative/flat) — likely confounded by outage regime; see AJO-conditional row"),
    })
    # wind | AJO-REFORZAR out (disentangle from outage regime)
    pao = p[p.ajo_ref_out == 1]
    if len(pao) >= 60:
        pp, p_bak = p, None
        sub = pao
        wd = []
        b = pd.cut(sub.cs_wind, bins=wind_bins, labels=wlab, include_lowest=True)
        for lab in wlab:
            mk = b == lab; n = int(mk.sum())
            wd.append((lab, round(100 * sub.bind[mk].mean(), 1) if n else None, n))
        rows.append({
            "factor": "Coastal+South wind (GW) | AJO-REFORZAR OUT",
            "on_breakpoint": str(wind_bins[1]), "strong": str(wind_bins[2]),
            "pbind_distribution": " -> ".join(f"{a}GW:{b}%(n{c})" for a, b, c in wd),
            "lambda_cond": f"DA med ${round(lam.median(),1)}",
            "confidence": "MED" if mono_up(wd) else "LOW",
            "note": "wind effect within the binding-enabling outage regime",
        })
    # load (low-load-enables hypothesis -> expect decreasing P with load)
    ld_dist = dist(p.load_gw, load_bins, llab)
    rows.append({
        "factor": "ERCOT load (GW) — low-enables hypothesis",
        "on_breakpoint": f"<{load_bins[2]}", "strong": f"<{load_bins[1]}",
        "pbind_distribution": " -> ".join(f"{a}GW:{b}%(n{c})" for a, b, c in ld_dist),
        "lambda_cond": f"DA med ${round(lam.median(),1)}",
        "confidence": "MED" if mono_dn(ld_dist) else "LOW",
        "note": ("low-load -> higher P(bind) confirmed" if mono_dn(ld_dist)
                 else "low-load-enables NOT supported in marginal data (confounded by outage timing)"),
    })
    # AJO-REFORZAR outage (the dominant gate)
    po = p[p.ajo_ref_out == 1]; pn = p[p.ajo_ref_out == 0]
    p_out = round(100 * po.bind.mean(), 1) if len(po) else None
    p_in = round(100 * pn.bind.mean(), 1) if len(pn) else None
    lift = round(p_out / p_in, 1) if p_out and p_in else None
    conf = "HIGH" if (lift and lift >= 3 and len(po) > 30 and len(pn) > 30) else (
        "MED" if len(po) > 30 and len(pn) > 30 else "LOW")
    rows.append({
        "factor": "AJO-REFORZAR 345 parallel OUT (gate)",
        "on_breakpoint": "line out", "strong": "line out + low load + high wind",
        "pbind_distribution": f"out:{p_out}%(n{len(po)}) vs in:{p_in}%(n{len(pn)}) [lift x{lift}]",
        "lambda_cond": f"DA med ${round(lam.median(),1)}",
        "confidence": conf,
        "note": "co-occurrence within winter season; AJO out since 2025-09 overlaps STPELM onset winter — not causal proof",
    })
    return base, n_all, rows


def outage_watchlist(cname, season_months):
    """Day-level: bound (DA or RT) that day; lift vs corridor 345 LINE outages, season-adjusted."""
    bind_days = set(raw[raw.CONSTRAINTNAME == cname].date.unique())
    o = od.copy()
    o["bind"] = o.date.isin(bind_days).astype(int)
    o["month"] = o.date.dt.month
    base = round(o.bind.mean(), 3)
    seas = o[o.month.isin(season_months)]
    seas_base = round(seas.bind.mean(), 3)
    rows = []
    for fac, col, label, zone in [
        ("AJO-REFORZAR 345 (AJO_REFORZ11/21)", "ajo_ref_out", "AJO-REFORZAR 345", "SOUTH"),
        ("REFORZAR 345 corridor (NEDIN/LON_HILL/AJO)", "reforzar_corr_out", "REFORZAR corridor 345", "SOUTH"),
        ("Other ELM CREEK 345 lines (SKYLINE/SMG/G6/MARION)", "elmcreek_other_out", "ELMCREEK 345 (non-monitored)", "SOUTH"),
    ]:
        sub = seas
        out_days = int(sub[col].sum())
        co = int(((sub[col] == 1) & (sub.bind == 1)).sum())
        p_out = round(co / out_days, 3) if out_days else None
        in_days = int((sub[col] == 0).sum())
        p_notout = round(sub.bind[sub[col] == 0].mean(), 3) if in_days else None
        lift = round(p_out / p_notout, 2) if p_out and p_notout else None
        note = f"p_bind|in={p_notout} (in_days={in_days}); season_base={seas_base}"
        if in_days == 0:
            note = f"UNDISCRIMINATING: out every winter day (in_days=0); season_base={seas_base}"
        rows.append({"facility": fac, "zone": zone, "out_days": out_days, "co_bind": co,
                     "p_bind_given_out": p_out, "seas_lift": lift, "note": note})
    return base, seas_base, rows


# ================= REUSED content (from clusterB_pos_deepdive plan) =================
PACKS = {
"BLESSING_1382": {
  "id": "BLESSING_1382",
  "display_name": "BLESSING_1382 — BLESSING 345kV autotransformer (SOUTH coastal)",
  "element": "BLESSING 345/138 XFMR", "kv": 345, "facility_type": "xfmr",
  "zone_from": "SOUTH", "zone_to": "SOUTH",
  "binding_basis": "post-contingency-N1",
  "contingencies": ["DELMTEX5", "MANSSTP5", "DSTPREF5", "DSTPSTA5", "MSTPSTA5"],
  "gks_sf": {"da": -0.0749, "rt": -0.07}, "sign": "pos",
  "mechanism": ("GKS injection from deep South TX reduces coastal South-TX export loading the Blessing "
                "345/138 transformer (SF<0 -> GKS relieves) -> raises GKS LMP -> discharge-favorable."),
  "status": "live",
  "section1_lambda_summary": {
    "da": {"bind_hrs": 4171, "mean": 11.9, "median": 4.8, "p90": 28.5, "p99": 106.4, "max": 342.0},
    "rt": {"bind_hrs": 396, "mean": 108.3, "median": 40.1, "p90": 193.7, "p99": 1533.3, "max": 4500.0},
    "rt_cap": 4500,
    "cum_impact_usd_per_mw": {"da": 3857, "rt": 2913, "total": 6770,
      "note": "POS (raises GKS LMP). DA = frequency play (4171 hrs, low lambda med $4.8); RT severity to $4500."}},
  "section4_rule_of_thumb": ("겨울+봄 overnight/morning HE3-10 + 높은 coastal+south wind + 낮은 ERCOT load => "
    "Blessing 345 xfmr 빈번 binding(DA), GKS discharge-favorable. 단발 신호 아니라 누적 tailwind."),
  "section6_drivers": [
    {"lens": "demand", "verdict": "HYPOTHESIS", "evidence": "off-peak (HE3-10 binds, HE12-17 trough) => low overnight load enables coastal export pocket; not a high-load driver."},
    {"lens": "supply/renewable", "verdict": "CONTRADICTED-marginal", "evidence": "panel (Nov-May HE3-10) shows P(bind) DECREASES with coastal+south wind (65.7%@<1.5GW -> 26.8%@>2.5GW, even conditional on AJO out) — overnight-wind-export hypothesis NOT supported; binding is more frequent on calmer overnight hours."},
    {"lens": "transmission outage", "verdict": "CONFIRMED-structural", "evidence": "pure post-contingency on STP/Elm-Creek/coastal outlet N-1 (DELMTEX5/MANSSTP5/DSTPREF5); base-case 0%. Parallel-345 outage discrimination weak (REFORZAR-corridor lift ~1.6, high base rate)."},
    {"lens": "temperature", "verdict": "INSUFFICIENT", "evidence": "not isolated; off-peak pattern argues against a temperature/load-peak driver."},
    {"lens": "weather/season", "verdict": "CONFIRMED-WINTER+SPRING", "evidence": "DA cum top Apr706/Jan559/Feb556/Dec492/May408/Nov395; summer near-zero (Aug32). RT top Feb733/Apr515/Jul452/Dec372/Nov361."}],
  "section7_gks_read": ("Highest-frequency live POS (discharge) tailwind: 4171 DA bind-hrs but low per-hour lambda. "
    "Lean discharge on winter/spring overnight-morning HE3-10 high coastal-wind low-load days; cumulative not single-event."),
  "seasonality_text": "Winter+spring, overnight/morning. DA peak Apr/Jan/Feb/Dec/May/Nov (not summer). Hour HE4-10 peak, HE12-17 trough.",
  "caveats": ["Post-contingency N-1 only (base-case 0%).",
              "Wind/outage drivers = co-occurrence + seasonality, not fitted per-episode regression.",
              "Section2/3 P(bind) denominator = full window 2024-07-03..2026-06-08; section3 conditioned on active season+hours.",
              "RT lambda via market_shift_factors MARKET=RT (pricenode-level at GKS); cross-checked vs rt/ on STPELM."],
  "_season_months": [11, 12, 1, 2, 3, 4, 5], "_hours": [3, 4, 5, 6, 7, 8, 9, 10],
  "_wind_bins": [0, 1.5, 2.5, 10], "_load_bins": [0, 45, 55, 200],
},
"STPELM27_1": {
  "id": "STPELM27_1",
  "display_name": "STPELM27_1 — STP–ELM CREEK 345kV (SOUTH coastal outlet)",
  "element": "SOUTH TEXAS PROJECT -> ELM CREEK", "kv": 345, "facility_type": "line",
  "zone_from": "SOUTH", "zone_to": "SOUTH",
  "binding_basis": "post-contingency-N1 (DELMSTP5); 2.7% base-case in RT",
  "contingencies": ["DELMSTP5", "DSTEXP12", "BASE CASE", "DLYTCIS5", "SELMST25"],
  "gks_sf": {"da": -0.0543, "rt": -0.0505}, "sign": "pos",
  "mechanism": ("STP-ELMCREEK carries STP + coastal generation north out of the Matagorda pocket. GKS sits "
                "south of STP; injecting at GKS substitutes for coastal-pocket export (SF<0 -> relieves) -> "
                "raises GKS LMP -> discharge-favorable. Highest-severity POS constraint for GKS."),
  "status": "live",
  "section1_lambda_summary": {
    "da": {"bind_hrs": 551, "mean": 92.1, "median": 20.1, "p90": 236.1, "p99": 882.8, "max": 1330.0},
    "rt": {"bind_hrs": 116, "mean": 794.5, "median": 382.3, "p90": 1936.7, "p99": 4500.0, "max": 4500.0},
    "rt_cap": 4500,
    "cum_impact_usd_per_mw": {"da": 2750, "rt": 4457, "total": 7207,
      "note": "POS. Low frequency / very high severity: RT mean lambda $795, P99=max=$4500 cap. The single highest-severity POS for GKS."}},
  "section4_rule_of_thumb": ("AJO-REFORZAR 345 parallel 라인 OUT 이 1차 gate(P(bind) 0.4%->18.8%, lift x47). "
    "그 위에 겨울밤(Dec>Jan>Nov) HE5-9·HE17-20 이면 RT severe binding($1000-$4500), GKS strong discharge signal. "
    "高wind은 frequency가 아니라 severity를 키움(rare $4500); 정상 corridor면 거의 안 바인딩."),
  "section6_drivers": [
    {"lens": "demand", "verdict": "HYPOTHESIS", "evidence": "low winter-overnight load is the enabling export-pocket condition, not a high-load driver."},
    {"lens": "supply/renewable", "verdict": "QUALIFIED", "evidence": "single peak $4500 night 2026-01-25 had ~3.7GW coastal+south wind, BUT panel (even conditional on AJO out) shows P(bind) HIGHEST at <2GW (28.5%) not >3GW (13.1%) — high wind drives SEVERITY of rare events, not binding FREQUENCY; wind is not a clean positive trigger."},
    {"lens": "transmission outage", "verdict": "CONFIRMED-dominant", "evidence": "AJO-REFORZAR 345 OUT (since 2025-09) is the gate: P(bind|HE4-9,17-20) = 18.8% out vs 0.4% in (lift x47); winter-day lift x14.6. Concentrates coastal/STP flow onto STP-ELMCREEK -> DELMSTP5 N-1 overload (limit ~611MW). Co-occurrence within 2025-26 winter, not causal proof."},
    {"lens": "temperature", "verdict": "CONFIRMED-WINTER", "evidence": "DA cum Dec1789/Jan806/Nov106; RT Dec3025/Jan1172/Nov261; ~zero outside Nov-Jan. Winter overnight = high wind + low load."},
    {"lens": "weather/season", "verdict": "CONFIRMED-WINTER", "evidence": "onset 2025 (no 2024 binding); regime-change constraint, treat with onset/active-outage features."}],
  "section7_gks_read": ("Highest-severity live POS (discharge) signal. Low frequency (116 RT bind-hrs) but RT mean "
    "lambda $795, max $4500. The winter-night discharge-timing signal: Dec>Jan>Nov, overnight/evening, when AJO/"
    "South-TX 345 corridor is out and coastal+south wind is high."),
  "seasonality_text": "Winter (Dec>Jan>Nov), overnight/morning HE5-9 + evening HE17-20. Onset 2025 (no 2024 data).",
  "caveats": ["Onset 2025: full-window P(bind) denominator dilutes (constraint inactive 2024-07..2025) — winter-night cells are nonetheless the only non-zero ones (fingerprint).",
              "CONTINGENCY text blank in rt/; decoded via DA CONTINGENCYID=DELMSTP5.",
              "RT $4500 episode cross-checked in rt/2026012522.csv.gz (PRICE=4500, VALUEMW 713>LIMITMW 611).",
              "Outage lift = co-occurrence within winter season, not contingency-membership / causation."],
  "_season_months": [11, 12, 1, 2], "_hours": [4, 5, 6, 7, 8, 9, 17, 18, 19, 20],
  "_wind_bins": [0, 2.0, 3.0, 10], "_load_bins": [0, 45, 52, 200],
},
}

for cn, pk in PACKS.items():
    pk["section2_month_hour"] = {"da_pbind": month_hour_pbind(cn, "DA"),
                                 "rt_pbind": month_hour_pbind(cn, "RT")}
    base, n_all, rows = thresholds(cn, pk.pop("_season_months_t", pk["_season_months"]),
                                   pk["_hours"], pk["_wind_bins"], pk["_load_bins"])
    pk["section3_thresholds"] = rows
    pk["caveats"].append(
        f"section3 conditioned on months={pk['_season_months']}, HE={pk['_hours']}; "
        f"panel n={n_all} hrs, base P(bind)={base}%. Wind/load = realized actuals proxy for DA forecast.")
    sb, ssb, orows = outage_watchlist(cn, pk["_season_months"])
    informative = any(r["seas_lift"] and r["seas_lift"] > 1.3 for r in orows) or \
                  any(r["seas_lift"] and r["seas_lift"] < 0.7 for r in orows)
    pk["section5_outage_watchlist"] = {
        "informative": bool(informative),
        "base_pbind_per_day": sb,
        "rows": orows,
        "caveat": (f"co-occurrence != causation; lift vs same-season (months={pk['_season_months']}) base "
                   f"{ssb}/day; full-window base {sb}/day. BLESSING is a 345/138 xfmr (no 345-LINE outage of "
                   "itself) -> watch-list tracks parallel South-TX 345 LINE outages. STPELM AJO-out overlaps "
                   "its 2025-26 winter onset, so lift is a regime signature, not proven contingency causation.")}
    for k in ["_hours", "_wind_bins", "_load_bins", "_season_months"]:
        pk.pop(k, None)
    out = D / f"datapack_{cn}.json"
    json.dump(pk, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("saved", out)
    print(f"  {cn}: s3 base={base}% n={n_all}; s5 base/day={sb} seas_base={ssb} informative={informative}")
    for r in rows: print("   ", r["factor"], "|", r["pbind_distribution"])
    for r in orows: print("    OUT", r["facility"][:30], "lift", r["seas_lift"], "p_out", r["p_bind_given_out"], "n_out", r["out_days"])
