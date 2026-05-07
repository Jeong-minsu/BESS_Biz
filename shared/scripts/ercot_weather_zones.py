"""
Canonical ERCOT 8 Weather Zone definitions and 2025 zonal peak demand.

Source:
- Zone-county map: ERCOT Load Profile / Capacity, Demand and Reserves Report
- Zonal peak (MW): ERCOT Long-Term Hourly Peak Demand and Energy Forecast
  (May-2024 vintage, 2025 summer peak by zone). Round numbers.

Note: El Paso County is on WECC, NOT ERCOT, so excluded from FAR_WEST.
"""
from __future__ import annotations

# County (UPPER, no suffix) -> ERCOT weather zone
# 254 TX counties; counties NOT in this dict are non-ERCOT (e.g. El Paso panhandle counties on SPP)
COUNTY_TO_ZONE: dict[str, str] = {
    # ---------- COAST ----------
    "BRAZORIA": "COAST", "CALHOUN": "COAST", "CHAMBERS": "COAST",
    "GALVESTON": "COAST", "HARDIN": "COAST", "HARRIS": "COAST",
    "JACKSON": "COAST", "JASPER": "COAST", "JEFFERSON": "COAST",
    "LIBERTY": "COAST", "MATAGORDA": "COAST", "MONTGOMERY": "COAST",
    "NEWTON": "COAST", "ORANGE": "COAST", "POLK": "COAST",
    "SAN JACINTO": "COAST", "TRINITY": "COAST", "TYLER": "COAST",
    "WALKER": "COAST", "WALLER": "COAST", "WHARTON": "COAST",

    # ---------- EAST ----------
    "ANDERSON": "EAST", "CAMP": "EAST", "CASS": "EAST",
    "CHEROKEE": "EAST", "FRANKLIN": "EAST", "FREESTONE": "EAST",
    "GREGG": "EAST", "HARRISON": "EAST", "HENDERSON": "EAST",
    "HOUSTON": "EAST", "MARION": "EAST", "MORRIS": "EAST",
    "NACOGDOCHES": "EAST", "PANOLA": "EAST", "RAINS": "EAST",
    "RUSK": "EAST", "SABINE": "EAST", "SAN AUGUSTINE": "EAST",
    "SHELBY": "EAST", "SMITH": "EAST", "TITUS": "EAST",
    "UPSHUR": "EAST", "VAN ZANDT": "EAST", "WOOD": "EAST",

    # ---------- FAR WEST ----------
    "ANDREWS": "FAR_WEST", "BREWSTER": "FAR_WEST", "CRANE": "FAR_WEST",
    "CROCKETT": "FAR_WEST", "CULBERSON": "FAR_WEST", "ECTOR": "FAR_WEST",
    "HUDSPETH": "FAR_WEST", "JEFF DAVIS": "FAR_WEST", "LOVING": "FAR_WEST",
    "MIDLAND": "FAR_WEST", "PECOS": "FAR_WEST", "PRESIDIO": "FAR_WEST",
    "REAGAN": "FAR_WEST", "REEVES": "FAR_WEST", "TERRELL": "FAR_WEST",
    "UPTON": "FAR_WEST", "VAL VERDE": "FAR_WEST", "WARD": "FAR_WEST",
    "WINKLER": "FAR_WEST",

    # ---------- NORTH ----------
    "ARCHER": "NORTH", "BAYLOR": "NORTH", "CLAY": "NORTH",
    "COTTLE": "NORTH", "FOARD": "NORTH", "HARDEMAN": "NORTH",
    "JACK": "NORTH", "MONTAGUE": "NORTH", "WICHITA": "NORTH",
    "WILBARGER": "NORTH", "YOUNG": "NORTH",

    # ---------- NORTH CENTRAL ----------
    "BOSQUE": "NORTH_CENTRAL", "COLLIN": "NORTH_CENTRAL",
    "COMANCHE": "NORTH_CENTRAL", "COOKE": "NORTH_CENTRAL",
    "DALLAS": "NORTH_CENTRAL", "DENTON": "NORTH_CENTRAL",
    "EASTLAND": "NORTH_CENTRAL", "ELLIS": "NORTH_CENTRAL",
    "ERATH": "NORTH_CENTRAL", "FANNIN": "NORTH_CENTRAL",
    "GRAYSON": "NORTH_CENTRAL", "HAMILTON": "NORTH_CENTRAL",
    "HILL": "NORTH_CENTRAL", "HOOD": "NORTH_CENTRAL",
    "HUNT": "NORTH_CENTRAL", "JOHNSON": "NORTH_CENTRAL",
    "KAUFMAN": "NORTH_CENTRAL", "LAMAR": "NORTH_CENTRAL",
    "LIMESTONE": "NORTH_CENTRAL", "MCLENNAN": "NORTH_CENTRAL",
    "MILLS": "NORTH_CENTRAL", "NAVARRO": "NORTH_CENTRAL",
    "PALO PINTO": "NORTH_CENTRAL", "PARKER": "NORTH_CENTRAL",
    "ROCKWALL": "NORTH_CENTRAL", "SOMERVELL": "NORTH_CENTRAL",
    "STEPHENS": "NORTH_CENTRAL", "TARRANT": "NORTH_CENTRAL",
    "WISE": "NORTH_CENTRAL",

    # ---------- SOUTH ----------
    "ARANSAS": "SOUTH", "ATASCOSA": "SOUTH", "BEE": "SOUTH",
    "BROOKS": "SOUTH", "CAMERON": "SOUTH", "DIMMIT": "SOUTH",
    "DUVAL": "SOUTH", "FRIO": "SOUTH", "HIDALGO": "SOUTH",
    "JIM HOGG": "SOUTH", "JIM WELLS": "SOUTH", "KARNES": "SOUTH",
    "KENEDY": "SOUTH", "KINNEY": "SOUTH", "KLEBERG": "SOUTH",
    "LA SALLE": "SOUTH", "LIVE OAK": "SOUTH", "MCMULLEN": "SOUTH",
    "MAVERICK": "SOUTH", "MEDINA": "SOUTH", "NUECES": "SOUTH",
    "REFUGIO": "SOUTH", "SAN PATRICIO": "SOUTH", "STARR": "SOUTH",
    "UVALDE": "SOUTH", "WEBB": "SOUTH", "WILLACY": "SOUTH",
    "WILSON": "SOUTH", "ZAPATA": "SOUTH", "ZAVALA": "SOUTH",

    # ---------- SOUTH CENTRAL ----------
    "AUSTIN": "SOUTH_CENTRAL", "BANDERA": "SOUTH_CENTRAL",
    "BASTROP": "SOUTH_CENTRAL", "BELL": "SOUTH_CENTRAL",
    "BEXAR": "SOUTH_CENTRAL", "BLANCO": "SOUTH_CENTRAL",
    "BRAZOS": "SOUTH_CENTRAL", "BURLESON": "SOUTH_CENTRAL",
    "BURNET": "SOUTH_CENTRAL", "CALDWELL": "SOUTH_CENTRAL",
    "COLORADO": "SOUTH_CENTRAL", "COMAL": "SOUTH_CENTRAL",
    "CORYELL": "SOUTH_CENTRAL", "DE WITT": "SOUTH_CENTRAL",
    "DEWITT": "SOUTH_CENTRAL", "EDWARDS": "SOUTH_CENTRAL",
    "FALLS": "SOUTH_CENTRAL", "FAYETTE": "SOUTH_CENTRAL",
    "FORT BEND": "SOUTH_CENTRAL", "GILLESPIE": "SOUTH_CENTRAL",
    "GOLIAD": "SOUTH_CENTRAL", "GONZALES": "SOUTH_CENTRAL",
    "GUADALUPE": "SOUTH_CENTRAL", "HAYS": "SOUTH_CENTRAL",
    "KENDALL": "SOUTH_CENTRAL", "KERR": "SOUTH_CENTRAL",
    "KIMBLE": "SOUTH_CENTRAL", "LAMPASAS": "SOUTH_CENTRAL",
    "LAVACA": "SOUTH_CENTRAL", "LEE": "SOUTH_CENTRAL",
    "LEON": "SOUTH_CENTRAL", "LLANO": "SOUTH_CENTRAL",
    "MADISON": "SOUTH_CENTRAL", "MASON": "SOUTH_CENTRAL",
    "MILAM": "SOUTH_CENTRAL", "REAL": "SOUTH_CENTRAL",
    "ROBERTSON": "SOUTH_CENTRAL", "SAN SABA": "SOUTH_CENTRAL",
    "TRAVIS": "SOUTH_CENTRAL", "VICTORIA": "SOUTH_CENTRAL",
    "WASHINGTON": "SOUTH_CENTRAL", "WILLIAMSON": "SOUTH_CENTRAL",

    # ---------- WEST ----------
    "BORDEN": "WEST", "BROWN": "WEST", "CALLAHAN": "WEST",
    "COKE": "WEST", "COLEMAN": "WEST", "CONCHO": "WEST",
    "DAWSON": "WEST", "FISHER": "WEST", "GAINES": "WEST",
    "GARZA": "WEST", "GLASSCOCK": "WEST", "HASKELL": "WEST",
    "HOWARD": "WEST", "IRION": "WEST", "JONES": "WEST",
    "KENT": "WEST", "KNOX": "WEST", "MARTIN": "WEST",
    "MCCULLOCH": "WEST", "MENARD": "WEST", "MITCHELL": "WEST",
    "NOLAN": "WEST", "RUNNELS": "WEST", "SCHLEICHER": "WEST",
    "SCURRY": "WEST", "SHACKELFORD": "WEST", "STERLING": "WEST",
    "STONEWALL": "WEST", "SUTTON": "WEST", "TAYLOR": "WEST",
    "THROCKMORTON": "WEST", "TOM GREEN": "WEST",

    # ---------- Post-2021 ERCOT integration (South Plains / Panhandle) ----------
    # Lubbock area (LP&L joined ERCOT June 2021) + adjacent SPS partial transition.
    # Assigned to WEST/NORTH for forecasting consistent with ERCOT load-zone practice.
    # WEST (South Plains - Lubbock area)
    "LUBBOCK": "WEST", "HALE": "WEST", "FLOYD": "WEST", "CROSBY": "WEST",
    "LAMB": "WEST", "HOCKLEY": "WEST", "COCHRAN": "WEST", "YOAKUM": "WEST",
    "TERRY": "WEST", "LYNN": "WEST", "DICKENS": "WEST",
    # NORTH (Panhandle south & far Panhandle)
    "SWISHER": "NORTH", "BRISCOE": "NORTH", "MOTLEY": "NORTH",
    "CHILDRESS": "NORTH", "HALL": "NORTH", "DONLEY": "NORTH",
    "COLLINGSWORTH": "NORTH", "WHEELER": "NORTH", "CASTRO": "NORTH",
    "BAILEY": "NORTH", "PARMER": "NORTH", "DEAF SMITH": "NORTH",
    "RANDALL": "NORTH", "ARMSTRONG": "NORTH", "CARSON": "NORTH",
    "GRAY": "NORTH", "HUTCHINSON": "NORTH", "MOORE": "NORTH",
    "SHERMAN": "NORTH", "HARTLEY": "NORTH", "OLDHAM": "NORTH",
    "POTTER": "NORTH", "OCHILTREE": "NORTH", "HANSFORD": "NORTH",
    "LIPSCOMB": "NORTH", "ROBERTS": "NORTH", "HEMPHILL": "NORTH",
    "KING": "NORTH",
    # ---------- East TX border counties (deep East / NE TX with ERCOT units) ----------
    "HOPKINS": "EAST", "DELTA": "EAST", "ANGELINA": "EAST", "RED RIVER": "EAST",
    # ---------- South Central additions ----------
    "GRIMES": "SOUTH_CENTRAL",
}

