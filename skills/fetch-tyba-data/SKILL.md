---
name: fetch-tyba-data
description: Use when fetching Tyba Energy forecasts for ERCOT BESS — next-day DA/RT energy price forecasts at GKS_BESS_RN (or any node/hub), ERCOT DA ancillary price forecasts (RRS/ECRS/Non-spin/Reg-up/Reg-down), and P(DA>RT)/P(RT>DA) spread-direction probabilities, including vintaged (as-of) pulls for leakage-free backtests. Documents REST auth, endpoints, required params, product names, timestamp semantics, and known gaps (RT AS coverage, no benchmark/shadow-asset API). Replaces fetch-smartbidder-data (Smartbidder subscription ended 2026-10).
---

# Fetch Tyba Data

Tyba Energy Price Forecast API — the project's D+1 price/AS/DART-probability source since 2026-10 (replaced Smartbidder). Full vendor reference: `API Docs/Tyba API Documentation.txt`. Production implementation: `shared/scripts/fetch_tyba_forecast.py` — **daily cycle에서는 `fetch_market_data.py`가 호출하므로 에이전트가 재-fetch하지 말고 산출물 CSV를 읽는다.**

---

## Daily output (read this first)

`shared/data/raw/tyba/{D+1}_GKS_forecast.csv` — one row per HE (CT, HE01–24; 23/25 on DST days)

| Column | Meaning | Source |
|---|---|---|
| `DA_LMP`, `RT_LMP` | GKS_BESS_RN energy price, P50 ($/MWh) | `most_recent_probabilistic_forecast`, `da` / `rt_lmp` |
| `P_RT_gt_DA`, `P_DA_gt_RT` | spread-direction probability — **sum = 1** | `most_recent_forecast`, `rt_energy_gt_da_energy_probability` / `da_energy_gt_rt_energy_probability` |
| `NSPIN`, `REGDN`, `REGUP`, `RRS`, `ECRS` | ERCOT DA AS clearing price, P50 (system-wide) | `most_recent_probabilistic_forecast`, `object_name=ERCOT` |

Spread sign convention (project rule): `spread = DA − RT`. High `P_DA_gt_RT` ⇒ DA expensive ⇒ short-DA signal.

Ad-hoc / backfill: `python shared/scripts/fetch_tyba_forecast.py 2026-10-15` (same output path).

---

## Auth

```python
from _env_loader import load_env_sections        # shared/scripts/_env_loader.py
token = load_env_sections()["tyba"]["TOKEN"]     # .env section header: '# Tyba API'
headers = {"Authorization": token}               # raw token — NO 'Bearer' prefix
```

Corporate network intercepts SSL → `import truststore; truststore.inject_into_ssl()` before requests (the production script does this optionally). Cloud routine: allowlist `dev.tybaenergy.com`.

---

## Endpoints

Base: `https://dev.tybaenergy.com/public/0.1/forecasts` (OpenAPI: `{base}/openapi.json`)

| Endpoint | Use |
|---|---|
| `most_recent_probabilistic_forecast` | energy & AS — latest run, quantiles |
| `vintaged_probabilistic_forecast` | energy & AS — as it stood N days ago / before a time (backtest) |
| `probabilistic_forecasts_by_vintage` | every run created in a vintage window |
| `most_recent_forecast` / `vintaged_forecast` / `forecasts_by_vintage` | point forecasts — **required for the DA/RT probabilities** (probabilistic endpoints return 400 for them) |
| `actuals` | undocumented; needs `org_id` (UUID, ask Tyba) — not used yet |

Required params on every call: `object_name`, `product`, `start_time`, `end_time` (UTC ISO, e.g. CT day 2026-10-15 CDT = `2026-10-15T05:00:00Z`→`2026-10-16T05:00:00Z`; CST = `06:00Z`). Missing → 422. Compute the window DST-aware (see production script) — never hard-code `T05:00Z`.

Probabilistic endpoints additionally **require `quantiles`** (e.g. `0.5`, or `0.1,0.5,0.9`; allowed 0.05–0.95) → response has `values` (one per quantile) + `mean_value`.

### Request shapes that work (verified 2026-10-14)

| Product(s) | object_name | Extra params |
|---|---|---|
| `da`, `rt_lmp` | `GKS_BESS_RN` (or hub e.g. `HB_HOUSTON`) | `forecast_type=day-ahead&predictions_per_hour=1&horizon_mins=1440` |
| `reserves` (RRS), `ecrs`, `non_spin_reserves`, `reg_up`, `reg_down` | `ERCOT` | same as above |
| `da_energy_gt_rt_energy_probability`, `rt_energy_gt_da_energy_probability` | `GKS_BESS_RN` | none (point endpoint) |

---

## Timestamps & vintage

- `datetime` is **hour-beginning**, node-local offset (`2026-10-15T00:00:00-05:00` = HE01).
- `end_time` is inclusive — drop the next day's 00:00 row.
- D+1 runs are issued **D-1 ~06:00 CT** (`forecasted_at`), before the 10:00 CT DAM bid close ⇒ `most_recent_*` pulled before 10:00 is leakage-free. For backtests use `vintaged_*` with `before_time`/`as_of` = D-1 10:00 CT (as_of may be at most 4 days before the operating date).

---

## Gotchas / known gaps

1. **`rt_lmp` with the doc-recommended `rolling-24hr` (pph=4, horizon 1515) stops around HE10** from the morning run. Use the `day-ahead` shape above for a full 24 h.
2. **RT AS (`rt_reserves`, `rt_ecrs`, `rt_reg_up`, …) only exist as `rolling-24hr` 15-min** → D+1 HE01–10 only. Not pulled by the daily pipeline. Day-ahead shape returns empty.
3. **Empty 200 response** ≈ request didn't match a live model (wrong `forecast_type` / pph / horizon for that product).
4. **P(DA>RT) + P(RT>DA) = 1 exactly** (same spread model). Smartbidder's two probabilities were estimated separately and did not sum to 1 — don't compare thresholds across vendors 1:1. Threshold study: `reports/ad-hoc/2026-09-21_Tyba_dart_probability_threshold_solver.md`.
5. **No spike probability product** (Smartbidder-style P(RT>$100)). Use upper quantiles (`quantiles=0.9`) of `rt_lmp` if needed.
6. **No benchmark / Shadow-asset / Production-asset API.** Tyba web UI has Production assets (actual GK schedule/bids/SoC) and Shadow assets (Tyba-optimizer hypothetical), but they're served by the web app's internal GraphQL (session + anti-forgery token; PAT rejected). Inquiry with Tyba pending — until then there is no benchmark revenue and Tenaska PTP is the only actuals source.
7. Smartbidder-era AS forecasts (DA Ancillary Prices plot) and Tyba AS are different models — recalibrate any AS thresholds learned on Smartbidder data before reuse.
