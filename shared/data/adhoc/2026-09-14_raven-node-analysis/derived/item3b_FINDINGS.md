# ITEM 3b — How Houston-zone ESS actually operate; energy-arbitrage vs AS for Raven

**Date**: 2026-09-14 | **Author**: item3b workstream | **Asset assumption**: Raven 100 MW / 200 MWh (2 h), RVN_RN (HOUSTON)
**Data**: all real fetches, no mock. Sources per section. Post-RTC+B era only (every window here is >= 2025-12-05, so one disclosure schema).
**Efficiency**: where a round-trip efficiency is applied it is stated (ETA = 0.85). TB2 itself is pre-efficiency per BRIEF.

> Estimate, not settlement. Fleet revenue is a public-data (60-day disclosure) estimate via `skills/estimate-bess-energy-as`. AS MCPC is ERCOT system-wide — no nodal multiplier applied anywhere.

---

## 0. Answer in three lines

1. **Raven's TB2 is not "high" — it is Houston-median-minus.** Summer 2026 (6/4–8/31) RT TB2 = **$46.95/MWh**, vs HB_HOUSTON 47.14, Houston-zone median 48.92 (**28th percentile of 232 Houston generator nodes**), RBN_BESS1 48.16, TAV_RN 47.98, but **GKS_BESS_RN 37.24**. The "+26% vs GKS" is a SOUTH-vs-HOUSTON zonal effect, not a Raven-node premium. Its top-2 and bottom-2 hours are at normal Houston absolute levels (top-2 RT $66.4 vs Houston median 68.8; bottom-2 $19.4 vs 19.8) — the TB2 is real, not an artifact of one rich or one cheap hour.
2. **Energy-lean is right, and it would be right at any Houston node**: AS MCPCs are system-wide and tiny in 2026 (summer RT RRS $0.3, ECRS $0.6, NSPIN $1.8–4.2 /MW-h; DA ~2x RT). Parking 100 MW in the best up-product during Raven's four cycling hours is worth ~$30/MW-day (median day $6.7) vs ~$87/MW-day for the 2-hour energy cycle net of ETA. **Crossover TB2 ≈ $3.4/MWh (median day), $15/MWh (mean, spike-skewed)**; energy beat AS-in-cycling-hours on **98.9 %** of summer days and in **every** tightness × congestion cell (ratio 4.5–11x).
3. **AS is additive, not a substitute**: the fleet earns AS mostly by *stacking* it in the 20 non-cycling hours (and holding DA AS awards through the peak, where DA MCPC at HE21–23 is $6–14/MW-h vs $30–37/MWh energy margin). The recommended mix is therefore *energy first in the 4 cycling hours, DA-sold AS (NSPIN/ECRS > RRS) on idle capacity*, with the AS allocation grown only on TIGHT days (see §5). See §2 for what the Houston 2 h fleet actually does.

---

## 1. Houston-zone BESS fleet

Source: `ercot/metadata/objects/all.csv.gz` (price_node ZONE) joined to the ERCOT DAM-ESR disclosure (`Settlement Point Name` per ESR). Capacity = **SCED-observed** `max(max HSL, max Telemetered Net Output)`; duration = `(Max SOC − Min SOC) / cap` from SCED ESR rows (see §3). EIA-860M July-2026 (`scratchpad/ercot_units_202607.csv`, real pull) used as a nameplate cross-check where the plant exists there; **Raven Storage is not yet in the EIA-860M July-2026 operating tab** (COD June 2026), so Raven's capacity is SCED-only.

_(fleet table — filled from `item3b_houston_mix_summer.csv` / `_ytd.csv` after the summer disclosure chunks complete)_

## 2. Actual product mix per resource

_(filled after chunks; YTD 1/2–5/25 preview is in `item3b_houston_mix_ytd_test.csv`)_

## 3. Capacity-denominator sanity

_(filled after chunks)_

## 4. Energy-vs-AS trade-off for Raven — the node-level facts

Source: `raw/price_panel` (Yes Energy datalake nodal hourly DA/RT LMP), `ercot/ancillary/rtc_mcpc_*` (RT MCPC, 5-min → hourly mean), ERCOT DAM-ESR disclosure (DA MCPC, one system-wide row per hour). Window 2026-06-04..08-31 (89 flowdays; first day with RVN_RN DA LMP).

### 4.1 Raven vs peers — absolute levels, not just spread (summer means, $/MWh)

