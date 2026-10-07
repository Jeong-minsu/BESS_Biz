# ITEM 1 — Raven (RVN_RN) vs GKS (GKS_BESS_RN): TB2, summer 2026

**Script**: `scripts/item1_tb2_rvn_vs_gks.py` | **Data**: `raw/price_panel/2026{06,07,08}.parquet` (Yes Energy datalake, real hourly DA/RT LMP; no mock, no fill)
**Outputs**: `item1_daily_tb2.csv` (per node/day/market TB2 + top-2/bottom-2 HE & prices), `item1_hourly_prices.csv`, `item1_summary.json` (dashboard-ready: `daily.{DA,RT}` series + summary blocks), `item1_tables.md`.

## Definitions and window

- Hourly prices are **period-ending CT**; HE1..HE24 (00:00 stamp = HE24 of the prior flowday, via panel `FLOWDAY`).
- `TB2 = mean(top-2 hourly LMP) − mean(bottom-2 hourly LMP)` per flowday, DA and RT separately, $/MWh.
- Revenue proxy = TB2 × 200 MWh (100 MW / 2h). **No round-trip efficiency applied** (theoretical, before RTE).
- Hubs: RVN_RN → `HB_HOUSTON` (OBJECTID 10000697077); GKS_BESS_RN → `HB_SOUTH` (10000697079); system reference `HB_BUSAVG` (10000698380). All are ERCOT hub price_nodes present in the panel.
- **Effective window** (days where *both* nodes have a full 24h):
  - DA: **2026-06-04 .. 2026-08-31, 89 days** — RVN_RN DA is missing 6/1, 6/2, 6/3 (node not yet priced).
  - RT: **2026-06-03 .. 2026-08-31, 90 days** — RVN_RN RT is missing 6/1 and 6/2 (6/2 only partial, dropped rather than filled).
  - GKS has all 92 days. The missing Raven days are excluded from every comparison, not imputed. Stats are on common days only, so the two nodes are always compared on identical dates.

## Headline

| $/MWh (daily TB2 mean) | RVN_RN | GKS_BESS_RN | Δ (RVN−GKS) | RVN wins (% days) |
|---|---|---|---|---|
| **DA** (89 d) | **39.27** (median 27.2) | **25.14** (median 21.0) | **+14.13** (+56%) | 91% |
| **RT** (90 d) | **46.66** (median 30.8) | **37.04** (median 25.3) | **+9.62** (+26%) | 63% |

Cumulative theoretical TB2 revenue, 100 MW/200 MWh, before RTE: DA **$699k vs $448k (+$251k)**; RT **$840k vs $667k (+$173k)** over the window.

Monthly DA TB2 means: Jun 25.0 vs 19.8, Jul 41.2 vs 25.3, Aug 49.8 vs 29.6. The gap widens every month into peak summer (DA Δ: +5.2 → +15.8 → +20.2; RT Δ: +2.5 → +4.1 → +21.7).

**Raven wins clearly in both markets, and the reason is not that Raven is a rich node — it is that GKS is a discounted one.** Raven's TB2 is essentially the Houston hub TB2 (DA 39.27 vs 38.81), and slightly *below* the system average (HB_BUSAVG 41.21). GKS sits $12–16/MWh below its own hub and the system.

## Q1 — Is Raven's TB2 high because discharge is rich or because charge is cheap?

Exact additive decomposition: `ΔTB2 = Δ(top-2 mean) − Δ(bottom-2 mean)` (discharge-side vs charge-side contribution).

| | ΔTB2 | discharge (top-2) contrib | charge (bottom-2) contrib | dominant |
|---|---|---|---|---|
| DA overall | +14.13 | **+16.36** | −2.23 | discharge |
| DA Jun / Jul / Aug | +5.2 / +15.8 / +20.2 | +6.5 / +19.3 / +22.0 | −1.3 / −3.5 / −1.8 | discharge, every month |
| RT overall | +9.62 | **+14.00** | −4.38 | discharge |
| RT Jun / Jul / Aug | +2.5 / +4.1 / +21.7 | +6.5 / +10.7 / +24.1 | −4.0 / −6.6 / −2.5 | discharge, every month |

