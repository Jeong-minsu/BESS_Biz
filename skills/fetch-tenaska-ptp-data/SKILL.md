---
name: fetch-tenaska-ptp-data
description: Use when fetching operational data from Tenaska's PowerTools Platform (PTP) API at api.ptp.energy — typically for previous-day BESS performance (Energy & AS Details, DA Energy bid market result, DA Energy only Offer market result) and resource HSL. Documents Basic→Bearer auth, the PTP hierarchy (root → endpoint → query), `query` vs `query-columnar`, the DataAndElementsQuery filter schema, and the standard previous-day pull pattern.
---

# Fetch Tenaska PTP Data

Tenaska's PowerTools Platform (PTP) exposes resource-level operational data through a generic, schema-driven API. Unlike vendor APIs with fixed endpoints, PTP **endpoints are user/business-defined "Viewports"** that map to a curated dataset (DA bids, AS details, etc.). Same query controller serves all of them.

> **Project use:** the user's ERCOT BESS resource is **GKS** (`GKS_BESS_RN`). Standard pulls for that resource:
> - **Energy & AS Details** — previous-day actuals (energy + ancillary throughput per HE)
> - **DA Energy Bid Market Result** — DA energy bid clearing
> - **DA Energy Only Offer Market Result** — DA energy-only offer clearing
> - **HSL** — high sustained limit (resource capability)

The exact root and endpoint *names* (slugs) you'll hit are configured by Tenaska for your account — discover them via the navigation pattern below, then hardcode the resolved names/IDs.

---

## Auth — Basic → Bearer (24h)

```python
import base64, requests

USER = os.environ["TENASKA_USERNAME"]
PWD  = os.environ["TENASKA_PASSWORD"]
basic = base64.b64encode(f"{USER}:{PWD}".encode()).decode()

r = requests.get("https://api.ptp.energy/authentication/token",
                 headers={"Authorization": f"Basic {basic}"}, timeout=30)
r.raise_for_status()
token = r.json()["data"]
auth_header = {"Authorization": f"Bearer {token}"}
```

- **TTL:** 24 hours from issue. Cache the token (file or in-memory) and refresh near expiration — do NOT fetch a token on every API call.
- **Rate limit:** sliding-window per user, **>1 call/sec sustained → 429**. Pace bulk pulls accordingly.
- **Health check:** `GET /status` should return `"We're live!"`.

**Base URL:** `https://api.ptp.energy`

---

## PTP hierarchy — discovering your endpoints

PTP uses HATEOAS — every response tells you what's clickable next. One-time discovery flow:

```
GET /ptp                                  → list of accessible markets (roots)
GET /ptp/{root}                           → list of endpoints in that market
GET /ptp/{root}/{endpoint}                → schema: element definitions, datapoints, options
GET /ptp/{root}/{endpoint}/elements       → live elements (e.g. resource instances) in date range
GET /ptp/{root}/{endpoint}/options        → reference-list values (e.g. settlement points)
GET /ptp/{root}/{endpoint}/query          → actual data (row-shaped)
GET /ptp/{root}/{endpoint}/query-columnar → actual data (intervallic / columnar shape)
```

`{root}` and `{endpoint}` accept either the friendly name or the GUID. Names may contain spaces — URL-encode.

**One-time setup:** hit `/ptp` and `/ptp/{root}` once, write down the endpoint name/ID for each of the four datasets you care about, then go straight to `/query` afterward.

---

## Standard query — GET form

```python
params = {
    "begin": "2026-04-29",   # yyyy-MM-dd  → flowday inclusive
    "end":   "2026-04-29",   # yyyy-MM-dd  → flowday inclusive
    # or interval form: "2026-04-29T00:00Z" → exclusive begin, inclusive end
    "elementDefinitions": "Generator",  # filter by type — comma or repeated
    "dataPoints": "DA_LMP;RT_LMP",      # ; or repeated query string param
    "fillNulls": "false",
}
r = requests.get(f"https://api.ptp.energy/ptp/{ROOT}/{ENDPOINT}/query",
                 params=params, headers=auth_header, timeout=120)
```

- **Date forms:**
  - `yyyy-MM-dd` → flowday, both inclusive
  - `yyyy-MM-ddTHH:mmZ` → interval-based; **begin exclusive, end inclusive** (note the asymmetry)
- **Array params:** semicolon-delimited (`a;b;c`) or repeated query string (`?dataPoints=a&dataPoints=b`). Use `;` if names contain commas/colons.
- `query` returns **row-per-element** with nested `dataPoints[].values[]`.
- `query-columnar` returns **interval-keyed columnar** form — usually easier to flatten into a wide DataFrame for time-series analysis.

## Filtering with DataAndElementsQuery — POST form

When query-string filtering isn't enough, POST the same payload structure to `/query`, `/query-columnar`, or `/elements`:

```python
payload = {
    "begin": "2026-04-29",
    "end":   "2026-04-30",
    "elementQueryMode": "ByParentAndFilter",
    "elementFilter": [
        {"elementProperty": "Name",
         "expression": "contains 'GKS'",
         "elementDefinition": "Generator"},
    ],
    "sequenceOptions": "GreatestEnabled",  # only the latest version of versioned data
    "dataPoints": ["HSL", "BasePoint", "AS_Awarded_RegUp"],
}
r = requests.post(f"https://api.ptp.energy/ptp/{ROOT}/{ENDPOINT}/query-columnar",
                  json=payload, headers={**auth_header, "Content-Type": "application/json"},
                  timeout=120)
```

**Filter expressions:** `=`, `!=`, `<`, `<=`, `>`, `>=`, `contains`, `!contains`, `not null`. Quote string values: `"contains 'GKS'"`.

**`elementQueryMode`:**

| Mode | When to use |
|---|---|
| `None` (default) | Explicit `elementIdentifiers` list — direct lookup. |
| `ByParentAndFilter` | Treat `elementIdentifiers` as parents; return all live children. **Required** if you want to use `elementFilter`. |
| `AllStaticElements_NoData` | Schema-only: enumerate static elements, skip data. |
| `ElementsByElementDefinition_NoData` | Schema-only: enumerate by element definition. |

**`sequenceOptions`** — only matters for sequenced (versioned) datasets:
- `GreatestEnabled` → latest version only (use this for "what's the current truth")
- `AllEnabled` (default) → every version
- `PreviousEnabled` → second-latest
- `FirstEnabled` → original

---

## The four datasets the user typically needs

For each, the workflow is: discover the `{ROOT}` and `{ENDPOINT}` once, save them, then `query-columnar` for the prior flowday.

### 1. Energy & AS Details (yesterday's actuals)

- **Element definition** typically: `Generator` (filter to `GKS`)
- **DataPoints** to request: energy throughput per HE, plus AS-cleared MW per product (`RegUp`, `RegDown`, `RRS`, `NonSpin`, `ECRS`)
- **Query:** `begin=<yesterday>` flowday; `sequenceOptions=GreatestEnabled` to get the final version

### 2. DA Energy Bid Market Result