# 2025 summer peak demand by zone, MW (ERCOT CDR May-2024 vintage, rounded)
# Sums to ~88,500 MW system peak forecast.
ZONE_PEAK_MW_2025: dict[str, float] = {
    "COAST":         19_500,
    "NORTH_CENTRAL": 29_500,
    "SOUTH_CENTRAL": 14_200,
    "SOUTH":          8_900,
    "FAR_WEST":       7_300,
    "WEST":           3_600,
    "EAST":           3_500,
    "NORTH":          2_600,
}

ZONE_PRETTY: dict[str, str] = {
    "COAST":         "Coast (Houston)",
    "NORTH_CENTRAL": "North Central (DFW)",
    "SOUTH_CENTRAL": "South Central (Austin/SA)",
    "SOUTH":         "South (Corpus/RGV)",
    "FAR_WEST":      "Far West (Permian)",
    "WEST":          "West",
    "EAST":          "East",
    "NORTH":         "North",
}

ZONE_COLOR: dict[str, str] = {
    "COAST":         "#1f77b4",
    "NORTH_CENTRAL": "#d62728",
    "SOUTH_CENTRAL": "#2ca02c",
    "SOUTH":         "#9467bd",
    "FAR_WEST":      "#ff7f0e",
    "WEST":          "#8c564b",
    "EAST":          "#17becf",
    "NORTH":         "#7f7f7f",
}


