"""Build per-constraint dashboard DATA PACKS for Cluster D LIVE constraints
(BRUNI_69_1, LOYOLA_69_1, LASCRU_MILO1_1) per DATAPACK_SCHEMA.md.

REUSE: clusterD_stats.json (lambda summary, cum impact, contingencies),
       clusterD_month_hour.json (cum-$ heatmaps -> seasonality text),
       clusterD_driver_wind.txt / plan (drivers, rule of thumb).
NEW-COMPUTE here:
  section2  P(bind) month x hour matrices (DA + RT) via calendar denominator
            (parquet is binding-rows-only -> denominator from full data span).
  section3  GR_SOUTH wind GW breakpoint -> conditional P(bind) + lambda, per
            constraint window.
  section5  SOUTH-zone transmission-outage -> binding seasonality-adjusted lift.

REAL data only (Yes Energy datalake S3). impact = -SF*lambda. Karpathy: only the
pieces the task needs; null where genuinely unknown. R&R = congestion (MCC) only.
"""
from __future__ import annotations
import sys, json
import concurrent.futures as cf
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, r'C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts')
import dl

D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
GR_SOUTH = 10004189447
TARGETS = ["BRUNI_69_1", "LOYOLA_69_1", "LASCRU_MILO1_1"]

# window in HOUR-OF-DAY (0..23, period-ending hourly to match wind_rti & driver).
# HE n covers hour-of-day (n-1). BRUNI HE22-07 -> hod 21..06; LOYOLA HE18-21 -> 17..20;
# LASCRU HE18-23 (evening/overnight) -> 17..22.
WINDOW_HOD = {
    "BRUNI_69_1":     [21, 22, 23, 0, 1, 2, 3, 4, 5, 6],
    "LOYOLA_69_1":    [17, 18, 19, 20],
    "LASCRU_MILO1_1": [17, 18, 19, 20, 21, 22],
}

# ----------------------------------------------------------------------------
# Load binding rows
# ----------------------------------------------------------------------------
raw = pd.read_parquet(D / "gks_msf_raw.parquet")
raw = raw[raw["SHADOWPRICE"] > 0].copy()
raw["dt"] = pd.to_datetime(raw["DATETIME"], format="%m/%d/%Y %H:%M:%S")
raw["date"] = raw["dt"].dt.normalize()
raw["month"] = raw["dt"].dt.month
raw["hod"] = raw["dt"].dt.hour          # 0..23 hour-of-day
raw["he"] = raw["dt"].dt.hour + 1       # 1..24 hour-ending
SPAN_LO, SPAN_HI = raw["dt"].min().normalize(), raw["dt"].max().normalize()

# calendar: days per (month) over the data span (denominator base)
cal = pd.date_range(SPAN_LO, SPAN_HI, freq="D")
days_per_month = pd.Series(cal.month).value_counts().to_dict()   # month -> #days in span

# ----------------------------------------------------------------------------
# SECTION 2 : P(bind) month x hour matrices  (rows month 1..12, cols HE1..HE24)
#   DA: 1 interval/hour/day -> denom = days_per_month
#   RT: 12 five-min/hour/day -> denom = days_per_month*12
# ----------------------------------------------------------------------------
def pbind_matrix(sub, mkt):
    m = sub[sub.MARKET == mkt]
    mat = []
    for mon in range(1, 13):
        dm = days_per_month.get(mon, 0)
        row = []
        for he in range(1, 25):
            cell = m[(m.month == mon) & (m.he == he)]
            if dm == 0:
                row.append(None); continue
            if mkt == "DA":
                num = cell["date"].nunique()          # <=1 DA hour/day
                denom = dm
            else:
                num = cell["dt"].nunique()             # distinct 5-min
                denom = dm * 12
            row.append(round(num / denom, 3))
        mat.append(row)
    return mat

# ----------------------------------------------------------------------------
# SECTION 3 : GR_SOUTH wind GW breakpoints -> conditional P(bind) + lambda
# ----------------------------------------------------------------------------
WIND_CACHE = D / "gr_south_wind_span.parquet"

