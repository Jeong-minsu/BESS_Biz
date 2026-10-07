# ITEM 2 — RVN_RN proxy selection + 3-year congestion analysis

Real Yes Energy datalake data only. Scripts: `scripts/item2_proxy_scan.py`, `scripts/item2_proxy_alt_nowhartn.py`,
`scripts/item2_scan_msf.py`, `scripts/item2_congestion_analysis.py`, `scripts/item2_sf_by_node.py`.
Derived: `derived/item2_*`.

## Part A — Proxy for RVN_RN (HOUSTON) before 2026-06

**Chosen proxy (`derived/item2_proxy_definition.json`)**

```
proxy_LMP = -0.065 + 0.4148*CBEC_ALL + 0.5407*RBN_BESS1 + 0.0445*TAV_RN     (same weights for DA and RT)
fallback for flowdays < 2023-12-01 (RBN_BESS1 not yet priced):  proxy_LMP = TAV_RN
```

NNLS (weights >= 0, normalised to sum 1) on the three user-nominated nodes, fit on the full overlap
2026-06-04..2026-09-13 after out-of-sample selection. R-squared (stacked DA+RT hourly) = 0.998.
Intercept -$0.07/MWh — immaterial. See the WHARTN caveat at the end of Part A / in Part B.

### Scan of all 1,109 usable price_nodes (overlap window 2026-06-04..09-13, 2,448 hours)

Ranking = mean rank over 7 metrics: Pearson corr on DA and RT levels, corr of hourly first
differences (DA, RT), RMSE of the basis RVN-node (DA, RT), and corr of the DA-RT spread.
`eligible_3yr` = node already priced in 2023-09 (needed for the 3-year job).

| node         | zone    |   corr_da |   corr_rt |   corr_dda |   corr_drt |   rmse_da |   rmse_rt |   corr_spread |   rmse_spread |   composite_rank | eligible_3yr   |
|:-------------|:--------|----------:|----------:|-----------:|-----------:|----------:|----------:|--------------:|--------------:|-----------------:|:---------------|
| WAL_RN       | HOUSTON |     0.998 |     0.998 |      0.995 |      0.998 |     1.172 |     1.513 |         0.996 |         1.797 |            2.429 | False (2025-05) |
| SBE_RN_1     | HOUSTON |     0.999 |     0.995 |      0.997 |      0.992 |     0.883 |     2.592 |         0.992 |         2.439 |            2.429 | True           |
| TAV_RN       | HOUSTON |     0.999 |     0.994 |      0.997 |      0.99  |     0.853 |     2.763 |         0.991 |         2.679 |            3.714 | True           |
| OR_BESS_RN   | HOUSTON |     0.999 |     0.994 |      0.997 |      0.989 |     0.875 |     2.797 |         0.991 |         2.711 |            5     | False (2024-01) |
| WGU_RN       | HOUSTON |     0.994 |     0.994 |      0.989 |      0.99  |     1.902 |     2.796 |         0.989 |         2.935 |            7.571 | True           |
| RN_LNP_SLR   | HOUSTON |     0.994 |     0.994 |      0.988 |      0.989 |     1.922 |     2.857 |         0.989 |         2.965 |            9.143 | False (2025-11) |
| WR_RN        | HOUSTON |     0.997 |     0.991 |      0.996 |      0.99  |     1.469 |     3.416 |         0.988 |         3.111 |           10     | False (2025-05) |
| RBN_BESS1    | HOUSTON |     0.991 |     0.996 |      0.99  |      0.997 |     2.359 |     2.509 |         0.994 |         2.278 |           13.571 | False (2023-12) |
| WES_ALL      | HOUSTON |     0.994 |     0.993 |      0.987 |      0.988 |     2.088 |     3.197 |         0.988 |         3.148 |           15.714 | True           |
| DAG_ALL      | HOUSTON |     0.994 |     0.992 |      0.987 |      0.988 |     2.165 |     3.338 |         0.988 |         3.111 |           16     | True           |
| DMA_RN       | HOUSTON |     0.994 |     0.992 |      0.987 |      0.988 |     2.167 |     3.334 |         0.988 |         3.122 |           16.429 | False (2024-08) |
| DA_BESS      | HOUSTON |     0.993 |     0.993 |      0.987 |      0.989 |     2.148 |     3.042 |         0.989 |         2.938 |           16.5   | False (2023-12) |
| DA_BESS2     | HOUSTON |     0.993 |     0.993 |      0.987 |      0.989 |     2.148 |     3.042 |         0.989 |         2.938 |           16.5   | False (2024-08) |
| NCO_RN       | HOUSTON |     0.993 |     0.992 |      0.986 |      0.987 |     2.198 |     3.396 |         0.987 |         3.258 |           21.429 | True           |
| CBEC_CC2     | SOUTH   |     0.996 |     0.988 |      0.994 |      0.988 |     1.822 |     3.914 |         0.984 |         3.533 |           22.286 | True           |
| CBEC_ALL     | SOUTH   |     0.996 |     0.988 |      0.994 |      0.988 |     1.822 |     3.914 |         0.984 |         3.533 |           22.286 | True           |
| CBEC_CC1     | SOUTH   |     0.996 |     0.988 |      0.994 |      0.988 |     1.822 |     3.914 |         0.984 |         3.533 |           22.286 | True           |
| BTM_ALL      | HOUSTON |     0.994 |     0.992 |      0.986 |      0.986 |     1.975 |     3.247 |         0.985 |         3.395 |           23.857 | True           |
| FTR_FTR_G1_4 | HOUSTON |     0.994 |     0.989 |      0.989 |      0.989 |     2.134 |     3.987 |         0.983 |         3.924 |           23.929 | True           |
| FTR_CC1      | HOUSTON |     0.994 |     0.989 |      0.989 |      0.989 |     2.134 |     3.987 |         0.983 |         3.924 |           23.929 | True           |

