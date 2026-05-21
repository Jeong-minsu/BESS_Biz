---
name: fetch-smartbidder-data
description: Use when fetching data from Ascend Analytics SmartBidder for ERCOT BESS — next-day DA/RT energy price forecasts, DA ancillary price forecasts, P(DA<RT)/P(DA>RT) spike probabilities, hourly state-of-charge for the prior day, and previous-day revenue summary for benchmark strategies (e.g., "Mount Blue Sky with Virtuals (RTC Version)"). Documents OAuth2 (MSAL) auth, the per-data-type endpoint, request schema, and ERCOT-side gotchas (load/gen sides, hour-ending semantics, plot vs data API).
---

# Fetch SmartBidder Data

Ascend Analytics SmartBidder exposes operational data for a configured BESS / renewable resource: model-generated forecasts, generated bids, awards, SOC, and per-strategy revenue. This skill covers the read-only (GET) access pattern for downstream modeling.

> **Project-specific defaults (this account):** `client=apex`, `iso=ERCOT`, `resource=Kiskadee Storage`. Substitute as needed.

---

## Auth

OAuth2 client-credentials via Microsoft Entra ID (MSAL). Token expires in minutes — cache and refresh.

```python
from msal import ConfidentialClientApplication
from _env_loader import load_env_sections      # shared/scripts/_env_loader.py

# Smartbidder creds live in the '# Smartbidder' .env section. The key names are
# generic (CLIENT_ID / CLIENT_SECRET / APPLICATION_ID) and collide with other
# vendors under a flat python-dotenv load — always read section-aware.
sb = load_env_sections()["smartbidder"]
APPLICATION_ID  = sb.get("APPLICATION_ID", "https://dataascendanalyticscom.azurewebsites.net")
CLIENT_ID       = sb["CLIENT_ID"]
CLIENT_SECRET   = sb["CLIENT_SECRET"]
AUTHORITY_URL   = f"https://login.microsoftonline.com/{sb.get('_TENANT', 'onascend.com')}"

def get_token():
    auth = ConfidentialClientApplication(CLIENT_ID, CLIENT_SECRET, AUTHORITY_URL)
    token = auth.acquire_token_for_client([f"{APPLICATION_ID}/.default"])
    return token["access_token"]

headers = {"Authorization": f"Bearer {get_token()}", "Accept": "application/json"}
```

- **Client secret rotation:** every 12 months — when calls start failing with 401, the secret has likely expired. Contact Ascend rep for a new one.
- **403** on a previously-working call → check `client` and `resource` strings exactly match what Ascend has configured.
- **Authorization** also includes IP allowlist on Ascend's side. Calls from a new VM / CI runner may need their IP whitelisted.

**Base URL:** `https://data.ascendanalytics.com`

---

## Data the model typically wants — and where to get each

There are two parallel surfaces: the **Data API** (raw resource series) and the **Plots API** (ready-to-display aggregates). For most data you have a choice; the Plots endpoint is usually the easiest path.

### 1. DA/RT Energy Forecasted Price (next-day)

**Plot endpoint:** `GET /plots/Energy Price Forecasts`

```python
import urllib.parse
params = {
    "client": CLIENT, "iso": "ERCOT", "resource": RESOURCE,
    "start_date": "2026-05-01T00:00:00-05:00",
    "end_date":   "2026-05-02T00:00:00-05:00",
}
plot_type = urllib.parse.quote("Energy Price Forecasts")
url = f"{BASE}/plots/{plot_type}"
r = requests.get(url, params=params,
                 headers={**headers, "Accept": "application/json"})
```

Returns hourly DA + RT price forecasts that the SmartBidder optimizer is using as inputs. Set `Accept: text/csv` if you'd rather parse CSV.

### 2. DA Ancillary Forecasted Price

**Plot endpoint:** `GET /plots/DA Ancillary Prices` (RT counterpart: `/plots/RT Ancillary Prices`).

> ⚠️ **Naming gotcha:** earlier doc revisions called this `Ancillary Price Forecasts` — that name is NOT registered (returns 404). Verify current plot names against `GET /swagger.json` if anything 404s.

Same param shape as Energy Price Forecasts. Returns per-product hourly columns:
`DA Non-Spin Price`, `DA RegDown Price`, `DA RegUp Price`, `DA RRS Price`, `DA ECRS Price`
plus a parallel `… Forecasted` series per product (the SmartBidder forecast pre-clearing).
For RT: same products at 5-min granularity. Use this for AS price input to BESS / DART agents.

### 3. P(DA<RT) and P(DA>RT) — spike / DART direction probabilities

Two viable endpoints — pick by what you actually need:

