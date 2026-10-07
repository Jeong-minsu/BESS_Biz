"""zone_ recon: can EIA-860M plants be attributed to ERCOT load zones via registry `unit` objects
(name = 'Plant Name:GenID (SETTLEMENT_POINT)') -> price_node ZONE ?"""
import re, sys, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
pd.set_option("display.width", 300); pd.set_option("display.max_colwidth", 60); pd.set_option("display.max_rows", 200)
obj = pd.read_parquet(ROOT / "raw/objects_all.parquet")
pn = obj[(obj.OBJECTTYPE == "price_node") & obj.ZONE.notna()].drop_duplicates("OBJECTNAME").set_index("OBJECTNAME").ZONE
units = obj[obj.OBJECTTYPE == "unit"].copy()
m = units.OBJECTNAME.str.extract(r"^(.*?):(.*?) \(([^()]*)\)$")
units["plant"], units["gen"], units["sp"] = m[0], m[1], m[2]
print("unit parse ok:", units.plant.notna().sum(), "/", len(units))
units["zone"] = units.sp.map(pn)
print("sp->zone matched:", units.zone.notna().sum(), "; unknown node:", (units.sp == "Node Unknown").sum())
print(units.zone.value_counts(dropna=False))
print(units[units.zone.isna() & (units.sp != "Node Unknown")].sp.value_counts().head(20))

eia = pd.read_excel(ROOT / "raw/zone_eia860m_july2026.xlsx", sheet_name="Operating", header=2, engine="openpyxl")
eia = eia[eia["Balancing Authority Code"] == "ERCO"]
eia["key"] = eia["Plant Name"].astype(str).str.strip().str.upper()
units["key"] = units.plant.astype(str).str.strip().str.upper()
pz = units.dropna(subset=["zone"]).groupby("key").zone.agg(lambda s: s.mode().iloc[0])
pz_n = units.dropna(subset=["zone"]).groupby("key").zone.nunique()
print("plants with >1 zone:", (pz_n > 1).sum())
eia["zone"] = eia.key.map(pz)
cap = "Nameplate Capacity (MW)"
print("EIA ERCOT rows:", len(eia), "matched:", eia.zone.notna().sum())
print("MW matched share by technology:")
g = eia.groupby("Technology").apply(lambda d: pd.Series({"mw": d[cap].sum(), "mw_matched": d.loc[d.zone.notna(), cap].sum()}))
g["share"] = (g.mw_matched / g.mw).round(3); print(g)
print("\nunmatched largest plants:")
print(eia[eia.zone.isna()].groupby(["Plant Name", "County", "Technology"])[cap].sum().sort_values(ascending=False).head(40))
print("\nCEMS-source unit sample with gen ids:"); print(units[["plant", "gen", "sp", "zone", "SOURCE"]].head(15).to_string())
