---
name: fetch-ercot-data
description: Use when fetching ERCOT market data — DA/RT LMP, system/regional load·wind·solar (forecast or actual), weather (temperature/dewpoint/wind speed), wind power forecast, or grid conditions (outages/PRC/AS/fuel mix/net-load FC). Documents the four data vendors (Yes Energy, ERCOT Public API, AG2/WSI Trader, Enverus Mosaic) — auth, base URLs, endpoints, item naming, batching, retry, vintage controls, and ERCOT-wide gotchas. Vendor-agnostic; reusable across any ERCOT modeling project.
---

# Fetch ERCOT Data

Four vendors cover virtually all ERCOT modeling needs. Pick by **what data**, then by **priority**:

> **Yes Energy (REST + S3 Datalake) > Enverus > AG2 > ERCOT Public API**

ERCOT Public API has tighter rate limits and slower throughput — it's the fallback when Yes Energy doesn't carry the dataset.

---

## Decision table — which vendor?

| I need… | Vendor | Surface |
|---|---|---|
| DA / RT LMP, system load·wind·solar (FC + actual), regional wind by zone | Yes Energy | DataSignals REST |
| D-day vintage capacity forecast, weather forecast, DA constraints, shift factors | Yes Energy | S3 Datalake (`yedatalake` bucket) |
| Outages (dispatchable / total / scheduled), PRC, AS cleared MW, fuel mix, Enverus net-load FC, Enverus wind STPF | Enverus | Mosaic API |
| Hourly Texas weather (forecast + history) — temp, dewpoint, wind speed, etc. | AG2 (WSI Trader) | CSVDownloadService — `GetHourlyForecasts` / `GetHistoricalObservations` |
| ERCOT regional wind power forecast (alternative to Yes Energy STWPF / COP_HSL) | AG2 (WSI Trader) | Same client — `GetWindcastIQHourlyForecast` |
| ERCOT next-day hourly load forecast — aggregate (`RTO`) and zonal (`SouthCentral`, `Houston`, `North`, `Coast`, …) | AG2 (WSI Trader) | Same client — `GetHourlyLoadData` (subscriber-only) |
| DAM/RTM SPP, load FC, wind/solar STPPF when Yes Energy is unavailable | ERCOT | Public API (OAuth B2C) |

---

## 1. Yes Energy — DataSignals REST API

- **Base URL:** `https://services.yesenergy.com/PS/rest`
- **Auth:** HTTP Basic (`YES_ENERGY_USERNAME` / `YES_ENERGY_PASSWORD`)
- **Bulk limit:** **75 items per call** → batch and concat
- **Bulk endpoint:** `/timeseries/multiple.csv?items=...&startdate=...&enddate=...&agglevel=hour`
- **Response:** wide CSV (`DATETIME, HOURENDING, <item1>, <item2>, ...`) — melt to long

**Item naming = `DATATYPE:OBJECTNAME`**

| Series | Item |
|---|---|
| DA LMP | `DALMP:<node>` |
| RT LMP | `RTLMP:<node>` |
| System load FC / actual | `LOAD_FORECAST:ERCOT` / `RTLOAD:ERCOT` |
| System wind FC (STWPF / COP_HSL) / actual | `WIND_STWPF:ERCOT` / `WIND_COPHSL:ERCOT` / `WIND_RTI:ERCOT` |
| System solar FC (STPPF) / actual | `SOLAR_STPPF:ERCOT` / `SOLAR_RTI:ERCOT` |
| Regional wind (zones) | `WIND_RTI:COAST`, `WIND_RTI:GR_SOUTH`, `WIND_RTI:GR_WEST`, `WIND_RTI:GR_NORTH`, `WIND_RTI:PANHANDLE` (also `_STWPF` / `_COPHSL` variants) |

**Wide-to-long parser:**

```python
melted = df.melt(id_vars=["DATETIME","HOURENDING"], var_name="item_raw", value_name="value")
melted["node"] = melted["item_raw"].str.replace(r"\s*\(.*\)", "", regex=True)
melted["data_type"] = melted["item_raw"].str.extract(r"\(([^)]+)\)")
```