def load_wind():
    if WIND_CACHE.exists():
        print("loading cached GR_SOUTH wind", WIND_CACHE.name)
        return pd.read_parquet(WIND_CACHE)
    days = [d.strftime("%Y%m%d") for d in cal]
    def f(d):
        try:
            df = dl.read_csv(f"ercot/gen/wind_rti/{d}.csv.gz", header=None)
            return df[df[0] == GR_SOUTH]
        except Exception:
            return None
    out, done = [], 0
    with cf.ThreadPoolExecutor(max_workers=24) as ex:
        for r in ex.map(f, days):
            done += 1
            if r is not None and len(r):
                out.append(r)
            if done % 200 == 0:
                print(f"  wind days {done}/{len(days)} with-data={len(out)}", flush=True)
    w = pd.concat(out, ignore_index=True)
    w.columns = ["OBJ", "DTYPE", "DATETIME", "TZ", "WIND_MW", "LOADID"][:w.shape[1]]
    w["dt"] = pd.to_datetime(w["DATETIME"], format="%m/%d/%Y %H:%M:%S")
    w["date"] = w["dt"].dt.normalize()
    w["hod"] = w["dt"].dt.hour
    w = w[["date", "hod", "WIND_MW"]].dropna()
    w["WIND_MW"] = pd.to_numeric(w["WIND_MW"], errors="coerce")
    w = w.dropna().drop_duplicates(["date", "hod"])
    w.to_parquet(WIND_CACHE)
    print("cached", WIND_CACHE.name, len(w), "hour rows")
    return w

WBINS = [0, 500, 1000, 1500, 2000, 2500, 1e9]
WLAB = ["<0.5", "0.5-1.0", "1.0-1.5", "1.5-2.0", "2.0-2.5", ">2.5"]

def wind_thresholds(cname, wind):
    hods = WINDOW_HOD[cname]
    # universe: every (date,hod) in window with wind obs
    u = wind[wind.hod.isin(hods)].copy()
    # DA binding flag on (date,hod)
    b = raw[(raw.CONSTRAINTNAME == cname) & (raw.MARKET == "DA")]
    bind_keys = set(zip(b.date, b.hod))
    u["bind"] = [(r.date, r.hod) in bind_keys for r in u.itertuples()]
    # lambda lookup for binding window hours (DA)
    lam_map = b.groupby(["date", "hod"]).SHADOWPRICE.max().to_dict()
    u["lam"] = [lam_map.get((r.date, r.hod), np.nan) for r in u.itertuples()]
    u["wbin"] = pd.cut(u.WIND_MW, WBINS, labels=WLAB, right=False)
    rows = []
    for lab in WLAB:
        g = u[u.wbin == lab]
        if len(g) < 20:           # min support
            rows.append((lab, len(g), None, None, None)); continue
        pb = g.bind.mean()
        lam = g[g.bind].lam
        rows.append((lab, len(g), round(pb, 3),
                     round(float(lam.median()), 0) if len(lam) else None,
                     round(float(lam.quantile(.90)), 0) if len(lam) else None))
    return rows

# ----------------------------------------------------------------------------
# SECTION 5 : SOUTH-zone outage -> binding seasonality-adjusted lift
# ----------------------------------------------------------------------------
OUT_COLS = ["ISO", "FACILITY", "FROMSTATION", "TOSTATION", "KV", "FROMZONE", "TOZONE",
            "FACILITY_TYPE", "TYPE", "TYPE_DETAIL", "STATUS", "STATUS_DETAIL", "STARTDATE",
            "ENDDATE", "PLANNED_STARTDATE", "PLANNED_ENDDATE", "OPEN_CLOSE", "TICKETID",
            "FACILITYID", "LASTCHANGEDATE", "PUBLISHDATE", "REPORTED_NAME", "FROMSTATIONID", "TOSTATIONID"]
OUT_CACHE = D / "outage_panel_south_69up.parquet"
MIN_KV_OUT = 69
MIN_SUPPORT = 20