Notes on the scan:
- 17 of the top 20 are HOUSTON; the only SOUTH-labelled entries are the three CBEC (Cedar Bayou) buses,
  which are one plant (identical prices). Cedar Bayou is physically in the Houston load pocket (Baytown)
  despite its SOUTH settlement-zone label, which is why it ranks top-20 and is still usable.
- No node is electrically identical to RVN_RN (min basis RMSE 0.85 $/MWh DA, 1.5 RT; nothing below 0.5).
  SBE_RN_1 / TAV_RN / OR_BESS_RN are near-identical to *each other* (pairwise DA RMSE < 1), so they add
  nothing as a blend beyond one of them.
- WAL_RN is the best raw match on every metric but only exists from 2025-05, so it cannot serve the 3-year
  history. It is the recommended proxy if a 16-month history is ever enough (WAL-based blend OOS score 0.90).
- Full table: `derived/item2_proxy_scan_all.csv` (1,109 nodes).

### Regression blends and out-of-sample validation

Fit on 2026-06-04..07-31 (58 days), test on 2026-08-01..09-13 (44 days). Metrics on the test window are
**errors in reconstructed daily TB2** (mean of top-2 hours minus mean of bottom-2 hours, DA and RT separately)
and in the daily-mean DA-RT spread. True OOS daily means: TB2_DA = $47.9/MWh, TB2_RT = $67.1/MWh.

| candidate | nodes / weights | icpt | fit R2 | TB2_DA MAE (bias) | TB2_RT MAE (bias) | daily spread MAE | hourly spread corr / sign-agree | score* |
|---|---|---|---|---|---|---|---|---|
| single best full-history | SBE_RN_1 | 0 | - | 0.79 (-0.78) | 1.24 (-0.82) | 0.41 | 0.997 / 0.981 | 1.42 |
| single TAV_RN | TAV_RN | 0 | - | **0.37** (+0.23) | 1.08 (+0.76) | 0.36 | 0.996 / 0.980 | 1.08 |
| nominated OLS | CBEC 0.41 / RBN 0.55 / TAV 0.04 | -0.00 | 0.9963 | 0.64 (-0.64) | 0.87 (-0.86) | 0.35 | 0.999 / 0.991 | 1.10 |
| **nominated NNLS (chosen)** | CBEC 0.41 / RBN 0.55 / TAV 0.04 | -0.09 | 0.9963 | 0.52 (-0.50) | **0.69** (-0.67) | **0.34** | **0.999 / 0.991** | **0.94** |
| nominated Houston-only OLS | RBN 0.42 / TAV 0.57 | +0.35 | 0.9891 | 0.59 (-0.35) | 1.17 (-0.57) | 0.39 | 0.998 / 0.988 | 1.27 |
| scan OLS (full-history) | SBE 0.66 / WGU 0.81 / DAG -0.45 | -0.40 | 0.9925 | 0.60 (-0.29) | 1.74 (-0.56) | 0.45 | 0.997 / 0.985 | 1.62 |
| scan NNLS (full-history) | SBE 0.53 / WGU 0.47 / DAG 0 | +0.32 | 0.9907 | 1.55 (-1.55) | 2.33 (-2.17) | 0.52 | 0.996 / 0.985 | 2.46 |
| WHARTN-free: RBN+WGU+WES NNLS | RBN 0.47 / WES 0.53 | +0.01 | - | 1.02 (-0.99) | 1.61 (-1.47) | 0.52 | - | 1.84 |
| WHARTN-free: RBN+WAL+WGU NNLS (2025-05+) | WAL 0.75 / WGU 0.25 / RBN 0.01 | +0.02 | - | 0.37 (+0.25) | 0.82 (+0.48) | 0.31 | - | 0.90 |

