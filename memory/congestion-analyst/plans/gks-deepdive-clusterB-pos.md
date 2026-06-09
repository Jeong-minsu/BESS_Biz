# GKS deep-dive — Cluster B POS (constraints that RAISE GKS_BESS_RN LMP / discharge-favorable)

**Created**: 2026-06-09 | **Author**: congestion-analyst | **Status**: DEEP-DIVE COMPLETE (3 constraints), REAL Yes Energy Datalake.
**Scope**: BLESSING_1382, 15060__B, STPELM27_1 — the "other POS" cluster from `gks-congestion-impact.md` ranking.
**Convention**: impact($/MWh) = −SHIFTFACTOR(k→GKS)×λ_k (CONGESTION_PROJECT.md L32). POS ⇒ SF<0 ⇒ GKS relieves k ⇒ raises GKS LMP ⇒ favors DISCHARGE.
**Code/derived**: `shared/data/adhoc/2026-06-09_gks-congestion-impact/scripts/deepdive_clusterB_pos.py` → `derived/clusterB_pos_deepdive.json`.
**Reuses**: [[houston-congestion-mdophr-stpwap]] datalake methodology; [[gks-node-identity]] (GKS=SOUTH/Valley, COD 2024-07).

## Element decode (CONFIRMED from metadata/objects/facility.csv.gz)
| Constraint | FACILITYID | Element | Type | kV | From→To (zone) |
|---|---|---|---|---|---|
| BLESSING_1382 | 10002850012 | BLESSING 345KV BLESSING_1382 | **XFMR** (autotransformer) | 345 | BLESSING (SOUTH) — coastal South-TX |
| 15060__B | 10016988513 | VEALMOOR–KOCHTAP 138KV | LINE | 138 | VEALMOOR (WEST) → KOCHTAP (WEST) — **PERMIAN BASIN confirmed** |
| STPELM27_1 | 10018559567 (+10018570280 reverse) | STP–ELMCREEK 345KV | LINE | 345 | SOUTH TEXAS PROJECT (SOUTH) → ELM CREEK (SOUTH) |

## Binding stats (binding=SHADOWPRICE>0; window 2024-07→2026-06, node COD)
| Constraint | Mkt | bind-hrs(eqv) | SF med | neg% | cum $ | λ med | λ mean | λ P90 | λ P99 | λ max | years |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BLESSING_1382 | DA | 4171 | −0.075 | 100 | +3,857 | 4.8 | 11.9 | 28.5 | 106 | 342 | 24/25/26 |
| BLESSING_1382 | RT | 396 | −0.070 | 100 | +2,913 | 40.1 | 108 | 194 | 1533 | **4500** | 24/25/26 |
| 15060__B | DA | 4611 | −0.0076 | 100 | +2,872 | 43.2 | 78 | 200 | 414 | 742 | 24/25 |
| 15060__B | RT | 1719 | **+0.0042** | 0 | **−2,256** | 273 | 333 | 760 | 1158 | 3500 | 24/25 |
| STPELM27_1 | DA | 551 | −0.054 | 100 | +2,750 | 20.1 | 92 | 236 | 883 | 1330 | 25/26 |
| STPELM27_1 | RT | 116 | −0.051 | 93 | **+4,457** | 382 | **795** | 1937 | **4500** | 4500 | 25/26 |

Base-case fraction ~0 for all except STPELM27 RT 2.7% (rest pure post-contingency N-1). RT cross-check: STPELM27_1 episode
2026-01-25 22:00–22:35 in `transmission/constraints/rt/2026012522.csv.gz` shows PRICE=$4500, VALUEMW=713 > LIMITMW=611
(genuine post-contingency overload) — matches market_shift_factors RT λ. CONTINGENCY text blank in rt/ (known caveat), decoded via DA CONTINGENCYID=DELMSTP5.

---

## 1) STPELM27_1 — STP–ELM CREEK 345kV (SOUTH) — the real prize (severity, winter)
- **Geography/electrical vs GKS**: STP (Matagorda coast) → Elm Creek (San Antonio area, SOUTH). A 345 outlet of the
  South Texas Project nuclear plant heading inland/north toward the SA load + the ERCOT 345 backbone. GKS (deep RGV/Valley,
  far south) has **SF≈−0.05**: GKS injection counter-flows the STP→ElmCreek direction (relieves it). When binding, raising
  GKS output relieves STP-ELMCREEK ⇒ raises GKS LMP ⇒ **discharge-favorable**.
