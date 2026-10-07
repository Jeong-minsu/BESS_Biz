"""Q3: Was the 2024->2026 fall in battery arbitrage value (TB2) structural (battery build-out) or
cyclical (loose system / cheap gas)? And what does that imply for FY2027 if new ESS slows and
AI-datacentre load grows?

Daily panel 2023-12-01 .. 2026-09-13:
  tb2      : ERCOT bus-average hub (HB_BUSAVG) RT TB2  = mean(top-2 h) - mean(bottom-2 h), $/MWh
  nl_peak  : daily max net load (load - wind - solar), GW          <- system tightness
  ramp     : evening net-load max (HE17-22) minus midday min (HE9-15), GW
  gas      : Houston Ship Channel daily weighted average, $/MMBtu
  ess_gw   : installed ERCOT ESS, GW (ERCOT actuals, linear between YE2023/24/25 and H1-2026)
Real data only.
"""
import sys, glob, json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl
BASE = Path(__file__).resolve().parents[1]; D = BASE / "derived"; RAW = BASE / "raw"

# ---------------------------------------------------------------- fundamentals
fu = pd.read_parquet(RAW / "item6_fundamentals.parquet")
fu["hour_end"] = pd.to_datetime(fu.hour_end)
fu["day"] = pd.to_datetime(fu.flowday)
fu["he"] = fu.hour_end.dt.hour.where(fu.hour_end.dt.hour != 0, 24)
fu["nl"] = (fu.load_mw - fu.wind_mw - fu.solar_mw) / 1000
g = fu.groupby("day")
daily = pd.DataFrame({
    "nl_peak": g.nl.max(),
    "load_peak": g.load_mw.max() / 1000,
    "ramp": fu[fu.he.between(17, 22)].groupby("day").nl.max() - fu[fu.he.between(9, 15)].groupby("day").nl.min(),
    "n": g.size(),
})
daily = daily[daily.n >= 23]

# ---------------------------------------------------------------- TB2 at bus average hub
BUSAVG = 10000698380
parts = []
for f in sorted(glob.glob(str(RAW / "price_panel/*.parquet"))):
    d = pd.read_parquet(f)
    parts.append(d[d.OBJECTID == BUSAVG][["DATETIME", "FLOWDAY", "RTLMP", "DALMP"]])
px = pd.concat(parts)
px["day"] = pd.to_datetime(px.FLOWDAY)
def tb2(s):
    s = s.dropna().sort_values()
    return s.iloc[-2:].mean() - s.iloc[:2].mean() if len(s) >= 20 else np.nan
daily["tb2"] = px.groupby("day").RTLMP.apply(tb2)
daily["tb2_da"] = px.groupby("day").DALMP.apply(tb2)

# ---------------------------------------------------------------- gas (cached)
GAS_CACHE = RAW / "q3_gas_hsc.parquet"
HSC = 10000002639
if GAS_CACHE.exists():
    gas = pd.read_parquet(GAS_CACHE)
else:
    def one(d):
        df = dl.try_read_csv(f"ercot/prices/gas/weighted_avg/{d:%Y%m%d}.csv.gz", header=None)
        if df is None:
            return None
        r = df[df[0] == HSC]
        return None if r.empty else (pd.Timestamp(d), float(r.iloc[0, 4]))
    days, d0 = [], date(2023, 11, 15)
    while d0 <= date(2026, 9, 13):
        days.append(d0); d0 += timedelta(days=1)
    with ThreadPoolExecutor(16) as ex:
        got = [x for x in ex.map(one, days) if x]
    gas = pd.DataFrame(got, columns=["day", "gas"])
    gas.to_parquet(GAS_CACHE, index=False)
gas = gas.set_index("day").gas.sort_index()
daily["gas"] = gas.reindex(pd.date_range(gas.index.min(), daily.index.max())).ffill().reindex(daily.index)

# ---------------------------------------------------------------- installed ESS (ERCOT actuals, nameplate GW)
anchors = pd.Series({pd.Timestamp("2023-12-31"): 3.998, pd.Timestamp("2024-12-31"): 9.187,
                     pd.Timestamp("2025-12-31"): 15.593, pd.Timestamp("2026-06-30"): 20.654})
idx = pd.date_range("2023-12-01", "2026-09-30")
ess = anchors.reindex(anchors.index.union(idx)).interpolate("time")
# extrapolate after H1-2026 at the H1-2026 pace
h1_rate = (20.654 - 15.593) / (anchors.index[3] - anchors.index[2]).days
tail = ess.index > anchors.index[3]
ess.loc[tail] = 20.654 + h1_rate * (ess.index[tail] - anchors.index[3]).days
ess.loc[ess.index < anchors.index[0]] = 3.998 - (anchors.index[0] - ess.index[ess.index < anchors.index[0]]).days * (9.187 - 3.998) / 366
daily["ess_gw"] = ess.reindex(daily.index)