\*score = mean(TB2_DA MAE, TB2_RT MAE) + daily spread MAE, all in $/MWh (lower is better). **Decision rule =
minimise this score on the OOS window, restricted to blends whose members have (near-)full 3-year history.**
(An unrestricted scan blend WAL_RN+SBE_RN_1+WGU_RN scored 0.57 but is unusable before 2025-05.)

Reading:
- Every candidate reproduces RVN_RN's TB2 to within ~1-2% of its level ($48-67) and its hourly spread with
  corr >= 0.996 — the proxy choice is *not* a large source of error for summer TB2/DART reconstruction.
- The nominated NNLS blend wins mainly on **RT** (TB2_RT MAE 0.69 vs 1.08 for TAV alone) because RBN_BESS1,
  a BESS resource node, tracks Raven's RT spikes best (RT first-difference corr 0.997, highest of any node).
- Its bias is slightly negative (understates TB2 by ~$0.5-0.7/MWh, ~1%); TAV_RN alone is slightly positive.
  Either is acceptable; the JSON carries both so consumers can bracket.
- The intercept is immaterial in every spec (|icpt| < $0.4/MWh).

**Limitations (important):**
1. The overlap is ~100 summer days (Jun-Sep 2026). The proxy is untested in winter/shoulder seasons, when
   Houston import constraints (and hence the RVN vs Cedar Bayou / Brazos Bend basis) behave differently.
   Treat pre-2026 winter reconstructions as +/-$2-3/MWh TB2 uncertainty rather than the +/-$0.7 seen OOS.
2. **WHARTN caveat (found in Part B):** constraint WHARTN has shift factor 0.999 at CBEC_ALL / TAV_RN /
   SBE_RN_1 / DAG_ALL and ~0 at RBN_BESS1 / WGU_RN / WAL_RN / WES_ALL / NCO_RN. It last bound 2026-06-02 —
   before RVN_RN had prices — so whether Raven sits behind it is unobservable, and the summer fit could not
   learn to exclude CBEC/TAV. The chosen blend passes 0.46 x lambda_WHARTN into reconstructed history:
   cumulative -16.4k $/MWh-h per MW over 2023-09..2026-06 (per-year DA/RT: 2023 -549/-2648, 2024 -2290/-4836,
   2025 -1079/-2286, 2026 -619/-2081), Feb-May and Sep-Nov, HE12-17. If Raven is confirmed NOT behind WHARTN,
   reconstructed midday prices are ~$3 (DA) / ~$18 (RT) too low on those binding days and TB2 is overstated on
   those days; strip it with `item2_congestion_hourly_panel.parquet` (CONSTRAINTNAME=='WHARTN', column mcc_h).
   WHARTN-free full-history blends score materially worse OOS (1.84-3.72), so the nominated blend is kept.
   Details: `derived/item2_proxy_definition.json["caveat_wharton"]`, `derived/item2_proxy_alt_nowhartn.json`.
3. RVN_RN only went live 2026-06; its own congestion footprint may still be settling.

---

## Part B — 3-year congestion at the Raven location (2023-09-01 .. 2026-09-13)

