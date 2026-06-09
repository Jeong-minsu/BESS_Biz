# GKS Cluster-C deep-dive — South-Texas export NEG paths (charge-favorable, GKS POSITIVE SF)

**Created**: 2026-06-09 | **Author**: congestion-analyst | **Status**: DEEP-DIVE COMPLETE (3 constraints)
**Scope**: full Houston-style 6-part deep-dive of the 3 confirmed Cluster-C constraints that LOWER GKS_BESS_RN LMP
(GKS positive shift factor ⇒ GKS export aggravates ⇒ prices its own node DOWN ⇒ charge-favorable). Congestion-analyst R&R only.
**Data**: REAL Yes Energy Datalake (S3 `yedatalake`), node `GKS_BESS_RN` pricenode 10017907494, window 2024-07-03→2026-06-08.
**Sign**: impact = −SF×λ; Neg = lowers GKS LMP. All 3 confirmed POSITIVE SF (GKS aggravates).
**Code/derived**: `shared/data/adhoc/2026-06-09_gks-congestion-impact/scripts/` (explore_clusterC, decode_clusterC,
build_panel_clusterC, analysis_clusterC, season_episode_xcheck, check_retire) + `derived/driver_panel_clusterC.parquet`,
`derived/seasonality_clusterC.json`.

## HEADLINE — forward relevance ≠ cumulative rank (the key operational finding)
Cumulative-$ ranking overstates two of the three. Data is continuous (GKS binds every month through Jun-2026):
- **E_PASP — LIVE.** Binds continuously through 2026-06-08. The durable forward charge signal. ~31% of its entire
  cumulative DA impact is ONE 3-day episode (Jan 24-26 2026).
- **LARDVN_LASCRU1_1 — LARGELY RETIRED ~Oct-2025.** Heavy through 2025-09 (391 DA/831 RT rows/mo), then collapses:
  2025-10 = 15/41, **zero Nov-2025→Mar-2026**, sporadic 2026-04/05 only. Almost certainly a Laredo-area 138 upgrade.
