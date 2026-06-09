"""STEP 2 fallback: empirical outage -> binding conditional-lift for MDOPHR99_A & STPWAP39_1.

Authoritative contingency-member lists are NOT in the datalake (and the ERCOT CRR
Network Model 'Contingencies' file is MIS Secure-Area only). This script builds the
empirical substitute: which 345kV HOUSTON/SOUTH corridor facilities, WHEN OUTAGED,
are most associated with each constraint binding.

Method (REAL data only, Yes Energy datalake S3):
  - Day-level panel over the window. For each day read ONE midday outage snapshot
    (HE13 file = ...12.csv.gz), keep STATUS==Active, KV>=345, FROMZONE in {HOUSTON,SOUTH}.
    (Planned/forced outages persist for days, so a daily snapshot is a faithful proxy
     for 'facility out on day D'.)
  - Day-level binding flag per constraint from the validated DA binding parquet.
  - Per facility: days_out, co-occurrence days_out_and_bind, P(bind|out), base rate,
    LIFT = P(bind|out)/base. Min support filter. Ranked.

Confound controls / caveats handled below:
  - Regime window per constraint (MDO-PHR is a 2025-onset constraint; full-window base
    rate would be ~0 pre-2025 and inflate lift for anything out in 2025).
  - Corridor outages co-occur (planned-outage seasons bundle many facilities) -> lift is
    co-occurrence, NOT proven causation. We also report the mean count of co-active
    corridor outages on binding vs non-binding days.
  - This finds the WEAKENING-OUTAGE signature (pre-existing outages that leave the
    corridor exposed so the studied N-1 overloads the monitored line). That is a DIFFERENT
    object from the contingency MEMBER element list (the simulated N-1). It is the
    practical proxy the task asks for, not the NMMS membership.

Run from this dir:  python outage_binding_lift.py
"""
from __future__ import annotations
import concurrent.futures as cf
from pathlib import Path
import numpy as np
import pandas as pd
import dl

OUT_COLS = ["ISO","FACILITY","FROMSTATION","TOSTATION","KV","FROMZONE","TOZONE",
            "FACILITY_TYPE","TYPE","TYPE_DETAIL","STATUS","STATUS_DETAIL","STARTDATE",
            "ENDDATE","PLANNED_STARTDATE","PLANNED_ENDDATE","OPEN_CLOSE","TICKETID",
            "FACILITYID","LASTCHANGEDATE","PUBLISHDATE","REPORTED_NAME","FROMSTATIONID","TOSTATIONID"]

WINDOW_START, WINDOW_END = "2023-01-01", "2026-06-08"
KEEP_ZONES = {"HOUSTON", "SOUTH"}
MIN_KV = 345
MIN_SUPPORT = 15           # min days_out to rank a facility
CACHE = Path(__file__).resolve().parents[1] / "derived" / "outage_panel_345_houston_south.parquet"

# regime windows: period over which each constraint is 'live' (non-trivial base rate)
REGIME = {
    "MDOPHR99_A": ("2025-01-01", "2026-06-08"),   # 2025-onset constraint
    "STPWAP39_1": ("2023-01-01", "2026-06-08"),   # binds across all years
}


def one_day(d):
    ymd = d.strftime("%Y%m%d")
    df = dl.try_read_csv(f"ercot/transmission/outages/actual/{ymd}12.csv.gz", header=None)
    if df is None:
        return None
    df.columns = OUT_COLS[:df.shape[1]]
    df = df[df["STATUS"].astype(str).str.upper() == "ACTIVE"].copy()
    df["kvn"] = pd.to_numeric(df["KV"], errors="coerce")
    df = df[(df["kvn"] >= MIN_KV) & (df["FROMZONE"].isin(KEEP_ZONES))]
    if df.empty:
        return None
    out = df[["FACILITYID", "FACILITY", "kvn", "FROMSTATION", "TOSTATION", "FROMZONE"]].drop_duplicates("FACILITYID")
    out["date"] = d.normalize()
    return out