### Method (reused from the GKS congestion project)
- Source: `ercot/transmission/constraints/market_shift_factors/{YYYYMMDD}.csv.gz` — SF x lambda pre-joined per
  pricenode, MARKET = DA (hourly) / RT (SCED 5-min). Pulled server-side (S3 Select) for RVN_RN + 10 candidate
  nodes, all 1,109 days, 0 missing files, 0 errors (`scripts/item2_scan_msf.py` -> `raw/msf_nodes/YYYYMM.parquet`).
  This is the cleaner equivalent of joining `constraints/da|rt` with `ercot_sced_shift_factors`; full 3-year
  DA **and** RT coverage was practical (~3 min), so no reduced RT scope was needed.
- Location SF = RVN_RN's own SF where it exists (2026-06+), else the proxy blend applied to SFs
  (MCC is linear in SF, so the price weights carry over exactly; TAV_RN fallback pre-2023-12).
- MCC contribution = -SF x lambda (project sign). **Positive = raises Raven LMP (discharge-favourable);
  negative = lowers it (charge-favourable).** DA row = 1 h, RT row = 1/12 h; RT binding = lambda > 0.
  Units are $/MWh-h per 1 MW of continuous position (= $ per MW-year when summed over a year).
- Aggregated month-by-month into an hourly constraint panel (`derived/item2_congestion_hourly_panel.parquet`)
  — all statistics derive from it. Scripts: `item2_congestion_analysis.py`, `item2_sf_by_node.py`.

### Proxy SF check (does the price proxy also reproduce Raven's congestion?)
Over the 2026-06..09 overlap, on the 30 constraints with the largest |MCC| at RVN_RN: corr(SF_RVN, SF_proxy) =
0.94, sign agreement 100%, sum|MCC| 16,486 (RVN) vs 16,503 (proxy). Per-constraint SFs agree within ~10-25%
except **FB_RS_60_A** (RS-FB 138 kV: RVN 0.27 vs proxy 0.17 — a Raven-local element the blend under-weights) and
**STPWAP39_1** (RVN -0.023 vs proxy -0.031: RBN_BESS1 sits at -0.06, CBEC at 0). Good enough for the ranking;
read individual pre-2026 SFs as +/-25%. Files: `item2_congestion_proxy_sf_check.csv`, `item2_congestion_sf_by_node.csv`.

### Aggregate congestion at the location
Net MCC by year (DA / RT): 2023 (4 mo) +8.0k / -4.3k; 2024 +13.7k / -23.2k; 2025 +17.0k / -25.0k;
2026 (8.5 mo) +7.0k / -8.7k. Gross |MCC|: DA 15k -> 48k -> 59k -> 56k; RT 21k -> 47k -> 54k -> 35k.
**Structural read: DA congestion at this location is net positive (raises DA LMP), RT congestion net negative
(lowers RT LMP)** — a persistent DA > RT congestion basis, i.e. short-DA / long-RT-favourable (spread = DA - RT > 0).
RVN_RN's own first 100 days confirm it: DA +3.0k, RT -1.0k.

### Top-10 constraints by |cumulative MCC contribution| (DA + RT, 3 years)