| Node | zone | TB2 DA | TB2 RT | top-2 DA | bot-2 DA | top-2 RT | bot-2 RT | mean RT |
|---|---|---|---|---|---|---|---|---|
| HB_WEST | — | 46.96 | 56.98 | 60.48 | 13.52 | 69.12 | 12.13 | 29.76 |
| HB_NORTH | — | 43.16 | 53.52 | 61.45 | 18.29 | 70.41 | 16.89 | 31.79 |
| HB_BUSAVG | — | 41.21 | 49.68 | 59.42 | 18.22 | 67.17 | 17.49 | 31.48 |
| RBN_BESS1 | HOUSTON | 39.93 | 48.16 | 59.65 | 19.72 | 67.84 | 19.68 | 33.25 |
| TAV_RN | HOUSTON | 39.41 | 47.98 | 59.00 | 19.60 | 66.64 | 18.66 | 32.30 |
| HB_HOUSTON | — | 38.81 | 47.14 | 58.85 | 20.04 | 67.00 | 19.85 | 33.65 |
| **RVN_RN** | **HOUSTON** | **39.27** | **46.95** | **58.81** | **19.54** | **66.38** | **19.44** | **32.51** |
| HB_SOUTH | — | 37.57 | 45.58 | 55.62 | 18.04 | 61.99 | 16.41 | 30.27 |
| GKS_BESS_RN | SOUTH | 25.14 | 37.24 | 42.45 | 17.31 | 52.22 | 14.98 | 28.40 |

- Raven's TB2 advantage over GKS (+$9.7 RT) is **all in the discharge leg** (+$14.2 top-2) partly given back on the charge leg (Raven charges $4.5 dearer than GKS — the Valley has cheaper midday power).
- Within the Houston zone (232 generator nodes, ≥80 days): Raven's percentile — TB2 RT **28 %**, top-2 RT 32 %, bottom-2 RT 41 %; TB2 DA 36 %. The zone is tight (TB2 RT std $2.2 across nodes). Raven sits in the Fort Bend/Brazoria BESS cluster (RBN, TAV, WAL, CLO) at ~$47–48, below the Brazoria-load-pocket cluster (PHO_ALL 49.7, EVLN 48.9, HLY 48.8) and above the Bypass/Jar/Longbow group (42.6–44.4). File: `item3b_houston_nodes_tb2_summer.csv`.
- Hour-of-day: Raven's top-2 hours are HE20–21 (57 %/50 % of days), bottom-2 are HE9–11 (solar belly, not overnight). Raven's basis vs HB_HOUSTON is ≈0 at the peak (+0.2..+0.6 HE20–22) and **negative midday (−3.3..−4.0 HE12–18)** — the node discounts in solar hours, which mildly helps a midday charge but does not change the peak.

### 4.2 Hour-by-hour: energy margin vs best AS price (summer means; margins net of ETA=0.85)

