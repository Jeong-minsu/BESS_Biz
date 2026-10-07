"""05 - energy-only decomposition: realized spread capture x cycles.

energy_rev ~= (discharge WAP - charge WAP) x discharge MWh, so
  opt_energy = energy_rev / TB2_rev = [realized spread / TB2 spread] x [discharge MWh / 200MWh]
"""
from pathlib import Path
import numpy as np, pandas as pd

D = Path(__file__).resolve().parents[1] / "derived"
INCIDENT = ("2026-03-24", "2026-04-13")
d = pd.read_parquet(D / "gks_daily_opt.parquet")
d["date"] = pd.to_datetime(d["date"])
d = d[d["tb2_rev"] > 0]


def agg(x):
    dis, chg = x["discharge_mwh"].sum(), x["charge_mwh"].sum()
    wap_d = x["discharge_rev"].sum() / dis if dis else np.nan
    wap_c = x["charge_cost"].sum() / chg if chg else np.nan
    tb2_sp = (x["tb2_rev"] / 200.0).mean()
    return pd.Series({
        "days": len(x),
        "energy_$": x["energy_rev"].sum(),
        "tb2_$": x["tb2_rev"].sum(),
        "opt_energy": x["energy_rev"].sum() / x["tb2_rev"].sum(),
        "discharge_WAP": wap_d, "charge_WAP": wap_c,
        "realized_spread": wap_d - wap_c,
        "tb2_spread": tb2_sp,
        "price_capture": (wap_d - wap_c) / tb2_sp,
        "cycles_per_day": dis / 200.0 / len(x),
        "discharge_MWh_d": dis / len(x),
        "charge_MWh_d": chg / len(x),
    })


pd.set_option("display.width", 250)
fmt = lambda v: f"{v:,.3f}"
t = d.groupby("year").apply(agg, include_groups=False)
t["PxQ"] = t["price_capture"] * t["cycles_per_day"]
print("=== energy only: spread capture x cycles ===")
print(t.to_string(float_format=fmt))

inc = d["date"].between(*INCIDENT)
t2 = d[~inc].groupby("year").apply(agg, include_groups=False)
t2["PxQ"] = t2["price_capture"] * t2["cycles_per_day"]
print("")
print("=== excl. 2026 outage 3/24-4/13 ===")
print(t2.to_string(float_format=fmt))

m = d.groupby(d["date"].dt.to_period("M")).apply(agg, include_groups=False)
m["PxQ"] = m["price_capture"] * m["cycles_per_day"]
print("")
print("=== monthly ===")
print(m[["days", "energy_$", "opt_energy", "price_capture", "cycles_per_day",
         "realized_spread", "tb2_spread"]].to_string(float_format=fmt))
