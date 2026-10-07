"""Rain vs regional wind forecast error (Coastal / South), 2024-01..2026-09.

err = actual - STWPF(D-1 leakage-free vintage), normalised by region capacity proxy
(rolling 60-day max of hourly actual). Rain = AG2 hourly observed precip at
Coastal {KCRP,KVCT,KIAH} / South {KBRO,KMFE,KLRD}.
Daily block bootstrap for CI. Outputs derived/results.json + prints tables.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, DER = ROOT / "raw", ROOT / "derived"; DER.mkdir(exist_ok=True)
STATIONS = {"KCRP": "coastal", "KVCT": "coastal", "KIAH": "coastal",
            "KBRO": "south", "KMFE": "south", "KLRD": "south"}
RNG = np.random.default_rng(0)


# ---------- precip: AG2 local STANDARD time (CST, no DST), hour = hour-beginning ----------
def load_precip(lag_hours: int = 0):
    p = pd.read_parquet(RAW / "precip.parquet")
    p.columns = ["date", "hour", "ws_mph", "precip_in", "station"]
    p["precip_in"] = pd.to_numeric(p["precip_in"], errors="coerce")
    p["ws_mph"] = pd.to_numeric(p["ws_mph"], errors="coerce")
    ts = pd.to_datetime(p["date"], format="%m/%d/%Y") + pd.to_timedelta(p["hour"], unit="h")
    # CST -> CPT: +1h when CDT in effect; hour-beginning -> hour-ending: +1h
    cpt = ts.dt.tz_localize("Etc/GMT+6").dt.tz_convert("America/Chicago").dt.tz_localize(None)
    p["hour_end"] = cpt + pd.Timedelta(hours=1 + lag_hours)
    p["region"] = p["station"].map(STATIONS)
    g = p.groupby(["region", "hour_end"]).agg(
        precip_mean=("precip_in", "mean"), precip_max=("precip_in", "max"),
        n_rain=("precip_in", lambda s: (s > 0.005).sum()), n_st=("precip_in", "count"),
        ws_mean=("ws_mph", "mean")).reset_index()
    return g


# ---------- wind panel ----------
def load_wind():
    fc = pd.read_parquet(RAW / "wind_fc.parquet")
    ac = pd.read_parquet(RAW / "wind_act.parquet")
    rows = []
    for r in ("coastal", "south"):
        d = fc[["hour_end", "flowday", f"fc_{r}"]].merge(ac[["hour_end", f"act_{r}"]], on="hour_end")
        d = d.rename(columns={f"fc_{r}": "fc", f"act_{r}": "act"})
        d["region"] = r
        rows.append(d)
    w = pd.concat(rows, ignore_index=True).dropna(subset=["fc", "act"])
    w = w.sort_values(["region", "hour_end"])
    # capacity proxy: rolling 60d (1440h) max of actual, centred-ish (use trailing + leading max)
    w["cap"] = w.groupby("region")["act"].transform(
        lambda s: s.rolling(1440, min_periods=200, center=True).max())
    w["cap"] = w.groupby("region")["cap"].transform(lambda s: s.bfill().ffill())
    w["err_mw"] = w["act"] - w["fc"]
    w["err_pct"] = 100 * w["err_mw"] / w["cap"]        # % of capacity proxy
    w["fc_pct"] = 100 * w["fc"] / w["cap"]
    w["month"] = w["hour_end"].dt.month
    w["he"] = w["hour_end"].dt.hour.replace(0, 24)
    w["season"] = pd.cut(w["month"], [0, 2, 5, 8, 11, 12],
                         labels=["DJF", "MAM", "JJA", "SON", "DJF"], ordered=False)
    w["year"] = w["hour_end"].dt.year
    return w


def block_boot(df, col, group, n=1000):
    """mean(col | group==1) - mean(col | group==0) with day-level resampling."""
    days = df["flowday"].unique()
    byday = {d: g for d, g in df.groupby("flowday")}
    diffs = []
    for _ in range(n):
        s = pd.concat([byday[d] for d in RNG.choice(days, len(days))])
        a, b = s.loc[s[group] == 1, col], s.loc[s[group] == 0, col]
        if len(a) < 20 or len(b) < 20:
            continue
        diffs.append(a.mean() - b.mean())
    return np.percentile(diffs, [2.5, 50, 97.5]).round(2).tolist() if diffs else None


def summarize(df, col="err_pct"):
    s = df[col]
    return {"n": int(len(s)), "days": int(df["flowday"].nunique()), "mean": round(s.mean(), 2),
            "median": round(s.median(), 2), "wmean5": round(s.clip(s.quantile(.05), s.quantile(.95)).mean(), 2),
            "pct_neg": round(100 * (s < 0).mean(), 1), "mae": round(s.abs().mean(), 2),
            "mean_fc_pct": round(df["fc_pct"].mean(), 1)}


def main():
    w = load_wind()
    out = {"period": [str(w.hour_end.min()), str(w.hour_end.max())], "regions": {}}

    # --- lag alignment check: station wind speed vs actual gen correlation at lags ---
    lagcorr = {}
    for lag in range(-2, 3):
        p = load_precip(lag)
        m = w.merge(p, on=["region", "hour_end"])
        lagcorr[lag] = {r: round(g["ws_mean"].corr(g["act"]), 3) for r, g in m.groupby("region")}
    out["lag_corr_ws_vs_act"] = lagcorr
    best_lag = max(lagcorr, key=lambda k: np.mean(list(lagcorr[k].values())))
    out["best_lag"] = best_lag
    p = load_precip(best_lag)
    m = w.merge(p, on=["region", "hour_end"], how="inner")
    m["rain_any"] = (m["n_rain"] >= 1).astype(int)
    m["rain_maj"] = (m["n_rain"] >= 2).astype(int)
    m["rain_bin"] = pd.cut(m["precip_mean"], [-1, 0.004, 0.03, 0.10, 0.30, 99],
                           labels=["dry", "trace<0.03", "0.03-0.10", "0.10-0.30", ">0.30"])
    # daily rain
    dd = m.groupby(["region", "flowday"]).agg(day_precip=("precip_mean", "sum"),
                                              day_rain_hours=("rain_any", "sum")).reset_index()
    m = m.merge(dd, on=["region", "flowday"])
    m["rainy_day"] = (m["day_precip"] >= 0.10).astype(int)
    # fc level tercile within region-year
    m["fc_ter"] = m.groupby(["region", "year"])["fc_pct"].transform(
        lambda s: pd.qcut(s, 3, labels=["low", "mid", "high"]))
    m.to_parquet(DER / "panel.parquet", index=False)

    for r, g in m.groupby("region"):
        R = {"overall": summarize(g)}
        R["by_rain_any"] = {k: summarize(x) for k, x in g.groupby("rain_any")}
        R["by_rain_maj"] = {k: summarize(x) for k, x in g.groupby("rain_maj")}
        R["by_rain_bin"] = {str(k): summarize(x) for k, x in g.groupby("rain_bin", observed=True)}
        R["by_rainy_day"] = {k: summarize(x) for k, x in g.groupby("rainy_day")}
        R["boot_rain_any"] = block_boot(g, "err_pct", "rain_any")
        R["boot_rain_maj"] = block_boot(g, "err_pct", "rain_maj")
        R["boot_rainy_day"] = block_boot(g, "err_pct", "rainy_day")
        # relative error (% of forecast) for hours with meaningful forecast
        gg = g[g["fc_pct"] >= 10].copy(); gg["rel"] = 100 * gg["err_mw"] / gg["fc"]
        R["rel_err_fc>=10pct"] = {k: {"n": int(len(x)), "median": round(x["rel"].median(), 1),
                                      "wmean5": round(x["rel"].clip(x["rel"].quantile(.05), x["rel"].quantile(.95)).mean(), 1)}
                                  for k, x in gg.groupby("rain_any")}
        # stratified: season / fc tercile / HE block / year
        g = g.assign(heblk=pd.cut(g["he"], [0, 6, 12, 18, 24], labels=["HE1-6", "HE7-12", "HE13-18", "HE19-24"]))
        for key in ("season", "fc_ter", "heblk", "year"):
            R[f"strat_{key}"] = {}
            for k, x in g.groupby(key, observed=True):
                d1, d0 = x[x.rain_any == 1], x[x.rain_any == 0]
                R[f"strat_{key}"][str(k)] = {
                    "n_rain": int(len(d1)), "n_dry": int(len(d0)),
                    "mean_rain": round(d1.err_pct.mean(), 2), "mean_dry": round(d0.err_pct.mean(), 2),
                    "med_rain": round(d1.err_pct.median(), 2), "med_dry": round(d0.err_pct.median(), 2),
                    "boot": block_boot(x, "err_pct", "rain_any", n=400)}
        # control: station wind speed quartile (is it rain, or just wrong wind?)
        g["ws_q"] = pd.qcut(g["ws_mean"], 4, labels=["q1", "q2", "q3", "q4"])
        R["strat_ws_q"] = {}
        for k, x in g.groupby("ws_q", observed=True):
            d1, d0 = x[x.rain_any == 1], x[x.rain_any == 0]
            R["strat_ws_q"][str(k)] = {"n_rain": int(len(d1)), "n_dry": int(len(d0)),
                                       "mean_rain": round(d1.err_pct.mean(), 2), "mean_dry": round(d0.err_pct.mean(), 2),
                                       "boot": block_boot(x, "err_pct", "rain_any", n=400)}
        out["regions"][r] = R

    (DER / "results.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    # console
    print("lag corr", lagcorr, "best", best_lag)
    for r, R in out["regions"].items():
        print(f"\n=== {r.upper()} ===  overall", R["overall"])
        for k in ("by_rain_any", "by_rain_maj", "by_rainy_day"):
            print(k); [print("  ", kk, vv) for kk, vv in R[k].items()]
        print("by_rain_bin"); [print("  ", kk, vv) for kk, vv in R["by_rain_bin"].items()]
        print("boot rain_any", R["boot_rain_any"], " rain_maj", R["boot_rain_maj"], " rainy_day", R["boot_rainy_day"])
        print("rel err", R["rel_err_fc>=10pct"])
        for key in ("strat_season", "strat_fc_ter", "strat_heblk", "strat_year", "strat_ws_q"):
            print(key); [print("  ", kk, vv) for kk, vv in R[key].items()]


if __name__ == "__main__":
    main()