`dis_margin` = RT LMP(HE) − bot-2 RT / ETA (value of discharging that hour with energy bought at the day's bottom-2). `best_up` = max(RegUp, RRS, ECRS, NSPIN) MCPC that hour. Full table: `item3b_hourly_crossover_summer.csv`.

| HE | RVN RT | dis margin | best up-AS (RT) | P(dis > AS) | share of top-2 days |
|---|---|---|---|---|---|
| 9–11 | 21–22 | −1.7..−0.8 | 0.8–1.4 (RegUp) | 10–22 % | bottom-2 hours (22–27 % each) |
| 12–18 | 23–32 | +0.5..+9.5 | 0.75–1.1 (RegUp) | 42–85 % | ~1 % |
| 19 | 38.9 | +16.0 | 1.3 | 93 % | 2 % |
| **20** | **56.0** | **+33.1** | 3.1 | **100 %** | **28 %** |
| **21** | **59.6** | **+36.8** | 7.6 (NSPIN) | **100 %** | **32 %** |
| 22 | 53.5 | +30.7 | 16.9 (NSPIN) | 87 % | 12 % |
| 23 | 46.1 | +23.3 | 16.8 (NSPIN) | 82 % | 6 % |
| 24, 1–7 | 26–35 | +3..+12 | 1.3–7.0 (NSPIN) | 57–89 % | ≤3 % |

Reading: in the two discharge hours the energy margin is 4–12x the best AS price *on average* and beats it on 100 % of days — there is no hour in the peak block where parking MW in AS is the better use of a full battery. AS only competes in the belly (HE9–18) where the battery is charging/idle anyway — i.e. AS is an **idle-capacity add-on**, not a peak substitute. DA AS MCPC is systematically higher than RT (YTD: DA > RT in 90–93 % of hours for RRS/ECRS/NSPIN; DA NSPIN HE21–23 $12–14 vs RT $8–13), so AS should be sold DA.

### 4.3 Crossover

Per MW, 2 h of energy arbitrage = `2 × (top2 − bot2/ETA)` ≈ **$87/MW-day** (summer mean; $35 loose / $118–185 tight). Parking the same MW in the best up-product during those 4 cycling hours = **$30/MW-day mean, $6.7 median** (RT MCPC). Crossover TB2 = AS4/2: **median $3.4/MWh, p75 $8.6, p90 $16, p95 $53**. Raven's TB2 is above the p90 crossover on essentially every day; energy won on 98.9 % of days (and beat even a full 24 h AS park on 66 % of days). Because AS pays the same at every node, the *only* thing that would flip this is a node with TB2 < ~$5–15 — no Houston node is near that.

## 5. Regime conditioning (summer 2026, 89 days) — 2 × 2 playbook

Tightness = daily system top-2 RT price (HB_BUSAVG) split at the median ($47); congestion sign = daily mean RT basis RVN_RN − HB_HOUSTON. Price-side cells from `item3b_regime_2x2_summer.csv`; fleet actual mix from `item3b_regime_fleet_mix_summer.csv` (§5.2, after chunks).

| cell (days) | RVN TB2 RT / DA | top-2 / bot-2 RT | basis (dis / chg) | energy 2h $/MW-d | AS 4h / AS 24h $/MW-d (RT) | E ÷ AS4 | lean |
|---|---|---|---|---|---|---|---|
| LOOSE × NEG (37) | 20.7 / 28.8 | 39.4 / 18.7 | −1.5 / −1.8 | 35 | 5 / 30 | 7.3x | energy, **DA-heavy** (DA TB2 > RT TB2); AS stacks freely |
| LOOSE × POS (7) | 27.1 / 26.3 | 48.8 / 21.7 | +6.2 / +0.1 | 47 | 7 / 36 | 11.2x | energy RT-lean (node premium shows up RT at discharge) |
| TIGHT × NEG (33) | 62.5 / 43.6 | 80.9 / 18.4 | +0.4 / −1.7 | 119 | 45 / 103 | 6.9x | energy RT-lean; charge leg benefits from NEG basis; carry DA NSPIN/ECRS on idle MW |
| TIGHT × POS (12) | 96.8 / 67.3 | 120.2 / 23.5 | +2.2 / +0.2 | 185 | 79 / 188 | 4.5x | energy RT-lean; AS spikes too — 24 h AS park ≈ 2 h energy, so **stack both**: full discharge at peak, max DA AS on the other 20 h |

Notes: (i) on TIGHT days DA TB2 lags RT TB2 by $19–29 → keep discharge MW for RT (short DA / long RT, spread = DA−RT negative); on LOOSE days DA TB2 exceeds RT TB2 by $8 → sell the cycle DA. (ii) POS-basis days are rare (19/89) and the premium is concentrated in the discharge hours (+2..+6), so a POS-basis day-ahead signal is an "extra RT discharge" signal, not a mix change. (iii) The NSPIN 24 h value on TIGHT days ($90–171/MW-d) is real but is earned on the *non-cycling* hours; it never exceeds the energy margin inside the peak block.

_(§5.2 fleet actual mix by cell — after chunks)_

---

## Files

Scripts (`scripts/`): `item3b_run_chunks.py`, `item3b_tb2_prices.py`, `item3b_rt_as_mcpc.py`, `item3b_da_as_mcpc.py`, `item3b_product_mix.py`, `item3b_crossover_regime.py`.
Derived (`derived/`): `item3b_hourly_prices_2026.parquet`, `item3b_daily_tb2.csv`, `item3b_summer_tb2_summary.csv`, `item3b_houston_nodes_tb2_summer.csv`, `item3b_rt_as_mcpc_hourly_2026.parquet`, `item3b_da_as_mcpc_hourly_2026.parquet`, `item3b_hourly_crossover_summer.csv`, `item3b_daily_regime_features_summer.csv`, `item3b_regime_2x2_summer.csv`, `item3b_houston_mix_*.csv`, `item3b_houston_hourly_mix_*.csv`, `item3b_houston_tb_daily_*.parquet`, `item3b_regime_fleet_mix_*.csv`.
