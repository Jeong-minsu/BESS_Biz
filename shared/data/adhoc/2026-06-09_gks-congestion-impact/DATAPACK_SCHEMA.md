# Per-constraint dashboard data-pack schema (GKS congestion deep-dive)

Each LIVE constraint → one JSON file `derived/datapack_<ID>.json` matching this schema EXACTLY (keys, types).
The main thread renders these uniformly into per-constraint Houston-style dashboards (7 sections).
REUSE already-computed values from the cluster plan files / derived JSONs; only NEW-compute the missing pieces
(outage watch-list lift, standardized thresholds, month×hour matrices where absent). REAL data only; null where genuinely unknown.

```json
{
  "id": "E_PASP",
  "display_name": "E_PASP — PAWNEE–CALAVERAS 345 interface",
  "element": "PAWNEE → CALAVERAS",
  "kv": 345,
  "facility_type": "interface | line | xfmr | GTC",
  "zone_from": "SOUTH", "zone_to": "SOUTH",
  "binding_basis": "base-case | post-contingency-N1",
  "contingencies": ["E_PASP (RTI base)", "..."],
  "gks_sf": { "da": 0.244, "rt": 0.223 },
  "sign": "neg",                          // neg = lowers GKS LMP (charge-favorable); pos = raises (discharge)
  "mechanism": "GKS Valley export loads the SA-import interface (positive SF) -> lowers own LMP",
  "status": "live",                        // live | retired | noise
  "section1_lambda_summary": {             // shadow-price summary (binding only; RT = PRICE>0)
    "da": { "bind_hrs": 4539, "mean": 13.6, "median": 13.6, "p90": 98, "p99": 633, "max": 4566 },
    "rt": { "bind_hrs": 776,  "mean": null, "median": 61, "p90": 259, "p99": 1286, "max": null },
    "rt_cap": 4500,
    "cum_impact_usd_per_mw": { "da": -56360, "rt": -22983, "total": -79343,
                               "note": "DA ex-Jan2026-episode = -38858 (episode = 31% of DA cum)" }
  },
  "section2_month_hour": {                 // P(bind) matrices, rows=month 1..12, cols=hour 0..23 (HE). null cells allowed
    "rt_pbind": [[...24...], ... 12 rows],
    "da_pbind": [[...24...], ... 12 rows]
  },
  "section3_thresholds": [                 // operational trigger table (only factors data supports)
    { "factor": "South wind (GW)", "on_breakpoint": "1.5", "strong": "2.5",
      "pbind_distribution": "0GW:7% -> 1.5GW:30% -> 2.5GW:40%", "lambda_cond": "$61 ($259 P90)",
      "confidence": "HIGH" }
  ],
  "section4_rule_of_thumb": "여름/저녁 HE17-21 + South·coastal wind >1.5GW + SA load >5GW => P(bind)~45-56%, charge-favorable.",
  "section5_outage_watchlist": {           // seasonality-adjusted lift: which real outages co-occur w/ binding
    "informative": true,                   // false if outage-undiscriminated (say so, like MDO-PHR)
    "base_pbind_per_day": 0.16,
    "rows": [ { "facility": "...", "zone": "SOUTH", "out_days": 40, "co_bind": 18,
                "p_bind_given_out": 0.45, "seas_lift": 2.8, "note": "multi-yr" } ],
    "caveat": "co-occurrence != causation; lift = weakening-outage signature, not contingency membership"
  },
  "section6_drivers": [                     // 5-lens verdicts
    { "lens": "demand", "verdict": "CONFIRMED", "evidence": "P(bind) 10%->47% as South load 3->7 GW" },
    { "lens": "supply/renewable", "verdict": "CONFIRMED", "evidence": "..." },
    { "lens": "transmission outage", "verdict": "HYPOTHESIS|CONFIRMED|INSUFFICIENT", "evidence": "..." },
    { "lens": "temperature", "verdict": "...", "evidence": "..." },
    { "lens": "weather", "verdict": "...", "evidence": "..." }
  ],
  "section7_gks_read": "highest-SF live charge signal; lean into cheap charging evening HE17-21 high-wind days.",
  "seasonality_text": "Jan episode + summer (Aug/Jul ex-episode). Hour: evening HE17-21.",
  "caveats": ["Jan-2026 -$17.5k 3-day episode = 31% of DA cum", "RTI base-case interface"]
}
```

## Unified map coords (one file `derived/unified_map_coords.json`) — compiled by the C-agent
Approximate public lat/long for GKS_BESS_RN + the key station of each of the 14 constraints (POS+NEG), labeled APPROXIMATE
(no CEII; datalake has no coords). Same shape as the Houston `corridor_facility_coords_approx.json`:
```json
{ "_meta": {...}, "gks": {"name":"GKS_BESS_RN","lat":..,"lon":..,"zone":"SOUTH"},
  "constraints": [ {"id":"E_PASP","label":"PAWNEE–CALAVERAS","lat":..,"lon":..,"zone":"SOUTH",
                    "sign":"neg","cum_usd":-79343,"status":"live","confidence":"high|med|low"} , ... 14 ] }
```
Flag any station that can't be confidently placed (null lat/lon, listed in `_meta.flagged_unplaceable`).
```
```
