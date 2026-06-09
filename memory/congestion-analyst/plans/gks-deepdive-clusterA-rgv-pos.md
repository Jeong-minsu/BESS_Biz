# GKS Cluster A deep-dive — POS constraints (raise GKS LMP / discharge-favorable)

**Created**: 2026-06-09 | **Author**: congestion-analyst | **Status**: STEP 2 DEEP-DIVE COMPLETE (3 constraints)
**Scope**: full per-constraint deep-dive of the 3 POS (LMP-raising) constraints Minsu confirmed: `HAINE__LA_PAL1_1`, `1710__C`, `421__A`.
**Data**: REAL Yes Energy Datalake (S3 `yedatalake`). Window = node existence 2024-07-03 → 2026-06-08 (~23 mo).
**Sign convention**: nodal MCC contribution = −SHIFTFACTOR(k→GKS)×λ. POS = GKS SF<0 (GKS relieves constraint) ⇒ binding raises GKS_BESS_RN LMP ⇒ **discharge-favorable**. (CONGESTION_PROJECT.md L32; [[gks-node-identity]].)
**Code/derived**: `shared/data/adhoc/2026-06-09_gks-congestion-impact/scripts/{deepdive_stats.py,drivers_clusterA.py}`,
`derived/{deepdive_clusterA_stats.json,drivers_clusterA.json,gks_msf_raw.parquet}`.

## ⚠️ HEADLINE CORRECTION — geography
Task framed all 3 as "RGV local lines". **Only HAINE__LA_PAL1_1 is RGV.** Per facility metadata (`objects/facility.csv.gz`, FROM/TOZONE):
- **HAINE__LA_PAL1_1** = LA PALMA→HAINE DRIVE 138 — **both SOUTH zone (deep RGV / Valley)**. Truly local.
- **1710__C** = BELL COUNTY SWITCHING→SALADO 138 — **both NORTH zone (Central TX, Bell County / Temple area)**. NOT RGV.
- **421__A** = BCESW→SANDOW SWITCH 345 — FROM NORTH, TO SOUTH (**Central TX, Sandow/Milam, North↔South zonal seam**). NOT RGV.

GKS's negative SF on 1710/421 is **not local topology** — it's the bulk **South-import-relief** effect: these Central-TX lines carry power North→South to serve South-Texas/Valley load; GKS injection in the deep South displaces that southward import → reduces flow → SF<0. The SF magnitudes prove it: 421__A (a 345 backbone segment) has |SF|≈0.13–0.32 (strong bulk-transfer coupling) while the truly-local HAINE 138 has |SF|≈0.03 (small, local). All 3 are still genuinely discharge-favorable for GKS, but the driver/relief story differs (HAINE = local renewable overload; 1710/421 = North→South import scarcity).

## RT λ source cross-check (per accepted flag) — PASSED
Sample: 1710__C 2024-08-20 17:xx CT. `transmission/constraints/rt/` PRICE = **$3499.99976** (= $3500 transmission cap) with VALUEMW 223 > LIMITMW 215 (overloaded/binding) at the same interval `market_shift_factors` RT λ=$3500. λ source validated. (HAINE 2026-03-25 lookup hit a TZ/hour-bucket offset between the msf DATETIME and the hourly `rt/` file name — magnitude check on 1710 is the clean PASS.) All 3 constraints are **~100% post-contingency (N-1)** — every dominant CONTINGENCYID maps to a named N-1 contingency; no base-case rows.