- **Element definition:** `DA Energy Bid` (Tenaska's exact slug — verify via `/elements` endpoint)
- The "market result" attaches clearing MW + clearing price as datapoints to each bid element
- Filter to your resource via `elementFilter` on the bid's parent or name

### 3. DA Energy Only Offer Market Result

- **Element definition:** `DA Energy Only Offer` — Tenaska's documented slug for this dataset (appears in their sample queries)
- Same shape as #2 — clearing MW + clearing price datapoints
- Useful filter: pull all offers created on the bid day (`CreatedUtc` between D-1 06:00Z and D-1 14:00Z roughly maps to ERCOT DAM submission window):

```python
"elementFilter": [
    {"elementProperty": "CreatedUtc", "expression": ">=2026-04-28T05:00:00Z",
     "elementDefinition": "DA Energy Only Offer"},
    {"elementProperty": "CreatedUtc", "expression": "<=2026-04-28T15:00:00Z",
     "elementDefinition": "DA Energy Only Offer"},
]
```

### 4. HSL (high sustained limit)

- HSL is typically a **datapoint** on a `Generator` element (not its own endpoint), capturing the resource's hour-by-hour declared capability.
- Once you've identified the endpoint that exposes it (often the same Energy & AS Details or COP endpoint), pull with `dataPoints=["HSL"]` and the resource filter.

---

## Response shape

```json
{
  "data": [
    {
      "element": "GKS_BESS_RN",
      "identifier": "<guid>",
      "definition": "Generator",
      "goLiveDate": "...",
      "expirationDate": "...",
      "dataPoints": [
        {
          "keyName": "HSL",
          "values": [
            {"intervalStartUtc": "2026-04-29T05:00:00Z",
             "intervalEndUtc":   "2026-04-29T06:00:00Z",
             "data": [{"value": 100.0, "sequence": 3}]}
          ]
        }
      ]
    }
  ],
  "validations": [],
  "info": { ... }
}
```

**Flattening helper:**

```python
def flatten_query(j, value_col_name="value"):
    rows = []
    for el in j["data"]:
        for dp in el["dataPoints"]:
            for v in dp["values"]:
                for d in v["data"]:
                    rows.append({
                        "element": el["element"],
                        "datapoint": dp["keyName"],
                        "interval_start_utc": v["intervalStartUtc"],
                        "interval_end_utc":   v["intervalEndUtc"],
                        "value": d.get("value"),
                        "sequence": d.get("sequence"),
                        **d.get("coords", {}),
                    })
    return pd.DataFrame(rows)
```

For dimensioned data (e.g., per-AS-product), the `coords` dict is the dimension key (`{"Product": "RegUp"}`) — spread it into columns when flattening.

---

## Validations (warning vs error)

`response.json()["validations"]` carries non-fatal warnings (`severity: "Warning"`) and fatal errors (`severity: "Error"`). Always inspect:

| Code | Meaning |
|---|---|
| 1101 / 1102 | Begin / End outside viewport — warning, partial data still returned |
| 2101 / 2102 | Invalid begin / end format — error, no data |
| 2104 | Query range outside viewport — error |
| 2106 | Filters resulted in zero datapoints — error (over-filtered) |
| 2401 | Invalid auth scheme — token expired or wrong header |
| 2402 | Rate-limited — back off |

---

## Standard previous-day pull (4-dataset wrapper)

```python
import os, base64, requests, pandas as pd
from datetime import date, timedelta

BASE = "https://api.ptp.energy"

def get_token():
    basic = base64.b64encode(f"{os.environ['TENASKA_USERNAME']}:"
                             f"{os.environ['TENASKA_PASSWORD']}".encode()).decode()
    r = requests.get(f"{BASE}/authentication/token",
                     headers={"Authorization": f"Basic {basic}"}, timeout=30)
    r.raise_for_status()
    return r.json()["data"]

# resolved once via discovery, then hardcoded:
ROOT      = "ERCOT"   # or whatever Tenaska named the market for your account
ENDPOINTS = {
    "energy_as_detail":   "<endpoint_slug_or_guid>",
    "da_energy_bid":      "<endpoint_slug_or_guid>",
    "da_energy_offer":    "<endpoint_slug_or_guid>",
    "hsl":                "<endpoint_slug_or_guid>",  # may be same as energy_as_detail
}
RESOURCE_NAME = "GKS"  # filter substring

def fetch(endpoint_id, payload, headers):
    r = requests.post(f"{BASE}/ptp/{ROOT}/{endpoint_id}/query-columnar",
                      json=payload, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json()

def yesterday_payload(extra_filters=None, datapoints=None):
    yday = (date.today() - timedelta(days=1)).isoformat()
    return {
        "begin": yday,
        "end":   yday,
        "elementQueryMode": "ByParentAndFilter",
        "sequenceOptions": "GreatestEnabled",
        "elementFilter": ([{"elementProperty": "Name",
                            "expression": f"contains '{RESOURCE_NAME}'",
                            "elementDefinition": "Generator"}]
                          + (extra_filters or [])),
        **({"dataPoints": datapoints} if datapoints else {}),
    }

token = get_token()
hdrs = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

energy_as = fetch(ENDPOINTS["energy_as_detail"], yesterday_payload(), hdrs)
hsl       = fetch(ENDPOINTS["hsl"],              yesterday_payload(datapoints=["HSL"]), hdrs)
bid       = fetch(ENDPOINTS["da_energy_bid"],    yesterday_payload(), hdrs)
offer     = fetch(ENDPOINTS["da_energy_offer"],  yesterday_payload(), hdrs)
```

Cache each as parquet keyed by `{dataset}_{flowday}` for backtest replay.

---

## Common gotchas

1. **Bearer-token caching.** A new token on every request will trip the 1-call-per-second average rate limit. Cache for ~23 hours.
2. **Date semantics asymmetry.** `yyyy-MM-dd` form is **inclusive on both ends**; `yyyy-MM-ddTHH:mmZ` form is **exclusive begin, inclusive end**. Mixing them silently shifts your window by a day.
3. **`elementFilter` requires `ByParentAndFilter` mode** (per Tenaska's docs — they note a current bug where `None` mode forces an explicit ID list). Always set `elementQueryMode: "ByParentAndFilter"` when filtering.
4. **`sequenceOptions` for any versioned dataset.** Without `GreatestEnabled`, you'll get every snapshot of the data and may double-count when summing. Set explicitly.
5. **HATEOAS = no static URLs.** Endpoint slugs/IDs are configured per-account. Discover once via `/ptp/{root}`, then save the IDs as constants — but be ready for them to change if Tenaska reorganizes Viewports.
6. **`coords` carries dimensions, not metadata.** Per-product AS data uses `coords: {"Product": "RegUp"}` — when flattening, this is data, not noise. Spread to columns.
7. **All times UTC by default.** Convert to CPT (`America/Chicago`) at the boundary if downstream code expects local — and remember DST: `intervalStartUtc` is unambiguous, `intervalStart` (local) is not.
8. **`/elements` vs `/query`.** `/elements` returns just the element list (no datapoint values), `/query` returns elements + values. Use `/elements` when you only need to enumerate resources.
9. **Validations are silent failure modes.** A 200 OK can still carry `severity: "Error"` validations (e.g., over-filtered → zero datapoints). Always inspect `response.json()["validations"]`.

---

## When **not** to use this skill

- Bid/offer **submission** (POST `/commit`) — that's a write workflow with operational safety considerations and a separate sign-off process; don't fold it into a fetch routine.
- Reading public ERCOT data (DAM/RT prices, system load, AS clearing prices) — those come from Yes Energy / ERCOT API, not PTP. PTP is for *your* resource's bid/award/operational data.
