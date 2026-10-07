"""ITEM 7 PART A — top-10 Raven constraints: main driver, shift factors (RVN real / proxy / GKS), binding hours.
Method reused from 2026-06-09 GKS / Houston projects: binding-vs-non-binding driver comparison, conditional P(bind) by
driver bin with the thresholds.py breakpoint rule (first bin with P(bind) >= max(2 x base, 20%)), and the outage
co-occurrence lift (P(bind-day | element out) / P(bind-day), within the constraint's own season -> seasonality-adjusted).
Driver ranking metric = AUC (Mann-Whitney) of the driver for the DA binding flag, inside the constraint's binding season
and peak-hour band (de-confounds diurnal/seasonal cycle). Real data only.
Inputs: derived/item2_congestion_hourly_panel.parquet, derived/item2_congestion_top10_profiles.json,
        raw/item7_driver_panel.parquet, raw/item7_outages_daily.parquet, derived/item7_gks_congestion_hourly_panel.parquet
Outputs: derived/item7_congestion_drivers.json, derived/item7_congestion_drivers.md
"""
import json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import mannwhitneyu

R = Path(__file__).resolve().parents[1]; D = R / "derived"
TOP = ["WHARTN", "BLESSI_PAVLOV1_1", "E_PASP", "1710__C", "HARGRO_TWINBU1_1", "STPELM27_1", "630__B", "STPWAP39_1", "587__A", "50__A"]
EXTRA = ["35055__A"]   # watch-list: #1 negative at the real RVN_RN in 2026 (item2)
FWD = {"WHARTN": "UNVERIFIABLE / likely proxy artifact (no binding since 2026-06-02; limit 470->691 MW)",
       "BLESSI_PAVLOV1_1": "FADED (74% of total in Oct-2023..Feb-2024; still binds at trivial lambda)",
       "E_PASP": "LIVE, growing (53% of |contrib| in last 12m); scale at Raven ~2/3 of proxy",
       "1710__C": "RETIRED (no binding since 2025-10-28)", "HARGRO_TWINBU1_1": "LIVE, chronic small RT drag",
       "STPELM27_1": "EPISODIC (Dec-Jan winter tail; top-3 days = 51%)", "630__B": "LIVE, stable spring shoulder",
       "STPWAP39_1": "LIVE, growing; most forward-relevant positive for Raven", "587__A": "LIVE, 2025 onset, growing",
       "50__A": "EPISODIC (Jan-2025 / Jan-2026 storms; top-3 days = 57%)", "35055__A": "LIVE, 2026 onset (watch-list)"}
prof = json.load(open(D / "item2_congestion_top10_profiles.json"))
P2 = pd.read_parquet(D / "item2_congestion_hourly_panel.parquet")
P2 = P2[P2.CONSTRAINTNAME.isin(TOP + EXTRA)]
G = pd.read_parquet(D / "item7_gks_congestion_hourly_panel.parquet"); G = G[G.CONSTRAINTNAME.isin(TOP + EXTRA)]
DRV = pd.read_parquet(R / "raw" / "item7_driver_panel.parquet")
DRV["net_load_ercot"] = DRV.load_ercot - DRV.wind_ercot - DRV.solar_ercot
DRV["wind_west_panhandle"] = DRV.wind_west + DRV.wind_panhandle
DRV["houston_net_import_proxy"] = DRV.load_coast - DRV.wind_coastal - DRV.solar_southeast
DRV["south_net_export_proxy"] = DRV.wind_south + DRV.wind_coastal - DRV.load_southern
DRIVERS = ["wind_south", "wind_coastal", "wind_west", "wind_panhandle", "wind_west_panhandle", "wind_north", "wind_ercot",
           "solar_southeast", "solar_farwest", "solar_ercot", "load_coast", "load_southern", "load_southcentral", "load_north",
           "load_northcentral", "load_west", "load_farwest", "load_ercot", "net_load_ercot", "houston_net_import_proxy", "south_net_export_proxy",
           "temp_hobby", "temp_galveston", "temp_dfw", "temp_sanantonio", "temp_corpus", "temp_midland"]
UNITS = {"wind": "MW", "solar": "MW", "load": "MW", "net": "MW", "houston": "MW", "south": "MW", "temp": "F"}
OUT = pd.read_parquet(R / "raw" / "item7_outages_daily.parquet")
OUT["date"] = pd.to_datetime(OUT.date, format="%Y%m%d")
hours_all = pd.date_range(P2.hour.min(), P2.hour.max(), freq="h")