**Rate limiting:** 429 → backoff `5 → 10 → 15s`. 401 → re-check creds (don't loop).

### Yes Energy S3 Datalake

Same vendor, separate surface. Holds **D-day vintage** files the REST API doesn't expose.

- **Bucket:** `yedatalake`
- **Auth:** AWS access key/secret (request from Yes Energy support; store in `.env`, never hardcode)
- **Common keys:**
  - `ercot/forecast/available_cap_forecast/{YYYYMMDD}.csv.gz`
  - `ercot/weather/forecast/{YYYYMMDD}.csv.gz`
  - `ercot/dam/constraints/{YYYYMMDD}.csv.gz`
  - `ercot/shift_factors/{YYYYMMDD}.csv.gz`
- **Pattern:** try D file first, fall back to D-1 (publish timing is irregular)

```python
import boto3, gzip, io, pandas as pd
s3 = boto3.client("s3",
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"])
for file_date in [d_str, d_minus_1_str]:
    try:
        obj = s3.get_object(Bucket="yedatalake",
            Key=f"ercot/forecast/available_cap_forecast/{file_date}.csv.gz")
        with gzip.open(io.BytesIO(obj["Body"].read())) as f:
            df = pd.read_csv(f, header=None)
        break
    except Exception:
        continue
```

---

## 2. Enverus — Mosaic API (grid conditions)

- **Base URL:** `https://api-mosaic-prod.enverus.com/mosaic-api`
- **Auth:** HTTP Basic
- **Endpoint:** `/timeseries/{dataset}` — params: `entity_ids=ERCOT&start_datetime=...&end_datetime=...&as_of=<vintage>&response_type=csv_wide`
- **TLS:** server cert sometimes fails verification — `verify=False` and silence `urllib3.exceptions.InsecureRequestWarning` is the established workaround

**Critical param: `as_of` controls vintage**
- `prior_day_rolling` → values as known on D-1 morning. **Use this for D-day features** (no look-ahead).
- `latest` → revised/final values. Backtest analysis only — do **not** train on this.

**Key dataset IDs (ERCOT):**

| Key | Dataset |
|---|---|
| outage_dispatchable | `ercot-grid_conditions-system_wide-iso_actual_dispatchable_outages` |
| outage_total | `ercot-grid_conditions-system_wide-iso_actual_total_outages` |
| outage_scheduled | `ercot-grid_conditions-system_wide-iso_scheduled_hourly_resource_outage_capacity` |
| prc | `ercot-grid_conditions-system_wide-iso_actual_prc` |
| system_conditions | `ercot-grid_conditions-system_wide-iso_actual_rt_system_conditions` |
| fuel_mix | `ercot-grid_conditions-system_wide-iso_actual_rt_fuel_mix` |
| as_cleared | `ercot-grid_conditions-system_wide-iso_actual_ancillary_service_cleared_mw` |
| env_net_load_fc | `ercot-load-system_wide-env_forecast_net_load` |
| env_wind_gen_stpf | `ercot-generation_wind-system_wide-env_forecast_generation_stpf` |

**Chunking:** long pulls → 3-month chunks, 1s sleep between.

---

## 3. AG2 (WSI Trader) — Weather + Wind Power + Load Forecast

One vendor, one auth, one client. Three product families share the same `_request` plumbing — **build a single client class that exposes `get_*_weather()`, `get_*_windcast()`, and `get_*_load_forecast()` methods**.

- **Base URL:** `https://www.wsitrader.com/Services/CSVDownloadService.svc`
- **Auth:** query-string (vendor's choice, not header): `?Account=<USER>&Profile=<PROFILE>&Password=<PASSWORD>`
- **No forecast archive** — must collect daily and persist if you want forecast history for backtest
- **Long historical pulls time out** → split into ≤6-month chunks per station

### 3a. Weather endpoints

- `/GetHourlyForecasts` — hourly forecast for a delivery date
- `/GetHistoricalObservations` — hourly observed (back to ~2010)

| Param | Values |
|---|---|
| `CityIds[]` | ICAO station codes — see Texas station set below |
| `DataTypes[]` | `temperature`, `dewpoint`, `windSpeed`, `cloudCover`, `windDirection`, `feelsLike`, `heatIndex`, `windChill`, `relativeHumidity`, `precipitation` |
| `TempUnits` | `F` |
| `HistoricalProductID` | `HISTORICAL_HOURLY_OBSERVED` (history endpoint) |
| `ForecastProductID` | `HOURLY_FORECAST` (forecast endpoint) |
| `timeutc` | `false` for local |

**Response quirk:** first line is a station header, second is column names — skip line 0 when parsing.

**Texas station set for ERCOT modeling** — covers the major load centers and the wind-heavy west/south corridors:

| City | ICAO | Region |
|---|---|---|
| Dallas-Fort Worth | `KDFW` | North |
| Houston (IAH) | `KIAH` | Coast |
| Austin (Bergstrom) | `KAUS` | South-Central |
| San Antonio | `KSAT` | South-Central |
| Midland | `KMAF` | West (wind belt) |
| Corpus Christi | `KCRP` | Coast (south) |
| Brownsville | `KBRO` | Lower Rio Grande Valley |

**ERCOT average** — AG2 doesn't expose a single "ERCOT aggregate" weather station. Pull all seven above and compute a load-weighted (or simple) mean per `datetime` × `data_type` at ingestion. Persist both the per-station rows and the aggregate column so downstream features can use either.

### 3b. WindCast IQ (regional wind power forecast)

- **Endpoint:** `/GetWindcastIQHourlyForecast`
- **Forecast types:** `Primary` (issued ~7:45 AM ET — use for D-1 production), `Latest`, `Update`, `All`

**ERCOT SiteIds (UUIDs):**

| Region | SiteId |
|---|---|
| ERCOT aggregate | `89b6bb6e-fdc5-11e5-8259-0019b9b47402` |
| Coastal | `089d129d-5f7a-11e9-937a-0e215c336de8` |
| Panhandle | `08aed221-5f7a-11e9-937a-0e215c336de8` |
| North | `89be4149-fdc5-11e5-8259-0019b9b47402` |
| South | `89dee8da-fdc5-11e5-8259-0019b9b47402` |
| West | `89e1b0f3-fdc5-11e5-8259-0019b9b47402` |

WindCast IQ is often complementary to Yes Energy STWPF / COP_HSL — modelers commonly take the **gap** between sources as a feature.

### 3c. Load Forecast (hourly + daily)

Subscriber-only product (separate licensing from weather/WindCast). For ERCOT, this is an alternative to ERCOT's own MTLF — the **WSI source** is AG2's proprietary forecast trained on their weather model.

- **Hourly endpoint:** `/GetHourlyLoadData` — returns the latest hourly forecast (current model run), typically covering D + several days out
- **Daily endpoint:** `/GetDailyLoadData` — peak / average daily MW; needs `ModelDate` (YYYYMMDD, ≤15 days back) + `ModelRun` (`00` or `12` Z) + `CalcType` (`PEAK` or `AVERAGE`)
- **Observations endpoint:** `/GetLoadObsData` — actual hourly load (`Obstype=latest` or `previous`)

**Required params (hourly):**

| Param | Values |
|---|---|
| `ISO` | `ERCOT` (also `PJM`, `MISO`, `CAISO`, `NYISO`, `ISONE`, `SPP`) |
| `Regions[]` | ERCOT: `RTO` (aggregate), `Houston`, `West`, `North`, `South` |
| `Subzones[]` | ERCOT: `Coast`, `East`, `FarWest`, `North`, `South`, **`SouthCentral`**, `West`, `NorthCentral`, `ALL` |
| `Sources[]` | `WSI` (AG2's own — most useful for next-day forecast), `GFS_OP`, `GFS_ENS`, `ECMWF_OP`, `ECMWF_ENS`, plus ISO-native sources (`PJM`, `PJM_DAY_AHEAD` for PJM only — ERCOT has no `_DAY_AHEAD` source via AG2) |
| `timeutc` (optional) | `false` for local prevailing TZ (default), `true` for UTC |

**Multi-source / multi-region constraints (vendor-imposed):**
1. Multiple `Sources[]` → only **one** `Regions[]` and **one** `Subzones[]` allowed
2. Multiple `Subzones[]` → only **one** sub-region (`Regions[]`) allowed

**Standard ERCOT next-day pulls:**

```python
# ERCOT aggregate (next-day hourly forecast, AG2's WSI source)
params = {"ISO": "ERCOT", "Regions[]": "RTO", "Sources[]": "WSI", "timeutc": "false"}

# South Central zone
params = {"ISO": "ERCOT", "Subzones[]": "SouthCentral", "Sources[]": "WSI", "timeutc": "false"}

# Both in one call (allowed: 1 region + 1 subzone + 1 source)
params = {"ISO": "ERCOT", "Regions[]": "RTO", "Subzones[]": "SouthCentral", "Sources[]": "WSI"}
```

**Vintage / archive:** `GetHourlyLoadData` returns only the **latest** model run — there is no historical archive endpoint for hourly. For backtest history, persist daily as it's published. `GetDailyLoadData` allows fetching past forecasts up to 15 days back via `ModelDate`.

**Use cases:**
- Cross-check vs ERCOT MTLF for systematic over/under bias
- South Central tracks Austin + San Antonio + part of Houston Coast — a surprisingly large slice of ERCOT load and the zone where summer peaks first stress reserves; useful for South-Central / Houston congestion modeling
- Pair `Sources[]=WSI` with `Sources[]=GFS_OP` and `Sources[]=ECMWF_OP` (single-region calls) to build a forecast-disagreement feature

---

## 4. ERCOT Public API (fallback)

- **Base URL:** `https://api.ercot.com/api/public-reports`
- **Auth (two-piece):**
  - OAuth B2C ROPC — POST to `https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token` with `grant_type=password`, `client_id=fec253ea-0d06-4272-a5e6-b478baeecd70`, `scope=openid fec253ea-0d06-4272-a5e6-b478baeecd70 offline_access`. Use `id_token` as Bearer.
  - `Ocp-Apim-Subscription-Key` header alongside Bearer.
- **Token TTL:** ~60 min — cache and refresh ~50 min in.
- **Pagination:** `?size=1000&page=N`, stop when `_meta.totalPages` reached. ~3s between pages.
- **Backoff:** 429/5xx → 30 → 60 → 120 → 300s, force re-auth on retry.

**Common report IDs:**

| Report | Endpoint |
|---|---|
| DAM SPP | `/np4-190-cd/dam_stlmts` |
| RTM SPP | `/np6-905-cd/spp_node_zone_hub` |
| Load forecast (by weather zone) | `/np3-565-cd/lf_by_model_weather_zone` |
| Wind STPPF | `/np4-737-cd/wpp_hrly_avrg_actl_fcast` |
| Solar STPPF | `/np4-738-cd/spp_hrly_avrg_actl_fcast` |
| DAM AS clearing | `/np4-188-cd/dam_clear_price_for_cap` |

---

## .env layout

Each vendor gets its own block. AG2 and Enverus both use generic `USER` / `PASSWORD` keys, so clients typically **hand-parse** by section header rather than rely on plain `python-dotenv` (which would clobber keys across sections).

```
YES_ENERGY_USERNAME=...
YES_ENERGY_PASSWORD=...

# Optional — only if using S3 datalake
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

ERCOT_USERNAME=...
ERCOT_PASSWORD=...
ERCOT_SUBSCRIPTION_KEY=...

# AG2 API Credentials
USER=...
PASSWORD=...
Profile=...

# Enverus
USERNAME=...
PASSWORD=...
```

---

## Universal patterns

### Caching wrapper

Backtests re-run constantly — wrap every raw API call in a parquet cache so reruns hit disk, not the vendor:

```python
def _load_or_fetch(name, fetch_fn, force_refresh=False):
    path = RAW_DIR / f"{name}.parquet"
    if path.exists() and not force_refresh:
        return pd.read_parquet(path)
    df = fetch_fn()
    if not df.empty:
        df.to_parquet(path, index=False)
    return df
```

### Retry / backoff

3 attempts, exponential backoff, force re-auth on 401. Per vendor:
- Yes Energy: `5 → 10 → 15s`
- ERCOT: `30 → 60 → 120 → 300s` (slow API)
- Enverus / AG2: `3 → 6 → 9s`

### Chunking long ranges

| Vendor | Chunk |
|---|---|
| Yes Energy REST | usually fine in one call up to ~2 yr; chunk by year if timing out |
| Enverus | 3-month chunks |
| AG2 historical | 6-month chunks per station |
| ERCOT API | paginate (1000/page); fetch by month |

---

## ERCOT-wide gotchas

1. **HE convention** — Yes Energy and ERCOT both return `HOURENDING` (HE1 = 00:00–01:00). Always normalize at ingestion: `dt.hour = HE - 1`. Off-by-one here silently corrupts every downstream feature.
2. **Spread sign convention (DART)** — `spread = DA − RT`. Positive ⇒ DA expensive ⇒ short DA / long RT signal. Pick once, apply consistently across features, target, and PnL.
3. **D-1 07:30 CPT cutoff** — DAM bid deadline is D-1 10:00 CPT. Every feature for a D-day model must be observable before ~07:30 (~2.5h slack for scoring/submission). Anything later = silent backtest leak. Enverus `as_of=prior_day_rolling` enforces this; Yes Energy items don't — you must check publish time yourself.
4. **DST** — spring-forward = 23 HE in a day, fall-back = 25 HE. Don't assume `len(day) == 24`.
5. **Time zone** — most ERCOT APIs return Central Prevailing Time. If merging with UTC sources (e.g. external weather grids), normalize once at ingestion, not at feature time.
6. **Forecast vintage > forecast accuracy** — a slightly worse forecast available at D-1 07:30 beats a perfect forecast available at D-1 14:00. When picking between vendors for the same series, vintage availability is the tiebreaker.

---

## When **not** to use this skill

- Building features from already-fetched data (that's a feature-engineering task, not ingestion).
- Reading existing parquets in a project's `data/` tree — just `pd.read_parquet`.
- Non-ERCOT ISOs (PJM, MISO, CAISO, NYISO) — vendor surfaces are similar but identifiers / report IDs differ. Don't reuse this skill verbatim.
