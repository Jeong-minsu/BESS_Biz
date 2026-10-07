"""zone_: EIA-860M (July 2026) nameplate capacity by ERCOT load zone x fuel, with COD-year timeline and CHP/industrial split.
DEFINITION: EIA-860M nameplate MW (AC), BA=ERCO, status Operating/Standby/OA; INCLUDES industrial cogeneration (PUN-type)
which ERCOT CDR excludes -> use for structure/CHP share, not for comparison with ERCOT HSL-based numbers.
Zone attribution: (1) EIA plant name -> registry `unit` object 'Plant:Gen (SETTLEMENT_POINT)' -> price_node ZONE;
(2) fallback: majority zone of (1)-matched plants in the same county. Residual unmatched reported.
Output: derived/zone_eia860m_capacity.json, derived/zone_eia860m_units.csv
"""
import json
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
obj = pd.read_parquet(ROOT / "raw/objects_all.parquet")
pn = obj[(obj.OBJECTTYPE == "price_node") & obj.ZONE.notna()].drop_duplicates("OBJECTNAME").set_index("OBJECTNAME").ZONE
units = obj[obj.OBJECTTYPE == "unit"].copy()
m = units.OBJECTNAME.str.extract(r"^(.*?):(.*?) \(([^()]*)\)$")
units["key"] = m[0].str.strip().str.upper(); units["zone"] = m[2].map(pn)
plant_zone = units.dropna(subset=["zone"]).groupby("key").zone.agg(lambda s: s.mode().iloc[0])

X = ROOT / "raw/zone_eia860m_july2026.xlsx"
op = pd.read_excel(X, sheet_name="Operating", header=2, engine="openpyxl")
ret = pd.read_excel(X, sheet_name="Retired", header=2, engine="openpyxl")
op, ret = op[op["Balancing Authority Code"] == "ERCO"].copy(), ret[ret["Balancing Authority Code"] == "ERCO"].copy()
CAP = "Nameplate Capacity (MW)"
FUEL = {"Solar Photovoltaic": "solar", "Onshore Wind Turbine": "wind", "Batteries": "ess",
        "Natural Gas Fired Combined Cycle": "gas_cc", "Natural Gas Fired Combustion Turbine": "gas_ct",
        "Natural Gas Steam Turbine": "gas_st", "Natural Gas Internal Combustion Engine": "gas_ic",
        "Conventional Steam Coal": "coal", "Nuclear": "nuclear"}
for d in (op, ret):
    d["fuel"] = d["Technology"].map(FUEL).fillna("other")
    d["key"] = d["Plant Name"].astype(str).str.strip().str.upper()
    d["zone_sp"] = d.key.map(plant_zone)
# county fallback learned from settlement-point matches (MW-weighted majority)
cz = op.dropna(subset=["zone_sp"]).groupby(["County", "zone_sp"])[CAP].sum().reset_index()
county_zone = cz.sort_values(CAP, ascending=False).drop_duplicates("County").set_index("County").zone_sp
split = cz.groupby("County").zone_sp.nunique(); split = split[split > 1].index.tolist()
for d in (op, ret):
    d["zone"] = d.zone_sp.fillna(d.County.map(county_zone)); d["zone_method"] = d.zone_sp.notna().map({True: "settlement_point", False: "county_majority"})
    d.loc[d.zone.isna(), "zone_method"] = "unmatched"
print("split counties (matched plants in >1 zone):", split)
print("attribution by method (MW):"); print(op.groupby("zone_method")[CAP].sum().round(0))
print("unmatched MW by fuel:"); print(op[op.zone.isna()].groupby("fuel")[CAP].sum().round(0))
print(op[op.zone.isna()].groupby(["Plant Name", "County", "fuel"])[CAP].sum().sort_values(ascending=False).head(15))