| # | constraint | element (zone) | dominant ctg | sign at Raven | SF (DA/RT) | cum DA | cum RT | total | forward relevance |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **WHARTN** | station constraint (HOUSTON), base case | BASE CASE | neg (charge) | +0.48 / +0.47 (proxy) | -4,537 | -11,852 | **-16,388** | **PROXY ARTIFACT / UNVERIFIABLE** |
| 2 | **BLESSI_PAVLOV1_1** | BLESSING-PAVLOV 138 kV (SOUTH) | SSTPESP8 | pos (discharge) | -0.064 / -0.067 | +8,068 | +7,417 | **+15,485** | FADED — 74% in Oct 2023-Feb 2024 |
| 3 | **E_PASP** | PAWNEE-CALAVERAS 345 interface (SOUTH) | BASE CASE | neg | +0.032 / +0.009 | -9,239 | -1,255 | **-10,494** | LIVE, growing (53% in last 12 mo) |
| 4 | **1710__C** | BELCNTY-SALSW 138 kV (NORTH) | DSALHUT5 | pos | -0.015 / -0.002 | +8,627 | +1,075 | **+9,703** | **RETIRED** — no binding since 2025-10-28 |
| 5 | **HARGRO_TWINBU1_1** | TWINBU-HARGROVE 138 kV (WEST) | DBAKCED5 | neg | +0.000 / +0.004 | -658 | -8,104 | **-8,762** | LIVE, chronic small drag |
| 6 | **STPELM27_1** | STP-ELMCREEK 345 kV (HOUSTON) | DELMSTP5 | neg | +0.060 / +0.046 | -3,024 | -4,822 | **-7,845** | EPISODIC — Dec/Jan; top-3 days = 51% |
| 7 | **630__B** | KLNSW-HHSTH 138 kV (NORTH) | DSALKLN5 | pos | -0.031 / -0.015 | +3,900 | +2,169 | **+6,069** | LIVE, stable (Mar-Apr) |
| 8 | **STPWAP39_1** | STP-W.A.PARISH 345 kV (HOUSTON) | DWPWFWP5 | pos | -0.028 / -0.029 | +3,166 | +2,809 | **+5,975** | LIVE, growing; 36% real RVN data |
| 9 | **587__A** | ARGYL-LWSVH 138 kV (NORTH) | MRNKDHM5 | pos | -0.008 / -0.004 | +3,836 | +1,991 | **+5,827** | LIVE, 2025 onset, growing |
| 10 | **50__A** | JEWET-BBSES 345 kV (NORTH) | DNAVOUT5 | neg | +0.119 / +0.049 | -2,137 | -3,655 | **-5,792** | EPISODIC — Jan 2025 / Jan 2026; top-3 days = 57% |

Next in rank: WESTEX (+4,953, RT-only, DA/RT SF sign conflict as at GKS), **35055__A (-4,835, the #1 constraint
at the real RVN_RN in 2026)**, ARROZ_EL_CAM1_1 (-4,553), 421__A (+4,178), FORTMA_YELWJC1_1 (-4,064).
Full list: `derived/item2_congestion_ranking_all.csv`. Per-constraint detail (per-year DA/RT totals and
means, 12x2 month matrix, 24x2 hourly P(bind) and mean lambda, DA-vs-RT stats, forward diagnostics):
`derived/item2_congestion_top10_profiles.json`.

### Per-constraint findings

**1. WHARTN (-16.4k, 72% RT) — treat as a proxy artifact until Raven's SF is observed.**
SF is 0.999 at CBEC_ALL / TAV_RN / SBE_RN_1 / DAG_ALL and -0.001 at RBN_BESS1 / WGU_RN / WAL_RN / WES_ALL / NCO_RN:
a station-level base-case constraint that those four plants sit directly behind (T.H. Wharton / Cedar Bayou
side), not a regional Houston constraint. Seasonality: Feb-May (Apr peak, -4.7k) and Sep-Nov; hourly: solar
hours HE12-17 (P(bind) DA 11%, RT 6% at HE13-15); lambda small in DA ($7 mean) but RT-heavy ($39 mean, p90 $70,
max $5,251). DA/RT sign agreement 100%. Limit raised 470 -> 536 -> 691 MW and no binding since 2026-06-02, so
forward relevance is low either way. Handling instructions are in Part A limitation 2.