def build_panel(days):
    if CACHE.exists():
        print(f"loading cached outage panel {CACHE.name}")
        return pd.read_parquet(CACHE)
    parts = []
    done = 0
    with cf.ThreadPoolExecutor(max_workers=24) as ex:
        for r in ex.map(one_day, days):
            done += 1
            if r is not None:
                parts.append(r)
            if done % 200 == 0:
                print(f"  outage days scanned {done}/{len(days)}  with-data={len(parts)}", flush=True)
    panel = pd.concat(parts, ignore_index=True)
    panel.to_parquet(CACHE)
    print(f"cached {CACHE.name}: {len(panel)} (facility,day) rows, "
          f"{panel.date.nunique()} days, {panel.FACILITYID.nunique()} distinct facilities")
    return panel


def bind_days():
    b = pd.read_parquet(Path(__file__).resolve().parents[1] / "derived" / "da_binding_mdophr_stpwap.parquet")
    b["date"] = pd.to_datetime(b["DATETIME"]).dt.normalize()
    out = {}
    for c in ["MDOPHR99_A", "STPWAP39_1"]:
        g = b[b.CONSTRAINTNAME == c]
        out[c] = g.groupby("date").size().rename("bind_hours")  # >0 => bound that day
    return out


def lift_table(panel, binders, constraint):
    lo, hi = REGIME[constraint]
    days_in = pd.date_range(lo, hi, freq="D")
    have = set(panel.date.unique())                    # days with outage data
    universe = pd.DatetimeIndex([d for d in days_in if d in have])
    bh = binders[constraint].reindex(universe).fillna(0)
    bind_day = pd.Series((bh.values > 0).astype(int), index=universe)
    base = bind_day.mean()
    n_days = len(universe)
    n_bind = int(bind_day.sum())

    # seasonality control: month-of-year base rate (binding is strongly seasonal;
    # raw lift would just reward facilities that happen to be out during binding season)
    mon = pd.Series(universe.month, index=universe)
    month_base = bind_day.groupby(mon).mean()           # P(bind | calendar month)
    day_exp = mon.map(month_base)                       # per-day seasonal expectation

    p = panel[panel.date.isin(universe)].copy()
    p["bind"] = p.date.map(bind_day.to_dict()).astype(int)
    p["exp"] = p.date.map(day_exp.to_dict()).astype(float)

    g = p.groupby(["FACILITYID", "FACILITY"]).agg(
        days_out=("date", "nunique"),
        days_out_bind=("bind", "sum"),
        exp_bind=("exp", "sum"),          # seasonally-expected binding days on its out-days
        kv=("kvn", "first"),
        frm=("FROMSTATION", "first"),
        to=("TOSTATION", "first"),
        zone=("FROMZONE", "first"),
    ).reset_index()
    g["p_bind_given_out"] = g.days_out_bind / g.days_out
    g["lift"] = g.p_bind_given_out / base                                  # raw lift vs flat base
    g["seas_lift"] = g.days_out_bind / g.exp_bind.replace(0, np.nan)       # seasonality-adjusted
    g = g[g.days_out >= MIN_SUPPORT]

    # co-active corridor outage count: stress confound check
    cc = p.groupby("date").FACILITYID.nunique().rename("n_corr_out")
    cc = cc.reindex(universe).fillna(0)
    mean_on_bind = cc[bind_day == 1].mean()
    mean_off_bind = cc[bind_day == 0].mean()

    return g, dict(constraint=constraint, window=f"{lo}..{hi}", n_days=n_days, n_bind=n_bind,
                   base=base, mean_corr_out_on_bind=mean_on_bind, mean_corr_out_off_bind=mean_off_bind,
                   month_base={int(k): round(v, 2) for k, v in month_base.items()})


