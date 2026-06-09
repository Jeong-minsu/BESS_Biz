"""Per-factor binding-probability breakpoint / threshold tables for MDOPHR99_A & STPWAP39_1.
Real data only (threshold_panel_2023_2026.parquet). Emits derived/trigger_tables.json + prints tables.
"""
import json
import numpy as np
import pandas as pd

P = pd.read_parquet("../derived/threshold_panel_2023_2026.parquet")

# global binding-lambda references (full history, memory-validated): median, P90
LAM_MED = {"MDOPHR99_A": 8.2, "STPWAP39_1": 20.3}
LAM_P90 = {"MDOPHR99_A": 42.8, "STPWAP39_1": 111.5}


def binstats(df, factor, bincol, cname, lam_p90):
    """conditional P(bind) and lambda quantiles per bin."""
    g = df.dropna(subset=[factor]).copy()
    g["bin"] = bincol(g[factor])
    rows = []
    for b, sub in g.groupby("bin", observed=True):
        nb = int(sub[cname + "_bind"].sum())
        n = len(sub)
        lam = sub.loc[sub[cname + "_bind"] == 1, cname + "_lam"].dropna()
        rows.append({
            "bin": str(b), "lo": float(getattr(b, "left", np.nan)),
            "n": n, "n_bind": nb, "p_bind_pct": round(100 * nb / n, 1) if n else None,
            "lam_med": round(float(lam.median()), 1) if len(lam) else None,
            "lam_p90": round(float(lam.quantile(0.9)), 1) if len(lam) else None,
        })
    return rows


def find_breakpoints(rows, base_pct, lam_med2x, lam_p90):
    """on-breakpoint = first bin (>=30 n) where p_bind >= max(2*base, 20%);
    strong = first bin where per-bin median lambda >= 2x global binding median (lambda escalation);
    p90cross = first bin where per-bin lambda P90 >= global lambda P90."""
    on = strong = p90cross = None
    for r in rows:
        if r["n"] < 30 or r["p_bind_pct"] is None:
            continue
        if on is None and r["p_bind_pct"] >= max(2 * base_pct, 20):
            on = r["lo"]
        if strong is None and r["lam_med"] is not None and r["lam_med"] >= lam_med2x:
            strong = r["lo"]
        if p90cross is None and r["lam_p90"] is not None and r["lam_p90"] >= lam_p90:
            p90cross = r["lo"]
    return on, strong, p90cross


def fixed_bins(edges):
    return lambda s: pd.cut(s, edges)


def analyze(cname, slc, label, factors, out):
    df = P.loc[slc]
    base = round(100 * df[cname + "_bind"].mean(), 2)
    n = len(df)
    print(f"\n{'='*78}\n{cname}  [{label}]  base P(bind)={base}%  n={n}")
    sec = {"slice": label, "n": n, "base_pct": base, "factors": {}}
    for fac, edges, restrict in factors:
        d = df if restrict is None else df.query(restrict)
        rows = binstats(d, fac, fixed_bins(edges), cname, LAM_P90[cname])
        on, strong, p90cross = find_breakpoints(rows, base, 2 * LAM_MED[cname], LAM_P90[cname])
        sec["factors"][fac] = {"restrict": restrict, "n": len(d.dropna(subset=[fac])),
                               "breakpoint_on": on, "strong_lambda_threshold": strong,
                               "lambda_p90_cross": p90cross, "bins": rows}
        print(f"\n  -- {fac}  (restrict={restrict})  on>={on}  strongLam(med2x)>={strong}  p90cross>={p90cross}")
        print("     bin                  n   nbind  P%    lamMed  lamP90")
        for r in rows:
            print(f"     {r['bin']:<18} {r['n']:>5} {r['n_bind']:>5}  {str(r['p_bind_pct']):>5}  "
                  f"{str(r['lam_med']):>6}  {str(r['lam_p90']):>6}")
    out[f"{cname}|{label}"] = sec


LOAD_E  = list(range(8000, 23000, 1000))
TEMP_E  = list(range(50, 100, 5))
WINDC_E = [0, 250, 500, 750, 1000, 1500, 2000, 3000]
WINDS_E = [0, 500, 1000, 1500, 2000, 3000, 4000, 6000]
SOLAR_E = [0, 250, 500, 1000, 1500, 2000, 2500, 3500]

PEAK = "hour>=12 and hour<=19"   # binding window for wind/solar de-confounding

out = {}

# MDO-PHR : 2025+ regime is the usable population
mdo_factors = [
    ("coast_load", LOAD_E, None),
    ("galv_temp",  TEMP_E, None),
    ("wind_coastal", WINDC_E, PEAK),
    ("wind_south",   WINDS_E, PEAK),
    ("solar_se",     SOLAR_E, PEAK),
]
analyze("MDOPHR99_A", P.year >= 2025, "2025+ regime (all hours)", mdo_factors, out)
analyze("MDOPHR99_A", (P.year >= 2025) & (P.season == "summer"), "2025+ summer", mdo_factors, out)

# STP-WAP : full window + summer
stp_factors = mdo_factors
analyze("STPWAP39_1", P.index.notna(), "all 2023-2026 (all hours)", stp_factors, out)
analyze("STPWAP39_1", P.season == "summer", "summer (Jun-Aug)", stp_factors, out)

with open("../derived/trigger_tables.json", "w") as f:
    json.dump(out, f, indent=1, default=str)
print("\nwrote ../derived/trigger_tables.json")
