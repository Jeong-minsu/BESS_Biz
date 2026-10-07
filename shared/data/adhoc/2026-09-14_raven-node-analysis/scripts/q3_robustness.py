"""Q3 robustness: is battery compression linear in GW, or diminishing (log GW)?
The 2027 answer depends heavily on this, so fit both, compare fit, and rerun the scenarios.
Also: RTC+B (real-time co-optimisation, live 2025-12-05) is a structural break that can be
confounded with the ESS term — add a post-RTC+B dummy and see whether the ESS effect survives.
Reuses the daily panel built by q3_supply_demand.py (rebuilt here from the same cached inputs).
"""
import runpy, json
from pathlib import Path
import numpy as np, pandas as pd, numpy.linalg as la

HERE = Path(__file__).resolve().parent
ns = runpy.run_path(str(HERE / "q3_supply_demand.py"), run_name="q3_import")
daily, D = ns["daily"], ns["D"]
ess_end26, base_mask = ns["ess_end26"], (daily.year == 2026) & (daily.month <= 9)


def design(dd, spec, rtcb):
    X = pd.DataFrame(index=dd.index)
    X["const"] = 1.0
    X["nl_peak"] = dd.nl_peak - 55
    X["nl_peak2"] = np.clip(dd.nl_peak - 60, 0, None) ** 2
    X["ramp"] = dd.ramp
    X["log_gas"] = np.log(dd.gas.clip(lower=0.5))
    X["ess"] = dd.ess_gw if spec == "linear" else np.log(dd.ess_gw)
    if rtcb:
        X["rtcb"] = (dd.index >= "2025-12-05").astype(float)
    for m in range(2, 13):
        X[f"m{m}"] = (dd.month == m).astype(float)
    return X


def fit(spec, rtcb):
    X = design(daily, spec, rtcb)
    y = np.log(daily.tb2).values
    b, *_ = la.lstsq(X.values, y, rcond=None)
    r = y - X.values @ b
    s2 = r @ r / (len(y) - X.shape[1])
    se = np.sqrt(np.diag(s2 * la.inv(X.values.T @ X.values))) * np.sqrt(7)
    aic = len(y) * np.log(r @ r / len(y)) + 2 * X.shape[1]
    return X, pd.Series(b, X.columns), pd.Series(se, X.columns), 1 - r.var() / y.var(), aic


SC = {"Downside": (9.6, 1.0, 0.8, 0.95), "Base": (6.5, 2.5, 1.0, 1.00), "Upside": (3.5, 5.0, 1.0, 1.05)}
out = {}
print(f"{'spec':28s} {'R2':>6} {'AIC':>9} {'ESS beta':>9} {'t':>6} {'RTCB':>7} | "
      f"{'carry':>6} {'Down':>6} {'Base':>6} {'Up':>6}   (2027 TB2 as % of 2026)")
for spec in ("linear", "log"):
    for rtcb in (False, True):
        X, b, se, r2, aic = fit(spec, rtcb)
        ref = X[base_mask].copy()
        base_ess = daily.loc[base_mask, "ess_gw"]

        def run(d_ess, d_nl, d_ramp, gm):
            xs = ref.copy()
            e = base_ess + (ess_end26 - base_ess.mean()) + d_ess / 2
            xs["ess"] = e if spec == "linear" else np.log(e)
            nl = daily.loc[base_mask, "nl_peak"] + d_nl
            xs["nl_peak"] = nl - 55
            xs["nl_peak2"] = np.clip(nl - 60, 0, None) ** 2
            xs["ramp"] = xs.ramp + d_ramp
            xs["log_gas"] = xs.log_gas + np.log(gm)
            return 100 * np.exp(xs.values @ b.values).mean() / np.exp(ref.values @ b.values).mean()

        carry = run(0, 0, 0, 1.0)
        sc = {k: run(*v) for k, v in SC.items()}
        key = f"{spec} ESS" + (" + RTC+B dummy" if rtcb else "")
        rt = f"{b['rtcb']:+.3f}" if rtcb else "   —"
        print(f"{key:28s} {r2:6.3f} {aic:9.1f} {b['ess']:+9.4f} {b['ess']/se['ess']:6.2f} {rt:>7} | "
              f"{carry:6.1f} {sc['Downside']:6.1f} {sc['Base']:6.1f} {sc['Upside']:6.1f}")
        out[key] = dict(r2=float(r2), aic=float(aic), ess_beta=float(b["ess"]), ess_t=float(b["ess"] / se["ess"]),
                        rtcb_beta=(float(b["rtcb"]) if rtcb else None), carry_over=float(carry),
                        scenarios={k: float(v) for k, v in sc.items()},
                        nl_peak_beta=float(b["nl_peak"]))

# break-even: how much 2027 ESS can be added before 2027 TB2 falls below 2026, per spec, at +2.5 GW and +5 GW peak net load
print("\nbreak-even 2027 ESS additions (GW) that keep TB2 flat vs 2026:")
for spec in ("linear", "log"):
    X, b, se, r2, aic = fit(spec, False)
    ref = X[base_mask].copy(); base_ess = daily.loc[base_mask, "ess_gw"]
    for d_nl in (2.5, 5.0, 8.0):
        best = None
        for add in np.arange(-10, 20.01, 0.1):
            xs = ref.copy()
            e = base_ess + (ess_end26 - base_ess.mean()) + add / 2
            if (e <= 0).any():
                continue
            xs["ess"] = e if spec == "linear" else np.log(e)
            nl = daily.loc[base_mask, "nl_peak"] + d_nl
            xs["nl_peak"] = nl - 55; xs["nl_peak2"] = np.clip(nl - 60, 0, None) ** 2
            xs["ramp"] = xs.ramp + 1.0
            v = np.exp(xs.values @ b.values).mean() / np.exp(ref.values @ b.values).mean()
            if v >= 1.0:
                best = add
        print(f"  {spec:6s} ESS, peak net load +{d_nl:.1f} GW: break-even 2027 adds = "
              f"{('%.1f GW' % best) if best is not None else 'none (<-10 GW)'}")
        out.setdefault("break_even", {})[f"{spec}_nl+{d_nl}"] = None if best is None else float(best)

json.dump(out, open(D / "q3_robustness.json", "w"), indent=1)
print("\nwrote q3_robustness.json")