def station_lift(panel, binders, constraint):
    """Station-level: any 345kV equipment at a station out that day = station-out.
    More interpretable than per-breaker; ties directly to contingency lead-stations."""
    lo, hi = REGIME[constraint]
    days_in = pd.date_range(lo, hi, freq="D")
    have = set(panel.date.unique())
    universe = pd.DatetimeIndex([d for d in days_in if d in have])
    bh = binders[constraint].reindex(universe).fillna(0)
    bind_day = pd.Series((bh.values > 0).astype(int), index=universe)
    base = bind_day.mean()
    mon = pd.Series(universe.month, index=universe)
    month_base = bind_day.groupby(mon).mean()
    day_exp = mon.map(month_base)

    p = panel[panel.date.isin(universe)].copy()
    p["bind"] = p.date.map(bind_day.to_dict()).astype(int)
    p["exp"] = p.date.map(day_exp.to_dict()).astype(float)
    st = p.groupby(["FROMSTATION", "FROMZONE"]).agg(
        days_out=("date", "nunique"),
    ).reset_index()
    # need bind/exp at station-day level (dedupe equipment within station-day)
    sd = p.drop_duplicates(["FROMSTATION", "date"])
    agg = sd.groupby(["FROMSTATION", "FROMZONE"]).agg(
        days_out_bind=("bind", "sum"), exp_bind=("exp", "sum")).reset_index()
    st = st.merge(agg, on=["FROMSTATION", "FROMZONE"])
    st["p_bind_given_out"] = st.days_out_bind / st.days_out
    st["seas_lift"] = st.days_out_bind / st.exp_bind.replace(0, np.nan)
    return st, base


def main():
    days = pd.date_range(WINDOW_START, WINDOW_END, freq="D")
    panel = build_panel(days)
    binders = bind_days()
    pd.set_option("display.width", 260); pd.set_option("display.max_colwidth", 30)
    for c in ["MDOPHR99_A", "STPWAP39_1"]:
        g, meta = lift_table(panel, binders, c)
        print("\n" + "=" * 100)
        print(f"{c}  window={meta['window']}  days={meta['n_days']}  binding-days={meta['n_bind']}  "
              f"base P(bind/day)={meta['base']:.3f}")
        print(f"  monthly base rate (1=Jan..12=Dec): {meta['month_base']}")
        print(f"  co-active corridor 345kV outages: mean on BINDING days={meta['mean_corr_out_on_bind']:.1f} "
              f"vs non-binding={meta['mean_corr_out_off_bind']:.1f}  (>1 confound: binding season has FEWER outages)")
        cols = ["FACILITY", "kv", "frm", "to", "zone", "days_out", "days_out_bind", "p_bind_given_out", "lift", "seas_lift"]
        print("\n  --- ranked by SEASONALITY-ADJUSTED lift (headline; min support {} out-days, min 10 co-bind) ---".format(MIN_SUPPORT))
        gs = g[g.days_out_bind >= 10].sort_values(["seas_lift", "days_out_bind"], ascending=False).head(20)
        show = gs[cols].copy()
        show["p_bind_given_out"] = show.p_bind_given_out.round(3)
        show["lift"] = show.lift.round(2); show["seas_lift"] = show.seas_lift.round(2)
        print(show.to_string(index=False))

        st, base = station_lift(panel, binders, c)
        print("\n  --- STATION-level seasonality-adjusted lift (min 15 out-days, min 8 co-bind) ---")
        sts = st[(st.days_out >= 15) & (st.days_out_bind >= 8)].sort_values("seas_lift", ascending=False).head(15)
        sts = sts.assign(p_bind_given_out=sts.p_bind_given_out.round(3), seas_lift=sts.seas_lift.round(2))
        print(sts[["FROMSTATION", "FROMZONE", "days_out", "days_out_bind", "p_bind_given_out", "seas_lift"]].to_string(index=False))
        # corridor watch-list stations explicitly (validated contingency lead-stations)
        watch = ["WA PARISH", "PH ROBINSON", "MEADOW", "SOUTH TEXAS PROJECT", "HILLJE", "BLESSING",
                 "OASIS", "KING REIT", "REFUGIO", "ELM CREEK", "ELMCREEK", "WHITE POINT", "WHITEPOINT"]
        w = st[st.FROMSTATION.str.upper().isin([x.upper() for x in watch])].copy()
        if len(w):
            print("\n  --- corridor watch-list stations (validated contingency lead-stations) ---")
            w = w.assign(p_bind_given_out=w.p_bind_given_out.round(3), seas_lift=w.seas_lift.round(2))
            print(w[["FROMSTATION", "FROMZONE", "days_out", "days_out_bind", "p_bind_given_out", "seas_lift"]]
                  .sort_values("seas_lift", ascending=False).to_string(index=False))


if __name__ == "__main__":
    main()