- **WHY relief**: STP-ELMCREEK carries south-coastal generation (STP + coastal wind) north out of the Matagorda/coastal
  pocket. GKS sits south of STP; injecting at GKS substitutes for coastal-pocket export, unloading the STP→ElmCreek path.
- **Contingency**: DELMSTP5 dominant (ELMCREEK-STP N-1 — loss of the parallel ElmCreek-STP circuit/breaker), then DSTEXP12,
  DLYTCIS5; 2.7% BASE CASE in RT. Post-contingency.
- **Driver 5-lens**:
  - Outage (#1, **CONFIRMED**): peak RT $4500 night 2026-01-25 22h coincides with **AJO 345kV corridor heavily out**
    (AJO-REFORZAR 345 LINE + breaker/DSC cluster out since 2025-09) + Blessing 138 outages. AJO is a parallel South-TX 345
    path; with it out, coastal/STP flow concentrates on STP-ELMCREEK and the DELMSTP5 N-1 overloads it (limit shrank to ~611MW).
  - Supply/wind (#2, **CONFIRMED**): same night GR_COASTAL ~2.1–2.2 GW + GR_SOUTH ~1.5–1.6 GW at HE22-23 (~3.7GW combined
    coastal+south wind) into low winter overnight load — net south→north export pressure through the corridor.
  - Temp/season (**CONFIRMED, WINTER**): DA cum$ Dec +1,789 / Jan +806 / Nov +106; RT Dec +3,025 / Jan +1,172 / Nov +261.
    Essentially zero outside Nov-Jan. Winter overnight = high wind + low load (opposite of Houston summer corridors).
  - Demand (HYPOTHESIS): low overnight winter load is the enabling condition (export pocket), not a high-load driver.
  - Hour: morning HE5-9 + evening HE17-20 lean (low midday). Overnight/shoulder, not midday-peak.
- **Onset 2025** (no 2024 data) — regime-change constraint like MDO-PHR; treat with onset/active-outage features (Stage 2).
- **GKS read**: RAISES LMP (discharge-favorable). RT cum +$4,457, mean λ $795, P99=max=$4,500 cap. Low frequency (116 RT
  bind-hrs) but the **single highest-severity POS constraint** for GKS. Matters: **winter (Dec>Jan>Nov), overnight/evening,
  when the AJO/South-TX 345 corridor is out and coastal+south wind is high.** This is the discharge-timing signal for winter nights.

## 2) BLESSING_1382 — BLESSING 345kV transformer (SOUTH coastal) — frequent, low-λ, coastal-export
- **Geography/electrical vs GKS**: 345kV **autotransformer** at Blessing station (Matagorda coast, between STP and the
  coastal 138 network), same corridor as STP-WAP/STP-ELMCREEK (see Houston work — BLY=Blessing). SF≈−0.075 clean both
  markets ⇒ GKS relieves ⇒ raises GKS LMP ⇒ **discharge-favorable**.
- **WHY relief**: the Blessing 345/138 transformer steps coastal South-TX generation down/through onto the 138 network;
  GKS injection from further south reduces the coastal export that loads the transformer.
- **Contingency**: DELMTEX5 dominant, MANSSTP5, DSTPREF5 (STP–Refugio, cf. Houston work), DSTPSTA5/MSTPSTA5 (STP-static).
  All STP/Elm-Creek/coastal outlet N-1s. Post-contingency, base-case 0%.
- **Driver 5-lens**:
  - Outage/contingency (#1, CONFIRMED structural): pure post-contingency on STP/coastal outlet losses — same coastal corridor.
  - Season (**CONFIRMED, broad winter+spring**): DA top Apr +706 / Jan +559 / Feb +556 / Dec +492 / May +408 / Nov +395.
    Not summer (Aug only +32). RT top Feb +733 / Apr +515 / Jul +452 / Dec +372 / Nov +361.
  - Hour (**CONFIRMED, overnight/morning**): DA+RT both peak HE4-10, trough HE12-17. Off-peak coastal-export pattern (high
    coastal wind + low load overnight) — same fingerprint as STPELM27, broader season.
  - Supply/wind (HYPOTHESIS, consistent): overnight coastal-wind export loads the transformer; not separately quantified per-episode here.
  - Demand/temp: INSUFFICIENT-DATA (not isolated; pattern is off-peak so not a load-peak driver).
- **GKS read**: RAISES LMP (discharge-favorable). DA cum +$3,857 (largest of the three on DA), RT +$2,913, RT max $4,500.
  **Frequency play** (4,171 DA bind-hrs, λ med only $4.8 DA / $40 RT) — broad low-grade discharge tailwind, concentrated
  **winter+spring overnight/morning**. Modest per-hour value; matters cumulatively, not as a single-event signal.

## 3) 15060__B — VEALMOOR–KOCHTAP 138kV (WEST / PERMIAN BASIN) — SIGN-UNSTABLE, near-zero coupling
- **Geography confirmed PERMIAN**: both VEALMOOR & KOCHTAP are WEST-zone (Permian Basin, near Midland). A 138kV line ~600+
  miles from GKS in the deep RGV/Valley.
- **HOW a Permian 138 reaches a Valley node — the honest answer: barely.** GKS SF on this line is **|SF|≈0.002–0.008**
  (near zero), and **the sign FLIPS between markets**: DA SF median −0.0076 (100% neg → POS, cum +$2,872) but **RT SF
  median +0.0042 (0% neg → NEG, cum −$2,256)**. Net DA+RT ≈ a wash. This is the long-distance residual DC sensitivity of a
  Valley injection on a remote Permian 138 element — physically marginal and numerically noisy, NOT a stable relief path.
  The constraint itself is a large genuine Permian congestion (DA λ med $43, RT λ med $273, **20,631 RT bind-intervals**),
  but GKS's coupling to it is incidental.
- **Contingency**: single SW_LVLT5 (a Permian SW/levelland-area N-1) in both markets.
- **Driver 5-lens**:
  - Supply/wind (#1, CONFIRMED pattern): classic Permian wind-export — hour profile peaks **overnight HE20-09**, troughs
    midday HE10-17 (solar+load relief). Massive RT frequency = chronic 2024-2025 Permian congestion.
  - Season: DA broad, fall-lean (Sep +482 / Oct +459 / Aug +386 / Apr +357). RT NEG every month (sign flip).
  - **Regime ended 2025** (NO 2026 data either market) — line likely re-rated/rebuilt or contingency retired (Permian 138
    buildout). Do not project forward without re-check.
  - Outage/demand/temp: INSUFFICIENT / not relevant (remote West-TX element, no GKS-local mechanism).
- **GKS read**: **DO NOT TREAT AS A REAL DISCHARGE SIGNAL.** The DA "+$2,872 POS" rank is a near-zero-SF artifact that the
  RT data contradicts (−$2,256). Net impact ≈ 0 and sign-unstable. Flag as a ranking false-positive: a Permian 138 has no
  reliable directional effect on GKS_BESS_RN. Exclude from GKS basis/discharge logic; keep only as a note that the
  identification ranking can surface remote noise constraints with tiny |SF| × large λ.

---

## Cross-constraint takeaways (for GKS discharge timing)
1. **Real POS discharge signals in this cluster = STPELM27_1 (winter-night severity) + BLESSING_1382 (winter/spring
   overnight frequency).** Both are the **coastal South-TX export corridor** (STP / Elm Creek / Blessing / AJO 345), where
   GKS injection counter-flows south→north export. Enabling condition: **low load + high coastal/south wind + a parallel
   South-TX 345 path OUT** — the winter-night mirror image of the Houston summer import corridors.
2. **15060__B is a false-positive** (remote Permian, |SF|~0, DA/RT sign flip, regime ended 2025) — drop from GKS logic.
3. **Seasonality contrast vs Cluster-A local RGV 138 lines** (HAINE/1710/421 = spring): this cluster's coastal-345 corridor
   is **winter** (STPELM27 Dec/Jan; Blessing winter+spring) — GKS discharge-favorable congestion is NOT summer-peak, it is
   winter overnight when South-TX wind exports and load is low.
4. **Stage-2 feature implications**: encode coastal-corridor onset (STPELM27 2025-onset), active South-TX 345 outage flags
   (AJO/Blessing/Hillje/STP-outlets watch-list), coastal+south wind actuals (GR_COASTAL/GR_SOUTH), and a |SF| floor /
   sign-stability check to suppress remote noise constraints like 15060__B.

## Caveats
- RT method = market_shift_factors MARKET='RT' (pricenode-level at GKS, λ pre-aligned); cross-checked vs rt/ PRICE for
  STPELM27 (CONFIRMED). SCED resource-level attribution not done (per-generator), as in identification run.
- Contingency MEMBER element lists not in datalake (CRR Network Model, Secure-Area; Minsu lacks cert) — contingency NAMES
  decoded, members inferred from corridor topology only.
- Wind/outage driver confirmation done on the single peak STPELM27 episode (2026-01-25) + seasonality; not a full panel
  regression per constraint (time-boxed). Directional CONFIRMED, not a fitted threshold table.
- Window = node existence 2024-07→2026-06 only.