daily = daily.dropna(subset=["tb2", "nl_peak", "gas", "ess_gw"])
daily = daily[daily.tb2 > 0]
daily["year"] = daily.index.year
daily["month"] = daily.index.month
daily["summer"] = daily.month.isin([6, 7, 8, 9])
print(f"daily panel: {len(daily)} days {daily.index.min().date()} .. {daily.index.max().date()}")

# ================================================================ 1. like-for-like: TB2 by year within tightness bins
print("\n=== [1] TB2 ($/MWh, median) by YEAR within the SAME system-tightness band (daily peak net load, GW) ===")
jas = daily[daily.month <= 9]                    # Jan-Sep like-for-like
bins = [0, 45, 50, 55, 60, 65, 100]
jas = jas.assign(band=pd.cut(jas.nl_peak, bins))
tab = jas.pivot_table(index="band", columns="year", values="tb2", aggfunc="median", observed=True)
cnt = jas.pivot_table(index="band", columns="year", values="tb2", aggfunc="size", observed=True)
print(tab.round(1).to_string())
print("days per cell:"); print(cnt.to_string())
days_by_year = jas.groupby("year").nl_peak.describe()[["mean", "50%", "max"]]
print("\nhow tight were the years? (Jan-Sep daily peak net load, GW)")
print(days_by_year.round(1).to_string())

# ================================================================ 2. regression
import numpy.linalg as la
X = pd.DataFrame(index=daily.index)
X["const"] = 1.0
X["nl_peak"] = daily.nl_peak - 55
X["nl_peak2"] = np.clip(daily.nl_peak - 60, 0, None) ** 2     # scarcity convexity above 60 GW
X["ramp"] = daily.ramp
X["log_gas"] = np.log(daily.gas.clip(lower=0.5))
X["ess_gw"] = daily.ess_gw
for m in range(2, 13):
    X[f"m{m}"] = (daily.month == m).astype(float)
y = np.log(daily.tb2)
beta, *_ = la.lstsq(X.values, y.values, rcond=None)
resid = y.values - X.values @ beta
n, k = X.shape
s2 = resid @ resid / (n - k)
# HAC-lite: inflate SE for daily autocorrelation using a block of 7 days
cov = s2 * la.inv(X.values.T @ X.values)
se = np.sqrt(np.diag(cov)) * np.sqrt(7)
coef = pd.DataFrame({"beta": beta, "se_block7": se, "t": beta / se}, index=X.columns)
r2 = 1 - resid.var() / y.var()
print(f"\n=== [2] log(TB2) regression, n={n}, R2={r2:.3f}  (SE inflated x sqrt(7) for autocorrelation) ===")
print(coef.loc[["nl_peak", "nl_peak2", "ramp", "log_gas", "ess_gw"]].round(4).to_string())
b = coef.beta
print(f"\n  +1 GW installed ESS  -> TB2 {100*(np.exp(b.ess_gw)-1):+.1f}%  (holding tightness, ramp, gas, month)")
print(f"  +1 GW peak net load  -> TB2 {100*(np.exp(b.nl_peak)-1):+.1f}% below 60 GW; convexity term above 60 GW")
print(f"  +1 GW evening ramp   -> TB2 {100*(np.exp(b.ramp)-1):+.1f}%")
print(f"  +10% gas price       -> TB2 {100*(1.1**b.log_gas-1):+.1f}%")

# ================================================================ 3. decomposition 2024 -> 2026 (Jan-Sep)
def mean_x(yr):
    s = X[(daily.year == yr) & (daily.month <= 9)]
    return s.mean()
x24, x26 = mean_x(2024), mean_x(2026)
contrib = {}
for c in ["nl_peak", "nl_peak2", "ramp", "log_gas", "ess_gw"]:
    contrib[c] = b[c] * (x26[c] - x24[c])
actual = np.log(daily[(daily.year == 2026) & (daily.month <= 9)].tb2).mean() - \
         np.log(daily[(daily.year == 2024) & (daily.month <= 9)].tb2).mean()
print("\n=== [3] decomposition of the change in log TB2, Jan-Sep 2024 -> 2026 ===")
print(f"  actual change: {100*(np.exp(actual)-1):+.1f}%")
labels = {"nl_peak": "tightness (peak net load)", "nl_peak2": "scarcity convexity (>60 GW)",
          "ramp": "evening ramp", "log_gas": "gas price", "ess_gw": "battery build-out"}
tot_expl = sum(contrib.values())
for c, v in contrib.items():
    print(f"  {labels[c]:30s} {100*(np.exp(v)-1):+7.1f}%   share of explained {100*v/tot_expl:6.1f}%")
