"""
#94 — Operational Playbook (Q10) — best product + DA/RT mix per 시황 (situation).

User question: 저녁 peak time에 어떤 상품을 어떤 DA/RT 비중으로 들어가야해?

Approach: for each (HE bucket × market condition) bucket, aggregate Strategy C
optimal choices to derive an operational rule:
  - Top product (most frequent winner)
  - DA vs RT share
  - Avg revenue per hour

Time buckets:
  HE 1-6:   Night
  HE 7-10:  Morning ramp
  HE 11-17: Mid-day
  HE 18-22: Evening peak
  HE 23-24: Late evening

Conditions:
  Net-load FC quintile (Q1-Q5)
  Solar FC quintile (Q1-Q5, lower = less solar = more scarcity)
  Wind FC error (under/normal/over)

Output:
  derived/q10_situational_playbook.json
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC = Path(__file__).resolve().parents[1]
DERIVED = ADHOC / "derived"

m = pd.read_parquet(DERIVED / "master_hourly.parquet")
m["datetime_ct"] = pd.to_datetime(m["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
m["he"] = m["datetime_ct"].dt.hour + 1
m["date"] = m["datetime_ct"].dt.date

# Tenaska HSL
thsl = pd.read_parquet(DERIVED / "tenaska_hsl_hourly.parquet")
thsl["datetime_ct"] = pd.to_datetime(thsl["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
m = m.merge(thsl, on="datetime_ct", how="left")
m["hsl"] = m["tenaska_hsl_telemetered"].combine_first(m["avail_discharge_mw"]).fillna(100)
m["soc"] = m["soc_mwh_max"].fillna(200)

PRODS = ["RRS", "ECRS", "NSPIN"]
SOC_DUR = {"RRS": 0.5, "ECRS": 1.0, "NSPIN": 4.0}

# Time buckets
def he_bucket(h: int) -> str:
    if 1 <= h <= 6:   return "Night (HE 1-6)"
    if 7 <= h <= 10:  return "Morning ramp (HE 7-10)"
    if 11 <= h <= 17: return "Mid-day (HE 11-17)"
    if 18 <= h <= 22: return "Evening peak (HE 18-22)"
    return "Late evening (HE 23-24)"

m["he_bucket"] = m["he"].apply(he_bucket)
m["netload_pct"] = m.groupby("he")["NET_LOAD_FORECAST_BID_CLOSE"].rank(pct=True)
m["solar_pct"]   = m.groupby("he")["SOLAR_COPHSL_BIDCLOSE"].rank(pct=True)
m["wind_pct"]    = m.groupby("he")["WIND_STWPF_BIDCLOSE"].rank(pct=True)

n = len(m)
hsl = m["hsl"].values
soc = m["soc"].values

# Build 6 combos (3 products × 2 venues) — Strategy C choice per hour
spreads = {p: m[f"AS_SPREAD_{p}"].values for p in PRODS}
rt_mcpc = {p: m[f"RT_AS_MCPC_{p}"].values for p in PRODS}
combo_revs = []
combo_labels = []
combo_mw = []
for p in PRODS:
    combo_revs.append(hsl * spreads[p])
    combo_mw.append(hsl)
    combo_labels.append(f"{p}_DA")
    rt_cap = np.minimum(hsl, soc / SOC_DUR[p])
    combo_revs.append(rt_cap * rt_mcpc[p])
    combo_mw.append(rt_cap)
    combo_labels.append(f"{p}_RT")
rev_mat = np.stack(combo_revs, axis=1)
mw_mat  = np.stack(combo_mw, axis=1)
winner_idx = np.argmax(rev_mat, axis=1)
winning_rev = rev_mat[np.arange(n), winner_idx]
winning_mw  = mw_mat [np.arange(n), winner_idx]
winning_combo = np.array([combo_labels[i] for i in winner_idx])
winning_product = np.array([c.split("_")[0] for c in winning_combo])
winning_venue   = np.array([c.split("_")[1] for c in winning_combo])

m["winner_combo"]   = winning_combo
m["winner_product"] = winning_product
m["winner_venue"]   = winning_venue
m["winner_rev"]     = winning_rev
m["winner_mw"]      = winning_mw

# Exclude zero-revenue hours (HSL=0 outage)
m_active = m[m["winner_rev"] > 0].copy()
print(f"Total hours: {n}, active (winner_rev>0): {len(m_active)}")
print()


def bucket_summary(label: str, sub: pd.DataFrame) -> dict:
    """Compute summary for a situation bucket."""
    if len(sub) == 0:
        return {"label": label, "hours": 0}
    # Product distribution
    prod_pct = sub["winner_product"].value_counts(normalize=True).mul(100).round(1)
    venue_pct_per_prod = (sub.groupby("winner_product")["winner_venue"]
                          .value_counts(normalize=True).mul(100).round(1).unstack(fill_value=0))
    # DA / RT mix overall in this bucket
    da_pct = (sub["winner_venue"] == "DA").mean() * 100
    rt_pct = 100 - da_pct
    # Per product DA/RT
    prod_venue = {}
    for p in PRODS:
        s_p = sub[sub["winner_product"] == p]
        if len(s_p) == 0:
            prod_venue[p] = {"hours": 0, "share_pct": 0, "da_pct": 0, "rt_pct": 0,
                             "avg_revenue_per_hour": 0, "total_revenue": 0}
        else:
            da_p = (s_p["winner_venue"] == "DA").mean() * 100
            prod_venue[p] = {
                "hours":                int(len(s_p)),
                "share_pct":            round(len(s_p) / len(sub) * 100, 1),
                "da_pct":               round(da_p, 1),
                "rt_pct":               round(100 - da_p, 1),
                "avg_revenue_per_hour": round(float(s_p["winner_rev"].mean()), 0),
                "total_revenue":        round(float(s_p["winner_rev"].sum()), 0),
            }
    top_product = prod_pct.idxmax() if len(prod_pct) else None
    return {
        "label":               label,
        "hours":               int(len(sub)),
        "avg_winner_rev_usd_per_hour": round(float(sub["winner_rev"].mean()), 0),
        "total_revenue":       round(float(sub["winner_rev"].sum()), 0),
        "top_product":         top_product,
        "product_distribution_pct": {p: round(float(prod_pct.get(p, 0)), 1) for p in PRODS},
        "overall_da_pct":      round(float(da_pct), 1),
        "overall_rt_pct":      round(float(rt_pct), 1),
        "per_product":         prod_venue,
    }


# ---------- Level 1: by HE bucket only ----------
print("=" * 90)
print("LEVEL 1 — by HE bucket only (5 buckets)")
print("=" * 90)
bucket_order = ["Night (HE 1-6)", "Morning ramp (HE 7-10)", "Mid-day (HE 11-17)",
                "Evening peak (HE 18-22)", "Late evening (HE 23-24)"]
playbook_l1 = {}
for b in bucket_order:
    s = bucket_summary(b, m_active[m_active["he_bucket"] == b])
    playbook_l1[b] = s
    print(f"\n{b}:")
    print(f"  Hours: {s['hours']:>4d}  ·  Avg revenue/hr: ${s['avg_winner_rev_usd_per_hour']:>5,.0f}  ·  Top product: {s['top_product']}")
    print(f"  Product mix:  RRS {s['product_distribution_pct']['RRS']:>4.0f}%  ·  ECRS {s['product_distribution_pct']['ECRS']:>4.0f}%  ·  NSPIN {s['product_distribution_pct']['NSPIN']:>4.0f}%")
    print(f"  Overall DA/RT: {s['overall_da_pct']:.0f}% / {s['overall_rt_pct']:.0f}%")
    for p in PRODS:
        pv = s["per_product"][p]
        if pv["hours"] > 0:
            print(f"    {p:6s}  {pv['hours']:>3d} hrs ({pv['share_pct']:>4.0f}%)  DA/RT {pv['da_pct']:>4.0f}/{pv['rt_pct']:>3.0f}  avg ${pv['avg_revenue_per_hour']:>5,.0f}/hr")


# ---------- Level 2: by HE bucket × net-load quintile ----------
print()
print("=" * 90)
print("LEVEL 2 — by HE bucket × Net-Load Forecast quintile (focus on Evening peak)")
print("=" * 90)
m_active["netload_quintile"] = pd.qcut(m_active["netload_pct"], 5,
                                        labels=["Q1 low","Q2","Q3","Q4","Q5 high"])
playbook_l2 = {}
for b in bucket_order:
    sub_b = m_active[m_active["he_bucket"] == b]
    playbook_l2[b] = {}
    print(f"\n{b}:")
    for q in ["Q1 low","Q2","Q3","Q4","Q5 high"]:
        s = bucket_summary(f"{b} × NetLoad {q}", sub_b[sub_b["netload_quintile"] == q])
        playbook_l2[b][q] = s
        if s["hours"] > 0:
            print(f"  NetLoad {q:8s}: {s['hours']:>3d} hrs  top={s['top_product']:5s}  "
                  f"RRS/ECRS/NSPIN = {s['product_distribution_pct']['RRS']:>3.0f}/{s['product_distribution_pct']['ECRS']:>3.0f}/{s['product_distribution_pct']['NSPIN']:>3.0f}%  "
                  f"DA/RT {s['overall_da_pct']:>3.0f}/{s['overall_rt_pct']:>3.0f}%  avg ${s['avg_winner_rev_usd_per_hour']:>5,.0f}/hr")


# ---------- Level 3: Evening peak deep-dive — HE × Solar quintile ----------
print()
print("=" * 90)
print("LEVEL 3 — Evening peak (HE 18-22) deep-dive: Solar quintile + HE")
print("=" * 90)
evening = m_active[m_active["he_bucket"] == "Evening peak (HE 18-22)"].copy()
evening["solar_quintile"] = pd.qcut(evening["solar_pct"], 5,
                                     labels=["Q1 low","Q2","Q3","Q4","Q5 high"],
                                     duplicates="drop")
playbook_l3 = {}
print(f"\n  By HE within Evening peak:")
for he in [18, 19, 20, 21, 22]:
    s = bucket_summary(f"HE {he}", evening[evening["he"] == he])
    playbook_l3[f"HE{he}"] = s
    if s["hours"] > 0:
        print(f"    HE {he}: {s['hours']:>3d} hrs  top={s['top_product']:5s}  "
              f"RRS/ECRS/NSPIN = {s['product_distribution_pct']['RRS']:>3.0f}/{s['product_distribution_pct']['ECRS']:>3.0f}/{s['product_distribution_pct']['NSPIN']:>3.0f}%  "
              f"DA/RT {s['overall_da_pct']:>3.0f}/{s['overall_rt_pct']:>3.0f}%  avg ${s['avg_winner_rev_usd_per_hour']:>5,.0f}/hr")

print(f"\n  By Solar quintile within Evening peak:")
solar_playbook = {}
for q in ["Q1 low","Q2","Q3","Q4","Q5 high"]:
    s = bucket_summary(f"Evening × Solar {q}", evening[evening["solar_quintile"] == q])
    solar_playbook[q] = s
    if s["hours"] > 0:
        print(f"    Solar {q:8s}: {s['hours']:>3d} hrs  top={s['top_product']:5s}  "
              f"RRS/ECRS/NSPIN = {s['product_distribution_pct']['RRS']:>3.0f}/{s['product_distribution_pct']['ECRS']:>3.0f}/{s['product_distribution_pct']['NSPIN']:>3.0f}%  "
              f"DA/RT {s['overall_da_pct']:>3.0f}/{s['overall_rt_pct']:>3.0f}%  avg ${s['avg_winner_rev_usd_per_hour']:>5,.0f}/hr")

# Save
out = {
    "level_1_by_he_bucket":              playbook_l1,
    "level_2_he_bucket_x_netload":       playbook_l2,
    "level_3_evening_peak_by_he":        playbook_l3,
    "level_3_evening_peak_by_solar":     solar_playbook,
}
(DERIVED / "q10_situational_playbook.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print()
print(f"saved -> derived/q10_situational_playbook.json")
