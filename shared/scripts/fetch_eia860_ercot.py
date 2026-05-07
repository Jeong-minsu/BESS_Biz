"""
Download EIA-860M (latest monthly) and produce a clean ERCOT-only
unit-level table for Solar / Wind / BESS with lat/lon and capacity.

Output: shared/data/raw/eia/ercot_units_<yyyymm>.csv

Source: https://www.eia.gov/electricity/data/eia860m/
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from datetime import date

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "shared" / "data" / "raw" / "eia"
RAW_DIR.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (BESS_Biz/1.0)"}

MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]

# Technologies we care about (EIA-860M "Technology" values)
TECH_SOLAR = {"Solar Photovoltaic", "Solar Thermal without Energy Storage",
              "Solar Thermal with Energy Storage"}
TECH_WIND = {"Onshore Wind Turbine", "Offshore Wind Turbine"}
TECH_BESS = {"Batteries"}

# EIA 860M tab uses these exact sheet names
SHEET_OPERATING = "Operating"


def find_latest_url() -> tuple[str, str]:
    """Probe EIA 860M URLs from current month back to find the latest available file.
    Returns (url, yyyymm)."""
    today = date.today()
    # try this month, then walk back up to 6 months
    candidates = []
    y, m = today.year, today.month
    for _ in range(7):
        candidates.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1

    for y, m in candidates:
        url = f"https://www.eia.gov/electricity/data/eia860m/xls/{MONTHS[m-1]}_generator{y}.xlsx"
        r = requests.head(url, headers=UA, timeout=30, allow_redirects=True)
        if r.status_code == 200:
            return url, f"{y}{m:02d}"
    raise RuntimeError("Could not find a valid EIA-860M file in last 7 months")


def download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 100_000:
        print(f"[cached] {dest.name}")
        return dest
    print(f"[download] {url}")
    r = requests.get(url, headers=UA, timeout=120)
    r.raise_for_status()
    dest.write_bytes(r.content)
    print(f"  -> {dest} ({dest.stat().st_size/1e6:.2f} MB)")
    return dest


def detect_header_row(xlsx_path: Path, sheet: str) -> int:
    """EIA-860M sheets have a 1-2 row banner before the header. Detect it."""
    probe = pd.read_excel(xlsx_path, sheet_name=sheet, header=None, nrows=5,
                          engine="openpyxl")
    for i, row in probe.iterrows():
        vals = [str(v).strip().lower() for v in row.tolist()]
        if any("plant" in v and "name" in v for v in vals):
            return i
    return 1  # fallback


def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=lambda c: str(c).strip())
    return df


def build_ercot_units(xlsx_path: Path) -> pd.DataFrame:
    header_row = detect_header_row(xlsx_path, SHEET_OPERATING)
    print(f"[parse] {SHEET_OPERATING} header at row {header_row}")
    df = pd.read_excel(xlsx_path, sheet_name=SHEET_OPERATING,
                       header=header_row, engine="openpyxl")
    df = normalize_cols(df)
    print(f"  loaded {len(df):,} rows, {len(df.columns)} cols")

    # Identify column names (EIA varies "Plant State" / "State" naming across years)
    def col(*candidates: str) -> str:
        for c in candidates:
            if c in df.columns:
                return c
        # case-insensitive fallback
        lc = {c.lower(): c for c in df.columns}
        for c in candidates:
            if c.lower() in lc:
                return lc[c.lower()]
        raise KeyError(f"None of {candidates} in columns: {list(df.columns)[:30]}")

    c_state = col("Plant State", "State")
    c_ba = col("Balancing Authority Code", "Balancing Authority")
    c_tech = col("Technology")
    c_status = col("Status")
    c_lat = col("Latitude")
    c_lon = col("Longitude")
    c_cap = col("Net Summer Capacity (MW)", "Nameplate Capacity (MW)")
    c_plant = col("Plant Name")
    c_pid = col("Plant ID", "Entity ID")
    c_gid = col("Generator ID")
    c_county = col("County")
    c_op_year = None
    for k in ("Operating Year", "Year", "Operating Month"):
        if k in df.columns:
            c_op_year = k
            break

    # Filters: TX state OR ERCO BA, status Operating, target tech
    mask_tx = df[c_state].astype(str).str.upper().eq("TX")
    mask_erco = df[c_ba].astype(str).str.upper().eq("ERCO")
    mask_state = mask_tx & mask_erco  # both — excludes El Paso (non-ERCOT) and SWPP/MISO TX bits
    mask_status = df[c_status].astype(str).str.contains("Operating", case=False, na=False)
    mask_tech = df[c_tech].isin(TECH_SOLAR | TECH_WIND | TECH_BESS)

    sub = df[mask_state & mask_status & mask_tech].copy()
    print(f"  ERCOT operating Solar/Wind/BESS: {len(sub):,} rows")

    # Coerce types, drop missing coords
    sub[c_lat] = pd.to_numeric(sub[c_lat], errors="coerce")
    sub[c_lon] = pd.to_numeric(sub[c_lon], errors="coerce")
    sub[c_cap] = pd.to_numeric(sub[c_cap], errors="coerce")
    sub = sub.dropna(subset=[c_lat, c_lon, c_cap])
    sub = sub[sub[c_cap] > 0]
    print(f"  after coord/cap clean: {len(sub):,} rows")

    # Map technology to fuel bucket
    def bucket(t: str) -> str:
        if t in TECH_SOLAR:
            return "SOLAR"
        if t in TECH_WIND:
            return "WIND"
        if t in TECH_BESS:
            return "BESS"
        return "OTHER"
    sub["fuel"] = sub[c_tech].map(bucket)

    out_cols = {
        c_pid: "plant_id",
        c_gid: "gen_id",
        c_plant: "plant_name",
        c_county: "county",
        c_state: "state",
        c_ba: "ba",
        c_tech: "technology",
        c_status: "status",
        c_lat: "lat",
        c_lon: "lon",
        c_cap: "capacity_mw",
    }
    if c_op_year:
        out_cols[c_op_year] = "operating_year"

    out = sub[list(out_cols.keys()) + ["fuel"]].rename(columns=out_cols)
    out = out.sort_values(["fuel", "capacity_mw"], ascending=[True, False])
    return out


def main() -> int:
    url, yyyymm = find_latest_url()
    fname = url.rsplit("/", 1)[-1]
    raw_xlsx = RAW_DIR / fname
    download(url, raw_xlsx)

    units = build_ercot_units(raw_xlsx)
    out_csv = RAW_DIR / f"ercot_units_{yyyymm}.csv"
    units.to_csv(out_csv, index=False)

    by_fuel = units.groupby("fuel").agg(units=("plant_id", "count"),
                                        mw=("capacity_mw", "sum")).round(0)
    print("\n[summary]")
    print(by_fuel.to_string())
    print(f"\n[output] {out_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
