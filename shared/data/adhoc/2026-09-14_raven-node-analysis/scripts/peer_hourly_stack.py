"""Houston top-3 BESS peers — average hourly product stack (post-RTC+B, 2025-12-05 .. 2026-07-17).

Peers = top 3 SITES by $/MW among Raven-comparable Houston BESS (2h, >=50MW) in the Jan-May 2026 ranking:
  WAL (Tesla, WAL_ESR1), CLO (Jupiter, CLO_ESR1+CLO_ESR2 combined), LON (Tokyo Gas, LON_ESR1).
GKS_BESS_ESR1 carried as a reference.

Source: ERCOT 60-day disclosure, per-operating-date cache written by skills/estimate-bess-energy-as
  (dam_disclosure_{date}: 60d DAM ESR Data; sced_disclosure_{date}: 60d ESR Data in SCED).
Parsing reuses the skill's own parsers (no re-implementation of field mapping). No new downloads.

Per site x hour-ending, as % of site capacity (max observed HSL):
  DA  : DA energy award (+discharge / -charge), DA AS awards by product
  RT  : telemetered net output (+discharge / -charge), RT (SCED) AS awards by product
Real data only.
"""
import sys, os, hashlib, json
from datetime import date, timedelta
from pathlib import Path
import numpy as np, pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
SKILL = ROOT / "skills/estimate-bess-energy-as/scripts"
sys.path.insert(0, str(SKILL))
import config  # noqa: E402
from src.data_fetcher import _parse_dam_esr, _parse_dam_esr_as_awards, _parse_sced_esr  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "derived"
SITES = {"WAL": ["WAL_ESR1"], "CLO": ["CLO_ESR1", "CLO_ESR2"], "LON": ["LON_ESR1"], "GKS": ["GKS_BESS_ESR1"]}
RES = [r for v in SITES.values() for r in v]
SITE_OF = {r: s for s, v in SITES.items() for r in v}


def cpath(key):
    return os.path.join(config.DATA_CACHE_DIR, "ercot_api_" + hashlib.md5(key.encode()).hexdigest() + ".parquet")


def read_filtered(path, want_cols=None):
    cols = pq.read_schema(path).names
    use = [c for c in cols if want_cols is None or c in want_cols]
    t = pq.read_table(path, columns=use, filters=[("Resource Name", "in", RES)])
    return t.to_pandas()


COLSETS = {}
rows_da, rows_rt, days_used = [], [], []
d = date(2025, 12, 5)
while d <= date(2026, 7, 17):
    pdam, psced = cpath(f"dam_disclosure_{d}"), cpath(f"sced_disclosure_{d}")
    if os.path.exists(pdam) and os.path.exists(psced):
        dam = read_filtered(pdam)
        # column sets differ across files (e.g. RTC+B go-live day) -> select per file, never reuse
        names = pq.read_schema(psced).names
        keep_kw = ("SCED Time Stamp", "Resource Name", "Telemetered Net Output", "Base Point", "HSL", "LSL",
                   "State of Charge", "AS Awards", "Repeated Hour Flag")
        SCED_COLS = [c for c in names if any(k.lower() in c.lower() for k in keep_kw)]
        COLSETS.setdefault(tuple(sorted(c for c in SCED_COLS if "Awards" in c)), []).append(d)
        sced = read_filtered(psced, SCED_COLS)
        if not dam.empty and not sced.empty:
            e = _parse_dam_esr(dam)
            a = _parse_dam_esr_as_awards(dam)
            da = e.merge(a, on=["datetime", "resource_name"], how="left")
            da["day"] = pd.Timestamp(d)
            rows_da.append(da)
            rt = _parse_sced_esr(sced)
            # hour-ending: SCED stamps within (HE-1, HE] -> ceil to the hour
            rt["he_ts"] = rt["datetime"].dt.ceil("h")
            g = rt.groupby(["resource_name", "he_ts"]).agg(
                rt_mw=("rt_mw", "mean"), hsl=("hsl", "max"),
                rt_regup_mw=("rt_regup_mw", "mean"), rt_regdn_mw=("rt_regdn_mw", "mean"),
                rt_rrs_mw=("rt_rrs_mw", "mean"), rt_ecrs_mw=("rt_ecrs_mw", "mean"),
                rt_nonspin_mw=("rt_nonspin_mw", "mean")).reset_index()
            g["day"] = pd.Timestamp(d)
            rows_rt.append(g)
            days_used.append(d)
    d += timedelta(days=1)

DA = pd.concat(rows_da, ignore_index=True)
RT = pd.concat(rows_rt, ignore_index=True)
for k, v in COLSETS.items():
    print("AS award column set:", k, "days", len(v), v[0], "..", v[-1])
print(f"days used: {len(days_used)} ({days_used[0]} .. {days_used[-1]})  DA rows {len(DA):,}  RT rows {len(RT):,}")

DA["site"] = DA.resource_name.map(SITE_OF)
RT["site"] = RT.resource_name.map(SITE_OF)
for c in ["rt_regup_mw", "rt_regdn_mw", "rt_rrs_mw", "rt_ecrs_mw", "rt_nonspin_mw"]:
    neg = (RT[c] < 0).sum()
    if neg:
        bad_days = sorted({str(x.date()) for x in RT.loc[RT[c] < 0, "day"]})
        print(f"WARNING {c}: {neg} negative hourly values (min {RT[c].min():.0f}) on days {bad_days} -> set to NaN (an AS award cannot be negative)")
        RT.loc[RT[c] < 0, c] = np.nan
