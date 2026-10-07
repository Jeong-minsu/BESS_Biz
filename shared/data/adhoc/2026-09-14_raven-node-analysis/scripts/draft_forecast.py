"""FY2027 Base revenue outlook for Raven (RVN_RN), 100MW/200MWh.

Method (trend-aware, not a 3yr median):
  1. Proxy-reconstructed RVN RT TB2, daily, 2023-09..2026-09.
  2. Annual LEVEL   = Jan-Sep mean TB2 per year -> extrapolate to 2027.
     (TB2 is in a system-wide multi-year decline: the same slope appears at HB_HOUSTON,
      so it is ERCOT storage buildout compressing spreads, not a Raven effect.)
  3. Seasonal SHAPE = monthly TB2 / that year's Jan-Sep mean, median across years.
  4. TB index 2027  = sum over months of 2 MWh/MW/day * TB2_m * days_m.
  5. Revenue        = TB index x capture rate from Houston 2h peers (real disclosure).
Real data only. Assumptions explicit in the JSON.
"""
import json, glob
from pathlib import Path
import numpy as np, pandas as pd

BASE = Path(__file__).resolve().parents[1]; OUT = BASE / "derived"
DAYS = {1:31,2:28,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}

t = pd.read_csv(OUT / "draft_tb2_daily_3yr.csv")
p = t[(t.node == "PROXY") & (t.mkt == "RT")]
mo = p.pivot_table(index="month", columns="year", values="tb2", aggfunc="mean")

# 1) annual level (Jan-Sep, like-for-like across 2024/25/26)
lvl = {y: np.mean([mo.loc[m, y] for m in range(1, 10)]) for y in (2024, 2025, 2026)}
r1, r2 = lvl[2025]/lvl[2024], lvl[2026]/lvl[2025]
print("annual Jan-Sep mean TB2:", {k: round(v,1) for k,v in lvl.items()})
print(f"YoY ratios: 2025/24={r1:.3f}  2026/25={r2:.3f}")
DECAY = 0.90   # Base: decline continues but decelerates (2024->25 -23.5%, 2025->26 -12.5%)
L27 = lvl[2026] * DECAY
print(f"Base 2027 level = {lvl[2026]:.1f} x {DECAY} = {L27:.1f} $/MWh")

# 2) seasonal shape: each year's month / that year's Jan-Sep mean; median across years
shape = {}
for m in range(1, 13):
    vals = [mo.loc[m, y] / lvl[y] for y in (2024, 2025, 2026)
            if y in mo.columns and not np.isnan(mo.loc[m, y])]
    shape[m] = float(np.median(vals))
sh = pd.Series(shape); sh = sh / (sh[range(1,10)].mean())   # renormalise so Jan-Sep mean == 1
print("\nseasonal shape (Jan-Sep mean = 1.0):"); print(sh.round(3).to_string())

base_tb2 = {m: L27 * sh[m] for m in range(1, 13)}
tb_index = {m: 2.0 * base_tb2[m] * DAYS[m] for m in range(1, 13)}
tbi = sum(tb_index.values())
print(f"\nBase 2027 monthly TB2: {[round(base_tb2[m],1) for m in range(1,13)]}")
print(f"TB index 2027 (2h) = ${tbi:,.0f} /MW-yr")

# sensitivity on the dominant parameter
sens = {f"{int((1-d)*100)}% decline": sum(2.0*lvl[2026]*d*sh[m]*DAYS[m] for m in range(1,13))
        for d in (1.00, 0.90, 0.80)}
print("\nTB index sensitivity to the 2027 decline assumption:")
for k, v in sens.items(): print(f"   {k:14s} ${v:,.0f}/MW-yr")

# 3) capture from Houston 2h peers (real 60-day disclosure, 2026-01-01..05-25)
hou = pd.read_csv(OUT / "draft_houston_mix_jan_may2026.csv")
pe = hou[(hou.duration_hours >= 1.85) & (hou.duration_hours <= 2.25) & (hou.cap_mw >= 50)]
q = pe.opt_rate_pct.quantile([.25, .5, .75]).round(1)
print("\nHouston 2h peer capture quartiles:", q.to_dict(),
      "| AS share median %:", round(pe.as_share_pct.median(), 1))

scen = {"low_p25": float(q[.25]), "base_median": float(q[.5]), "high_p75": float(q[.75])}
rev = {k: tbi * v / 100 for k, v in scen.items()}
print("\n=== FY2027 outlook, Raven 100MW/200MWh (energy+AS, DART excluded) ===")
for k in scen:
    print(f"  capture {scen[k]:5.1f}% -> ${rev[k]:,.0f}/MW-yr = ${rev[k]*100/1e6:.2f}M")

json.dump({
 "asset": {"name":"Raven BESS","node":"RVN_RN","zone":"HOUSTON","mw":100,"mwh":200,"duration_h":2},
 "method":"trend-extrapolated TB index (2h) x Houston 2h peer capture rate",
 "proxy":{"formula":"-0.065 + 0.4148*CBEC_ALL + 0.5407*RBN_BESS1 + 0.0445*TAV_RN",
          "oos_tb2_da_mae":0.53,"oos_tb2_rt_mae":0.72,"oos_days":45},
 "observed_annual_level_jan_sep_tb2":{str(k):round(v,1) for k,v in lvl.items()},
 "yoy_ratio":{"2025_over_2024":round(r1,3),"2026_over_2025":round(r2,3)},
 "decay_assumption_2027":DECAY,
 "base_2027_level_tb2":round(L27,1),
 "seasonal_shape":{str(m):round(float(sh[m]),3) for m in range(1,13)},
 "base_2027_monthly_tb2":{str(m):round(base_tb2[m],1) for m in range(1,13)},
 "tb_index_2027_usd_per_mw_yr":round(tbi),
 "tb_index_sensitivity":{k:round(v) for k,v in sens.items()},
 "peer_capture_pct":scen,
 "peer_as_share_median_pct":float(round(pe.as_share_pct.median(),1)),
 "revenue_usd_per_mw_yr":{k:round(v) for k,v in rev.items()},
 "revenue_total_usd_100mw":{k:round(v*100) for k,v in rev.items()},
 "caveats":[
  "Peer capture is Jan1-May25 2026 (winter+spring) - summer peer disclosure was not downloaded (run stopped by user). Summer capture may differ.",
  "TB index assumes 2 MWh/MW/day and no round-trip-efficiency haircut; peer opt_rate is measured on the same basis, so the ratio is internally consistent.",
  "The 2027 decline factor (0.90) is the single largest driver - see tb_index_sensitivity.",
  "Proxy validated on ~100 summer days only; winter/shoulder untested (+-$2-3 TB2).",
  "WHARTN constraint contributes to proxy history but Raven's exposure is unverifiable (item2).",
  "New ERCOT storage additions, AS price decay and RTC+B effects are only implicitly in the trend.",
  "DART virtual excluded - item3a found no node-specific edge at RVN_RN."]
}, open(OUT/"draft_forecast_2027.json","w"), indent=2)
pd.Series(base_tb2).round(2).to_csv(OUT/"draft_base_monthly_tb2_2027.csv")
mo.round(2).to_csv(OUT/"draft_monthly_tb2_by_year.csv")
print("\nwrote draft_forecast_2027.json")