---
## 1. HAINE__LA_PAL1_1 — LA PALMA–HAINE DRIVE 138 (RGV local)
**Element/context**: 138 kV line, LA PALMA → HAINE DRIVE, both SOUTH (Hidalgo Co., deep Valley). FACILITYID 10002540916.
Dominant contingency **MHARNED5** (23211/28k rows, λ̄ $155) + SRAYRI38 (3361, $159), SN_SAJO5, SRAYRI28 — local RGV 138 N-1s (Harlingen/Rio area). GKS SF mean **−0.027** (DA) / **−0.035** (RT), min −0.092. Small |SF| = local line, marginal per-MW but binds constantly. GKS injection relieves local Valley 138 loading.
**Binding stats**: DA 7207 bind-hrs, λ median **$16**, P90 $125, P99 $315, max $584, mean $43, cum **+$10.9k** (rank #1 by frequency). RT 19994 intervals (~1736 hrs), λ median **$155**, P90 $364, P99 $827, max $3500, mean $186, cum **+$10.9k**. Years 2024:2911 / 2025:19107 / 2026:6015 — persistent, active in 2026.
**Drivers (5-lens, Mar-2025 sample, base-rate 65%)**:
- Demand: CONFIRMED — South load bind 3944 vs nonbind 3559 MW; P(bind) 0.44(low)→0.80(high load), λ 37→127.
- Supply/renewable: CONFIRMED — South solar bind 897 vs 493 (P(bind)→0.88 at high solar); GR_SOUTH wind bind 1841 vs 1272 (P(bind)→0.88 top-decile). **High local Valley solar+wind overloads the 138 → binds.**
- Outage: CONFIRMED contributory for the Mar-2026 RT $3500 spike — LA_PALMA 138/345 components on **planned outage 02/04–03/xx 2026** + LA_PALMA-KNGFSHER 345 planned. Structural pattern is renewable, outage amplifies.
- Temp/weather: HYPOTHESIS — load proxy; spring afternoon, no direct temp series pulled.
**Seasonality**: Spring (Feb–May peak; Mar/Apr biggest), trough Aug–Oct. Hour HE12–19 (afternoon, peak HE16–17), λ peaks HE17–18.
**Thresholds (RGV, spring)**: South load >~4 GW & solar high ⇒ P(bind)~0.80–0.88; λ scales with load to ~$125 (P90).
**GKS read**: raises GKS LMP — **discharge-favorable**. Frequency prize (small per-hr, huge hour-count). Matters most **spring afternoons HE12–19**; reliable but modest $/MWh.

---
## 2. 1710__C — BELL COUNTY SW–SALADO 138 (Central TX, NOT RGV)
**Element/context**: 138 kV, BELL COUNTY SWITCHING STATION → SALADO, both NORTH (Bell Co./Temple, Central TX). FACILITYID 10016245188.
Dominant contingency **DSALHUT5** (8652 rows, λ̄ $646; SALADO–HUTTO double) + DROUCHI8, DHUTGEA8 (λ̄ $3001), SGE2GEO8 ($3500) — Central-TX N-1/N-2. GKS SF mean **−0.025** (DA)/**−0.013** (RT), min −0.037. Small |SF| (distant line) but high λ ⇒ **severity** play. GKS relief = reduced North→South transfer.
**Binding stats**: DA 1728 bind-hrs, λ median **$132**, P90 $583, P99 $1047, max $1944, mean $225, cum **+$9.8k**. RT 7191 intervals (~608 hrs), λ median **$531**, P90 $1930, P99 $3500, max $3500, mean **$815** (highest of the 3), cum +$5.9k. **Years 2024:1550 / 2025:7468 / 2026: ZERO.**
**⚠️ FORWARD-RELEVANCE FLAG**: 1710__C has **not bound at all in 2026** (last binding 2025). Likely a line/area upgrade or topology change resolved it. Treat as **historically large but possibly retired** — low weight for forward GKS dispatch until re-confirmed.
**Drivers (5-lens, Aug-2024 sample, base-rate 21%)**:
- Demand: CONFIRMED — North load bind 2272 vs 1974; P(bind) 0.01(low)→0.51(high), λ →$260+. Summer-peak transfer.
- Supply/renewable: CONFIRMED inverse-wind — **GR_SOUTH wind bind 758 vs nonbind 981 (P(bind) 0.30 low-wind → 0.10 high-wind)**: low South wind ⇒ more North→South import ⇒ binds. Solar correlation (1401 vs 481) is largely midday time-of-day.
- Outage: INSUFFICIENT — only stale HUTTO planned/PS outages on the Aug-2024 episode day; primary driver = summer peak load + scarcity ($3500 caps in early-AM ramp & evening).
- Temp/weather: HYPOTHESIS (summer load proxy).
**Seasonality**: Summer/early-fall heavy (Aug biggest, then Oct/Sep/Jul/Jun/May). Anomalous **Feb spike** (166 rows, λ̄ $3370 — a winter-storm-type episode, Feb-2025). Hour: rows HE13–19; but **mean λ is extreme HE6–9 ($3249–3500)** = morning-ramp scarcity on few intervals.
**Thresholds (summer)**: North load high + low South wind ⇒ P(bind)~0.4–0.5, λ̄ $200–$310. Tail risk = $3500 cap (P99).
**GKS read**: when it bound, biggest λ of the 3 (severity). Discharge-favorable, summer HE13–19 + AM-ramp tails. **But dead in 2026 → discount heavily forward.**

---
## 3. 421__A — BCESW–SANDOW SWITCH 345 (Central TX seam, NOT RGV)
**Element/context**: 345 kV, BCESW (NORTH) → SANDOW SWITCH (SOUTH), Central TX (Sandow/Milam, North↔South seam). FACILITYID 10002864831.
Contingencies **DSALHUT5** (2428, λ̄ $90), **MSSNDBG5** (1623, $100), SBCESND5, SSNDBGR5, MSBCEBG5 — Sandow/BCESW/Bergstrom 345 N-1s. GKS SF mean **−0.193** (DA)/**−0.118** (RT), min **−0.324** — **largest |SF| of the 3**: GKS is strongly electrically coupled to this 345 South-import path; each MW of GKS discharge meaningfully relieves it.
**Binding stats**: DA 1182 bind-hrs, λ median $10, P90 $61, P99 $187, max $437, mean $24, cum **+$5.7k**. RT 4981 intervals (~415 hrs), λ median $48, P90 $197, P99 $700, max $2417, mean $87, cum +$4.2k. **Years 2024:160 / 2025:2983 / 2026:3023 — actively GROWING.**
**Drivers (5-lens; Apr-2025 sample thin, base-rate 2%)**:
- Transmission outage: **CONFIRMED structural** — on the strong RT episode 2025-11-25 (λ $2417), parallel 345 segments **BGRSW–BCESW 431_B, BGRSW–SNDSW 455_A, BCESW–YARSW 3425_B were all Forced-out since Apr–May 2025** + multiple BCESW/SANDOW bus components. Loss of parallel 345 paths forces flow onto 421__A → explains the 2025→2026 ramp.
- Demand: weak-positive (SouthCentral load bind 9022 vs 8222) — INSUFFICIENT in the thin April sample.
- Supply/renewable: HYPOTHESIS inverse-wind (GR_SOUTH wind bind 993 vs nonbind 1908) — consistent with 1710 import story but sample thin.
- Temp/weather: INSUFFICIENT.
**Seasonality**: Spring (Apr biggest) + late-fall/winter (Nov/Dec); afternoon HE10–18, λ peaks HE17–18 ($121–140).
**Thresholds**: data-thin; primary switch = **active parallel-345 outage state** (BGRSW/BCESW/SNDSW/YARSW corridor) → conditional P(bind) high. Recommend an outage-state feature for Stage-2.
**GKS read**: discharge-favorable; **highest per-MW leverage** (|SF| up to 0.32) of the 3 and the **only one growing into 2026** → most forward-relevant of Cluster A. Matters most spring + late-fall afternoons, conditioned on the Sandow/BCESW 345 outage state.

---
## Cross-constraint synthesis for GKS dispatch
- **Unifying mechanism**: all 3 raise GKS LMP because GKS injection *reduces* the constrained flow. HAINE = local RGV-138 renewable overload (high South solar+wind → bind). 1710 & 421 = North→South import scarcity (high North/Central load + **low** South wind → more southbound import → Central-TX lines bind); GKS discharge substitutes for imports → relief.
- **Forward ranking for GKS**: **421__A** (growing 2026, biggest |SF|, outage-gated) > **HAINE** (persistent frequency, spring afternoons) >> **1710__C** (largest historic λ but **zero 2026 binding — likely retired**).
- **When discharge-favorable congestion is most likely**: spring afternoons (HAINE + 421) and summer afternoons/AM-ramp (1710 historic). Low-South-wind + high-load hours amplify the Central-TX (1710/421) relief value.
- **Stage-2 modeling notes**: add (a) parallel-345 outage-state feature for 421__A (BGRSW/BCESW/SNDSW/YARSW), (b) South-zone solar+wind for HAINE, (c) a binding-onset/retirement flag (1710 went dead 2026, 421 ramped up) — static historical binding rates would mis-rank these.