DA["he"] = DA.datetime.dt.hour.where(DA.datetime.dt.hour != 0, 24)
RT["he"] = RT.he_ts.dt.hour.where(RT.he_ts.dt.hour != 0, 24)

# site capacity = max observed HSL summed across the site's units (prior denominator bug: never trust static CSV)
cap = RT.groupby(["site", "resource_name"]).hsl.max().groupby("site").sum()
print("site capacity (max HSL, MW):", cap.round(0).to_dict())

# sign sanity: DA award & RT output should be negative when charging
print("DA award min/max by site:", DA.groupby("site").da_mw.agg(["min", "max"]).round(0).to_dict(orient="index"))
print("RT output min/max by site:", RT.groupby("site").rt_mw.agg(["min", "max"]).round(0).to_dict(orient="index"))

# site-level hourly sums first (combine CLO units), then average over days
DA_PROD = ["da_mw", "da_regup_mw", "da_regdn_mw", "da_rrs_mw", "da_ecrs_mw", "da_nonspin_mw"]
RT_PROD = ["rt_mw", "rt_regup_mw", "rt_regdn_mw", "rt_rrs_mw", "rt_ecrs_mw", "rt_nonspin_mw"]
DA["da_dis"] = DA.da_mw.clip(lower=0); DA["da_chg"] = DA.da_mw.clip(upper=0)
RT["rt_dis"] = RT.rt_mw.clip(lower=0); RT["rt_chg"] = RT.rt_mw.clip(upper=0)
dsite = DA.groupby(["site", "day", "he"])[DA_PROD + ["da_dis", "da_chg"]].sum().reset_index()
rsite = RT.groupby(["site", "day", "he"])[RT_PROD + ["rt_dis", "rt_chg"]].sum().reset_index()
m = dsite.merge(rsite, on=["site", "day", "he"], how="inner")
m["season"] = np.where(m.day.dt.month.isin([6, 7, 8]), "여름(6~7월)", "겨울·봄(12~5월)")

def profile(df):
    g = df.drop(columns=["day"]).groupby(["site", "he"]).mean(numeric_only=True)
    denom = g.index.get_level_values("site").map(cap).astype(float).values
    return g.div(denom, axis=0) * 100

prof_all = profile(m)
prof_season = {s: profile(m[m.season == s]) for s in m.season.unique()}

# 3-peer average (equal weight per site, as % of capacity)
peers = ["WAL", "CLO", "LON"]
avg_all = prof_all.loc[peers].groupby("he").mean()
avg_season = {s: p.loc[[x for x in peers if x in p.index.get_level_values(0)]].groupby("he").mean() for s, p in prof_season.items()}

pd.set_option("display.width", 250)
show = ["da_dis", "da_chg", "da_regup_mw", "da_regdn_mw", "da_rrs_mw", "da_ecrs_mw", "da_nonspin_mw",
        "rt_dis", "rt_chg", "rt_regup_mw", "rt_regdn_mw", "rt_rrs_mw", "rt_ecrs_mw", "rt_nonspin_mw"]
print("\n=== 3-peer average, % of capacity by HE (all days) ===")
print(avg_all[show].round(1).to_string())
print("\n=== GKS, % of capacity by HE ===")
print(prof_all.loc["GKS"][show].round(1).to_string())

# daily summary per site: avg MW-hours share
def summary(p):
    return {
        "da_discharge_hours_equiv": float(p.da_dis.sum() / 100), "da_charge_hours_equiv": float(-p.da_chg.sum() / 100),
        "rt_discharge_hours_equiv": float(p.rt_dis.sum() / 100), "rt_charge_hours_equiv": float(-p.rt_chg.sum() / 100),
        "avg_as_pct_da": float(p[["da_regup_mw", "da_regdn_mw", "da_rrs_mw", "da_ecrs_mw", "da_nonspin_mw"]].sum(axis=1).mean()),
        "avg_as_pct_rt": float(p[["rt_regup_mw", "rt_regdn_mw", "rt_rrs_mw", "rt_ecrs_mw", "rt_nonspin_mw"]].sum(axis=1).mean()),
        "da_energy_share_of_rt_discharge": float(p.da_dis.sum() / p.rt_dis.sum()) if p.rt_dis.sum() else None,
        "top_discharge_he_rt": [int(x) for x in p.rt_dis.sort_values(ascending=False).index[:4]],
        "top_charge_he_rt": [int(x) for x in p.rt_chg.sort_values().index[:4]],
    }
summ = {s: summary(prof_all.loc[s]) for s in SITES}
summ["PEER_AVG"] = summary(avg_all)
for s in ["PEER_AVG", "WAL", "CLO", "LON", "GKS"]:
    print(s, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in summ[s].items()})

def to_json(p):
    return {c: [round(float(p.loc[h, c]), 2) if h in p.index else 0.0 for h in range(1, 25)] for c in show}

out = {
    "window": f"{days_used[0]} .. {days_used[-1]} ({len(days_used)} days, post-RTC+B)",
    "capacity_mw": {k: float(v) for k, v in cap.items()},
    "profiles": {"PEER_AVG": to_json(avg_all), **{s: to_json(prof_all.loc[s]) for s in SITES}},
    "profiles_season": {s: {"PEER_AVG": to_json(p)} for s, p in avg_season.items()},
    "summary": summ,
    "units": "percent of site capacity (max observed HSL); discharge +, charge -; AS = awarded MW",
}
json.dump(out, open(OUT / "peer_hourly_stack.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("\nwrote peer_hourly_stack.json")