def auc(x, y):
    a, b = x[y == 1].dropna(), x[y == 0].dropna()
    if len(a) < 20 or len(b) < 20: return np.nan
    return mannwhitneyu(a, b).statistic / (len(a) * len(b))


def sf_block(sub_da, sub_rt, col):
    return {"da": None if sub_da[col].dropna().empty else round(float(sub_da[col].dropna().mean()), 4),
            "rt": None if sub_rt[col].dropna().empty else round(float(sub_rt[col].dropna().mean()), 4)}


res = {}
for cn in TOP + EXTRA:
    s = P2[P2.CONSTRAINTNAME == cn]; da = s[s.MARKET == "DA"]; rt = s[s.MARKET == "RT"]
    g = G[G.CONSTRAINTNAME == cn]; gda = g[g.MARKET == "DA"]; grt = g[g.MARKET == "RT"]
    pr = prof.get(cn)
    r = {"constraint": cn, "forward_relevance": FWD[cn]}
    if pr:
        r.update(element=pr["element"], element_zone=pr["element_zone"], dominant_contingency=pr["dominant_contingency"],
                 cum_mcc_rvn=pr["cum_mcc"], sign_at_raven=pr["sign_at_raven"])
    else:
        r.update(element="SAMSW-VENSW 345 kV (NORTH)", element_zone="NORTH", dominant_contingency=None, cum_mcc_rvn={"da": round(float(da.mcc_h.sum()), 1), "rt": round(float(rt.mcc_h.sum()), 1), "total": round(float(s.mcc_h.sum()), 1)},
                 sign_at_raven="neg (lowers RVN LMP / charge-favorable)")
    # ---- shift factors ----
    real_da, real_rt = da[da.src == "RVN"], rt[rt.src == "RVN"]
    r["shift_factor"] = {"rvn_real_2026_06plus": sf_block(real_da, real_rt, "sf_rvn_mean"),
                         "rvn_real_hours": {"da": int(len(real_da)), "rt": round(float(real_rt.bind_frac.sum()), 1)},
                         "proxy_blend": sf_block(da, rt, "sf_proxy_mean"),
                         "proxy_blend_in_overlap": sf_block(real_da, real_rt, "sf_proxy_mean"),
                         "location_used_by_item2": sf_block(da, rt, "sf_mean"),
                         "gks_bess_rn": sf_block(gda, grt, "sf_mean"), "gks_hours": {"da": int(len(gda)), "rt": round(float(grt.bind_frac.sum()), 1)}}
    a = r["shift_factor"]["rvn_real_2026_06plus"]["da"]; a = r["shift_factor"]["location_used_by_item2"]["da"] if a is None else a
    gk = r["shift_factor"]["gks_bess_rn"]["da"]
    if a is None or gk is None or abs(a) < 0.005 or abs(gk) < 0.005: rel = "one-sided/negligible at one node"
    elif np.sign(a) != np.sign(gk): rel = "OPPOSING"
    else: rel = f"same-sign (GKS/RVN magnitude ratio {gk / a:.1f}x)"
    r["shift_factor"]["relation_rvn_vs_gks"] = rel
    # ---- binding hours ----
    hp = pr["hourly_profile"] if pr else None
    def band(mk):
        if hp is None:
            sub = da if mk == "da" else rt
            pb = (sub.groupby(sub.hour.dt.hour + 1).bind_frac.sum() / (len(hours_all) / 24)).reindex(range(1, 25)).fillna(0).values
            lam = (sub.groupby(sub.hour.dt.hour + 1).lam_h.sum() / sub.groupby(sub.hour.dt.hour + 1).bind_frac.sum()).reindex(range(1, 25)).values
        else:
            pb = np.array(hp[mk]["p_bind"], float); lam = np.array([np.nan if v is None else v for v in hp[mk]["mean_lambda"]], float)
        if pb.max() <= 0: return None
        hes = [h + 1 for h in range(24) if pb[h] >= 0.7 * pb.max()]
        if len(hes) > 6: hes = sorted(int(h) + 1 for h in np.argsort(-pb)[:6])   # flat profile -> top-6 hours
        return {"peak_band_HE": f"HE{min(hes)}-HE{max(hes)}", "band_hours": hes, "peak_HE": int(pb.argmax() + 1), "p_bind_peak": round(float(pb.max()), 3),
                "p_bind_band_mean": round(float(pb[[h - 1 for h in hes]].mean()), 3), "p_bind_all_hours": round(float(pb.mean()), 4),
                "mean_lambda_band": round(float(np.nanmean(lam[[h - 1 for h in hes]])), 1), "mean_lambda_all": round(float(np.nanmean(lam)), 1)}
    r["binding_hours"] = {"da": band("da"), "rt": band("rt")}
    if pr: r["binding_months"] = pr["binding_months"]
    else:
        mb = s.groupby(s.hour.dt.month).mcc_h.apply(lambda x: x.abs().sum()); r["binding_months"] = [int(m) for m in mb[mb > 0.05 * mb.sum()].index]
    # ---- drivers ----
    months = r["binding_months"] or list(range(1, 13))
    y0, y1 = s.hour.min().year, s.hour.max().year
    pop = DRV[(DRV.index.month.isin(months)) & (DRV.index.year >= y0) & (DRV.index.year <= y1)].copy()
    dabind = da.set_index("hour").mcc_h; pop["bind"] = pop.index.isin(dabind.index).astype(int)
    pop["lam"] = da.set_index("hour").lam_h.reindex(pop.index).fillna(0.0)
    bandhe = r["binding_hours"]["da"]["band_hours"] if r["binding_hours"]["da"] else list(range(1, 25))
    pop["HE"] = np.where(pop.index.hour == 0, 24, pop.index.hour)
    pb = pop[pop.HE.isin(bandhe)]
    base_all, base_band = float(pop.bind.mean()), float(pb.bind.mean())
    rank = []
    for v in DRIVERS:
        if v not in pb: continue
        au = auc(pb[v], pb.bind)
        if np.isnan(au): continue
        rank.append(dict(driver=v, auc=round(float(au), 3), sep=round(abs(au - 0.5), 3), direction="higher when binding" if au > 0.5 else "lower when binding",
                         bind_mean=round(float(pb.loc[pb.bind == 1, v].mean()), 0), nonbind_mean=round(float(pb.loc[pb.bind == 0, v].mean()), 0)))
    rank = sorted(rank, key=lambda d: -d["sep"])
    r["driver_population"] = {"months": months, "years": [int(y0), int(y1)], "hours": int(len(pop)), "band_hours": int(len(pb)),
                              "base_p_bind_all_hours": round(base_all, 3), "base_p_bind_in_band": round(base_band, 3)}
    r["driver_ranking_top8"] = rank[:8]
    # thresholds for top-2 drivers (decile bins inside band population)
    thr = []
    for d in rank[:2]:
        v = d["driver"]; x = pb[[v, "bind", "lam"]].dropna()
        edges = np.unique(np.quantile(x[v], np.linspace(0, 1, 11)))
        x["bin"] = pd.cut(x[v], edges, include_lowest=True)
        tab = x.groupby("bin", observed=True).agg(n=("bind", "size"), p_bind=("bind", "mean"), lam_when_bind=("lam", lambda z: z[z > 0].mean() if (z > 0).any() else np.nan))
        rows = [dict(lo=round(float(b.left), 0), hi=round(float(b.right), 0), n=int(t.n), p_bind=round(float(t.p_bind), 3), lam=None if pd.isna(t.lam_when_bind) else round(float(t.lam_when_bind), 1)) for b, t in tab.iterrows()]
        rows_dir = rows if d["auc"] > 0.5 else rows[::-1]
        # thresholds.py rule (2x base or 20%); when base is already high (>25%) use base + 20 pp instead
        cut = max(2 * base_band, 0.20) if base_band < 0.25 else base_band + 0.20
        on = next((rw for rw in rows_dir if rw["n"] >= 30 and rw["p_bind"] >= cut), None)
        lam_all = x.loc[x.bind == 1, "lam"].mean()
        strong = next((rw for rw in rows_dir if rw["lam"] is not None and rw["lam"] >= 2 * lam_all), None)
        unit = UNITS[v.split("_")[0]]
        thr.append(dict(driver=v, unit=unit, bins=rows,
                        p_bind_bottom_decile=rows[0]["p_bind"], p_bind_top_decile=rows[-1]["p_bind"],
                        on_threshold=None if on is None else (f"{v} > {on['lo']:.0f} {unit}" if d["auc"] > 0.5 else f"{v} < {on['hi']:.0f} {unit}"),
                        on_threshold_p_bind=None if on is None else on["p_bind"],
                        strong_lambda_threshold=None if strong is None else (f"{v} > {strong['lo']:.0f} {unit}" if d["auc"] > 0.5 else f"{v} < {strong['hi']:.0f} {unit}"),
                        mean_lambda_when_bind=round(float(lam_all), 1)))
    r["thresholds"] = thr
    # ---- outage lens (daily, within season) ----
    days = pd.Series(pop.index.normalize().unique())
    bind_days = set(dabind.index.normalize().unique())
    o = OUT[OUT.date.isin(days)]
    ez = r["element_zone"]
    if ez: o = o[(o.zone_from == ez) | (o.zone_to == ez)]
    base_day = float(days.isin(bind_days).mean()); orows = []
    for el, grp in o.groupby("element"):
        od = grp.date.unique()
        if len(od) < 15: continue
        cb = sum(1 for d_ in od if d_ in bind_days)
        if cb < 5: continue
        orows.append(dict(element=el, kv=int(grp.kv.iloc[0]), out_days=int(len(od)), co_bind_days=int(cb), p_bind_given_out=round(cb / len(od), 3), lift=round(cb / len(od) / base_day, 2) if base_day else None))
    orows = sorted(orows, key=lambda d: -(d["lift"] or 0))
    r["outage_lens"] = {"base_p_bind_day_in_season": round(base_day, 3), "zone_filter": ez, "top5_by_lift": orows[:5],
                        "informative": bool(orows and orows[0]["lift"] and orows[0]["lift"] >= 1.5)}
    res[cn] = r
    print(f"\n=== {cn} | rel {rel} | base band {base_band:.2f} | band {r['binding_hours']['da'] and r['binding_hours']['da']['peak_band_HE']}")
    for d in rank[:4]: print("   ", d)
    for t in thr: print("    THR", t["driver"], t["on_threshold"], t["on_threshold_p_bind"], "| bottom/top decile", t["p_bind_bottom_decile"], t["p_bind_top_decile"], "| strong", t["strong_lambda_threshold"])
    for o_ in orows[:3]: print("    OUT", o_)