op["chp_industrial"] = op["Sector"].astype(str).str.contains("CHP|Industrial", case=False)
cur = op.pivot_table(index="fuel", columns="zone", values=CAP, aggfunc="sum").fillna(0).round(0)
cur["ERCOT"] = cur.sum(axis=1); print("\nCurrent nameplate by zone x fuel (MW):"); print(cur)
gas = op[op.fuel.str.startswith("gas")]
chp = gas.pivot_table(index="zone", columns="chp_industrial", values=CAP, aggfunc="sum").fillna(0).round(0)
chp.columns = ["gas_merchant_mw", "gas_chp_industrial_mw"]; chp["chp_share"] = (chp.gas_chp_industrial_mw / chp.sum(axis=1)).round(3)
print("\nGas CHP/industrial share by zone:"); print(chp)

# timeline: cumulative nameplate at each year-end 2022..2025 and Jul-2026, by zone x fuel, from Operating Year/Month
op["cod"] = pd.to_datetime(dict(year=op["Operating Year"], month=op["Operating Month"].fillna(6), day=1), errors="coerce")
ret["retdate"] = pd.to_datetime(dict(year=ret["Retirement Year"], month=ret["Retirement Month"].fillna(6), day=1), errors="coerce") \
    if "Retirement Year" in ret.columns else pd.NaT
snaps = {"2022-12": "2022-12-31", "2023-12": "2023-12-31", "2024-12": "2024-12-31", "2025-12": "2025-12-31", "2026-07": "2026-07-31"}
tl = []
for lab, ts in snaps.items():
    ts = pd.Timestamp(ts)
    a = op[op.cod <= ts].groupby(["zone", "fuel"])[CAP].sum()
    r = ret[(ret.retdate > ts)].groupby(["zone", "fuel"])[CAP].sum() if "Retirement Year" in ret.columns else pd.Series(dtype=float)
    s = a.add(r, fill_value=0).round(0).reset_index(); s["snapshot"] = lab; tl.append(s)
tl = pd.concat(tl); tl.columns = ["zone", "fuel", "mw", "snapshot"]
h = tl[tl.zone == "HOUSTON"].pivot_table(index="fuel", columns="snapshot", values="mw").fillna(0)
print("\nHOUSTON nameplate timeline (operating units as of snapshot, retired units added back while still operating):"); print(h)
e = tl.groupby(["fuel", "snapshot"]).mw.sum().unstack().fillna(0); print("\nERCOT (attributed) timeline:"); print(e)
print("\nRetired in ERCO since 2023 (MW by zone x fuel):")
if "Retirement Year" in ret.columns:
    print(ret[ret["Retirement Year"] >= 2023].pivot_table(index="fuel", columns="zone", values=CAP, aggfunc="sum").fillna(0).round(0))

# Houston additions since 2023 (largest)
add = op[(op.cod >= "2023-01-01") & (op.zone == "HOUSTON")].groupby(["Plant Name", "County", "fuel", "Operating Year"])[CAP].sum().sort_values(ascending=False)
print("\nHouston COD>=2023 additions:", round(add.sum()), "MW"); print(add.head(25))

op[["Plant ID", "Plant Name", "County", "Technology", "fuel", "Sector", "chp_industrial", CAP, "Operating Year", "zone", "zone_method"]] \
    .to_csv(ROOT / "derived/zone_eia860m_units.csv", index=False)
out = {"definition": "EIA-860M July 2026, nameplate MW (AC), BA=ERCO, Operating sheet (incl. SB/OA/OS statuses), INCLUDES industrial CHP/PUN cogeneration. Zone via settlement-point (registry unit objects) else county majority.",
       "attribution_mw_by_method": op.groupby("zone_method")[CAP].sum().round(0).to_dict(),
       "split_counties": split,
       "current_by_zone_fuel": cur.reset_index().to_dict(orient="records"),
       "gas_chp_share_by_zone": chp.reset_index().to_dict(orient="records"),
       "timeline_by_zone_fuel": tl.to_dict(orient="records"),
       "houston_additions_since_2023": add.reset_index().rename(columns={CAP: "mw"}).head(40).to_dict(orient="records")}
(ROOT / "derived/zone_eia860m_capacity.json").write_text(json.dumps(out, indent=1, default=float)); print("wrote")