def normalize_county(name: str) -> str:
    """Normalize a county name to the dict key form.

    Handles multi-county EIA entries like 'Kent & Stonewall' or 'Kent and Stonewall'
    by taking the first county.
    """
    if not isinstance(name, str):
        return ""
    s = name.strip().upper()
    # split multi-county strings — take first
    for sep in (" & ", "&", " AND ", ", ", ","):
        if sep in s:
            s = s.split(sep)[0].strip()
            break
    # strip ' County' suffix if present
    for suf in (" COUNTY", " CO."):
        if s.endswith(suf):
            s = s[: -len(suf)].strip()
            break
    # canonicalize a few variants
    s = s.replace(".", "")
    if s == "DE WITT":
        return "DEWITT"
    return s


def zone_for(county_name: str) -> str | None:
    return COUNTY_TO_ZONE.get(normalize_county(county_name))


if __name__ == "__main__":
    print(f"counties mapped: {len(COUNTY_TO_ZONE)}")
    print(f"system peak (sum of zones): {sum(ZONE_PEAK_MW_2025.values()):,.0f} MW")
    by_zone: dict[str, int] = {}
    for z in COUNTY_TO_ZONE.values():
        by_zone[z] = by_zone.get(z, 0) + 1
    for z, n in sorted(by_zone.items(), key=lambda x: -x[1]):
        print(f"  {z:<14} counties={n:3d}  peak={ZONE_PEAK_MW_2025[z]:>6,} MW")
