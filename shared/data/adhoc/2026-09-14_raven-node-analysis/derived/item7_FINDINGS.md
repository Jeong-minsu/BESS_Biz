# ITEM 7 — Top-10 congestion drivers / shift factors / binding hours (PART A) and the GKS <-> Raven basis trade (PART B)

Real Yes Energy datalake data only (no mock). Scripts: `scripts/item7_fetch_gks_msf.py`, `item7_fetch_drivers.py`,
`item7_fetch_outages.py`, `item7_basis_panel.py`, `item7_drivers.py`, `item7_basis_trade.py`, `item7_crr.py`.
Derived: `derived/item7_*` (JSON/CSV/parquet), logs `derived/item7_*_log.txt`.

Method reused from the GKS congestion-impact and Houston constraint projects (2026-06-09): `market_shift_factors`
SF x lambda pre-join, `MCC = -SF x lambda`, RT binding = lambda > 0, binding-vs-non-binding driver comparison with the
`thresholds.py` breakpoint rule, and the seasonality-adjusted outage co-occurrence lift. Driver ranking = AUC of each
candidate for the DA binding flag inside the constraint's binding season and peak-hour band (de-confounds the diurnal
and seasonal cycle). New data pulled: GKS_BESS_RN SF 2024-07-03..2026-09-13 (`raw/msf_gks/`), a 3-year hourly driver panel
(7 wind regions, 7 solar regions, 9 weather-zone loads, 8 station temperatures; `raw/item7_driver_panel.parquet`) and daily
HE23 outage snapshots >= 138 kV (`raw/item7_outages_daily.parquet`).

Conventions: spread = DA - RT (positive => short DA). Basis = RVN - GKS. HE = hour-ending, CT.

---

## PART A — Top-10 constraints at the Raven location: driver, shift factors, binding hours