print(f"  unexplained / other          {100*(np.exp(actual-tot_expl)-1):+7.1f}%")
print("  inputs 2024 vs 2026 (Jan-Sep means):",
      {c: (round(float(daily[(daily.year==2024)&(daily.month<=9)][c].mean()),2),
           round(float(daily[(daily.year==2026)&(daily.month<=9)][c].mean()),2))
       for c in ["nl_peak", "ramp", "gas", "ess_gw"]})

# ================================================================ 4. FY2027 scenarios
base26 = daily[(daily.year == 2026) & (daily.month <= 9)]
L26 = base26.tb2.mean()
ess_end26 = 20.654 + h1_rate * 184          # YE2026 at H1 pace
x_ref = X[(daily.year == 2026) & (daily.month <= 9)].copy()

def scenario(d_ess, d_nl, d_ramp, gas_mult):
    xs = x_ref.copy()
    xs["ess_gw"] = xs.ess_gw + (ess_end26 - base26.ess_gw.mean()) + d_ess   # 2027 avg ~= YE2026 + half-year of 2027 adds
    nl = base26.nl_peak + d_nl
    xs["nl_peak"] = nl - 55
    xs["nl_peak2"] = np.clip(nl - 60, 0, None) ** 2
    xs["ramp"] = xs.ramp + d_ramp
    xs["log_gas"] = xs.log_gas + np.log(gas_mult)
    pred = np.exp(xs.values @ beta)
    ref = np.exp(x_ref.values @ beta)
    return 100 * pred.mean() / ref.mean()

SC = {
 "Downside — pipeline fully built, load trend slows":
    dict(d_ess=9.6 / 2, d_nl=1.0, d_ramp=0.8, gas_mult=0.95,
         why="2027 ESS adds = EIA-860M planned 9.6 GW (half-year avg effect); net-load peak +1 GW; solar deepens ramp"),
 "Base — CDR pipeline with normal slippage, trend load growth":
    dict(d_ess=6.5 / 2, d_nl=2.5, d_ramp=1.0, gas_mult=1.00,
         why="2027 ESS adds ~6.5 GW (CDR +8.2 GW less ~20% slippage); peak net load +2.5 GW (~4% load trend)"),
 "Upside — ESS slips hard + AIDC load connects":
    dict(d_ess=3.5 / 2, d_nl=5.0, d_ramp=1.0, gas_mult=1.05,
         why="2027 ESS adds only 3.5 GW (heavy slippage/OBBBA); +2.5 GW extra datacentre load on top of trend"),
}
print(f"\n=== [4] FY2027 TB2 level vs 2026 (2026 Jan-Sep mean bus-avg RT TB2 = ${L26:.1f}) ===")
print(f"  (YE2026 installed ESS assumed {ess_end26:.1f} GW at H1-2026 pace)")
res = {}
for k, v in SC.items():
    lvl = scenario(v["d_ess"], v["d_nl"], v["d_ramp"], v["gas_mult"])
    res[k] = dict(level_pct_of_2026=lvl, **v)
    print(f"  {k:55s} -> {lvl:6.1f}% of 2026   | {v['why']}")

# carry-over effect alone: batteries already added during 2026 H2 that the 2026 average has not absorbed
carry = scenario(0, 0, 0, 1.0)
print(f"\n  carry-over only (no 2027 adds, no load growth; just full-year effect of 2026 H2 builds): {carry:.1f}%")

json.dump({
  "panel": {"days": int(len(daily)), "start": str(daily.index.min().date()), "end": str(daily.index.max().date())},
  "like_for_like_tb2_median_by_band": {str(i): {str(c): (None if pd.isna(v) else float(v)) for c, v in r.items()} for i, r in tab.iterrows()},
  "days_per_cell": {str(i): {str(c): int(v) if not pd.isna(v) else 0 for c, v in r.items()} for i, r in cnt.iterrows()},
  "tightness_by_year": days_by_year.round(2).to_dict(orient="index"),
  "regression": {"n": int(n), "r2": float(r2), "coef": coef.loc[["nl_peak","nl_peak2","ramp","log_gas","ess_gw"]].to_dict(orient="index")},
  "elasticities": {"ess_per_gw_pct": float(100*(np.exp(b.ess_gw)-1)), "nl_peak_per_gw_pct": float(100*(np.exp(b.nl_peak)-1)),
                   "ramp_per_gw_pct": float(100*(np.exp(b.ramp)-1)), "gas_10pct_pct": float(100*(1.1**b.log_gas-1))},
  "decomposition_2024_2026": {"actual_pct": float(100*(np.exp(actual)-1)),
                              **{labels[c]: float(100*(np.exp(v)-1)) for c, v in contrib.items()},
                              "unexplained_pct": float(100*(np.exp(actual-tot_expl)-1))},
  "scenarios_2027": res, "carry_over_pct": float(carry), "tb2_2026_busavg": float(L26),
  "ess_ye2026_assumed_gw": float(ess_end26),
}, open(D / "q3_supply_demand.json", "w"), indent=1, default=float)
print("\nwrote q3_supply_demand.json")