**Answer: discharge, entirely.** Raven's top-2 hours are $14–16/MWh richer than GKS's; Raven's charge hours are actually *more expensive* than GKS's (GKS bottom-2 is cheaper by $2–4/MWh, which works against Raven). The charge side is a small drag in every month, DA and RT. Sanity: GKS's cheapest DA hour in the window was $4.61 vs Raven's $13.77; GKS also printed 5 RT hours below zero (min −$2.30), Raven none.

## Q2 — Why do they differ? Hub vs local congestion basis

`ΔTB2 = [TB2(HB_HOUSTON) − TB2(HB_SOUTH)] + [TB2(RVN) − TB2(HB_HOUSTON)] − [TB2(GKS) − TB2(HB_SOUTH)]` (exact, checked).

| $/MWh | ΔTB2 | (1) zonal hub gap HOU−SOUTH | (2) Raven local basis | (3) GKS local basis | net local (2)−(3) |
|---|---|---|---|---|---|
| **DA overall** | +14.13 | +1.24 (9%) | +0.46 (3%) | **−12.43 (88%)** | +12.89 |
| DA Jun / Jul / Aug | +5.2 / +15.8 / +20.2 | +0.4 / +0.5 / +2.7 | −0.1 / +0.9 / +0.5 | −4.9 / −14.4 / −17.0 | |
| **RT overall** | +9.62 | +1.57 (16%) | −0.22 (−2%) | **−8.28 (86%)** | +8.05 |
| RT Jun / Jul / Aug | +2.5 / +4.1 / +21.7 | +1.4 / −0.6 / +3.9 | −1.6 / +0.4 / +0.4 | −2.7 / −4.2 / −17.4 | |

Ranked root causes:

1. **GKS local congestion discount in its discharge hours (~86–88% of the gap).** GKS's node−hub basis in its own top-2 hours averages **−$10.4/MWh (DA)** and **−$5.6 (RT)**; the basis is positive in only 10% (DA) / 31% (RT) of its discharge hours. Hour-of-day profile: GKS basis vs HB_SOUTH is ≈0 through the day but collapses to **−15.6 / −15.8 (DA HE20/HE21)** and −13.0 / −14.3 (RT HE20/21) — exactly the evening ramp when a 2h battery discharges. Median evening (HE19–22) GKS basis is −8.4 DA; it is below −$5 on 63% of days and positive on only 3%, and it deepens by month (Jun −2.9 → Jul −10.0 → Aug −11.4). This is the South/Valley export-constraint signature already documented for GKS (see project memory: GKS_BESS_RN = SOUTH/Valley zone, MCC = −SF×λ). Corroboration from dispatch timing: Raven's DA top-2 hours are HE20–21 in 79% of slots, whereas GKS's are pushed later to HE22–23 in 46% of slots (Raven 18%) — GKS's optimal discharge migrates out of the congested HE20–21 window, forfeiting the system peak.
2. **Zonal hub difference, Houston vs South (~9–16%).** HB_HOUSTON TB2 exceeds HB_SOUTH by only $1.2 (DA) / $1.6 (RT). Houston is priced above South by up to +$10/MWh in the solar midday (HE12–17), but that is when both nodes *charge*, so it barely moves TB2; in the evening peak the hub gap is only +$3–4.
3. **Raven's own basis is ~zero where it matters (~0–3%).** RVN_RN tracks HB_HOUSTON almost exactly in the evening (DA basis HE20–24 within ±$0.4, median evening basis −0.24, never below −$5 on a daily-average basis). Raven does carry a **negative midday basis (−$3 to −$5 at HE12–17, DA and RT)**, i.e. the node is *cheaper* than the Houston hub during solar hours — but Raven's bottom-2 hours are usually HE9–11 where the basis is ≈0, so this only adds a fraction of a $/MWh via the charge side. Net: Raven's congestion basis is neutral in discharge hours and mildly favourable in charge hours — **it is not a congestion-premium node**.

