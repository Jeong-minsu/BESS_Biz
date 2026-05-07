"""
Build an interactive Texas grid map (Folium / Leaflet) showing:

  - Solar PV units (EIA-860M operating)        : yellow circles, radius ~sqrt(MW)
  - Wind units                                 : teal circles
  - BESS units                                 : purple circles
  - Load (8 ERCOT Weather Zones, peak demand)  : choropleth on counties

Output: reports/ad-hoc/texas_grid_map.html
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd
import requests
import folium
from folium import plugins
from branca.element import Template, MacroElement

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))
from ercot_weather_zones import (  # noqa: E402
    COUNTY_TO_ZONE, ZONE_PEAK_MW_2025, ZONE_PRETTY, ZONE_COLOR,
    normalize_county, zone_for,
)

RAW_DIR = ROOT / "shared" / "data" / "raw" / "eia"
OUT_HTML = ROOT / "reports" / "ad-hoc" / "texas_grid_map.html"
OUT_HTML.parent.mkdir(parents=True, exist_ok=True)

COUNTIES_GEOJSON_URL = (
    "https://gist.githubusercontent.com/sdwfrost/"
    "d1c73f91dd9d175998ed166eb216994a/raw/"
    "e89c35f308cee7e2e5a784e1d3afc5d449e9e4bb/counties.geojson"
)

FUEL_COLOR = {
    "SOLAR": "#f2c80f",   # warm yellow
    "WIND":  "#06b6d4",   # teal
    "BESS":  "#9333ea",   # purple
}
FUEL_LABEL = {
    "SOLAR": "Solar PV",
    "WIND":  "Wind",
    "BESS":  "Battery (BESS)",
}


def latest_units_csv() -> Path:
    files = sorted(RAW_DIR.glob("ercot_units_*.csv"))
    if not files:
        raise FileNotFoundError(
            "No ercot_units_*.csv in shared/data/raw/eia. "
            "Run fetch_eia860_ercot.py first."
        )
    return files[-1]


def load_units() -> pd.DataFrame:
    p = latest_units_csv()
    df = pd.read_csv(p)
    df["zone"] = df["county"].map(zone_for)
    print(f"[units] {p.name}: {len(df):,} rows")
    n_un = df["zone"].isna().sum()
    if n_un:
        print(f"  WARN: {n_un} units have no zone (unmapped county). "
              f"Counties: {sorted(df.loc[df['zone'].isna(), 'county'].unique())}")
    return df


def zone_capacity_table(units: pd.DataFrame) -> pd.DataFrame:
    """Pivot of zone x fuel capacity (MW), with TOTAL row/col and Load peak."""
    piv = (units.dropna(subset=["zone"])
                 .groupby(["zone", "fuel"])["capacity_mw"].sum()
                 .unstack(fill_value=0).round(0))
    for f in ("SOLAR", "WIND", "BESS"):
        if f not in piv.columns:
            piv[f] = 0
    piv = piv[["SOLAR", "WIND", "BESS"]]
    piv["GEN_TOTAL"] = piv.sum(axis=1)
    piv["LOAD_PEAK"] = piv.index.map(ZONE_PEAK_MW_2025)
    # sort by load peak desc
    piv = piv.reindex(sorted(piv.index, key=lambda z: -ZONE_PEAK_MW_2025.get(z, 0)))
    # add TOTAL row
    tot = piv.sum(numeric_only=True).rename("TOTAL")
    piv = pd.concat([piv, tot.to_frame().T])
    return piv


def load_tx_counties() -> dict:
    """Fetch and cache the 254 TX counties GeoJSON."""
    cache = RAW_DIR / "tx_counties.geojson"
    if cache.exists() and cache.stat().st_size > 100_000:
        gj = json.loads(cache.read_text())
        print(f"[geo] cached: {cache.name} ({len(gj['features'])} features)")
        return gj
    print(f"[geo] download {COUNTIES_GEOJSON_URL}")
    r = requests.get(COUNTIES_GEOJSON_URL, timeout=60)
    r.raise_for_status()
    full = r.json()
    tx = {
        "type": "FeatureCollection",
        "features": [
            f for f in full["features"]
            if str(f["properties"].get("STATEFP", "")).zfill(2) == "48"
        ],
    }
    # annotate each feature with ERCOT zone (None if non-ERCOT)
    for f in tx["features"]:
        nm = f["properties"]["NAME"]
        z = zone_for(nm)
        f["properties"]["zone"] = z
        f["properties"]["zone_pretty"] = ZONE_PRETTY.get(z, "Non-ERCOT")
        f["properties"]["zone_peak_mw"] = ZONE_PEAK_MW_2025.get(z, 0)
        f["properties"]["county_norm"] = normalize_county(nm)
    cache.write_text(json.dumps(tx))
    print(f"[geo] saved {cache.name} ({len(tx['features'])} TX counties)")
    return tx


def radius_for(mw: float) -> float:
    """Marker radius in pixels — sqrt scaling so the eye reads area as MW."""
    if mw <= 0:
        return 2.0
    r = 1.4 * math.sqrt(mw)
    return max(2.5, min(r, 32.0))


def build_map(units: pd.DataFrame, geo: dict) -> folium.Map:
    m = folium.Map(
        location=[31.3, -99.5],   # roughly TX centroid
        zoom_start=6,
        tiles="cartodbpositron",
        control_scale=True,
        prefer_canvas=True,
    )
    folium.TileLayer("OpenStreetMap", name="OSM", show=False).add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellite",
        show=False,
    ).add_to(m)

    # ---------------- Load (zone choropleth on counties) ----------------
    def style_county(feat):
        z = feat["properties"].get("zone")
        if not z:
            return {"fillColor": "#e5e7eb", "color": "#9ca3af",
                    "weight": 0.4, "fillOpacity": 0.15}
        # intensity by zone peak share
        share = ZONE_PEAK_MW_2025[z] / sum(ZONE_PEAK_MW_2025.values())
        # opacity range 0.25 .. 0.75 mapped from share
        op = 0.25 + 0.50 * (share / max(s/sum(ZONE_PEAK_MW_2025.values())
                                        for s in ZONE_PEAK_MW_2025.values()))
        return {
            "fillColor": ZONE_COLOR[z],
            "color": "#ffffff",
            "weight": 0.6,
            "fillOpacity": float(op),
        }

    load_layer = folium.FeatureGroup(name="Load — Weather Zone Peak (MW)", show=True)
    folium.GeoJson(
        geo,
        name="weather-zones",
        style_function=style_county,
        highlight_function=lambda x: {"weight": 2, "color": "#111"},
        tooltip=folium.GeoJsonTooltip(
            fields=["NAME", "zone_pretty", "zone_peak_mw"],
            aliases=["County:", "Weather Zone:", "Zone Peak (MW):"],
            sticky=False,
            labels=True,
            localize=True,
        ),
    ).add_to(load_layer)
    load_layer.add_to(m)

    # ---------------- Generation unit markers ----------------
    # Keep FG references so we can wire interactive radio buttons later.
    gen_fgs: dict[str, folium.FeatureGroup] = {}
    gen_meta: dict[str, dict] = {}
    for fuel in ("SOLAR", "WIND", "BESS"):
        sub = units[units["fuel"] == fuel]
        total_mw = float(sub["capacity_mw"].sum())
        n = len(sub)
        fg = folium.FeatureGroup(
            name=f"{FUEL_LABEL[fuel]} — {n} units / {total_mw:,.0f} MW",
            show=True,
            control=False,   # legend radio buttons drive these instead of LayerControl
        )
        gen_fgs[fuel] = fg
        gen_meta[fuel] = {"n": n, "mw": total_mw}
        cluster = plugins.MarkerCluster(
            name=f"{fuel}-cluster",
            disableClusteringAtZoom=8,
            maxClusterRadius=35,
            showCoverageOnHover=False,
            spiderfyOnMaxZoom=True,
        )
        for _, r in sub.iterrows():
            lat, lon = r["lat"], r["lon"]
            mw = float(r["capacity_mw"])
            pop = (
                f"<b>{r['plant_name']}</b><br>"
                f"Type: {FUEL_LABEL[fuel]}<br>"
                f"Capacity: <b>{mw:,.1f} MW</b><br>"
                f"County: {r['county']}<br>"
                f"Plant ID / Gen: {r['plant_id']} / {r['gen_id']}<br>"
                f"Tech: {r['technology']}"
            )
            folium.CircleMarker(
                location=(lat, lon),
                radius=radius_for(mw),
                color=FUEL_COLOR[fuel],
                weight=1.0,
                fill=True,
                fillColor=FUEL_COLOR[fuel],
                fillOpacity=0.65,
                popup=folium.Popup(pop, max_width=320),
                tooltip=f"{r['plant_name']} — {mw:,.0f} MW",
            ).add_to(cluster)
        cluster.add_to(fg)
        fg.add_to(m)

    # ---------------- Zone summary panel (top-right under LayerControl) ----------------
    zt = zone_capacity_table(units)
    rows_html = []
    rows_html.append(
        '<tr style="background:#f3f4f6; font-weight:600; font-size:10px;">'
        '<th style="padding:3px 6px; text-align:left;">Zone</th>'
        '<th style="padding:3px 6px; text-align:right;">Solar</th>'
        '<th style="padding:3px 6px; text-align:right;">Wind</th>'
        '<th style="padding:3px 6px; text-align:right;">BESS</th>'
        '<th style="padding:3px 6px; text-align:right;">Gen Σ</th>'
        '<th style="padding:3px 6px; text-align:right;">Load Pk</th>'
        '</tr>'
    )
    for z in zt.index:
        is_total = z == "TOTAL"
        z_label = "TOTAL" if is_total else ZONE_PRETTY.get(z, z).split(" (")[0]
        bg = "#fafafa" if not is_total else "#fef3c7"
        sw = ZONE_COLOR.get(z, "#999") if not is_total else "transparent"
        rows_html.append(
            f'<tr style="background:{bg}; font-size:10px; '
            f'{"font-weight:700; border-top:2px solid #333;" if is_total else ""}">'
            f'<td style="padding:2px 6px;">'
            f'<span style="display:inline-block; width:8px; height:8px; '
            f'background:{sw}; border-radius:2px; margin-right:4px;"></span>'
            f'{z_label}</td>'
            f'<td style="padding:2px 6px; text-align:right;">{zt.loc[z, "SOLAR"]/1000:.1f}</td>'
            f'<td style="padding:2px 6px; text-align:right;">{zt.loc[z, "WIND"]/1000:.1f}</td>'
            f'<td style="padding:2px 6px; text-align:right;">{zt.loc[z, "BESS"]/1000:.1f}</td>'
            f'<td style="padding:2px 6px; text-align:right; color:#374151;">'
            f'<b>{zt.loc[z, "GEN_TOTAL"]/1000:.1f}</b></td>'
            f'<td style="padding:2px 6px; text-align:right; color:#7f1d1d;">'
            f'{zt.loc[z, "LOAD_PEAK"]/1000:.1f}</td>'
            f'</tr>'
        )
    summary_html = f"""
    <div style="position: fixed; top: 80px; right: 14px; z-index:9998;
        background:rgba(255,255,255,0.96); padding:8px 10px; border-radius:8px;
        box-shadow:0 2px 8px rgba(0,0,0,0.15); font-family:Inter,Arial,sans-serif;">
      <div style="font-size:11px; font-weight:700; margin-bottom:4px; color:#111;">
        Capacity by Weather Zone (GW)
      </div>
      <table style="border-collapse:collapse;">
        {''.join(rows_html)}
      </table>
      <div style="font-size:9px; color:#6b7280; margin-top:3px;">
        Gen: EIA-860M Mar-2026 (Operating). Load: ERCOT 2025 zone peak.
      </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(summary_html))

    # ---------------- Title ----------------
    title_html = """
    <div style="position: fixed; top: 10px; left: 60px; z-index:9999;
        background:rgba(255,255,255,0.92); padding:10px 14px; border-radius:8px;
        box-shadow:0 2px 8px rgba(0,0,0,0.15); font-family:Inter,Arial,sans-serif;">
      <div style="font-size:15px; font-weight:700; color:#111;">
        ERCOT Grid Map — Solar / Wind / BESS / Load
      </div>
      <div style="font-size:11px; color:#555; margin-top:2px;">
        Units: EIA-860M (March 2026, Operating) &middot; Load: ERCOT 2025 Zone Peak
        &middot; Toggle layers ↗
      </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    # ---------------- Legend (units + zones) ----------------
    z_rows = "".join(
        f'<div style="display:flex; align-items:center; gap:6px; margin:2px 0;">'
        f'<span style="display:inline-block; width:12px; height:12px; '
        f'background:{ZONE_COLOR[z]}; border-radius:2px; opacity:0.8;"></span>'
        f'<span style="font-size:11px;">{ZONE_PRETTY[z]} — '
        f'<b>{ZONE_PEAK_MW_2025[z]/1000:.1f} GW</b></span></div>'
        for z in sorted(ZONE_PEAK_MW_2025, key=lambda x: -ZONE_PEAK_MW_2025[x])
    )

    # Interactive radio rows: ALL / SOLAR / WIND / BESS
    def fuel_radio_row(value: str, label: str, color: str, sub_label: str = "") -> str:
        return (
            f'<label style="display:flex; align-items:center; gap:6px; '
            f'margin:3px 0; cursor:pointer; user-select:none;">'
            f'  <input type="radio" name="fuel-filter" value="{value}" '
            f'         style="margin:0; cursor:pointer;"'
            f'         {"checked" if value=="ALL" else ""}>'
            f'  <span style="display:inline-block; width:12px; height:12px; '
            f'         background:{color}; border-radius:50%;"></span>'
            f'  <span style="font-size:11px;">{label}'
            f'    <span style="color:#6b7280; font-size:10px;">{sub_label}</span>'
            f'  </span>'
            f'</label>'
        )

    fuel_rows_html = (
        fuel_radio_row("ALL", "<b>All</b>", "#374151",
                       f" &mdash; {sum(m_['n'] for m_ in gen_meta.values())} units") +
        fuel_radio_row("SOLAR", FUEL_LABEL["SOLAR"], FUEL_COLOR["SOLAR"],
                       f" &mdash; {gen_meta['SOLAR']['mw']/1000:.1f} GW") +
        fuel_radio_row("WIND",  FUEL_LABEL["WIND"],  FUEL_COLOR["WIND"],
                       f" &mdash; {gen_meta['WIND']['mw']/1000:.1f} GW") +
        fuel_radio_row("BESS",  FUEL_LABEL["BESS"],  FUEL_COLOR["BESS"],
                       f" &mdash; {gen_meta['BESS']['mw']/1000:.1f} GW")
    )

    legend_html = f"""
    <div style="position: fixed; bottom: 24px; left: 14px; z-index:9999;
        background:rgba(255,255,255,0.94); padding:10px 12px; border-radius:8px;
        box-shadow:0 2px 8px rgba(0,0,0,0.15); font-family:Inter,Arial,sans-serif;
        max-width:240px;">
      <div style="font-size:12px; font-weight:700; margin-bottom:4px;">
        Generators <span style="font-weight:400; color:#6b7280; font-size:10px;">
          (click to filter)</span>
      </div>
      {fuel_rows_html}
      <div style="font-size:10px; color:#666; margin-top:6px;">
        circle area &prop; MW (sqrt scaled)
      </div>
      <hr style="margin:6px 0; border:none; border-top:1px solid #eee;">
      <div style="font-size:12px; font-weight:700; margin-bottom:4px;">
        Load (Weather Zone Peak)
      </div>
      {z_rows}
      <div style="font-size:10px; color:#666; margin-top:4px;">
        2025 summer peak forecast, ERCOT CDR
      </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # ---------------- Wire radio buttons to FeatureGroup show/hide ----------------
    map_var = m.get_name()
    js_layers = ", ".join(
        f"'{k}': {gen_fgs[k].get_name()}" for k in ("SOLAR", "WIND", "BESS")
    )
    radio_js = f"""
    <script>
    (function() {{
      function applyFuelFilter(target) {{
        var map = {map_var};
        var layers = {{ {js_layers} }};
        Object.keys(layers).forEach(function(k) {{
          var layer = layers[k];
          var shouldShow = (target === 'ALL' || k === target);
          if (shouldShow) {{
            if (!map.hasLayer(layer)) map.addLayer(layer);
          }} else {{
            if (map.hasLayer(layer)) map.removeLayer(layer);
          }}
        }});
      }}
      // Wait for map+legend to be in DOM, then attach.
      function attach() {{
        var radios = document.querySelectorAll('input[name="fuel-filter"]');
        if (!radios.length) {{ setTimeout(attach, 100); return; }}
        radios.forEach(function(r) {{
          r.addEventListener('change', function(e) {{
            applyFuelFilter(e.target.value);
          }});
        }});
      }}
      if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', attach);
      }} else {{
        attach();
      }}
    }})();
    </script>
    """
    m.get_root().html.add_child(folium.Element(radio_js))

    folium.LayerControl(collapsed=False, position="topright").add_to(m)
    plugins.Fullscreen(position="topleft").add_to(m)
    plugins.MousePosition(position="bottomright", num_digits=3).add_to(m)
    return m


def main() -> int:
    units = load_units()
    geo = load_tx_counties()

    # quick sanity
    n_unmapped = sum(1 for f in geo["features"] if not f["properties"].get("zone"))
    print(f"[geo] non-ERCOT TX counties: {n_unmapped} (expect ~46)")

    m = build_map(units, geo)
    m.save(str(OUT_HTML))
    sz = OUT_HTML.stat().st_size / 1e6
    print(f"\n[output] {OUT_HTML}  ({sz:.2f} MB)")

    # Aggregates for the user
    agg = units.groupby("fuel").agg(units=("plant_id", "count"),
                                    mw=("capacity_mw", "sum")).round(0)
    print("\n[generation summary]")
    print(agg.to_string())
    print(f"\n[load summary] system peak ~ {sum(ZONE_PEAK_MW_2025.values())/1000:.1f} GW")

    zt = zone_capacity_table(units)
    print("\n[zone breakdown - MW]")
    print(zt.round(0).to_string())

    # Also save zone summary CSV for distribution
    summary_csv = OUT_HTML.parent / "texas_grid_zone_summary.csv"
    zt.round(0).to_csv(summary_csv)
    print(f"\n[output] {summary_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
