"""Cluster A (POS/discharge) section5 outage->binding lift for HAINE__LA_PAL1_1 & 421__A.

Mirrors the Houston outage_binding_lift.py method (REAL Yes Energy datalake, no mock):
  - daily midday outage snapshot (HE13 file = ...12.csv.gz), STATUS==Active.
  - targeted to the relevant station tokens per constraint (138kV RGV local for HAINE,
    345 Central-TX Sandow/BCESW/BGRSW/YARSW seam for 421__A), so the panel stays small.
  - day-level binding flag per constraint from gks_msf_raw.parquet (DA, SHADOWPRICE>0).
  - per-facility & per-station: days_out, co-bind, P(bind|out), raw lift, seasonality-adj lift.

Regime windows: HAINE binds full node window; 421__A is a 2025-onset (growing) constraint,
so its regime starts 2025-01-01 to avoid inflating lift with the near-zero 2024 base.
Caveat: co-occurrence != causation; lift = weakening-outage signature, not NMMS contingency
membership (that file is MIS Secure-Area only)."""
from __future__ import annotations
import concurrent.futures as cf
import json
from pathlib import Path
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")
import dl

OUT_COLS = ["ISO","FACILITY","FROMSTATION","TOSTATION","KV","FROMZONE","TOZONE",
            "FACILITY_TYPE","TYPE","TYPE_DETAIL","STATUS","STATUS_DETAIL","STARTDATE",
            "ENDDATE","PLANNED_STARTDATE","PLANNED_ENDDATE","OPEN_CLOSE","TICKETID",
            "FACILITYID","LASTCHANGEDATE","PUBLISHDATE","REPORTED_NAME","FROMSTATIONID","TOSTATIONID"]

D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
WINDOW_START, WINDOW_END = "2024-07-03", "2026-06-08"
MIN_KV = 138
CACHE = D / "clusterA_outage_panel.parquet"

# station tokens that matter for each constraint's relief geography
TOKENS = [
    # 421__A central-TX seam
    "BCESW", "BGRSW", "SNDSW", "SANDOW", "YARSW", "GDLSW", "BERGSTROM", "BRGSW",
    "SALADO", "HUTTO", "BELL COUNTY", "BELCNTY",
    # HAINE RGV local
    "LA PALMA", "LA_PALMA", "HAINE", "KINGFISHER", "KNGFSHER", "RAYMONDVILLE",
    "RAYRI", "HARLINGEN", "HARNED", "SAN BENITO", "RIO HONDO", "EDINBURG",
    "MERCEDES", "WESLACO", "LON HILL", "SAJO", "BONRIO",
]
TOKENS_U = [t.upper() for t in TOKENS]

REGIME = {
    "HAINE__LA_PAL1_1": ("2024-07-03", "2026-06-08"),
    "421__A":           ("2025-01-01", "2026-06-08"),
}
MIN_SUPPORT = 15
MIN_COBIND = 8


def one_day(d):
    ymd = d.strftime("%Y%m%d")
    df = dl.try_read_csv(f"ercot/transmission/outages/actual/{ymd}12.csv.gz", header=None)
    if df is None:
        return None
    df.columns = OUT_COLS[:df.shape[1]]
    df = df[df["STATUS"].astype(str).str.upper() == "ACTIVE"].copy()
    df["kvn"] = pd.to_numeric(df["KV"], errors="coerce")
    fs = df["FROMSTATION"].astype(str).str.upper()
    ts = df["TOSTATION"].astype(str).str.upper()
    tokmask = False
    for tok in TOKENS_U:
        tokmask = tokmask | fs.str.contains(tok, regex=False) | ts.str.contains(tok, regex=False)
    df = df[(df["kvn"] >= MIN_KV) & tokmask]
    if df.empty:
        return None
    out = df[["FACILITYID", "FACILITY", "kvn", "FROMSTATION", "TOSTATION", "FROMZONE", "TYPE"]].drop_duplicates("FACILITYID")
    out["date"] = d.normalize()
    return out