Take-away for the FY2027 outlook: Raven's TB2 should be modelled as **≈ HB_HOUSTON TB2 (≈ 0.95× HB_BUSAVG)**, not as GKS × uplift. The GKS→Raven "uplift" (+56% DA) is almost entirely the removal of GKS's evening South-zone discount, which is GKS-specific and should not be extrapolated as Houston upside.

## Q3 — DA vs RT behaviour

| Node | DA TB2 | RT TB2 | RT/DA | RT>DA days | RT TB2 σ |
|---|---|---|---|---|---|
| RVN_RN | 39.27 | 46.95 | 1.20 | 47% | 59.2 |
| GKS_BESS_RN | 25.14 | 37.24 | **1.48** | **67%** | 49.6 |
| HB_HOUSTON / HB_SOUTH / HB_BUSAVG | 38.8 / 37.6 / 41.2 | 47.1 / 45.6 / 49.7 | 1.21 / 1.21 / 1.21 | 52 / 54 / 51% | 58 / 55 / 62 |

- Raven is **not** an RT-volatility-driven node: its RT/DA ratio (1.20) equals the hubs', and RT beats DA on fewer than half of days (the RT mean is pulled up by two days: 8/17 RT TB2 $226 and 8/22 $141). Its DA TB2 is where the structural edge lives (RVN>GKS on 91% of DA days).
- GKS *is* relatively RT-skewed (RT/DA 1.48, RT>DA on 67% of days) — but for the wrong reason: its DA is depressed by the evening congestion discount, and RT dispersion around a low DA level makes RT look attractive. The RT gap RVN−GKS is smaller (+9.6) and noisier (p10 −6.8, p90 +32.4; 37% of days GKS RT TB2 > RVN).

## Q4 — Tails (LMP<0, LMP>$500), common-day window

| | DA <0 h | DA >500 h | RT <0 h (sum) | RT >500 h | RT max | DA max |
|---|---|---|---|---|---|---|
| RVN_RN | 0 | 0 | **0** | 1 ($525.5, 8/26 HE23) | 525.5 | 229.3 (higher than GKS 141.4) |
| GKS_BESS_RN | 0 | 0 | **5** (−$5.7 total, min −2.30; 7/14 HE13, 7/17 HE11/13/14, 8/07 HE19) | 1 ($521.0, same hour) | 521.0 | 141.4 |
| hubs | 0 | 0 | 0 | 1 each (525.8–534.6) | | |

Summer 2026 was a low-scarcity summer: a single system-wide RT hour above $500 (2026-08-26 HE23, all nodes), no hour above $1,000, no DA hour above $230. Tail behaviour therefore does not separate the nodes; the only node-specific tail is GKS's handful of slightly negative RT hours (midday solar + one evening hour), consistent with its export-constrained location. Raven shows no negative-price exposure in the window (min RT $9.74).

## Caveats

