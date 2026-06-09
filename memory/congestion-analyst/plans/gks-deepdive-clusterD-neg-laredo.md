# GKS Cluster D deep-dive — Laredo/border NEG (charge-favorable) constraints

**Created**: 2026-06-09 | **Author**: congestion-analyst | **Status**: DEEP-DIVE COMPLETE (Step 2 confirmed by Minsu)
**Scope**: 3 constraints with POSITIVE GKS shift factor → GKS injection AGGRAVATES → LOWERS GKS_BESS_RN LMP → **charge-favorable**.
Targets: BRUNI_69_1, LOYOLA_69_1, LASCRU_MILO1_1 (all Webb Co. / Laredo border area, SOUTH zone).
**Data**: REAL Yes Energy Datalake (S3 `yedatalake`). Source = `market_shift_factors` at GKS pricenode 10017907494 (`gks_msf_raw.parquet`, binding rows SHADOWPRICE>0). Same convention as identification pass: impact $/MWh = −SF×λ; cum $ time-weighted (DA 1h, RT 1/12h).
**Code/derived**: `shared/data/adhoc/2026-06-09_gks-congestion-impact/scripts/{deepdive_clusterD.py, driver_wind_clusterD.py}` → `derived/{clusterD_stats.json, clusterD_month_hour.json, clusterD_driver_wind.txt}`.

## ELEMENT DECODE (kV verified vs metadata facility.csv.gz) — corrects the "69" name
| Constraint | FACILITYID | Element (metadata FACILITYNAME) | Type | **kV (verified)** | From→To |
|---|---|---|---|---|---|
| BRUNI_69_1 | 10000806154 | "BRUNI 138KV BRUNI_69_1" | **XFMR** | **138 kV** (138/69 autotransformer at BRUNI sub) | BRUNI station, SOUTH |
| LOYOLA_69_1 | 10002370188 / 10000798785 | "LOYOLA 138KV" + "LOYOLA 69KV" | **XFMR** (two windings) | **138/69 kV transformer** at LOYOLA SWITCHYARD | LOYOLA, SOUTH |
| LASCRU_MILO1_1 | 10015995515 | "LASCRUCE-MILO 138KV LASCRU_MILO1_1" | **LINE** | **138 kV** (genuine line) | LASCRUCE → MILO, SOUTH |
- **kV correction**: BRUNI and LOYOLA are **138-kV-class transformers** (autotransformers, NOT 69-kV lines); the "_69_1" is the equipment/low-side tag. LASCRU_MILO1_1 is a genuine **138 kV LINE**. So cluster is "138 kV (+138/69 XFMR)", not 69 kV.
- **Tiny thermal limits**: rt/ file LIMITMW ≈ **38 MW** for LOYOLA → small element → saturates fast → λ slams the **$3500 RT shadow-price cap**. (NB: RT cap observed = $3500, distinct from the $4500 figure in Houston memory; ERCOT RT transmission-constraint cap.)
- **WHY GKS positive SF**: GKS sits deep South Texas/RGV. These elements carry South-Texas **export/through-flow toward the Laredo–border network**; GKS injection adds to that flow → positive SF → aggravates → own LMP pushed down. SF confirmed in `gks_msf_raw.parquet`: BRUNI median +0.0128, LOYOLA +0.0119–0.0154, LASCRU +0.091 (LASCRU on the direct line path → ~7× larger SF than the two transformers).