def build_panel(days):
    if CACHE.exists():
        print("loading cached", CACHE.name)
        return pd.read_parquet(CACHE)
    parts, done = [], 0
    with cf.ThreadPoolExecutor(max_workers=24) as ex:
        for r in ex.map(one_day, days):
            done += 1
            if r is not None:
                parts.append(r)
            if done % 150 == 0:
                print(f"  scanned {done}/{len(days)} with-data={len(parts)}", flush=True)
    panel = pd.concat(parts, ignore_index=True)
    panel.to_parquet(CACHE)
    print(f"cached {CACHE.name}: {len(panel)} (facility,day) rows, {panel.date.nunique()} days, "
          f"{panel.FACILITYID.nunique()} facilities")
    return panel


def bind_days(raw):
    da = raw[(raw.MARKET == "DA") & (raw.SHADOWPRICE > 0)].copy()
    da["date"] = pd.to_datetime(da.DATETIME, format="%m/%d/%Y %H:%M:%S").dt.normalize()
    out = {}
    for c in REGIME:
        g = da[da.CONSTRAINTNAME == c]
        out[c] = g.groupby("date").size().rename("bind_hours")
    return out


def lift(panel, binders, constraint):
    lo, hi = REGIME[constraint]
    days_in = pd.date_range(lo, hi, freq="D")
    have = set(panel.date.unique())
    universe = pd.DatetimeIndex([d for d in days_in if d in have])
    bh = binders[constraint].reindex(universe).fillna(0)
    bind_day = pd.Series((bh.values > 0).astype(int), index=universe)
    base = float(bind_day.mean())
    mon = pd.Series(universe.month, index=universe)
    month_base = bind_day.groupby(mon).mean()
    day_exp = mon.map(month_base)

    p = panel[panel.date.isin(universe)].copy()
    p["bind"] = p.date.map(bind_day.to_dict()).astype(int)
    p["exp"] = p.date.map(day_exp.to_dict()).astype(float)

    # station-level (dedupe equipment within station-day)
    sd = p.drop_duplicates(["FROMSTATION", "date"])
    g = sd.groupby(["FROMSTATION", "FROMZONE"]).agg(
        days_out=("date", "nunique"), days_out_bind=("bind", "sum"),
        exp_bind=("exp", "sum")).reset_index()
    g["p_bind_given_out"] = g.days_out_bind / g.days_out
    g["raw_lift"] = g.p_bind_given_out / base if base else np.nan
    g["seas_lift"] = g.days_out_bind / g.exp_bind.replace(0, np.nan)
    g = g.sort_values(["seas_lift", "days_out_bind"], ascending=False)

    cc = p.groupby("date").FROMSTATION.nunique().reindex(universe).fillna(0)
    meta = dict(constraint=constraint, window=f"{lo}..{hi}", n_days=int(len(universe)),
                n_bind=int(bind_day.sum()), base_pbind_per_day=round(base, 4),
                mean_stations_out_on_bind=round(float(cc[bind_day == 1].mean()), 2),
                mean_stations_out_off_bind=round(float(cc[bind_day == 0].mean()), 2),
                month_base={int(k): round(v, 3) for k, v in month_base.items()})
    return g, meta


def main():
    raw = pd.read_parquet(D / "gks_msf_raw.parquet")
    days = pd.date_range(WINDOW_START, WINDOW_END, freq="D")
    panel = build_panel(days)
    binders = bind_days(raw)
    result = {}
    pd.set_option("display.width", 240)
    for c in REGIME:
        g, meta = lift(panel, binders, c)
        rows = []
        gq = g[(g.days_out >= MIN_SUPPORT) & (g.days_out_bind >= MIN_COBIND)]
        for _, r in gq.head(20).iterrows():
            rows.append(dict(station=r.FROMSTATION, zone=r.FROMZONE, out_days=int(r.days_out),
                             co_bind=int(r.days_out_bind), p_bind_given_out=round(float(r.p_bind_given_out), 3),
                             raw_lift=round(float(r.raw_lift), 2),
                             seas_lift=None if pd.isna(r.seas_lift) else round(float(r.seas_lift), 2)))
        result[c] = dict(meta=meta, stations=rows)
        print("\n" + "=" * 90)
        print(c, meta)
        print(pd.DataFrame(rows).to_string(index=False) if rows else "  (no station met support thresholds)")
    json.dump(result, open(D / "clusterA_outage_lift.json", "w"), indent=2)
    print("\nsaved", D / "clusterA_outage_lift.json")


if __name__ == "__main__":
    main()