- **CATARI_PILONC1_1 — RETIRED ~Jun-2025.** Heavy through 2025-05, then near-zero (trivial 2026-02 only).
- ⇒ For bess-optimizer charge-siting: weight **E_PASP high**, LARDVN/CATARINA as **historical / near-dormant** (monitor for
  re-binding, don't lean on them forward). This is a constraint-RETIREMENT regime change — the mirror of MDO-PHR onset;
  Stage-2 embedding must encode offset as well as onset.

---

## 1) E_PASP — PAWNEE→CALAVERAS 345kV interface (RTI / GTC-like, BASE CASE)
- **Element**: FACILITYID 10017409521 / RTI 10017407444, FROMSTATION **PAWNEE** (SOUTH, Bee Co. nr Three Rivers) →
  TOSTATION **CALAVERAS** (SOUTH; CPS Energy Calaveras/Spruce-Deely complex SE of San Antonio), 345kV. FACILITYTYPE = **RTI**
  (regional transmission interface / stability-GTC), **NOT a single monitored line N-1**.
- **Contingency = BASE CASE (100%)** — unlike the Houston N-1 constraints and unlike LARDVN/CATARINA. E_PASP is an
  *interface limit* that binds in the unconstrained base case (like VALEXP). It is a South-TX→San-Antonio export interface.
- **GKS SF CONFIRMED POSITIVE**: DA mean **+0.244** (range +0.169..+0.369), RT **+0.223** (`gks_msf_raw.parquet`). High &
  consistently positive: GKS injection in the Valley flows north over Pawnee→Calaveras → loads the interface → aggravates →
  prices GKS node DOWN. Highest SF of the three (biggest per-MW charge benefit).
- **Binding stats** (PRICE>0): DA 4,539 bind-hrs, λ mean $54.2 / med $13.6 / P90 $98 / P99 $633 / max $4,566.
  RT 9,314 intervals (~776 h), λ mean $140 / med $61 / P90 $259 / P99 $1,286. (RT msf max $15,341 is a SINGLE un-corroborated
  spike — see x-check below; realistic RT peak ~$3,500-3,665.)
- **Jan-2026 concentration RESOLVED = SINGLE 3-DAY EPISODE, not recurring.** Jan 24-26 2026 = **−$17,502 = 31.1% of the
  ENTIRE DA cumulative −$56,360**. Those 3 days: 24/24 hrs bound, λ med $206 / $1,061 / $314, max $4,566. Jan-2026
  ex-episode = only −$1,115 (a normal month). Next-worst single days are −$1,007 (2025-02-20), −$964, −$892 — an order of
  magnitude smaller. **E_PASP DA EX-episode = −$38,858.** Report both. (Prior "Jan −$20.5k" = all-January-months summed;
  the 2026 event alone is −$17.5k.) Likely a late-Jan-2026 winter event / parallel-345 outage on the SA import corridor.
- **Drivers (5-lens, DA panel binning)**:
  - SUPPLY/wind = **CONFIRMED primary**. P(bind) 7%→40% across South-wind 0→2500 MW; **coastal-wind corr +0.45 (highest
    single driver)**, south-wind +0.26. >3000 MW South wind P(bind) falls (whole-region surplus). Wind+coastal injection
    pushes north over the interface.
  - DEMAND = **CONFIRMED (San-Antonio-pull)**. P(bind) 10%→**47%** across South-load 3→7 GW; corr +0.29. Counter-intuitive
    for an "export" path until you see it's an export-TO-LOAD interface: high evening San-Antonio/South load pulls South-TX
    generation north over Pawnee→Calaveras. Net-surplus proxy ≈0 corr precisely because BOTH high wind AND high load load it.
  - TEMP/WEATHER = HYPOTHESIS (load is the channel; not separately isolated).
  - OUTAGE = HYPOTHESIS for the Jan-2026 episode (24/24-hr 3-day bind at λ→$4.5k is the outage signature; contingency=BASE
    CASE so an outage would be a *standing* derate on a parallel 345, not an N-1). Not confirmed (no outage pull this run).
  - SOLAR = INSUFFICIENT (corr +0.06).
- **Seasonality**: month — Jan (episode-dominated), then **Aug/Jul** (summer wind+load); ex-episode it is summer-heavy.
  RT — May/Jan/Aug/Jul. **Hour — EVENING PEAK HE17-21 (P(bind) 45-56%)**, trough overnight (13-17%). Evening = wind still
  high + solar gone + SA load peak.
- **Thresholds**: South wind ≥1.5 GW → P(bind) ≥36%; ≥2 GW → ~40%. South load ≥5 GW → 47%. HE17-21 the binding window.
  Combined evening + South/coastal wind >1.5 GW + South load >5 GW = the high-charge-value setup.
- **GKS read**: LIVE, highest-SF charge signal. Lean into cheap charging **evening HE17-21** on high-South/coastal-wind days
  (and the rare multi-day winter export events where λ→$1k+). Most negative MCC when wind AND evening load both high.

## 2) LARDVN_LASCRU1_1 — LAREDOVNTH→LASCRUCE 138kV (post-contingency N-1) — *largely retired ~Oct-2025*
- **Element**: FACILITYID 10015857039, FROMSTATION **LARDVNTH** (Laredo-area 138 bus, SOUTH/Webb Co.) → TOSTATION
  **LASCRUCE** (Las Cruces, SOUTH-TX — *not* New Mexico), 138kV LINE.
- **Contingency = N-1 family** (shared with CATARINA): MFOAVLO5 (dominant), MLOBFOR5, MLOFOAV5, DFOAVLO5, DFOWSMG5 — a
  Laredo/SW-South-TX 138 composite-contingency corridor (member lists not in datalake; same caveat as Houston work).
- **GKS SF CONFIRMED POSITIVE**: DA mean **+0.083** (−0.034..+0.146), RT **+0.090**. GKS Valley export raises flow on the
  Laredo 138 corridor → aggravates → charge-favorable.
- **Binding stats**: DA 4,948 rows / 4,020 bind-hrs, λ mean $53 / med $19 / P90 $153 / P99 $367 / max $682. **RT 14,957
  intervals (~1,246 h), λ mean $236 / med $176 / P90 $447 / P99 $1,102 / max $3,500 (= the RT shadow-price cap; CONFIRMED
  identical to rt/ PRICE $3,499.99976 on 2024-11-17 16:05 — clean validation of the msf-RT method).** Largest RT-neg of the
  three by cumulative $.
- **Drivers**: SUPPLY/**South wind = CONFIRMED clean primary** — P(bind) 6%→**45%** across 0→2500 MW AND λ rises with it
  (med $3→$80-124). Wind corr +0.28, coastal +0.29. This is the textbook wind-export N-1: more South wind → more flow on the
  Laredo corridor → harder bind + higher λ. DEMAND secondary (P(bind) 13%→40% at high load, U-shaped). Solar/net ≈0/neg.
- **Seasonality**: month **Jul/Aug/Apr/Jun** (summer + spring wind). **Hour — EVENING/OVERNIGHT peak HE19-22 (46-49%),
  elevated overnight** = South-TX wind diurnal (peaks evening/night). RT prize bigger than DA.
- **RETIREMENT**: heavy through 2025-09, collapses 2025-10 (15 DA/41 RT), **zero Nov-2025→Mar-2026**, sporadic since. Treat as
  historical; monitor for re-binding.
- **GKS read**: historically the biggest RT charge signal (overnight/evening high-wind), but **near-dormant since Oct-2025**.
  Do NOT weight forward unless re-binding observed.

## 3) CATARI_PILONC1_1 — PILONCILLO↔CATARINA 138kV (post-contingency N-1) — SEVERITY; *retired ~Jun-2025*
- **Element**: FACILITYID 10002553470 (PILONCIL→CATARINA) / 10002859190 (reverse), 138kV LINE. **CATARINA & PILONCILLO =
  Dimmit Co., deep SW South-TX (Eagle Ford / heavy wind+solar zone)**, SW of San Antonio.
- **Contingency = N-1 family** (shares MLOBFOR5, MFOAVLO5, MLOFOAV5, DFOWSMG5 with LARDVN ⇒ same SW-South-TX 138 corridor)
  plus SBIGASH8, MASHDIL8, MLOFOW15. Composite contingencies.
- **GKS SF CONFIRMED POSITIVE (weak)**: DA mean **+0.043** (−0.076..+0.137), RT **+0.061**. Small & occasionally negative —
  GKS only marginally aggravates.
- **Binding stats — SEVERITY play**: DA 4,627 rows / 3,906 bind-hrs, λ mean $11 / med $3 (low). **RT 5,625 intervals, λ mean
  $370 / med $327 / P90 $695 / P99 $1,104 / max $3,500 (cap).** RT λ is the highest median of any GKS NEG constraint — a few
  hundred severe hours, not a frequency play.
- **Drivers — OPPOSITE REGIME from the wind-export pair**: every driver corr NEGATIVE (wind −0.14, load −0.30, solar −0.26).
  P(bind) peaks at **LOW load** (89% @2.5-3 GW → 9% @5-7 GW), **LOW wind**, **LOW/zero solar**, and **OVERNIGHT HE0-8
  (32-39%), dead midday HE10-17 (~10%)**. Interpretation: **light-load / low-renewable overnight local-pocket constraint** in
  sparse SW South-TX — local solar relieves it midday; absent solar + minimum load overnight, the post-contingency 138 binds,
  and λ is severe ($327 median RT). Severity (λ) still rises in the rare high-wind/high-load bins even though frequency there
  is low. CONFIRMED as a light-load overnight regime; mechanism (voltage/radial vs thermal) not separable from this data.
- **Seasonality**: RT-dominated, **Jan/May/Feb/Mar** (winter/spring overnight). Hour overnight HE0-8.
- **RETIREMENT**: heavy through 2025-05, near-zero since 2025-06.
- **GKS read**: historically a SEVERE but infrequent overnight charge signal (when it binds, RT λ huge → very cheap
  overnight charging), but **retired since mid-2025** and GKS SF is weak. Low forward weight; monitor.

---

## Cross-cutting / methodology notes
- **RT method x-check (task FLAG #1 closed)**: market_shift_factors RT SHADOWPRICE == `transmission/constraints/rt/` PRICE
  confirmed exactly for LARDVN ($3,499.99976). **RT shadow-price cap for these South 138s = $3,500** (not the $4,500
  transmission cap seen on Houston 345s). **E_PASP's single $15,341 RT msf value is an OUTLIER** — uncorroborated by rt/
  (which maxed $3,665 that hour, 2025-05-16 19:45); binding was real but use rt/-corroborated severity, treat $15k as a spike.
- **E_PASP is BASE-CASE interface (RTI/GTC)**; LARDVN & CATARINA are N-1. Different binding physics — embed interface vs N-1
  as a feature.
- **Constraint-RETIREMENT regime change** (LARDVN ~Oct-2025, CATARINA ~Jun-2025) is the mirror of MDO-PHR onset. Static
  historical-binding stats would over-weight both. Stage-2 must encode recency / active-status decay, not just onset.
- **South-TX wind diurnal** = evening/overnight peaking — opposite of solar-pocket Houston constraints. The two live/big
  signals (E_PASP, LARDVN) are evening/overnight high-wind plays ⇒ GKS cheapest charging is evening/overnight, not midday.
- Related: [[gks-node-identity]], [[houston-congestion-mdophr-stpwap]], plan `gks-congestion-impact.md`.
</content>
</invoke>