def load_outage_panel():
    if OUT_CACHE.exists():
        print("loading cached outage panel", OUT_CACHE.name)
        return pd.read_parquet(OUT_CACHE)
    def one(d):
        ymd = d.strftime("%Y%m%d")
        df = dl.try_read_csv(f"ercot/transmission/outages/actual/{ymd}12.csv.gz", header=None)
        if df is None:
            return None
        df.columns = OUT_COLS[:df.shape[1]]
        df = df[df["STATUS"].astype(str).str.upper() == "ACTIVE"].copy()
        df["kvn"] = pd.to_numeric(df["KV"], errors="coerce")
        df = df[(df["kvn"] >= MIN_KV_OUT) & (df["FROMZONE"] == "SOUTH")]
        if df.empty:
            return None
        o = df[["FACILITYID", "FACILITY", "kvn", "FROMSTATION", "TOSTATION", "FROMZONE"]].drop_duplicates("FACILITYID")
        o["date"] = d.normalize()
        return o
    parts, done = [], 0
    with cf.ThreadPoolExecutor(max_workers=24) as ex:
        for r in ex.map(one, cal):
            done += 1
            if r is not None:
                parts.append(r)
            if done % 200 == 0:
                print(f"  outage days {done}/{len(cal)} with-data={len(parts)}", flush=True)
    panel = pd.concat(parts, ignore_index=True)
    panel.to_parquet(OUT_CACHE)
    print("cached", OUT_CACHE.name, len(panel), "(facility,day) rows")
    return panel

def outage_lift(cname, panel):
    # day-level binding (any DA binding hour that day)
    b = raw[(raw.CONSTRAINTNAME == cname) & (raw.MARKET == "DA")]
    bind_by_day = b.groupby("date").size()
    have = set(panel.date.unique())
    universe = pd.DatetimeIndex(sorted(d for d in cal if d in have))
    bind_day = pd.Series([1 if (d in bind_by_day.index and bind_by_day[d] > 0) else 0 for d in universe], index=universe)
    base = float(bind_day.mean())
    mon = pd.Series(universe.month, index=universe)
    month_base = bind_day.groupby(mon).mean()
    day_exp = mon.map(month_base)

    p = panel[panel.date.isin(universe)].copy()
    p["bind"] = p.date.map(bind_day.to_dict()).astype(int)
    p["exp"] = p.date.map(day_exp.to_dict()).astype(float)
    # station-level (dedupe equipment within station-day) - more interpretable
    sd = p.drop_duplicates(["FROMSTATION", "date"])
    g = sd.groupby(["FROMSTATION", "FROMZONE"]).agg(
        days_out=("date", "nunique"), days_out_bind=("bind", "sum"),
        exp_bind=("exp", "sum"), kv=("kvn", "max")).reset_index()
    g["p_bind_given_out"] = g.days_out_bind / g.days_out
    g["seas_lift"] = g.days_out_bind / g.exp_bind.replace(0, np.nan)
    g = g[(g.days_out >= MIN_SUPPORT)].sort_values(["seas_lift", "days_out_bind"], ascending=False)
    return g, base, {int(k): round(float(v), 3) for k, v in month_base.items()}

# ----------------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    print("span", SPAN_LO.date(), "->", SPAN_HI.date(), "days/month", days_per_month)
    sec2 = {}
    for t in TARGETS:
        sub = raw[raw.CONSTRAINTNAME == t]
        sec2[t] = {"da_pbind": pbind_matrix(sub, "DA"), "rt_pbind": pbind_matrix(sub, "RT")}
    json.dump(sec2, open(D / "clusterD_pbind_matrix.json", "w"), indent=1)
    print("saved clusterD_pbind_matrix.json")

    wind = load_wind()
    sec3 = {}
    for t in TARGETS:
        sec3[t] = wind_thresholds(t, wind)
        print(f"\n=== SECTION3 {t}  window-hod {WINDOW_HOD[t]} ===")
        for lab, n, pb, lm, l90 in sec3[t]:
            print(f"  {lab:8s} GW  n={n:5d}  P(bind)={pb}  lam_med={lm}  lam_p90={l90}")
    json.dump(sec3, open(D / "clusterD_wind_thresholds.json", "w"), indent=1)
    print("saved clusterD_wind_thresholds.json")

    panel = load_outage_panel()
    sec5 = {}
    for t in TARGETS:
        g, base, mb = outage_lift(t, panel)
        sec5[t] = {"base": base, "month_base": mb,
                   "rows": g.head(12).to_dict("records")}
        print(f"\n=== SECTION5 {t}  base P(bind/day)={base:.3f} ===")
        print(g.head(12)[["FROMSTATION", "kv", "days_out", "days_out_bind", "p_bind_given_out", "seas_lift"]].to_string(index=False))
    # convert numpy types for json
    def clean(o):
        if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
        if isinstance(o, list): return [clean(x) for x in o]
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return round(float(o), 3)
        return o
    json.dump(clean(sec5), open(D / "clusterD_outage_lift.json", "w"), indent=1)
    print("\nsaved clusterD_outage_lift.json")