**2. BLESSI_PAVLOV1_1 (+15.5k, pos).** Blessing-Pavlov 138 kV (Matagorda/Wharton County, STP export path);
Raven relieves it (SF -0.06; RVN's own -0.057 confirms). 74% of the 3-year total came in Oct 2023 (+10k) and
Jan-Feb 2024; 2025 +0.4k, 2026 +0.2k. Binds mostly in DA (11.5% of hours, lambda $37) with rare RT spikes (0.7%,
lambda $570, capped $3,500 in Oct 2023). Evening HE19-22. DA/RT sign agreement 99%; DART lean short (DA richer,
92% of active hours). Still binds (last 2026-09-13) but at trivial lambda — **do not extrapolate the 2023 level**.

**3. E_PASP (-10.5k, neg, DA-dominant 7:1).** Pawnee-Calaveras 345 interface (South -> San Antonio import).
Raven aggravates it (SF +0.02-0.03; RVN own 0.019 vs proxy 0.029 — proxy overstates ~50%). Binds 21% of
DA hours (lambda $49), evening HE18-22 (P(bind) 49% at HE21); RT 3% (lambda $133). Jul-Aug + Jan; the
2026-01-24..26 episode is 28% of the total. Growing: 2024 -1.3k, 2025 -4.7k, 2026 YTD -4.5k. DA/RT sign
agreement 84% (lowest of the ten); net DART lean **long** (chronic DA-only binding depresses DA more than RT;
cumulative spread -8.0k). LIVE and forward-relevant, but scale at Raven is ~2/3 of the proxy figure.

**4. 1710__C (+9.7k, pos).** Belton-Salado 138 kV (Central TX), post-contingency. Summer afternoons HE15-19
(P(bind) DA 26%, lambda $213-380; RT 12%, lambda ~$1,000). **No binding since 2025-10-28 (same retirement seen
at GKS)** — exclude from 2027.

**5. HARGRO_TWINBU1_1 (-8.8k, 92% RT).** Twin Buttes-Hargrove 138 kV, West Texas. Tiny SF (0.001-0.002) but the
most frequently binding constraint in ERCOT DA (47% of all hours, lambda $134) and RT lambda mean $1,153 (capped
$3,500). Overnight HE1-6, winter + late summer. Every year -1k to -4k; 2026 YTD -0.8k. DA/RT sign agreement 93%;
DART lean short by $ but 65% of active hours long — spiky. LIVE, chronic, small: a steady RT-side drag of
roughly $1-3k/MW-yr.

**6. STPELM27_1 (-7.8k, neg, RT-heavier).** STP-Elm Creek 345 kV under the Elm Creek-STP contingency; Raven
aggravates (SF +0.05-0.06, consistent across all Houston nodes). Binds only Dec-Jan (2025-02 onset), overnight
and HE19-21; RT lambda mean $805, max $4,500. Top-3 days (2026-01-25, 2025-12-01/02) = 51% of total. DA/RT sign
agreement 100%. Forward: **episodic winter tail risk**, not a base-load driver — model as a Dec-Jan event.

**7. 630__B (+6.1k, pos).** Klein SW-HHSTH 138 kV (NORTH), Mar-Apr overnight (HE1-5), P(bind) DA 6%, lambda $104;
RT 3%, lambda $223. Stable +1.2-1.5k/yr since 2024; RVN's own SF (-0.016) matches the proxy. LIVE spring-shoulder
discharge tailwind (overnight, so it mainly lifts the charge-hour floor rather than the discharge peak).

**8. STPWAP39_1 (+6.0k, pos).** STP-W.A. Parish 345 kV (Houston import), post-contingency — the constraint
analysed in the 2026-06 Houston work. Raven relieves it (own SF -0.023). Summer afternoons May-Aug HE15-18
(P(bind) DA 24%, lambda $57; RT 13%, lambda $106, cap $4,500 in Aug). 2025 +3.3k, 2026 YTD +2.2k; #2 at the real
node in its first 100 days (+2.0k). DA/RT sign agreement 100%; DART near-balanced (55% short hours). **LIVE and
the most forward-relevant positive for Raven: a summer-peak discharge tailwind.**

**9. 587__A (+5.8k, pos).** Argyle-Lewisville 138 kV (North, DFW). 2025 onset, winter overnight HE1-5
(Nov-Apr), P(bind) DA 12%, lambda $141; RT 4%, lambda $406. +1.8k (2025), +2.8k (2026 YTD). SF small (-0.008) and
identical across all Houston nodes — a system-wide North congestion echo, not Raven-specific. LIVE.

**10. 50__A (-5.8k, neg).** Jewett-Big Brown SES 345 kV (NORTH) under a Navarro outage contingency. Two January
episodes (2025-01-15, 2026-01-24..26) = 57% of the total; nothing outside Jan-Feb. SF +0.09-0.12, uniform across
Houston nodes (Houston imports from the north). Winter-storm tail event; do not annualise.

### Cross-cutting patterns
- **Seasonality**: charge-favourable (negative) congestion clusters in **winter (Dec-Feb: E_PASP, STPELM27,
  50__A, HARGRO)** and in the **spring/fall solar shoulders at midday (WHARTN, if real)**. Discharge-favourable
  (positive) clusters in **summer afternoons/evenings (STPWAP HE15-18; 1710__C retired)** and in **spring/winter
  overnight (630__B, 587__A)**.
- **Hourly**: positive congestion at the location is an afternoon/evening (HE15-22) phenomenon; negative
  congestion is overnight (HE1-6: HARGRO, STPELM27, 50__A) and midday (WHARTN). This lines up with a 2-hour BESS
  cycle (charge overnight/midday, discharge HE16-21).
- **DA vs RT**: DA binds far more often at low lambda (DA freq 2-47% of hours), RT rarely but at 3-20x the lambda
  (caps $3,500 / $4,500). 8 of 10 have DA/RT sign agreement >= 93% (E_PASP 84% lowest) — the congestion
  *direction* is reliable between markets, which is favourable for DART. Net DART lean from congestion is
  **short** (DA richer) for 9 of 10 by cumulative $; E_PASP is the exception (long).
- **Forward relevance summary**: LIVE and extrapolable — STPWAP39_1, E_PASP (at ~2/3 proxy scale), 630__B,
  587__A, HARGRO_TWINBU1_1; plus 35055__A from the real-node table below. EPISODIC (winter tail, model as
  events) — STPELM27_1, 50__A. FADED — BLESSI_PAVLOV1_1. RETIRED — 1710__C. UNVERIFIABLE / likely proxy
  artifact — WHARTN.

### What actually bound at RVN_RN in its first 100 days (2026-06-04 .. 09-13, real data)
| constraint | element (zone) | SF_RVN | hours | DA | RT | total |
|---|---|---|---|---|---|---|
| 35055__A | SAMSW-VENSW 345 kV (NORTH) | +0.098 | 717 | -2,325 | -811 | **-3,136** |
| STPWAP39_1 | STP-WAP 345 kV (HOUSTON) | -0.023 | 1,311 | +837 | +1,154 | **+1,991** |
| 1710__A | SALDS-SONTERRA 138 kV (NORTH) | -0.012 | 580 | +1,012 | +84 | +1,095 |
| TREADW_YELWJC1_1 | TREADWELL-YELLOWJACKET 138 kV (WEST) | -0.012 | 1,519 | +573 | +264 | +838 |
| SEA_AAT1 | SEA 138 kV autotransformer (NORTH) | -0.002 | 806 | +797 | -11 | +786 |
| E_PASP | PAWNEE-CALAVERAS (SOUTH) | +0.026 | 896 | -735 | -44 | -778 |
| FB_RS_60_A | RS-FB 138 kV (Raven-local) | +0.348 | 305 | -450 | -296 | -746 |
| 1715__B | TMPSW-FRYSW 138 kV (NORTH) | -0.009 | 364 | +450 | +254 | +705 |
| 107__B | HCKSW-EXCSW 345 kV (NORTH) | -0.061 | 325 | +682 | -45 | +637 |
| 378T387_1 | HWRDTP-WELLBR 138 kV (SOUTH) | +0.009 | 209 | -202 | -324 | -526 |
| THWZEN98_A | ZENITH-T.H.WHARTON 345 kV (HOUSTON) | -0.062 | 415 | +299 | +222 | +521 |
| 6200__F | TYPRK-PLYAM 138 kV | -0.016 | 679 | +512 | -11 | +501 |

Net at RVN over the 100 days: DA +3.0k, RT -1.0k. **35055__A** (Sam Switch-Venus 345, North) is new in 2026 and
is the largest negative at the real node — a Houston-import constraint that the 3-year ranking puts at #12 only
because it barely existed before 2026; it belongs on the 2027 watch-list alongside STPWAP39_1. **FB_RS_60_A**
is the one constraint where the location is genuinely local (SF 0.35 at RVN; TAV 0.73, CBEC 0.44, RBN -0.09) —
the proxy under-weights it; small so far (-0.7k). File: `derived/item2_congestion_rvn_overlap_top12.csv`.

### Caveats
- Pre-2026-06 location SFs are proxy-blend SFs; the overlap check shows +/-10-25% per-constraint error and one
  artifact class (WHARTN). Cumulative $ figures pre-2026 inherit that.
- Contingency -> element membership is not in the datalake (names only); "dominant ctg" = most frequent
  CONTINGENCYID label.
- RT lambda at $3,500 (138 kV) / $4,500 (345 kV) is real scarcity pricing, not an error; E_PASP RT max $15,341
  is a multi-row hour sum.
- 2023-09..11 uses the TAV_RN fallback; 2023 is a partial year (4 months) in per-year tables.