- 89/90 common days of a single summer; Raven's history starts 2026-06-02/04, so there is no prior-year check on Raven's basis behaviour (proxy validation is another agent's item).
- TB2 is theoretical (perfect foresight, no RTE, no AS, no SOC constraints); use for relative node comparison, not absolute revenue.
- Zonal attribution uses hub prices as the reference; the "local basis" therefore includes anything not captured by the zonal hub (nodal congestion + losses).

---

# Full tables (generated by `item1_tb2_rvn_vs_gks.py`)

**DA TB2 daily stats ($/MWh), 2026-06-04..2026-08-31 (89 common days)**

|               |   n |   mean |   median |   p10 |   p90 |   min |    max |     sum |
|:--------------|----:|-------:|---------:|------:|------:|------:|-------:|--------:|
| RVN_RN        |  89 |  39.27 |    27.23 | 18.82 | 73.08 | 10.16 | 198.79 | 3495.14 |
| GKS_BESS_RN   |  89 |  25.14 |    20.98 | 14.99 | 38.72 |  7.24 | 117.69 | 2237.73 |
| HB_HOUSTON    |  89 |  38.81 |    27.01 | 19    | 71.39 | 10.4  | 191.49 | 3454.51 |
| HB_SOUTH      |  89 |  37.57 |    26.96 | 20.15 | 64.82 |  9.84 | 175.25 | 3344.13 |
| HB_BUSAVG     |  89 |  41.21 |    29.01 | 20.37 | 77.69 | 11.26 | 198.17 | 3667.62 |
| RVN_minus_GKS |  89 |  14.13 |     6.86 |  0.18 | 34.64 | -4.77 | 119.65 | 1257.41 |


**DA TB2 monthly mean ($/MWh)**

|         |   RVN_RN |   GKS_BESS_RN |   HB_HOUSTON |   HB_SOUTH |   HB_BUSAVG |
|:--------|---------:|--------------:|-------------:|-----------:|------------:|
| 2026-06 |    25.02 |         19.8  |        25.12 |      24.72 |       25.87 |
| 2026-07 |    41.16 |         25.34 |        40.25 |      39.75 |       42.64 |
| 2026-08 |    49.79 |         29.59 |        49.31 |      46.59 |       53.14 |


**DA RVN−GKS daily TB2 delta decomposition ($/MWh): discharge (top-2) vs charge (bottom-2) contribution**

|         |   delta_tb2 |   discharge_contrib |   charge_contrib |   discharge_share | dominant   |
|:--------|------------:|--------------------:|-----------------:|------------------:|:-----------|
| overall |       14.13 |               16.36 |            -2.23 |             1.158 | discharge  |
| 2026-06 |        5.22 |                6.5  |            -1.28 |           nan     | discharge  |
| 2026-07 |       15.82 |               19.3  |            -3.49 |           nan     | discharge  |
| 2026-08 |       20.2  |               22    |            -1.8  |           nan     | discharge  |


**DA hub/basis decomposition of RVN−GKS TB2 gap ($/MWh)**

|         |   delta_tb2 |   hub_houston_minus_south |   rvn_local_basis_contrib |   gks_local_basis_contrib |   net_local |   tb2_busavg |   tb2_hb_houston |   tb2_hb_south |   rvn_vs_busavg |   gks_vs_busavg |
|:--------|------------:|--------------------------:|--------------------------:|--------------------------:|------------:|-------------:|-----------------:|---------------:|----------------:|----------------:|
| overall |       14.13 |                      1.24 |                      0.46 |                    -12.43 |       12.89 |        41.21 |            38.81 |          37.57 |           -1.94 |          -16.07 |
| 2026-06 |        5.22 |                      0.4  |                     -0.1  |                     -4.92 |        4.82 |        25.87 |            25.12 |          24.72 |           -0.84 |           -6.06 |
| 2026-07 |       15.82 |                      0.49 |                      0.91 |                    -14.41 |       15.33 |        42.64 |            40.25 |          39.75 |           -1.48 |          -17.3  |
| 2026-08 |       20.2  |                      2.73 |                      0.48 |                    -16.99 |       17.47 |        53.14 |            49.31 |          46.59 |           -3.34 |          -23.54 |


**DA node−hub basis in each node's own top-2 (discharge) / bottom-2 (charge) hours ($/MWh)**

|             |   basis_discharge_hours_mean |   basis_discharge_pos_share |   basis_charge_hours_mean |   basis_charge_neg_share |   basis_all_hours_mean |
|:------------|-----------------------------:|----------------------------:|--------------------------:|-------------------------:|-----------------------:|
| RVN_RN      |                         0.23 |                       0.433 |                     -0.69 |                    0.685 |                  -1.32 |
| GKS_BESS_RN |                       -10.37 |                       0.096 |                     -1.07 |                    0.562 |                  -2.71 |


**DA hour-ending mean price / basis profile ($/MWh, common days)**

|   HE |   RVN_RN |   GKS_BESS_RN |   HB_HOUSTON |   HB_SOUTH |   HB_BUSAVG |   basis_RVN |   basis_GKS |   hub_diff |   rvn_minus_gks |
|-----:|---------:|--------------:|-------------:|-----------:|------------:|------------:|------------:|-----------:|----------------:|
|    1 |    29.58 |         28.03 |        29.46 |      29.58 |       29.38 |        0.11 |       -1.55 |      -0.11 |            1.55 |
|    2 |    27.02 |         26.02 |        26.88 |      27.04 |       26.82 |        0.14 |       -1.02 |      -0.16 |            1    |
|    3 |    25.86 |         25.15 |        25.74 |      25.96 |       25.7  |        0.12 |       -0.81 |      -0.22 |            0.71 |
|    4 |    25.39 |         24.88 |        25.27 |      25.52 |       25.27 |        0.13 |       -0.63 |      -0.25 |            0.51 |
|    5 |    25.65 |         25.32 |        25.48 |      25.79 |       25.52 |        0.17 |       -0.48 |      -0.32 |            0.33 |
|    6 |    27.14 |         26.89 |        26.96 |      27.28 |       27.01 |        0.18 |       -0.4  |      -0.32 |            0.26 |
|    7 |    27.53 |         27.53 |        27.28 |      27.74 |       27.31 |        0.26 |       -0.22 |      -0.47 |            0.01 |
|    8 |    24.82 |         24.98 |        24.56 |      25.05 |       24.47 |        0.26 |       -0.07 |      -0.49 |           -0.16 |
|    9 |    20.05 |         19.71 |        20.14 |      19.87 |       19.38 |       -0.09 |       -0.16 |       0.26 |            0.34 |
|   10 |    19.83 |         18.15 |        20.67 |      18.61 |       18.33 |       -0.84 |       -0.46 |       2.06 |            1.68 |
|   11 |    21.02 |         18.01 |        22.87 |      18.57 |       18.95 |       -1.84 |       -0.56 |       4.3  |            3.01 |
|   12 |    23.63 |         19.5  |        26.64 |      19.96 |       20.95 |       -3.01 |       -0.46 |       6.68 |            4.13 |
|   13 |    26.75 |         22.31 |        30.87 |      22.57 |       23.77 |       -4.12 |       -0.26 |       8.3  |            4.44 |
|   14 |    29.23 |         25.05 |        34.08 |      25.06 |       26.45 |       -4.86 |       -0.01 |       9.03 |            4.18 |
|   15 |    30.6  |         26.57 |        35.45 |      26.32 |       28.1  |       -4.85 |        0.26 |       9.13 |            4.03 |
|   16 |    32.03 |         27.48 |        36.72 |      27.03 |       29.24 |       -4.69 |        0.46 |       9.7  |            4.55 |
|   17 |    32.88 |         27.45 |        37.59 |      27.66 |       30.79 |       -4.71 |       -0.21 |       9.93 |            5.44 |
|   18 |    32.98 |         27.05 |        36.19 |      28.34 |       31.39 |       -3.21 |       -1.29 |       7.85 |            5.93 |
|   19 |    41.02 |         30.36 |        42.44 |      37.54 |       40.77 |       -1.42 |       -7.18 |       4.91 |           10.66 |
|   20 |    57.57 |         38.28 |        57.54 |      53.83 |       58.21 |        0.03 |      -15.56 |       3.71 |           19.29 |
|   21 |    58.24 |         39.02 |        57.86 |      54.79 |       58.61 |        0.39 |      -15.77 |       3.06 |           19.22 |
|   22 |    52.5  |         40.33 |        52.35 |      50.99 |       52.65 |        0.15 |      -10.66 |       1.36 |           12.17 |
|   23 |    42.83 |         36.65 |        42.79 |      42.23 |       42.79 |        0.04 |       -5.58 |       0.56 |            6.18 |
|   24 |    32.64 |         30.17 |        32.58 |      32.52 |       32.52 |        0.06 |       -2.36 |       0.06 |            2.47 |


**DA tail hours (common-day window)**

|             |   hours |   neg_hours |   neg_sum |   neg_min |   spike500_hours |   spike500_sum |   spike1000_hours |    max |   mean |
|:------------|--------:|------------:|----------:|----------:|-----------------:|---------------:|------------------:|-------:|-------:|
| RVN_RN      |    2136 |           0 |         0 |     13.77 |                0 |              0 |                 0 | 229.25 |  31.95 |
| GKS_BESS_RN |    2136 |           0 |         0 |      4.61 |                0 |              0 |                 0 | 141.39 |  27.29 |
| HB_HOUSTON  |    2136 |           0 |         0 |     13.5  |                0 |              0 |                 0 | 221.34 |  33.27 |
| HB_SOUTH    |    2136 |           0 |         0 |      8.53 |                0 |              0 |                 0 | 201.67 |  29.99 |
| HB_BUSAVG   |    2136 |           0 |         0 |      9.84 |                0 |              0 |                 0 | 227.77 |  31.02 |


**RT TB2 daily stats ($/MWh), 2026-06-03..2026-08-31 (90 common days)**

|               |   n |   mean |   median |   p10 |   p90 |    min |    max |     sum |
|:--------------|----:|-------:|---------:|------:|------:|-------:|-------:|--------:|
| RVN_RN        |  90 |  46.66 |    30.76 | 16.64 | 71.12 |   9.71 | 424.31 | 4198.99 |
| GKS_BESS_RN   |  90 |  37.04 |    25.33 | 16.78 | 45.03 |  11.3  | 373.68 | 3333.36 |
| HB_HOUSTON    |  90 |  46.88 |    31.01 | 17.74 | 68.3  |   9.6  | 426.93 | 4219.24 |
| HB_SOUTH      |  90 |  45.31 |    33.37 | 18.2  | 56.8  |   9.69 | 422.02 | 4078.28 |
| HB_BUSAVG     |  90 |  49.35 |    33.01 | 17.19 | 77.13 |  10.11 | 464.45 | 4441.63 |
| RVN_minus_GKS |  90 |   9.62 |     1.91 | -6.81 | 32.42 | -22.17 | 185.11 |  865.62 |


**RT TB2 monthly mean ($/MWh)**

|         |   RVN_RN |   GKS_BESS_RN |   HB_HOUSTON |   HB_SOUTH |   HB_BUSAVG |
|:--------|---------:|--------------:|-------------:|-----------:|------------:|
| 2026-06 |    32.31 |         29.86 |        33.9  |      32.52 |       33    |
| 2026-07 |    35.72 |         31.67 |        35.36 |      35.91 |       37    |
| 2026-08 |    70.55 |         48.89 |        70.13 |      66.27 |       76.47 |


**RT RVN−GKS daily TB2 delta decomposition ($/MWh): discharge (top-2) vs charge (bottom-2) contribution**

|         |   delta_tb2 |   discharge_contrib |   charge_contrib |   discharge_share | dominant   |
|:--------|------------:|--------------------:|-----------------:|------------------:|:-----------|
| overall |        9.62 |               14    |            -4.38 |             1.455 | discharge  |
| 2026-06 |        2.45 |                6.47 |            -4.02 |           nan     | discharge  |
| 2026-07 |        4.06 |               10.65 |            -6.59 |           nan     | discharge  |
| 2026-08 |       21.66 |               24.14 |            -2.48 |           nan     | discharge  |


**RT hub/basis decomposition of RVN−GKS TB2 gap ($/MWh)**

|         |   delta_tb2 |   hub_houston_minus_south |   rvn_local_basis_contrib |   gks_local_basis_contrib |   net_local |   tb2_busavg |   tb2_hb_houston |   tb2_hb_south |   rvn_vs_busavg |   gks_vs_busavg |
|:--------|------------:|--------------------------:|--------------------------:|--------------------------:|------------:|-------------:|-----------------:|---------------:|----------------:|----------------:|
| overall |        9.62 |                      1.57 |                     -0.22 |                     -8.28 |        8.05 |        49.35 |            46.88 |          45.31 |           -2.7  |          -12.31 |
| 2026-06 |        2.45 |                      1.37 |                     -1.59 |                     -2.66 |        1.08 |        33    |            33.9  |          32.52 |           -0.69 |           -3.14 |
| 2026-07 |        4.06 |                     -0.55 |                      0.36 |                     -4.24 |        4.61 |        37    |            35.36 |          35.91 |           -1.28 |           -5.34 |
| 2026-08 |       21.66 |                      3.86 |                      0.42 |                    -17.38 |       17.8  |        76.47 |            70.13 |          66.27 |           -5.92 |          -27.58 |


**RT node−hub basis in each node's own top-2 (discharge) / bottom-2 (charge) hours ($/MWh)**

|             |   basis_discharge_hours_mean |   basis_discharge_pos_share |   basis_charge_hours_mean |   basis_charge_neg_share |   basis_all_hours_mean |
|:------------|-----------------------------:|----------------------------:|--------------------------:|-------------------------:|-----------------------:|
| RVN_RN      |                         0.34 |                       0.389 |                     -1.3  |                    0.6   |                  -1.1  |
| GKS_BESS_RN |                        -5.58 |                       0.311 |                     -3.25 |                    0.678 |                  -1.83 |


**RT hour-ending mean price / basis profile ($/MWh, common days)**

|   HE |   RVN_RN |   GKS_BESS_RN |   HB_HOUSTON |   HB_SOUTH |   HB_BUSAVG |   basis_RVN |   basis_GKS |   hub_diff |   rvn_minus_gks |
|-----:|---------:|--------------:|-------------:|-----------:|------------:|------------:|------------:|-----------:|----------------:|
|    1 |    30.36 |         29.31 |        30.22 |      30.35 |       30.14 |        0.14 |       -1.03 |      -0.12 |            1.05 |
|    2 |    27.71 |         27.07 |        27.5  |      27.74 |       27.5  |        0.21 |       -0.67 |      -0.24 |            0.63 |
|    3 |    26.56 |         25.88 |        26.36 |      26.66 |       26.38 |        0.21 |       -0.78 |      -0.3  |            0.68 |
|    4 |    25.89 |         25.39 |        25.74 |      25.99 |       25.75 |        0.16 |       -0.6  |      -0.25 |            0.5  |
|    5 |    26.57 |         26.09 |        26.4  |      26.74 |       26.42 |        0.17 |       -0.65 |      -0.34 |            0.48 |
|    6 |    27.83 |         27.91 |        27.66 |      28.13 |       27.66 |        0.17 |       -0.22 |      -0.46 |           -0.08 |
|    7 |    29.02 |         29.08 |        28.69 |      29.31 |       28.83 |        0.33 |       -0.23 |      -0.63 |           -0.06 |
|    8 |    25.6  |         25.8  |        25.12 |      25.92 |       25.52 |        0.48 |       -0.12 |      -0.8  |           -0.21 |
|    9 |    21.37 |         21.05 |        21.48 |      21.14 |       20.57 |       -0.11 |       -0.09 |       0.34 |            0.32 |
|   10 |    21.21 |         19.84 |        21.87 |      19.74 |       19.4  |       -0.66 |        0.1  |       2.12 |            1.36 |
|   11 |    22.11 |         19.14 |        23.96 |      19.31 |       19.49 |       -1.85 |       -0.17 |       4.64 |            2.96 |
|   12 |    23.47 |         19.9  |        26.67 |      19.7  |       20.33 |       -3.2  |        0.21 |       6.97 |            3.57 |
|   13 |    27.25 |         22.53 |        31.23 |      22.07 |       23.13 |       -3.98 |        0.46 |       9.16 |            4.72 |
|   14 |    29.46 |         25.87 |        33.27 |      25.02 |       26    |       -3.81 |        0.85 |       8.25 |            3.59 |
|   15 |    31.27 |         27.03 |        34.84 |      25.9  |       27.92 |       -3.56 |        1.13 |       8.94 |            4.24 |
|   16 |    32.3  |         27.29 |        35.99 |      26.26 |       29.12 |       -3.69 |        1.02 |       9.73 |            5.01 |
|   17 |    32.42 |         26.82 |        36.15 |      25.74 |       29.86 |       -3.73 |        1.08 |      10.41 |            5.6  |
|   18 |    32.37 |         27.28 |        35.63 |      27.1  |       31.56 |       -3.26 |        0.18 |       8.53 |            5.09 |
|   19 |    38.85 |         30.86 |        40.3  |      35.67 |       39.6  |       -1.45 |       -4.82 |       4.63 |            8    |
|   20 |    55.83 |         38.9  |        55.64 |      51.93 |       56.63 |        0.2  |      -13.03 |       3.71 |           16.94 |
|   21 |    59.43 |         40.54 |        58.84 |      54.87 |       59.78 |        0.59 |      -14.33 |       3.97 |           18.88 |
|   22 |    53.39 |         43.72 |        53.28 |      52.06 |       54.11 |        0.11 |       -8.34 |       1.23 |            9.67 |
|   23 |    46.07 |         42.85 |        46    |      45.62 |       46    |        0.07 |       -2.78 |       0.38 |            3.22 |
|   24 |    34.74 |         33.52 |        34.68 |      34.7  |       34.53 |        0.06 |       -1.18 |      -0.02 |            1.22 |


**RT tail hours (common-day window)**

|             |   hours |   neg_hours |   neg_sum |   neg_min |   spike500_hours |   spike500_sum |   spike1000_hours |    max |   mean |
|:------------|--------:|------------:|----------:|----------:|-----------------:|---------------:|------------------:|-------:|-------:|
| RVN_RN      |    2160 |           0 |       0   |      9.74 |                1 |          525.5 |                 0 | 525.5  |  32.55 |
| GKS_BESS_RN |    2160 |           5 |      -5.7 |     -2.3  |                1 |          521   |                 0 | 520.98 |  28.49 |
| HB_HOUSTON  |    2160 |           0 |       0   |      6.53 |                1 |          526.1 |                 0 | 526.09 |  33.65 |
| HB_SOUTH    |    2160 |           0 |       0   |      1.85 |                1 |          525.8 |                 0 | 525.78 |  30.32 |
| HB_BUSAVG   |    2160 |           0 |       0   |      5.31 |                1 |          534.6 |                 0 | 534.63 |  31.51 |


**Cumulative TB2 revenue proxy, $ per 100MW/200MWh, before RTE**

|    |   RVN_RN |   GKS_BESS_RN |   RVN_minus_GKS |   win_rate_RVN_gt_GKS |
|:---|---------:|--------------:|----------------:|----------------------:|
| DA |   699028 |        447545 |          251483 |                 0.91  |
| RT |   839798 |        666673 |          173125 |                 0.633 |


**DA vs RT TB2 by node ($/MWh, days with both)**

|             |   days |   da_mean |   rt_mean |   rt_minus_da_mean |   rt_over_da_ratio |   rt_gt_da_share |   rt_tb2_std |   da_tb2_std |
|:------------|-------:|----------:|----------:|-------------------:|-------------------:|-----------------:|-------------:|-------------:|
| RVN_RN      |     89 |     39.27 |     46.95 |               7.67 |              1.195 |            0.472 |        59.17 |        31.48 |
| GKS_BESS_RN |     89 |     25.14 |     37.24 |              12.1  |              1.481 |            0.674 |        49.56 |        15.5  |
| HB_HOUSTON  |     89 |     38.81 |     47.14 |               8.33 |              1.215 |            0.517 |        58.13 |        30.49 |
| HB_SOUTH    |     89 |     37.57 |     45.58 |               8.01 |              1.213 |            0.539 |        55.42 |        26.72 |
| HB_BUSAVG   |     89 |     41.21 |     49.68 |               8.47 |              1.205 |            0.506 |        62.03 |        32.07 |
