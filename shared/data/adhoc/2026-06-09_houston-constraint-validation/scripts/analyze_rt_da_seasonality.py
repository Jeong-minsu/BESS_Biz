"""RT vs DA shadow-price stats + month/hour seasonality + month x hour matrices.
Real data only. RT = scan_rt_full.py output (5-min SCED). DA = scan_da.py output (hourly).

P(bind) denominators (window 2023-01-01..2026-06-08, assume every day has DA + ~12 SCED/hr):
  DA:  binding-hours / (days_in_window_bucket)            per (month, HE)
  RT:  binding-intervals / (days_in_window_bucket * 12)   per (month, hour)
Hour = DATETIME hour (== ERCOT HE per memory; DA peak hr14 == 'HE14').
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")

D = Path(__file__).resolve().parents[1] / "derived"
TARGETS = ["MDOPHR99_A", "STPWAP39_1"]
START, END = "2023-01-01", "2026-06-08"

def load():
    da = pd.read_parquet(D / "da_binding_mdophr_stpwap.parquet")
    rt = pd.read_parquet(D / "rt_binding_mdophr_stpwap.parquet")
    da["dt"] = pd.to_datetime(da.DATETIME, format="%m/%d/%Y %H:%M:%S")
    rt["dt"] = pd.to_datetime(rt.DATETIME, format="%m/%d/%Y %H:%M:%S")
    for df in (da, rt):
        df["mon"] = df.dt.dt.month
        df["hr"] = df.dt.dt.hour
        df["yr"] = df.dt.dt.year
    # BINDING = positive shadow price. RT rt/ file lists monitored/active constraints
    # incl. PRICE==0 (slack, not actually binding); DA file lists priced rows only.
    print(f"RT rows pre-filter={len(rt)}  PRICE>0={int((rt.PRICE>0).sum())}  PRICE==0(dropped)={int((rt.PRICE==0).sum())}")
    print(f"DA rows pre-filter={len(da)}  PRICE>0={int((da.PRICE>0).sum())}")
    rt = rt[rt.PRICE > 0].copy()
    da = da[da.PRICE > 0].copy()
    return da, rt

def day_counts_by_month():
    cal = pd.date_range(START, END, freq="D")
    return pd.Series(cal.month).value_counts().sort_index()  # days in window per month-of-year

def qstats(s):
    return dict(n=int(len(s)), mean=round(float(s.mean()),1), p50=round(float(s.median()),1),
                p90=round(float(s.quantile(.90)),1), p99=round(float(s.quantile(.99)),1),
                max=round(float(s.max()),1))

def overall(da, rt):
    print("\n================ RT vs DA OVERALL (2023-01-01..2026-06-08) ================")
    for c in TARGETS:
        d, r = da[da.CONSTRAINTNAME==c], rt[rt.CONSTRAINTNAME==c]
        ds, rs = qstats(d.PRICE), qstats(r.PRICE)
        print(f"\n--- {c} ---")
        print(f"  DA: binding-hours={ds['n']:6d}  lambda mean${ds['mean']} p50${ds['p50']} p90${ds['p90']} p99${ds['p99']} max${ds['max']}")
        print(f"  RT: binding-intervals={rs['n']:6d} (~{rs['n']/12:.0f} binding-hrs)  lambda mean${rs['mean']} p50${rs['p50']} p90${rs['p90']} p99${rs['p99']} max${rs['max']}")
        print(f"  RT/DA p50 ratio={rs['p50']/ds['p50']:.2f}  p99 ratio={rs['p99']/ds['p99']:.2f}  max ratio={rs['max']/ds['max']:.2f}")

def month_profile(da, rt, dcount):
    print("\n================ MONTH-OF-YEAR PROFILE ================")
    for c in TARGETS:
        print(f"\n--- {c} ---  (P(bind): DA=hrs/(days), RT=intervals/(days*12))")
        print("  mon | DA P(bind) DA medλ DA p90 | RT P(bind) RT medλ RT p90")
        d, r = da[da.CONSTRAINTNAME==c], rt[rt.CONSTRAINTNAME==c]
        for m in range(1,13):
            days = dcount[m]
            dm, rm = d[d.mon==m], r[r.mon==m]
            dp = len(dm)/(days*24); rp = len(rm)/(days*24*12)
            dmed = dm.PRICE.median() if len(dm) else float("nan")
            dp90 = dm.PRICE.quantile(.9) if len(dm) else float("nan")
            rmed = rm.PRICE.median() if len(rm) else float("nan")
            rp90 = rm.PRICE.quantile(.9) if len(rm) else float("nan")
            print(f"  {m:3d} | {dp*100:7.1f}%  ${dmed:6.1f} ${dp90:6.1f} | {rp*100:7.1f}%  ${rmed:6.1f} ${rp90:6.1f}")

def hour_profile(da, rt, dcount):
    total_days = int(dcount.sum())
    print("\n================ HOUR-OF-DAY PROFILE (HE == DATETIME hour) ================")
    for c in TARGETS:
        print(f"\n--- {c} ---")
        print("  HE | DA P(bind) DA medλ | RT P(bind) RT medλ")
        d, r = da[da.CONSTRAINTNAME==c], rt[rt.CONSTRAINTNAME==c]
        for h in range(24):
            dh, rh = d[d.hr==h], r[r.hr==h]
            dp = len(dh)/total_days; rp = len(rh)/(total_days*12)
            dmed = dh.PRICE.median() if len(dh) else float("nan")
            rmed = rh.PRICE.median() if len(rh) else float("nan")
            print(f"  {h:3d} | {dp*100:7.1f}%  ${dmed:6.1f} | {rp*100:7.1f}%  ${rmed:6.1f}")

def matrices(da, rt, dcount):
    """12x24 P(bind) and median-lambda grids per constraint per market."""
    out = []
    for c in TARGETS:
        for mkt, df, perhr in [("DA", da[da.CONSTRAINTNAME==c], 1), ("RT", rt[rt.CONSTRAINTNAME==c], 12)]:
            pbind = np.full((12,24), 0.0)
            medlam = np.full((12,24), np.nan)
            for m in range(1,13):
                denom = dcount[m]*perhr
                for h in range(24):
                    cell = df[(df.mon==m)&(df.hr==h)]
                    pbind[m-1,h] = round(len(cell)/denom, 4) if denom else 0.0
                    if len(cell):
                        medlam[m-1,h] = round(float(cell.PRICE.median()),2)
            out.append(dict(constraint=c, market=mkt, metric="p_bind",
                            rows="month_1_12", cols="hour_0_23",
                            matrix=pbind.tolist()))
            out.append(dict(constraint=c, market=mkt, metric="median_lambda_usd",
                            rows="month_1_12", cols="hour_0_23",
                            matrix=[[None if np.isnan(v) else v for v in row] for row in medlam]))
    meta = dict(window=f"{START}..{END}", source="Yes Energy Datalake yedatalake (REAL)",
                da_file="ercot/transmission/constraints/da", rt_file="ercot/transmission/constraints/rt (NP6-86-CD SCED 5-min)",
                hour_def="DATETIME hour == ERCOT HE (DA peak hr14 == HE14)",
                pbind_denominator="DA: days_in_window_month; RT: days_in_window_month*12 (assumes ~12 SCED intervals/hr)",
                caveat="RT CONTINGENCY text blank in YE rt/ variant (decoded via DA CONTINGENCYID elsewhere)")
    payload = dict(meta=meta, grids=out)
    fp = D / "seasonality_month_hour_matrices.json"
    fp.write_text(json.dumps(payload, indent=1))
    print("\nSAVED matrices ->", fp)
    return fp

if __name__ == "__main__":
    da, rt = load()
    dcount = day_counts_by_month()
    print("RT year coverage:", rt.yr.min(), "->", rt.yr.max(),
          "| RT rows:", len(rt), "| DA rows:", len(da))
    print("RT rows per year:\n", rt.groupby(["CONSTRAINTNAME","yr"]).size().to_string())
    overall(da, rt)
    month_profile(da, rt, dcount)
    hour_profile(da, rt, dcount)
    matrices(da, rt, dcount)
