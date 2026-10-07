"""Houston zone overview — installed capacity by ERCOT weather zone x fuel, YE2022..Jul-2026,
plus the planned pipeline for H2-2026 and 2027.

Source: EIA-860M July 2026 (Operating / Retired / Planned), Balancing Authority = ERCO.
County -> ERCOT weather zone via shared/scripts/ercot_weather_zones.py.
"Houston" here = weather zone COAST (Harris, Brazoria, Galveston, Fort Bend-adjacent coast,
Matagorda, Wharton ...), which contains the Houston load zone and Raven.

Convention: NAMEPLATE MW, all sectors (incl. industrial CHP / PUN) — the sector split is
reported separately because industrial cogen is a defining Houston feature.
Real data only.
"""
import sys, json
from pathlib import Path
import pandas as pd, numpy as np

ROOT = Path(__file__).resolve().parents[5]
BASE = Path(__file__).resolve().parents[1]; D = BASE / "derived"
sys.path.insert(0, str(ROOT / "shared" / "scripts"))
from ercot_weather_zones import COUNTY_TO_ZONE  # noqa: E402

XL = ROOT / "shared/data/raw/eia/july_generator2026.xlsx"


def load(sheet):
    df = pd.read_excel(XL, sheet_name=sheet, header=2, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    df = df[df["Balancing Authority Code"] == "ERCO"].copy()
    df["county_u"] = (df["County"].astype(str).str.upper()
                      .str.replace(" COUNTY", "", regex=False).str.strip())
    df["zone"] = df.county_u.map(COUNTY_TO_ZONE)
    df["mw"] = pd.to_numeric(df["Nameplate Capacity (MW)"], errors="coerce").fillna(0.0)
    return df


def fuel(tech):
    t = str(tech)
    if "Batter" in t: return "ESS"
    if "Solar" in t: return "Solar"
    if "Wind" in t: return "Wind"
    if "Natural Gas" in t or "Other Gases" in t: return "Gas"
    if "Coal" in t: return "Coal"
    if "Nuclear" in t: return "Nuclear"
    return "Other"


op, ret, pl = load("Operating"), load("Retired"), load("Planned")
for df in (op, ret, pl):
    df["fuel"] = df["Technology"].map(fuel)

unmapped = op[op.zone.isna()].mw.sum()
print(f"Operating ERCO units: {len(op)}  total {op.mw.sum():,.0f} MW  | unmapped county MW: {unmapped:,.0f}")

op["y_on"] = pd.to_numeric(op["Operating Year"], errors="coerce")
ret["y_on"] = pd.to_numeric(ret["Operating Year"], errors="coerce")
ret["y_off"] = pd.to_numeric(ret["Retirement Year"], errors="coerce")

YEARS = [2022, 2023, 2024, 2025, 2026]   # 2026 = as of Jul-2026
rows = []
for y in YEARS:
    a = op[op.y_on <= y].groupby(["zone", "fuel"]).mw.sum()
    b = ret[(ret.y_on <= y) & (ret.y_off > y)].groupby(["zone", "fuel"]).mw.sum()
    s = a.add(b, fill_value=0.0)
    for (z, fu), v in s.items():
        rows.append(dict(year=y, zone=z, fuel=fu, mw=v))
cap = pd.DataFrame(rows)

FUELS = ["Gas", "Solar", "Wind", "ESS", "Coal", "Nuclear", "Other"]
ZONES = ["COAST", "SOUTH", "SOUTH_CENTRAL", "NORTH_CENTRAL", "WEST", "FAR_WEST", "NORTH", "EAST"]

piv = cap.pivot_table(index=["zone", "fuel"], columns="year", values="mw", aggfunc="sum").fillna(0)

# ERCOT total sanity check vs ERCOT CDR-based actuals already in the repo (ESS YE2025 15,593 MW nameplate)
tot = cap.groupby(["year", "fuel"]).mw.sum().unstack().fillna(0)
print("\nERCOT total nameplate by fuel (EIA-860M reconstruction), MW:")
print(tot[FUELS].round(0).to_string())

print("\n=== Houston (COAST) nameplate by fuel, MW ===")
hou = piv.loc["COAST"].reindex(FUELS).fillna(0)
print(hou.round(0).to_string())

# planned pipeline by zone (H2-2026 and 2027)
pl["py"] = pd.to_numeric(pl["Planned Operation Year"], errors="coerce")
pipe = pl[pl.py.isin([2026, 2027])].groupby(["zone", "py", "fuel"]).mw.sum().reset_index()
print("\n=== planned additions (EIA-860M planned list), MW — COAST vs ERCOT ===")
for y in (2026, 2027):
    c = pipe[(pipe.zone == "COAST") & (pipe.py == y)].set_index("fuel").mw
    e = pipe[pipe.py == y].groupby("fuel").mw.sum()
    print(f"  {y}: COAST {c.reindex(FUELS).fillna(0).round(0).to_dict()}")
    print(f"        ERCOT {e.reindex(FUELS).fillna(0).round(0).to_dict()}")

# industrial cogen share of gas (sector)
gas_sec = op[(op.fuel == "Gas")].groupby(["zone", "Sector"]).mw.sum().unstack().fillna(0)
gas_sec["total"] = gas_sec.sum(axis=1)
ind_cols = [c for c in gas_sec.columns if "Industrial" in str(c) or "Commercial" in str(c)]
gas_sec["industrial_chp_share"] = gas_sec[ind_cols].sum(axis=1) / gas_sec["total"]
print("\n=== gas capacity: industrial/commercial CHP share by zone (operating, Jul-2026) ===")
print(gas_sec[["total", "industrial_chp_share"]].reindex(ZONES).round(3).to_string())

# zone comparison table (Jul-2026 mix + 3-yr growth)
comp = []
for z in ZONES:
    if z not in piv.index.get_level_values(0):
        continue
    p = piv.loc[z].reindex(FUELS).fillna(0)
    t26, t23 = p[2026].sum(), p[2023].sum()
    comp.append(dict(
        zone=z, total_2026=t26, total_2023=t23,
        growth_mw_2023_2026=t26 - t23, growth_pct=100 * (t26 / t23 - 1) if t23 else np.nan,
        **{f"share_{f}": 100 * p.loc[f, 2026] / t26 if t26 else 0 for f in FUELS},
        **{f"add_{f}_2023_2026": p.loc[f, 2026] - p.loc[f, 2023] for f in FUELS},
        ess_mw_2026=p.loc["ESS", 2026], ess_mw_2023=p.loc["ESS", 2023],
        planned_2027_ess=float(pipe[(pipe.zone == z) & (pipe.py == 2027) & (pipe.fuel == "ESS")].mw.sum()),
        gas_ind_chp_share=float(gas_sec.loc[z, "industrial_chp_share"]) if z in gas_sec.index else np.nan,
    ))
comp = pd.DataFrame(comp)
print("\n=== zone comparison (nameplate, Jul-2026) ===")
cols = ["zone", "total_2026", "growth_pct", "share_Gas", "share_Solar", "share_Wind", "share_ESS",
        "add_ESS_2023_2026", "add_Solar_2023_2026", "planned_2027_ess", "gas_ind_chp_share"]
print(comp[cols].round(1).to_string(index=False))

out = {
    "source": "EIA-860M July 2026 (Operating/Retired/Planned), BA=ERCO, nameplate MW, all sectors",
    "zone_definition": "ERCOT weather zone; Houston = COAST (contains Houston load zone and Raven)",
    "years": YEARS, "fuels": FUELS,
    "ercot_total_by_fuel": {str(y): {f: float(tot.loc[y, f]) if f in tot.columns else 0.0 for f in FUELS} for y in YEARS},
    "coast_by_fuel": {str(y): {f: float(hou.loc[f, y]) for f in FUELS} for y in YEARS},
    "zone_comparison": comp.replace({np.nan: None}).to_dict(orient="records"),
    "planned": pipe.to_dict(orient="records"),
    "unmapped_operating_mw": float(unmapped),
}
json.dump(out, open(D / "zone_capacity.json", "w"), indent=1, default=float)
print("\nwrote zone_capacity.json")