- **`GET /forecast-composite`** — raw 5-min probability series. The docs describe `forecast-composite` as "forecasts of spikes (RT LMP > $100 and DA LMP < RT LMP)". This is the model output the SmartBidder optimizer consumes.
- **`GET /plots/DA-RT Forecast`** — same data, plot-friendly aggregation; often hourly.
- **`GET /plots/RT Price Spike Probabilities`** — narrower (RT spike only).

Required params: `client`, `iso`, `resource`, `start_date`, `end_date`, `return_format=json`.

> **Heads-up on predictive value:** in this account's modeling work the DA-RT probability series turned out to have **no incremental predictive value** beyond price/load/wind features alone. Pull it for benchmarking, but don't expect alpha from feeding it into an ML model.

### 4. Hourly SOC for the prior day

**Data endpoint:** `GET /soc-detailed`

```python
params = {
    "client": CLIENT, "iso": "ERCOT", "resource": RESOURCE,
    "start_date": "2026-04-29T00:00:00-05:00",  # yesterday 00:00 CPT
    "end_date":   "2026-04-30T00:00:00-05:00",
    "return_format": "json",
    # "strategy": "Mount Blue Sky with Virtuals (RTC Version)",  # optional
}
r = requests.get(f"{BASE}/soc-detailed", params=params, headers=headers)
```

- Native granularity is **5-minute, period-ending**. Resample to hourly downstream — `df.set_index('timestamp').resample('1H', closed='right', label='right').last()` for an end-of-hour SOC, or `.mean()` for a centered average.
- **Default strategy** is the realized strategy. To pull simulated SOC for a benchmark strategy, pass `strategy=<name>` (comma-separated for multiple).
- Fields: `soc_pct` (0–1), `soc_mwh`, `soc_mwh_max`, optional `soc_mwh_min`.

### 5. Previous-day revenue summary for a benchmark strategy

User's benchmark strategy: **`Mount Blue Sky with Virtuals (RTC Version)`** — Ascend's near-perfect-foresight benchmark including virtuals. Two ways to fetch:

**Hourly / daily detail (Data API):** `GET /revenue`

```python
params = {
    "client": CLIENT, "iso": "ERCOT", "resource": RESOURCE,
    "start_date": "2026-04-29T00:00:00-05:00",
    "end_date":   "2026-04-30T00:00:00-05:00",
    "return_format": "json",
    "strategy": "Mount Blue Sky with Virtuals (RTC Version)",
    "resolution": "daily",   # or 5minutely / hourly / monthly / yearly
}
r = requests.get(f"{BASE}/revenue", params=params, headers=headers)
```

Response is `{columns: [...], data: [[...]]}` — reconstruct as a DataFrame:
```python
j = r.json()
df = pd.DataFrame(j["data"], columns=j["columns"])
```

Columns: `product, revenue, side_of_resource, strategy, timestamp, update_timestamp`. ERCOT-only: `side_of_resource ∈ {gen, load, na_placeholder}`. To get *total* revenue per period, filter `product == "total"` and `side_of_resource == "na_placeholder"`.

**Plot summary:** `GET /plots/Revenue Summary?strategies=Mount Blue Sky with Virtuals (RTC Version)` — pre-aggregated for display; pass `strategies` as a comma-separated list for cross-strategy comparison (active vs. benchmark).

> ⚠️ **`/revenue` is an estimate, not settled.** Ascend explicitly notes that prices may revise (settle prices), and outage/connectivity issues can introduce divergence vs. invoiced settlements. Fine for relative benchmarking; do not reconcile to the books.

---

## Common parameter conventions

| Param | Notes |
|---|---|
| `client` | Your contracted client name. Case-sensitive. |
| `iso` | `ERCOT`, `CAISO`, `PJM`, `SPP`. |
| `resource` | The resource UnitID exactly as configured by Ascend. |
| `start_date` / `end_date` | ISO-8601 with tz offset (`-05:00` for CPT non-DST, `-06:00` during DST — actually CPT is `-06:00` standard / `-05:00` daylight; double-check). **Period-ending, inclusive-exclusive** semantics. To pull "all of yesterday", set `start_date` = yesterday 00:00 CPT, `end_date` = today 00:00 CPT. |
| `return_format` | Must be `json` for Data API endpoints. Plots endpoints accept `json` or `csv` via the `Accept` header. |
| `strategy` / `strategies` | Optional. Defaults to active strategy. Multi-value via comma-separated. |
| `last_updated` | Filter to rows updated since this ISO-8601 timestamp — useful for incremental sync. |

## Plots vs Data API — when to use which