## CONTINGENCIES — all POST-CONTINGENCY (no base case)
- None of the dominant contingency IDs are in the 4 "BASE CASE" metadata entries → 100% post-contingency (N-1/N-2). Codes are composite (S=single / D=double / M=multiple element). Authoritative element membership needs CRR Network Model (Minsu lacks USCERT cert — see houston memory lesson #2); do NOT assume 1 contingency = 1 line.
- **BRUNI** dominated by `MFOAVLO5` / `DFOAVLO5` / `MLOBFOR5` (FO-AV-LO Laredo-area outage group, multiple/double).
- **LASCRU_MILO** dominated by the **same** `DFOAVLO5` (3666/3895 RT rows) → BRUNI and LASCRU are electrically coupled around the same FO-AV-LO outage.
- **LOYOLA** dominated by `SN_SLON5` + `SKLELOY8` (single-element N-1 at Loyola).

## BINDING STATS (from clusterD_stats.json)
| Constraint | Mkt | bind-hrs | bind-int | λ med | λ mean | λ P90 | λ P99 | λ max | cum $ | top months | top HE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BRUNI_69_1 | DA | 4022 | 3249 | 69 | 182 | 490 | 1306 | 2597 | −10,343 | Apr/Dec/Jan | overnight HE22-07 |
| BRUNI_69_1 | RT | 547 | 6512 | 821 | 978 | 2011 | 3500 | 3500 | −7,274 | Apr/Dec/Jan | overnight HE20-07 |
| LOYOLA_69_1 | DA | 4435 | 3338 | 58 | 109 | 283 | 616 | 2267 | −6,770 | May/Apr/Nov | evening HE18-21 |
| LOYOLA_69_1 | RT | 782 | 9239 | 391 | 576 | 1143 | 3500 | 3500 | −7,343 | May/Apr/Jan | evening HE18-21 |
| LASCRU_MILO1_1 | DA | 1774 | 1439 | 11 | 30 | 84 | 195 | 420 | −5,052 | Nov/Jan/Oct | evening HE20-23 |
| LASCRU_MILO1_1 | RT | 325 | 3895 | 123 | 189 | 399 | 1118 | 3096 | −5,471 | Jan/Nov/Oct | evening HE19-22 |
- **RT cross-check PASSED** (LOYOLA 2026-01-25 HE19-20): msf SHADOWPRICE == rt/ PRICE exactly (560.46, 675.55, 1790.80, 1620.11, 3499.99…). Confirms the `market_shift_factors` RT λ feed = SCED rt/ PRICE. Multiple contingencies bind simultaneously per interval (one at the $3500 cap + others lower).
- Severity ranking RT mean λ: **BRUNI $978 > LOYOLA $576 > LASCRU $189**. All saturate the cap in their worst episodes.

## DRIVER 5-LENS (clusterD_driver_wind.txt)
1. **Supply / South-zone WIND — CONFIRMED (dominant).** Mean GR_SOUTH wind in DA binding hours vs non-binding: LOYOLA 2025-05 **1854 vs 977 MW (1.90×)**; BRUNI 2025-04 **2266 vs 1486 MW (1.52×)**; LASCRU 2026-01 **1815 vs 769 MW (2.36×)**. South-wind diurnal shape (peak overnight HE22-05, trough midday HE10-16) **matches the binding-hour profiles**. Mechanism: overnight Webb/Duval/Starr-county wind surge → export through Laredo 138/69 transformers + LASCRUCE-MILO 138 → post-contingency overload → bind.
2. **Outage / contingency — CONFIRMED structurally** (100% post-contingency) but **specific outage INSUFFICIENT** (CRR model not accessible). FO-AV-LO group is the recurring N-1/N-2.
3. **Demand / local load — HYPOTHESIS.** Evening peaks (HE18-22) for LOYOLA/LASCRU align with local load peak, but not isolated from the evening wind ramp. Not separately confirmed.
4. **Solar — HYPOTHESIS.** Midday binding trough is consistent with local/South solar relief offsetting export, but not directly tested.
5. **Temp/weather — INSUFFICIENT.** Strong RT episodes 2026-01-24/25 coincide with a Jan-2026 winter event (cold load + high wind) but temperature not isolated from wind.

## SEASONALITY
- **BRUNI**: Spring (Apr peak, −$3.96k DA) + Dec/Jan secondary. Overnight-dominant (HE22-07), midday trough.
- **LOYOLA**: Spring (May/Apr) + Nov. Evening-dominant (HE18-21).
- **LASCRU_MILO**: Fall/Winter (Nov/Jan/Oct). Evening/overnight (HE19-23). Jan-2026 is the single biggest RT month (−$2.37k).
- Common thread: shoulder-season + cool-season **high-wind, low-local-solar** windows.

## OPERATIONAL THRESHOLDS (data-supported)
- **South-zone (GR_SOUTH) wind > ~1800 MW overnight/evening** is the primary binding trigger for the cluster (binding-hour median ≈ 1800–1900 MW vs ~800–1500 non-binding). LASCRU most wind-sensitive (2.36× separation, near-zero binding when South wind < ~900 MW midday).
- Requires the **FO-AV-LO Laredo-area contingency group active** (post-contingency) — these never bind in base case.
- Hour windows: BRUNI HE22-07; LOYOLA/LASCRU HE18-23.

## GKS-SPECIFIC READ (direction = LOWERS LMP → CHARGE-FAVORABLE)
- All three **depress GKS_BESS_RN LMP** when binding → **favor charging** during the binding windows (overnight for BRUNI, evening HE18-23 for LOYOLA/LASCRU). This aligns charge timing with cheap overnight/evening high-wind South-Texas hours.
- **Cumulative impact (per 1 MW continuous, full ~23-mo history)**: BRUNI −$17.6k (DA −10.3k + RT −7.3k), LOYOLA −$14.1k (DA −6.8k + RT −7.3k), LASCRU −$10.5k (DA −5.1k + RT −5.5k). Cluster D total ≈ **−$42.2k/MW**. Material but each individually smaller than E_PASP/LARDVN-LASCRU (the top NEG drivers).
- **Frequency vs severity**: BRUNI/LOYOLA bind thousands of DA hours at modest SF but huge λ (transformer cap-outs); LASCRU fewer hours but higher SF. The RT prize is cap-driven (rare $3500 spikes), so RT value is episodic (Jan/Apr/May high-wind events), not steady.
- **Caveat**: SF for BRUNI/LOYOLA tiny (~0.013) → small $/MWh per event despite high λ; only material because they bind so often. LASCRU SF ~0.09 → larger per-event swing.

## FLAGS
- Specific transmission-outage attribution blocked by CRR Network Model access (carry-over from houston memory lesson #2).
- Driver test used GR_SOUTH zonal wind (reachable); station-level Laredo wind not in datalake.
- This is constraint-MCC analysis only (R&R = congestion). Charge/dispatch decision is bess-optimizer's.