json.dump(res, open(D / "item7_congestion_drivers.json", "w"), indent=1, default=str)

# ---- markdown table ----
def f(v, nd=3): return "n/a" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:+.{nd}f}"
lines = ["| # | constraint | element (zone) | main driver(s) [AUC] | threshold (P(bind) bottom->top decile) | SF RVN real DA/RT | SF proxy DA/RT | SF GKS DA/RT | relation | DA band: P(bind), mean λ | RT band: P(bind), mean λ | forward |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
for i, cn in enumerate(TOP + EXTRA, 1):
    r = res[cn]; sfd = r["shift_factor"]; bd, br = r["binding_hours"]["da"], r["binding_hours"]["rt"]
    drv = "; ".join(f"{d['driver']} {'↑' if d['auc'] > 0.5 else '↓'} [{d['auc']:.2f}]" for d in r["driver_ranking_top8"][:2])
    th = "; ".join(f"{t['on_threshold'] or 'no breakpoint'} ({t['p_bind_bottom_decile']:.0%}->{t['p_bind_top_decile']:.0%})" for t in r["thresholds"])
    rr = sfd["rvn_real_2026_06plus"]; pp = sfd["proxy_blend"]; gg = sfd["gks_bess_rn"]
    lines.append(f"| {i if i <= 10 else 'W'} | **{cn}** | {r['element']} ({r['element_zone']}) | {drv} | {th} | {f(rr['da'])} / {f(rr['rt'])} | {f(pp['da'])} / {f(pp['rt'])} | {f(gg['da'])} / {f(gg['rt'])} | {sfd['relation_rvn_vs_gks']} | "
                 f"{bd['peak_band_HE'] if bd else 'n/a'}: {bd['p_bind_band_mean']:.0%}, ${bd['mean_lambda_band']:.0f} | {br['peak_band_HE'] if br else 'n/a'}: {(br['p_bind_band_mean'] if br else 0):.1%}, ${(br['mean_lambda_band'] if br else 0):.0f} | {r['forward_relevance']} |")
open(D / "item7_congestion_drivers.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\nsaved item7_congestion_drivers.json / .md")