- **Plots API** (`/plots/<plot_type>`) — pre-aggregated, ready to chart. URL-encode the plot type (it has spaces). Set `Accept: text/csv` for CSV output. Use this when you want the same numbers SmartBidder shows in its UI.
- **Data API** (`/forecast-composite`, `/revenue`, `/soc-detailed`, `/da-bids`, `/rt-bids`, `/da-settlements`, `/observed-renewable`, `/ancillary-throughput`, etc.) — raw resource data, finer granularity, more parameters. Use this for modeling pipelines.

---

## Common gotchas

1. **`204 No Content`** is the success-empty case (no data for the requested window) — treat it like an empty DataFrame, not an error. `400` is parameter format / missing-required.
2. **Period-ending semantics throughout.** A timestamp of `2026-05-01T01:00:00-05:00` represents the hour 00:00–01:00 CPT. To match Yes Energy / ERCOT API which return `HOURENDING`, this aligns directly: `dt.hour − 1` rule still applies if you want HE → 0–23 hour-of-day.
3. **`side_of_resource` matters in ERCOT only.** Battery bids/awards split into `gen` (discharge) and `load` (charge). When summing energy revenue, sum across both. For aggregate / cross-ISO comparison, use `na_placeholder` rows where present (`product == "total"`).
4. **5-minute → hourly.** SOC and `revenue` (default) are 5-minute granular. Pick `last` for end-of-hour state, `sum` for hourly revenue, `mean` for averages — never blindly `.first()`.
5. **Plot type names have spaces** (`Energy Price Forecasts`, `Revenue Summary`, `DA-RT Forecast`). URL-encode them: `urllib.parse.quote("Revenue Summary")` → `Revenue%20Summary`.
6. **MSAL tokens are short-lived.** The SDK caches and refreshes when you call `acquire_token_for_client` again, so just call it before each API request batch — don't hand-roll token TTL logic.
7. **Strategy names are exact strings** with spaces and punctuation. `Mount Blue Sky with Virtuals (RTC Version)` must be passed verbatim (URL-encode for the query string).

---

## Standard daily-pull pattern

Run after midnight CPT to pull the prior day's actuals + the next day's forecasts:

```python
import os, requests, urllib.parse, pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

CPT = ZoneInfo("America/Chicago")
BASE = "https://data.ascendanalytics.com"
from _env_loader import load_env_sections
sb        = load_env_sections()["smartbidder"]
CLIENT    = sb.get("SMARTBIDDER_CLIENT", "apex")
RESOURCE  = sb.get("Resource") or sb.get("SMARTBIDDER_RESOURCE", "Kiskadee Storage")
BENCHMARK = "Mount Blue Sky with Virtuals (RTC Version)"

today  = datetime.now(CPT).replace(hour=0, minute=0, second=0, microsecond=0)
y0, y1 = today - timedelta(days=1), today
d0, d1 = today, today + timedelta(days=1)

def gett(path, params):
    r = requests.get(f"{BASE}{path}", params=params, headers=headers, timeout=120)
    if r.status_code == 204: return pd.DataFrame()
    r.raise_for_status()
    j = r.json()
    return pd.DataFrame(j["data"], columns=j["columns"]) if "columns" in j else pd.DataFrame(j)

base = {"client": CLIENT, "iso": "ERCOT", "resource": RESOURCE, "return_format": "json"}

# Forecasts for tomorrow
fc_dart = gett("/forecast-composite",  {**base, "start_date": d0.isoformat(), "end_date": d1.isoformat()})
fc_e    = gett(f"/plots/{urllib.parse.quote('Energy Price Forecasts')}",
               {k: v for k, v in base.items() if k != "return_format"} |
               {"start_date": d0.isoformat(), "end_date": d1.isoformat()})
fc_as   = gett(f"/plots/{urllib.parse.quote('Ancillary Price Forecasts')}",
               {k: v for k, v in base.items() if k != "return_format"} |
               {"start_date": d0.isoformat(), "end_date": d1.isoformat()})

# Yesterday's actuals
soc_y   = gett("/soc-detailed", {**base, "start_date": y0.isoformat(), "end_date": y1.isoformat()})
rev_bm  = gett("/revenue", {**base, "start_date": y0.isoformat(), "end_date": y1.isoformat(),
                            "strategy": BENCHMARK, "resolution": "daily"})
```

Cache each response as parquet keyed by `{endpoint}_{date}` for backtest replay.

---

## When **not** to use this skill

- Submitting bids / overrides — that's `POST /da-bids`, `POST /rt-bids` (write surface) and is a separate workflow with safety implications.
- Settlement reconciliation — `/revenue` is estimates, not invoiced settlements.
- Non-Ascend ISOs you don't own — auth scoping prevents cross-account access anyway.