Population for drivers = all hours of the constraint's binding months across the years it was active, restricted to its
peak DA binding band (HE list below); "threshold" = first driver decile where P(bind) >= max(2 x base, 20%) (or base + 20 pp
when base already > 25%), with P(bind) in the bottom -> top decile in brackets. SF columns: RVN real = RVN_RN's own SF on
hours it bound since 2026-06-04; proxy = item2 blend (0.41 CBEC + 0.54 RBN + 0.04 TAV); GKS = GKS_BESS_RN's own SF.
Band statistics: P(bind) averaged over the band hours, mean lambda over binding hours in the band. "W" = watch-list extra
(35055__A, the #1 negative at the real node in 2026). Full numbers: `item7_congestion_drivers.json`; table also in
`item7_congestion_drivers.md`.

| # | constraint | element (zone) | main driver(s) [AUC] | threshold (P(bind) bottom->top decile) | SF RVN real DA/RT | SF proxy DA/RT | SF GKS DA/RT | RVN vs GKS | DA band: P(bind), mean λ | RT band: P(bind), mean λ | forward |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **WHARTN** | station constraint, base case (HOUSTON) | solar_ercot ↑ [0.59]; wind_coastal ↓ [0.42] — weak | none (5%->20%) | n/a (never bound while RVN priced) | +0.480 / +0.466 | 0 / −0.001 | one-sided (proxy only) | HE12-17: 11%, $8 | HE11-16: 5.6%, $28 | UNVERIFIABLE / proxy artifact; no binding since 2026-06-02 |
| 2 | **BLESSI_PAVLOV1_1** | BLESSING-PAVLOV 138 kV (SOUTH) | wind_coastal ↑ [0.68]; south_net_export ↑ [0.68] (physical); AUC leaders are epoch proxies (see note) | coastal wind top decile 2 GW+ ; 52%->2% on FarWest-load trend proxy | −0.054 / −0.062 | −0.065 / −0.068 | +0.006 / +0.007 | OPPOSING (GKS negligible) | HE9-21: 14%, $56 | HE16-22: 1.0%, $810 | FADED |
| 3 | **E_PASP** | PAWNEE-CALAVERAS 345 interface (SOUTH) | load_ercot ↑ [0.78]; load_southcentral ↑ [0.78] | ERCOT load > 74.2 GW (13%->91%); SC load > 13.4 GW (16%->91%, strong λ) | +0.030 / +0.009 | +0.033 / +0.009 | +0.241 / +0.220 | same sign, GKS 7.9x | HE18-22: 45%, $58 | HE17-20: 9.3%, $160 | LIVE, growing |
| 4 | **1710__C** | BELCNTY-SALSW 138 kV (NORTH) | load_southern ↑ [0.73]; solar_southeast ↑ [0.72] | Southern load > 6.2 GW (11%->81%); SE solar > 2.5 GW (18%->87%) | n/a | −0.015 / −0.002 | −0.025 / −0.013 | same sign, GKS 1.6x | HE14-19: 24%, $285 | HE15-18: 10.6%, $906 | RETIRED (last 2025-10-28) |
| 5 | **HARGRO_TWINBU1_1** | TWINBU-HARGROVE 138 kV (WEST) | wind_west_panhandle ↓ [0.37]; wind_west ↓ [0.37] — near-permanent | none (85%->59%: binds less at high West wind) | 0.000 / +0.004 | 0.000 / +0.004 | −0.001 / +0.003 | negligible at both | all hours: 61%, $182 | HE1-6: 12.8%, $1,236 | LIVE, chronic small RT drag |
| 6 | **STPELM27_1** | STP-ELMCREEK 345 kV (HOUSTON) | wind_ercot ↓ [0.30]; wind_west ↓ [0.32] | ERCOT wind < 8.1 GW (39%->11%, strong λ < 5.9 GW); West wind < 1.5 GW (50%->16%) | n/a | +0.060 / +0.045 | −0.070 / −0.043 | OPPOSING | flat (top HE1-6): 3%, $102 | HE7-21: 0.6%, $872 | EPISODIC Dec-Jan |
| 7 | **630__B** | KLNSW-HHSTH 138 kV (NORTH) | wind_ercot ↑ [0.73]; wind_west ↑ [0.73] | West wind > 14.2 GW (0%->17-26%) | −0.027 / −0.012 | −0.031 / −0.015 | −0.028 / −0.013 | same sign, 1.0x | flat overnight: 6%, $97 | 2.9%, $228 | LIVE, spring shoulder |
| 8 | **STPWAP39_1** | STP-W.A.PARISH 345 kV (HOUSTON) | solar_southeast ↑ [0.79]; solar_ercot ↑ [0.78]; wind_coastal ↑ [0.76]; load_coast ↑ [0.75] | SE solar > 2.4 GW (12%->77%); ERCOT solar > 23.9 GW (11%->80%) | −0.021 / −0.027 | −0.031 / −0.031 | +0.094 / +0.093 | **OPPOSING** (confirmed) | HE14-19: 23%, $50 | HE13-18: 11.9%, $101 | LIVE, growing |
| 9 | **587__A** | ARGYL-LWSVH 138 kV (NORTH) | wind_ercot ↑ [0.85]; wind_west ↑ [0.84] | ERCOT wind > 23.0 GW (0%->58%); West wind > 14.7 GW (0%->57%) | −0.009 / −0.003 | −0.008 / −0.004 | −0.005 / −0.001 | same sign, 0.6x | flat overnight: 14%, $171 | 5.1%, $412 | LIVE, 2025 onset |
| 10 | **50__A** | JEWET-BBSES 345 kV (NORTH) | net_load_ercot ↑ [0.78]; temp_dfw ↓ [0.23]; wind_west_panhandle ↓ [0.27] | net load > 44.8 GW (0%->31%; strong λ > 50.3 GW); DFW < 33 F (31%->3%) | n/a | +0.119 / +0.049 | +0.157 / +0.052 | same sign, 1.3x | HE4-10: 2%, $34 | HE7-22: 0.4%, $1,037 | EPISODIC Jan storms |
| W | **35055__A** | SAMSW-VENSW 345 kV (NORTH) | solar_ercot ↑ [0.85]; solar_southeast ↑ [0.83] | ERCOT solar > 25.0 GW (0%->79%); SE solar > 2.8 GW (1%->65%) | +0.128 / +0.036 | +0.095 / +0.025 | +0.105 / +0.035 | same sign, 0.8x | HE13-18: 14%, $27 | HE12-17: 5.6%, $94 | LIVE, 2026 onset |

### Per-constraint notes

1. **WHARTN** — No driver separates binding from non-binding hours (best AUC 0.59, ERCOT solar). Midday HE12-17, Feb-May/Sep-Nov.
   The outage lens is the only strong signal: Houston 138 kV lines FT-UW / UW-QAB out on 16 days -> P(bind-day) 88%, lift 4.7x; it is
   an outage-conditioned station constraint. RVN never bound to it, GKS SF is 0. Treat as unverifiable / not forward-relevant.
2. **BLESSI_PAVLOV1_1** — The AUC leaders (low FarWest load, low North load) are epoch proxies: those loads grew monotonically
   and "low" simply selects 2023-Q4/2024-Q1 when 74% of the binding happened — which is the FADED verdict restated. The physical
   drivers that survive are coastal wind (AUC 0.68, binding-hour mean 1.98 GW vs 1.34 GW) and the South net-export proxy — an STP
   export-path line loaded by coastal wind. RVN real SF −0.054 confirms the proxy (−0.065). GKS SF +0.006, i.e. opposing in sign but
   negligible. Evening HE16-22 in RT; DA binding spread across HE9-21.
3. **E_PASP** — Load-driven San Antonio import: P(bind) 13% -> 91% from bottom to top ERCOT-load decile in HE18-22; breakpoint
   ~74 GW ERCOT / 13.4 GW South-Central. Consistent with the GKS finding (South load + South wind). Same sign at both nodes but
   GKS SF is 7.9x Raven's (+0.24 vs +0.03) — this is a GKS constraint that Raven barely feels. RVN real SF (+0.030) agrees with the
   proxy (+0.033) on the same hours (item2's 0.019 was a different averaging; both say ~+0.02-0.03).
4. **1710__C** — Summer-afternoon HE14-19, Southern load > 6.2 GW and SE solar > 2.5 GW push P(bind) above 80%. Retired since
   2025-10-28 at both nodes; exclude from 2027.
5. **HARGRO_TWINBU1_1** — Binds 61% of all season hours in DA; it is closer to a standing base case than a driver-conditioned
   constraint. Only weak conditioning: less likely at high West/Panhandle wind (85% -> 59%). RT binding overnight HE1-6 with mean
   lambda $1,236 (cap $3,500). SF ~0 at both nodes (0.000-0.004); the RT drag comes from lambda size, not SF.
6. **STPELM27_1** — Winter only. Binds when ERCOT wind is LOW (< 8 GW -> 52%; strong lambda below 5.9 GW) and West wind < 1.5 GW,
   i.e. Houston is importing from STP on a low-wind, high-thermal-dispatch night. Outage lens: BCK 345 kV transformers and
   CCK-BCK 345 out on all 19 co-binding days (lift 1.9). OPPOSING signs (RVN +0.060 proxy, GKS −0.070) — Raven aggravates, GKS
   relieves. RVN has not observed it (no binding since 2026-01-27); the proxy SF is consistent across all Houston nodes.
7. **630__B** — Spring overnight, West-wind driven (> 14.2 GW -> 32%; 0% in the bottom decile). Same SF at both nodes (−0.028).
   North 138 kV outages (EMPOD-EMORY, KLRPR lines) lift P(bind-day) 2.7-2.8x.
8. **STPWAP39_1** — Confirms the 2026-06 Houston work: source-driven summer import. Solar (SE > 2.4 GW -> 75%; ERCOT > 23.9 GW ->
   77%), coastal wind (AUC 0.76; 2.29 GW binding vs 1.38 GW) and Coast load (AUC 0.75) all load the STP->Parish corridor in HE14-19.
   Outage lens: JAR 345 KT1 transformer / GA-LM 138 out -> 96-98% bind-days (lift 1.55-1.58). **SF signs are opposite: RVN real
   −0.021 (relieves), GKS +0.094 (aggravates)** — GKS's magnitude is 4.5x Raven's. Proxy overstates Raven's SF by ~50% (−0.031).
9. **587__A** — Winter overnight, strongly wind-driven: 0% P(bind) below 6 GW ERCOT wind, 58% above 23 GW. SF tiny and identical
   across Houston/South nodes (−0.005..−0.009): a system-wide North echo.
10. **50__A** — Winter-storm constraint: net load > 44.8 GW and DFW < 33 F (both deciles ~25-31%), strong lambda above 50 GW net
    load; West/Panhandle wind low when binding. Same sign at both nodes (RVN +0.119 proxy, GKS +0.157). Not observed by RVN yet.
- **35055__A (watch-list)** — Midday HE13-18, ERCOT solar > 25 GW -> 46-79%; the strongest solar-driven constraint in the set and
  the #1 negative at the real node in 2026. RVN real SF +0.128 vs proxy +0.095 (proxy understates by 25%); GKS +0.105 — same sign.

RVN real-vs-proxy SF summary (hours both observed, 2026-06-04..09-13): STPWAP −0.021 vs −0.031 (proxy 50% too big),
35055__A +0.128 vs +0.095 (proxy 25% too small), BLESSI −0.054 vs −0.065, 630__B −0.027 vs −0.031, E_PASP +0.030 vs +0.033,
587__A −0.009 vs −0.008, HARGRO 0 vs 0. WHARTN, 1710__C, STPELM27_1 and 50__A have not bound since RVN was priced — their Raven
SF remains proxy-only.

Caveats: outage "lift" is co-occurrence within season, not contingency membership (membership is not in the datalake); when all
out-days of an element bind the lift equals 1/base and several elements tie — read them as a watch-list, as in the GKS project.
Driver AUCs are for DA binding; RT binding is a subset with the same drivers at higher lambda.

---

## PART B — GKS <-> Raven basis trade

Window: GKS has prices/SF from 2024-07 (COD), so the "3-year" basis is the GKS history **2024-07-04..2026-09-13 (800 flowdays,
19,246 hours)**, with RVN real from 2026-06-04 (2,448 h) and the item2 proxy before. Overlap = 2026-06-04..09-13.

### B1. Which constraints have opposing SF signs at the two nodes, and do they move the basis?

Of 1,575 constraints that bound at either node in the window, **64 have opposing DA-SF signs** (|SF| >= 0.005 at both nodes).
Ranked by gross basis impact Σ|MCC_RVN − MCC_GKS| ($/MWh-h per MW), which is |ΔSF| x λ summed over binding hours:

| rank (all) | constraint | SF RVN DA | SF GKS DA | ΔSF | cum basis DA / RT | gross basis | last 12 m | last bind | status |
|---|---|---|---|---|---|---|---|---|---|
| 4 | **STPWAP39_1** | −0.021 (real) | +0.094 | −0.115 | +10,872 / +11,246 | **22,118** | 11,049 | 2026-09-13 | LIVE |
| 7 | **STPELM27_1** | +0.060 (proxy) | −0.070 | +0.130 | −5,774 / −9,279 | **15,109** | 14,958 | 2026-01-27 | EPISODIC (winter) |
| 45 | COLETO_VICTOR2_1 | −0.021 | +0.046 | | +1,091 / +1,555 | 2,646 | 1,013 | 2026-07-15 | live, small |
| 48 | BR_HOC09_A | −0.028 | +0.008 | | +871 / +1,556 | 2,428 | 2,330 | 2026-09-13 | live, small |
| 52 | JN_WAP64_A | −0.016 | +0.052 | | +1,072 / +1,002 | 2,074 | 0 | 2025-06-18 | dormant |
| 60 | BI_WAP50_A | −0.010 | +0.040 | | +675 / +789 | 1,464 | 174 | 2026-09-11 | live, tiny |
| — | 262_A_1, BI_SMR98_A, DOWOAS18_A, WAPWLY72_A, NCARBI_SEADRF1_1, BLESSI_PAVLOV1_1, CKT_3136_1, JCKSTP18_A, BI_JN_64_A | | | | | 860-1,360 each | | | mostly Houston-corridor N-1, tiny |

**STP-WAP is confirmed**: RVN relieves it (real SF −0.021), GKS aggravates it (+0.094); every binding hour widens the Houston-over-South
basis (+$22.1k/MW gross over 26 months, ~$10k/MW-yr, split evenly DA/RT). STPELM27_1 is the mirror image (Raven aggravates, GKS relieves)
but is a Dec-Jan event constraint. Everything else opposing is < $2.7k/MW.

But the opposing set is a **small part of the basis: 11% of gross basis**. The basis is dominated by constraints with a large SF at
GKS and ~0 at Raven — same-sign or one-sided, not opposing:

| constraint | SF RVN DA | SF GKS DA | gross basis | share |
|---|---|---|---|---|
| E_PASP | +0.030 | +0.241 | 75,296 | 22% |
| LARDVN_LASCRU1_1 | +0.004 | +0.082 | 48,907 | 14% (retired 2026-05) |
| HAINE__LA_PAL1_1 | 0.000 | −0.027 | 23,500 | 7% |
| STPWAP39_1 (opposing) | −0.021 | +0.094 | 22,118 | 6% |
| BRUNI_69_1 | 0.000 | +0.012 | 20,196 | 6% |
| VALEXP | — | +1.000 | 18,260 | 5% |
| STPELM27_1 (opposing) | +0.060 | −0.070 | 15,109 | 4% |
| LOYOLA_69_1, CATARI_PILONC1_1, LASCRU_MILO1_1, 1710__C, NLARSW_PILONC1_1, WHARTN | | | 10-14k each | |

Variance explained (hourly basis from prices regressed on Σ constraint MCC differences):

| | DA basis, full | DA basis, overlap (real RVN) | RT basis, full | RT basis, overlap |
|---|---|---|---|---|
| all constraints | R² 0.999 (β 1.00) | 0.99999 | 0.30 (β 0.44) | 0.49 (β 0.69) |
| **opposing constraints only** | **0.014** | **0.036** | **0.010** | **0.041** |
| item2 top-10 | 0.81 | 0.59 | 0.04 | 0.06 |

The constraint decomposition reproduces the DA basis essentially exactly (R² 0.999, β 1.00 — a clean check that the SF x λ
machinery and the price panel agree). The opposing-sign constraints explain **1-4% of basis variance**. The basis is a GKS-side
South-Texas congestion story (E_PASP, Laredo-Las Cruces, Haine, Bruni, VALEXP) in which Raven is simply the Houston hub.
RT basis is only 30-49% explained by hourly-aggregated constraints because RT MCC is 5-min and price spikes carry
non-congestion components (the 1-h aggregation and the RT-cap intervals lose the rest).

### B2. The RVN − GKS basis

| $/MWh | DA basis (full) | RT basis (full) | DA basis (overlap) | RT basis (overlap) | hub HOU−SOUTH DA / RT (full) |
|---|---|---|---|---|---|
| mean | **+5.39** | **+4.40** | +4.14 | +3.70 | +1.19 / +0.86 |
| median | +0.37 | −0.06 | +0.77 | 0.00 | +0.11 / +0.02 |
| std | 24.3 | 29.5 | 10.1 | 14.8 | 7.0 / 15.0 |
| p5 / p95 | −7.3 / +28.3 | −10.6 / +32.6 | −3.8 / +18.6 | −6.2 / +21.6 | |
| min / max | −77 / +1,125 | −1,087 / +1,542 | −30 / +134 | −55 / +254 | |
| share > 0 | 54% | 45% | 59% | 50% | |

By year (DA / RT mean): 2024 (H2) +0.5 / +0.5; 2025 +7.2 / +6.4; 2026 +6.2 / +4.3. The basis appeared in 2025 (E_PASP growth, LARDVN,
GKS's evening discount) — it was ~zero in 2024-H2.
Hour-of-day (full, DA): +4-5 overnight HE1-8, +1.3-2.7 midday HE9-16, then **+11.1 (HE19), +18.0 (HE20), +16.2 (HE21), +10.8 (HE22)**,
+7.2 (HE23). RT: same shape, peak +15.9 at HE20. The whole basis is the GKS evening discount identified in item1.
Seasonal (DA): Jan +14.2 (storm episodes), Mar-May +7-9, Jun-Aug +5-6, Sep-Oct ~0, Nov-Dec +2-4. RT: Feb-May +7-9, summer +3-4, Sep-Oct ~0.
Zonal hub basis is only +1.2 / +0.9 — the nodal basis is 4-5x the hub basis, i.e. GKS-local.

### B3. Tradeable structures

**(a) DA basis virtual — short DA at RVN + long DA at GKS, 1 MW each.** PnL_h = spread_RVN − spread_GKS = basis_DA − basis_RT.

| | full window (19,246 h) | overlap, real RVN (2,449 h) |
|---|---|---|
| EV $/MWh, win rate, P/L ratio | **+1.00**, 51.5%, 1.20 | +0.44, 48%, 1.25 |
| t-stat | 4.3 | 1.6 |
| p1 / p99, min / max | −44 / +48, −1,519 / +1,080 | −36 / +42, −222 / +85 |
| daily Sharpe, fixed side (annualised) | spread **1.24**; RVN-short leg 1.22; GKS-short leg 0.65 | spread 1.46; RVN-long leg 1.29; **GKS-long leg 2.36** |
| walk-forward Sharpe (per-HE side chosen on 1st half, applied to 2nd) | spread **−1.03** (EV −0.19); RVN leg +0.02; GKS leg +0.99 | spread **−0.65**; RVN leg +0.51; GKS leg +1.39 |
| corr(spread_RVN, spread_GKS) | 0.71 | 0.74 |
| HE19-22 block: EV, win, p1 | +2.28, 57%, −73 (t 3.0) | +1.43, 59%, −115 (t 1.0) |

Per-HE EV (full) is positive in 21 of 24 hours but never above $3.6/MWh (HE21), with p1 losses of $60-86 in HE19-22; the largest
hours are all system RT spikes (2025-04-07 HE7 −$1,519; 2025-05-16 HE20 −$1,234) or the Jan-2026 storm (+$883, +$751 ...). The spread
does **not** beat the legs: in-sample its Sharpe equals the RVN-short leg (1.24 vs 1.22) and is far below GKS-long in the overlap
(1.46 vs 2.36); out of sample the spread is the only one of the three that is negative in both windows. Sign of the per-hour edge is
unstable across halves, which is what a 1.4%-explained basis implies: the spread's PnL is mostly the *difference of two DART noises*,
not a congestion signal.

**(b) CRR / FTR obligations, South -> Houston.** Datalake `ercot/ftr/auction/{YYYY_MM_monthly}/obligationmcp.csv.gz` is accessible
(nodal MCP in $/MW per TOU block; path cost = MCP_sink − MCP_source). Realised payout = Σ block hours (DA_sink − DA_source) (ERCOT has no
marginal-loss component, so DA LMP differences are pure congestion). TOU: WDPEAK weekday HE7-22, WEPEAK weekend/NERC-holiday HE7-22,
OFFPEAK HE1-6 + HE23-24. 26 monthly auctions 2024-08..2026-09; GKS_BESS_RN priced in all, RVN_RN only from 2026-09.
Files: `item7_crr_mcp_by_node.csv`, `item7_crr_path_pnl.csv`, `item7_crr_summary.csv`.

| path (obligation, 1 MW all three TOUs) | months | auction cost | realised | PnL | PnL/MW-yr | monthly hit rate | PnL ex Jan-2026 |
|---|---|---|---|---|---|---|---|
| **GKS_BESS_RN -> HB_HOUSTON** | 25 | $104.1k | $118.3k | **+$14.2k** | +$6.8k | 56% | **+$0.7k** (Jan-2026 storm = +$13.4k) |
| GKS_BESS_RN -> HB_SOUTH | 25 | 81.5k | 94.7k | +13.2k | +6.3k | ~45% | ≈ 0 ex Jan-2026 |
| HB_SOUTH -> HB_HOUSTON | 26 | 24.6k | 23.4k | −1.2k | −0.5k | 50% | |
| HB_BUSAVG -> HB_HOUSTON | 26 | 21.4k | 17.7k | −3.7k | −1.7k | 45% | |
| GKS_BESS_RN -> RVN_RN | 1 (Sep-2026) | 3.2k | 0.2k | **−3.0k** | | | RVN cleared rich in its first auction |

By year, GKS->HB_HOUSTON: 2024 −$3.7k, 2025 +$12.5k, 2026 +$5.5k; by TOU the only consistently positive block is OFFPEAK (+$4.0k/MW-yr,
Sharpe 0.8) — the peak blocks are priced fairly (realised $7.5 vs cost $7.7/MWh WDPEAK). The auction prices the GKS discount
almost exactly; the residual is one storm month. GKS is already the source node the market pays you to hedge — that is the existing
GKS book's CRR hedge question (crr-trader scope), not a two-asset product.

**(c) Physical dispatch complementarity — own local signal vs one common schedule** (TB2 perfect-foresight, 100 MW/200 MWh each,
before RTE; common schedule = same 2 charge + 2 discharge hours for both assets chosen on the summed price):

| | DA full (800 d) | RT full | DA overlap (102 d) | RT overlap |
|---|---|---|---|---|
| Σ TB2 independent vs common, $/MWh/day | 96.3 vs 92.2 | 116.8 vs 109.6 | 66.0 vs 63.5 | 86.8 vs 82.5 |
| uplift | **+4.5%**, **≈ $303k/yr** | **+6.5%**, ≈ $523k/yr | +4.1%, ≈ $188k/yr | +5.2%, ≈ $316k/yr |
| days with identical top-2 discharge hours | 43% | 39% | 27% | 25% |
| days with no common discharge hour | 21% | 28% | 23% | 21% |
| mean discharge HE, RVN vs GKS | 18.4 vs 17.3 | 17.7 vs 16.5 | 20.4 vs 20.0 | 18.8 vs — |

GKS's optimal discharge sits ~1 hour earlier than Raven's on average and differs on 57-75% of days; dispatching each asset on its own
nodal price is worth ~4-6% of combined TB2 (~$0.3-0.5M/yr on ~$7-8.5M/yr theoretical). This is the only quantified portfolio uplift
in this analysis — and it is the default behaviour of two independent books, not a spread product.

### B4. Risk view

- **Leg correlation**: hourly DA price 0.83, RT price 0.74, DART spread 0.71, daily TB2 0.90 (DA) / 0.79 (RT) [overlap: 0.79 / 0.81 /
  0.74 / 0.82 / 0.85]. The legs are one ERCOT book with a GKS congestion residual; the spread removes the common factor and leaves
  the residual plus twice the idiosyncratic noise.
- **Scarcity**: 22 hours with HB_BUSAVG RT > $500 in the window. RT basis std in those hours **$505 vs $22 in normal hours (23x)**,
  range −$119 to +$1,542; RT leg correlation stays 0.73 (both legs spike together) but the residual does not net: spread PnL ranged
  −$1,519 to +$938 in a single hour, mean −$70. Those 22 hours (0.11% of hours) carry 6.3% of the spread's gross PnL. A basis book
  is short a scarcity straddle it does not get paid for.
- **What kills it**: 19.6% of gross basis comes from constraints with no binding since Mar-2026 (LARDVN retired 2026-05, 1710__C,
  CATARINA, WHARTN) and a further 18.6% from faded ones; among the opposing set, 35.5% is STPELM27_1 (winter-only, unobserved since
  Jan-2026) and JN_WAP64_A (dormant). The one live opposing constraint, STP-WAP, is post-contingency and sits on a corridor CenterPoint
  is reconductoring (PHR-WAP, PHR-Meadow) with chronic parallel-path outages (Hillje, STP-ELMCREEK) — its λ is outage-conditioned and
  can vanish with topology work, as MDO-PHR appeared in 2025 without warning. E_PASP (22% of gross basis, live) is a GKS-only exposure.
- **Proxy risk**: pre-2026-06 RVN is the item2 blend (WHARTN artifact −$9.7k of "basis" is proxy-only; STP-WAP proxy SF 50% too large).
  All full-window numbers above inherit that; the overlap column is real and points the same way.

### B5. Verdict

**Not a product-expansion opportunity as a basis/spread product.** The hypothesis is right about the mechanism — STP-WAP (and
STPELM27_1) do have opposite shift factors at RVN_RN and GKS_BESS_RN — but wrong about materiality: opposing constraints are 11% of
gross basis and explain 1-4% of hourly basis variance. The RVN−GKS basis (+$5.4 DA / +$4.4 RT, +$16-18 at HE20-21) is GKS's
South-zone evening discount (E_PASP, LARDVN, HAINE, BRUNI, VALEXP) with Raven acting as the Houston hub; you can capture exactly the
same thing today with a GKS-vs-HB_HOUSTON position, and the CRR market already prices it (GKS->HB_HOUSTON obligation: +$0.7k/MW over
25 months ex the Jan-2026 storm, 56% monthly hit rate).

Size: **$0/yr defensible for a DA basis virtual** (in-sample +$1.0/MWh, ~$88k/yr at 10 MW round-the-clock, but walk-forward Sharpe −1.0
and no improvement over trading the legs). **CRR GKS->HB_HOUSTON: headline +$680k/yr at 100 MW is one storm month; ex-storm ≈ +$36k/yr
with −$240k single-month tails** — a hedge decision for the GKS book, not new revenue. The genuine portfolio value is **dispatch on local
signals: +$0.3M/yr (DA) to +$0.5M/yr (RT) theoretical (+4-6% of combined TB2)**, plus the diversification of the two DART books
(spread corr 0.71-0.74), both of which come from running two independent nodal books.

Main reason it does not work: the two nodes are not on opposite ends of a shared constraint set — Raven is congestion-neutral
(item1/item3a: basis var 5% of its spread, tracks HB_HOUSTON within ±$0.4 in the evening) while GKS carries all the congestion; a
"spread" therefore has one signal leg and one noise leg, and the one live opposing constraint (STP-WAP, ~$10k/MW-yr gross) is
post-contingency, outage-conditioned and too small to build a book on.

Recommended next step (if any): hand STP-WAP and the GKS->HB_HOUSTON OFFPEAK path to crr-trader as a candidate hedge for the GKS book;
for Raven, continue to model it as ≈ HB_HOUSTON with STPWAP39_1 / 35055__A as the two live nodal drivers (summer PM tailwind /
midday-solar headwind).
