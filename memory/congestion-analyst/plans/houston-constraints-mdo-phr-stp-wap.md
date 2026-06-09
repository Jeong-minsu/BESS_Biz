# Houston-area constraint reference: MDO-PHR & STP-WAP

**Created**: 2026-06-09 | **Author**: congestion-analyst | **Status**: domain-reasoned priors (no binding history yet — Stage 0)

Reference note for Stage 2 constraint embedding / Houston basis priors. Element decoding is CONFIRMED from
ERCOT RPG + CenterPoint + NRC docs. Binding/λ driver rankings are HYPOTHESIS pending datalake ingestion.

## Element decoding (CONFIRMED)
- **PHR** = P.H. Robinson — CenterPoint 345 kV switching station, Galveston Bay (Bacliff/Texas City). Gen retired ~2018 → now a transmission node only.
- **WAP** = W.A. Parish — NRG ~3.6 GW coal+gas, Fort Bend Co. (Thompsons/Smithers Lake), SW Houston. Major 345 kV injection node.
- **MDO** = Meadow — CenterPoint 345 kV station SE Houston. (CNP "PHR–Meadow 345 kV double-circuit ~17.4 mi".)
- **STP** = South Texas Project nuclear, ~2.5 GW, Matagorda Co. coast. Has confirmed 345 kV circuit direct to W.A. Parish.

All three (STP, WAP, PHR/MDO) sit on the **SW→SE Houston 345 kV import corridor**. CenterPoint is hardening/
reconductoring PHR–WAP (40.2 mi) and PHR–Meadow (17.4 mi) → both are thermally/reliability constrained.

## STP-WAP (STP ↔ W.A. Parish 345 kV) — IMPORT-CORRIDOR / source-driven
Binds on south→Houston import. Strong when: high Houston/coastal load + STP both units full + high South/coastal
wind-solar injection + a parallel coastal 345 path (STP–Hillje/Blessing, Parish–Hillje) OUT + hot (load↑ & rating↓).
Dormant: shoulder load, STP refuel outage, all parallels in, low south renewables.
Driver rank: (1) parallel-path outage, (2) STP output + south/coastal renewable injection, (3) Houston load, (4) temp (load+derate), (5) coastal weather/storm forced outages.

## MDO-PHR (Meadow ↔ P.H. Robinson 345 kV double-circuit) — LOAD-POCKET / sink-driven
Internal SE Houston / Galveston Bay / Texas City / Clear Lake pocket. PHR gen retired → pocket is import-dependent.
Strong when: high bay-area summer AC + petrochem load + one circuit of the double-ckt OUT (N-1) or PHR–WAP out +
hot. Dormant: mild, both circuits in, low pocket load.
Driver rank: (1) double-ckt N-1 / PHR–WAP outage, (2) bay-area load level, (3) temp (load+derate), (4) local gen deficit (PHR retired; nearby coastal units), (5) coastal storm outages.

## Confirmation data needed (all in datalake per CONGESTION_PROJECT §5, none ingested yet)
- `transmission/constraints/da/` + SCED shadow price NP6-86-CD → actual binding freq, λ, contingency name per constraint
- `metadata/objects/{facility,contingency}.csv.gz` → exact monitored element + contingency def
- `market_shift_factors/` / `ercot_sced_shift_factors/` → which units (STP, Parish, coastal wind) have high shift factor
- `transmission/outages/actual/` → correlate outage → binding switch
- weather/load actual+vintage → Houston-zone load, coastal temp, south/coastal wind/solar
- `ftr/auction/` → CRR market priced view of HB_HOUSTON / South→Houston paths

---

# EMPIRICAL VALIDATION (2026-06-09) — clearly separated from prior HYPOTHESIS above

**Status**: validated against real Yes Energy Datalake (S3 `yedatalake`) data. NOT mock.
Window: DA binding history 2023-01-01 → 2026-06-08 (16yr source available; scanned 3.4yr).
RT/SCED + shift-factor + outage + load + weather pulled for strong-binding episodes.
Working scripts + derived parquet: `shared/data/adhoc/2026-06-09_houston-constraint-validation/`.

## Exact identifiers (CONFIRMED)
- **MDO-PHR** = CONSTRAINTNAME `MDOPHR99_A`, REPORTED_NAME "MDO-PHR 345KV".
- **STP-WAP** = CONSTRAINTNAME `STPWAP39_1`, REPORTED_NAME "STP-WAP 345KV".
- Both bind almost exclusively as **post-contingency (N-1)** constraints, not base case.

## Binding statistics (DAM, 2023→2026-06)
- MDOPHR99_A: 2,596 binding-hours; λ mean $16.6, median $8.2, P90 $42.8, P99 $122.5, max $160.1.
  - **Binding ONSET = 2025**: zero DAM binding before 2024-10. New constraint regime (CenterPoint PHR/WAP work).
  - Strongest days: 2025-04-29..05-02, 2026-05-04/16 (SPRING, not summer). HE peak 12-17 (peak HE14).
  - Top contingencies (by hrs): DWAP_OB5 1238, DPHRCTR5 642, DKG_NB_5 415, DOASWAP5 117.
- STPWAP39_1: 2,066 binding-hours; λ mean $47, median $20.3, P90 $111.5, P99 $412, max $828.6.
  - Binds EVERY summer (2023/24/25). Strongest: 2023-08-09..14 (heat wave, λ→$828), 2025-05-14/15. HE peak 15-18.
  - Top contingencies: DWPWFWP5 1749, DBLBYWF5 145 (Blessing coastal path), DWPWFCK5 79, DSTPREF5 39.
- RT/SCED (NP6-86-CD) physical binding CONFIRMED: MDO-PHR λ→$247 @2025-05-02 12:25 (flow=limit=1291MW);
  STP-WAP λ→$347 @2025-05-14 16:40. (CONTINGENCY text blank in YE rt/ variant; decoded via DA CONTINGENCYID.)

## Per-lens verdicts
### MDO-PHR (MDOPHR99_A)
| Lens (hypo rank) | Verdict | Evidence |
|---|---|---|
| Element decode | CONFIRMED | REPORTED_NAME "MDO-PHR 345KV" |
| Parallel-path / N-1 outage (#1) | **CONFIRMED (strongest)** | post-contingency only; DWAP_OB5 dominant. 2025-05-02 active outages: WAP 345kV breakers A220/250/270/C710/C720, PHR 138kV + PHR-SBK line (since 04/21). Binding ONSET in 2025 coincident w/ CenterPoint work. |
| Bay/Coast load (#2) | CONFIRMED | P(bind) 11%→74% monotone across COAST-load deciles |
| Temperature (#3) | CONFIRMED (hot mode) + REFINED | Galveston temp deciles 8-9 → 77-85% bind; secondary cool-shoulder mode (outage-driven) → temp not sole driver |
| Local gen / supply | REFINED | high-|SF| units = coastal-SW injectors: Dow Chemical +0.32, JAR/TORT BESS +0.45/+0.31, TNG_SOLAR +0.32 — pocket loaded by SW injection, NOT WAP output directly |
| Coastal storm (#5) | INSUFFICIENT-DATA | no storm event in window |

### STP-WAP (STPWAP39_1)
| Lens (hypo rank) | Verdict | Evidence |
|---|---|---|
| Element decode | CONFIRMED | REPORTED_NAME "STP-WAP 345KV" |
| Parallel-path / N-1 outage (#1) | CONFIRMED | DWPWFWP5 dominant (WAP parallel), DBLBYWF5=Blessing. 2025-05-14 active: WAP 345 breakers, STP JS01/02 + STP-ANGSTROM, **Hillje 345kV out since 2024** (chronic parallel coastal path) |
| STP output + south/coastal injection (#2) | **CONFIRMED (clean mechanism)** | STP units SF **+0.195** (highest, source); South-TX units PEY/DAN/PLN +0.16; **WAP units NEGATIVE SF −0.08..−0.14 = sink/relief** |
| Houston load (#3) | CONFIRMED | P(bind) 1%→64% monotone across COAST-load deciles |
| Temperature (#4) | CONFIRMED | Galveston temp deciles 8-9 → 69-86%; Aug-2023 heat = max λ $828 |
| Coastal storm (#5) | INSUFFICIENT-DATA | no storm event isolated |
| South-solar/coastal-wind injection | PARTIALLY-CONFIRMED | SF mechanism + midday binding component support; zonal coastal-renewable actual output NOT isolated as quantitative driver |

## Key surprises / refinements vs hypothesis
1. **MDO-PHR is a 2025 regime-change constraint** — zero DAM binding before 2024-10, then heavy. Outage driver is clearly #1 (its existence is outage-conditioned), and its strongest binding is SPRING (outage season), not summer peak.
2. **MDO-PHR supply driver = coastal-SW injection (Dow/BESS/solar), not WAP output.** Hypothesis implied PHR-area local-gen deficit; mechanism is injection-side loading from the SW.
3. **W.A. Parish generation RELIEVES STP-WAP (negative SF).** Parish is the sink end, not a co-source. Hypothesis treated Parish mostly under MDO-PHR.
4. **STP-WAP has two distinct regimes**: heat/load-driven (Aug-2023, few outages, max λ) vs outage-driven (May-2025, heavy WAP/STP/Hillje outages). Temperature curve shows the dual mode (high at both temp extremes).
5. Dual-driver fingerprint visible in temp-decile curves (U-then-rise) and hour-of-day (MDO midday solar+AC; STP later load/import peak).

## Still unconfirmed / why
- Coastal storm-forced-outage lens (both, rank #5): no hurricane/storm in validation window.
- Zonal coastal-wind / south-solar actual injection as quantitative driver: only indirect (shift factor + HE profile). Needs per-resource 60-day SCED gen or zonal renewable actuals joined to binding.
- Contingency→element membership (which exact lines are inside DWAP_OB5 / DWPWFWP5 / DBLBYWF5): see CONTINGENCY MEMBERSHIP section below — partly resolved; explicit member-list join is NOT in the datalake.

---

# CONTINGENCY → ELEMENT MEMBERSHIP (2026-06-09, real datalake metadata)

Script: `shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts/contingency_membership.py`.
Tables: `metadata/objects/{contingency,facility,objectrelationships,station}.csv.gz` (these are HEADERED, unlike the
data files). REAL data only.

## Join-key verification (CONFIRMED)
- DA constraint file `CONTINGENCYID` == `contingency.csv.gz` `OBJECTID`. Verified on known cases:
  DWAP_OB5=10000764081, DPHRCTR5=10000799443, DWPWFWP5=10016987455, DBLBYWF5=10017083050 — all match the
  CONTINGENCYIDs seen binding MDOPHR99_A / STPWAP39_1.
- DA constraint file `FACILITYID` == `facility.csv.gz` `OBJECTID` → resolves the **monitored element** exactly.

## Monitored elements (CONFIRMED, exact)
| Constraint | FACILITYID | Monitored line | From → To | kV |
|---|---|---|---|---|
| MDOPHR99_A | 10002409705 | MDO-PHR 345KV | MEADOW (HOUSTON) → PH ROBINSON (HOUSTON) | 345 |
| STPWAP39_1 | 10002923616 | STP-WAP 345KV | SOUTH TEXAS PROJECT (SOUTH) → WA PARISH (HOUSTON) | 345 |

Confirms element decode mechanically: MDO=MEADOW, PHR=PH ROBINSON, STP=SOUTH TEXAS PROJECT, WAP=WA PARISH (all real ERCOT stations, HOUSTON/SOUTH zone).

## Contingency MEMBER element lists — **INSUFFICIENT-DATA (not in datalake)**
- `objectrelationships.csv.gz` has 16 RELTYPEs (FACILITY2BASEFACILITY, LMPBUSNODE2STATION, UNIT2PLANT, …) but
  **NO CONTINGENCY2* relation**. Rows referencing any of the 8 contingency OBJECTIDs = **0**.
- `contingency.csv.gz` is name-only (OBJECTID, ISO, CONTINGENCYNAME, TIMEZONE, STATUS) — no member list.
- ⇒ ERCOT's NMMS/CIM contingency-definition (the element list that goes OUT) is **NOT shipped** in the Yes Energy
  datalake. The literal "objectrelationships membership join" the task targeted does not exist here. Do not guess
  full member lists.

## Best-effort decode from contingency NAME tokens (LABELED inference, partial)
Two contingency codes map cleanly to a facility circuit-designation suffix (high confidence):
| Contingency | Decodes to (single line) | Verified facility |
|---|---|---|
| DOASWAP5 (MDO-PHR, 117h) | **OASIS → WA PARISH 345kV** | OAS-WA PARISH 345KV OASWAP99 |
| DKG_NB_5 (MDO-PHR, 415h) | **KING REIT → NORTHBELT 345kV** (Houston N loop) | KG-NB 345KV KG_NB_97 (token also reused on CDHSW-DESSW / GBY-SDN — mild ambiguity) |

The remaining six are **composite / breaker-/bus-defined** contingencies whose code is NOT a facility circuit token
(searched FACILITYNAME/EQUIPMENTID/SEGMENTID = 0 hits). Only the leading STATION token is decodable:
| Contingency | Lead station (decoded) | Best-guess primary equipment (NOT datalake-confirmed) |
|---|---|---|
| DWAP_OB5 (MDO-PHR, 1238h, dominant) | WAP = WA PARISH | WA Parish 345 bus/breaker section ("_OB") N-1 |
| DPHRCTR5 (MDO-PHR, 642h) | PHR = PH ROBINSON | PH Robinson 345 bus/circuit ("CTR") N-1 |
| DWPWFWP5 (STP-WAP, 1749h, dominant) | WP≈WHITEPOINT / WA Parish, WF=coastal wind | STP/WhitePoint coastal-corridor element; "WP" sink-end |
| DWPWFCK5 (STP-WAP, 79h) | same WP/WF family | sibling of DWPWFWP5 |
| DBLBYWF5 (STP-WAP, 145h) | BLY = **BLESSING** (confirmed station; BLY-WAP/BLY-HLJ 345 lines exist) | Blessing coastal path N-1 |
| DSTPREF5 (STP-WAP, 39h) | STP + REF = **REFUGIO** (STP-REF 345kV REFSTP27 exists) | **likely STP–Refugio 345kV line — CORRECTS earlier "STP refuel" guess** |

## Corridor topology pulled (CONFIRMED facilities, for mechanism/feature use)
- WA PARISH 345 outlets: STP-WAP (monitored), OAS-WAP, BI-WAP (Bellaire), BLY-WAP (Blessing), HLJ-WAP (Hillje).
- STP 345 outlets (parallels to STP-WAP): STP-ANGSTROM, STP-ELMCREEK, STP-HLJ, STP-BLESSING, STP-DOW, STP-JCK,
  STP-REF, STP-WHITE_PT, STP-G6, STP-MAT, STP-STATIC. Loss of any high-flow STP outlet shifts STP gen onto STP-WAP.
- Coastal parallels (matter for binding): BLU-HLJ 345 (BLUHLJ72), BLY-HLJ 345, HLJ-WAP 345, STP-ELMCREEK 345 (STPELM27), ELMCREEK-MARION/SKYLINE/SANMIGUEL/HILLCTRY 345.

## Cross-check vs actuals (CONSISTENT — no contradiction)
- 6/8 case active outages (BLU-HLJ 345, STP-ELMCREEK 345, STP JS03/04, HLJ JS05/06) are all CONFIRMED real
  facilities/stations here. Binding contingencies that day = DWAP_OB5+DPHRCTR5 (MDO-PHR), DWPWFWP5 (STP-WAP).
  Mechanism is internally consistent: pre-existing coastal-parallel OUTAGES (Hillje/Blessing/ElmCreek paths) weaken
  the corridor, then the studied N-1 on WAP/PHR/STP equipment overloads the monitored MDO-PHR / STP-WAP line. The
  contingency MEMBERS are *different* elements from the coincident planned outages — exactly how post-contingency
  constraints work.
- May-2025 actuals (WAP 345 breakers out, STP-ANGSTROM out, Hillje out since 2024) align with the WAP-bus / coastal
  contingency families binding MDO-PHR & STP-WAP.
- High-|SF| story holds: STP source (+0.195) + a parallel-STP-outlet contingency (ELMCREEK/HLJ/BLESSING/ANGSTROM,
  all confirmed STP outlets) → flow shifts onto STP-WAP. WA Parish gen NEGATIVE SF = sink-end relief, consistent with
  WAP being the TO-station of both monitored lines.

## What this lets us do MECHANICALLY now
- **Binding event → equipment linkage (partial, deterministic where possible):** for any binding hour we read the DA
  `CONTINGENCYID`, map to contingency NAME (verified join), and for DOASWAP5/DKG_NB_5 name the exact outaged line;
  for the WAP/PHR/STP/BLESSING/REFUGIO families we name the lead station/equipment and the corridor it sits on.
- **Outage→binding correlation is now keyed:** the confirmed corridor facility list (WAP/STP outlets + Hillje/Blessing/
  ElmCreek parallels) is the exact watch-list to join `transmission/outages/actual/` against — an outage on any of these
  + a same-corridor contingency binding = the equipment-out signature.
- **Stage-2 feature:** encode per-constraint (lead-contingency-station, corridor-membership-onehot, count-of-corridor-
  parallels-out) rather than relying on a CIM member list we don't have.

## Surprises / mismatches
1. **No contingency-membership table exists in the datalake** — the highest-value piece (full element list per
   contingency) must come from ERCOT NMMS/CIM directly, not Yes Energy S3. Flagged INSUFFICIENT-DATA, not guessed.
2. **DSTPREF5 likely = STP–REFUGIO 345kV line, not "STP refuel outage"** (STP-REF 345KV REFSTP27 is a real line). Prior
   note's reactor-refuel reading is probably wrong; treat as STP–Refugio coastal outlet contingency.
3. DKG_NB_5 token "KG_NB_97" is reused on three 345 facilities (KING REIT–NORTHBELT, CEDAR HILL–DESOTO, GREENS
   BAYOU–SHELDON); for a Houston MDO-PHR contingency the KING REIT–NORTHBELT (literal "KG-NB") reading is most
   plausible but not unique.
4. Only 2 of 8 binding contingencies are auto-named single lines; the dominant ones (DWAP_OB5, DWPWFWP5) are composite
   — meaning a clean "one contingency = one line out" feature would mis-model the two most important cases.

---

## 2026-06-08 case (daily lookback, real datalake)
Script: `shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts/case_2026_06_08.py`. All slices reachable (DA/RT/outage/load/wx).
- **Both bound strongly, midday.** MDO-PHR DAM HE9-21 (peak HE15 λ$79, λ med $28), STP-WAP DAM HE12-19 (peak HE16 λ$31). RT/SCED far hotter: MDO-PHR 172 intervals peak 14:00 λ**$484** (flow=limit 1272), STP-WAP 113 intervals peak 14:45 λ**$400** (flow=limit 1286). Big RT>>DA gap.
- **Contingencies (decoded via CONTINGENCYID, DA text blank):** MDO-PHR = DWAP_OB5 (12h) + DPHRCTR5 (11h); STP-WAP = DWPWFWP5 (8h). Exactly the validated top contingencies for each. All post-contingency N-1.
- **Outages:** parallel coastal 345 paths OUT — BLU-HLJ 345 + HLJ JS05/06 (planned, since 05/15/2026), STP-ELMCREEK 345 (since 05/19), STP JS03/04 345 DSC (since 05/11). Hillje parallel out again (fresh planned ticket, not the 2024 chronic one). No base-case WAP/PHR/Meadow 345 line out → MDO-PHR is pure post-contingency load-pocket binding.
- **Load/temp:** COAST peak HE17 20,238 MW (daily mean 17,124) — solid summer load; Galveston max 86F, Hobby/Victoria 90F — upper-decile warm but NOT a heat-wave. Midday-weighted binding ⇒ south solar + AC loading corridor (qual; renewable MW not pulled).
- **Verdict:** outage-driven regime (Hillje + STP-ELMCREEK 345 parallels out) on a moderately hot summer-load midday — NOT heat-driven. Matches validated driver story (STP-WAP parallel-path #1 via DWPWFWP5; MDO-PHR load-pocket post-contingency via DWAP_OB5/DPHRCTR5). New: STP-ELMCREEK + STP JS03/04 add source-side STP-outlet reduction not isolated in validation; Hillje out via fresh 05/15 ticket. RT λ 6x DA confirms real-time tightening typical of outage-constrained corridor.

## CONGESTION_PROJECT stage-progress implication
- This validation exercised live slices of Stage 0 tasks 0.2 (metadata), 0.3 (DA constraints), 0.5 (SCED shift factors), 0.11 (outages), 0.15 (weather) + load — proving the **datalake-only Stage 0 plan is viable end-to-end** (S3 reachable, schemas headerless→ddl order, real data).
- Feeds Open Decision "initial constraint subset for Stage 1": these 2 Houston constraints are good Stage-1/2 candidates.
- **Constraint-embedding design impact (Stage 2)**: must include binding-ONSET / active-outage / contingency-membership features — static 365d historical-binding stats would have completely missed MDO-PHR (it had none pre-2025). Regime-change handling is not optional for this corridor.

---

# CONTINGENCY → ELEMENT MEMBERSHIP — Step 1 (authoritative) + Step 2 (empirical), 2026-06-09 run

**Goal of this run:** finish the contingency→element membership. Try ERCOT authoritative source first; fall back to
empirical outage→binding matching. Scripts: `shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts/outage_binding_lift.py`
(+ cached panel `derived/outage_panel_345_houston_south.parquet`). REAL data only.

## STEP 1 — Authoritative source: IDENTIFIED but NOT programmatically reachable with our access
- **The data product = ERCOT CRR Auction Network Model "Contingencies" file** (the per-contingency element list),
  shipped each auction cycle as part of the CRR Network Model bundle (Mapping Documents + Contingencies + Monitored
  Elements + Sources/Sinks). This is the canonical contingency definition; ERCOT aligned CRR/MMS contingency defs to
  the EMS/NMMS-CIM defs so all systems share one membership list.
- **Posting / access:** **MIS Secure Area + CRR Market User Interface (MUI)**. Audience = "CRR Account Holders".
  Posted 10 business days before each Monthly Auction (20 before Long-Term). Format = zip (CSV + xlsx mapping docs).
  Confirmed via market notices M-C010926-01 (Jan-2026), M-B031925-01, M-A080725-01.
- **Reachability with our credentials = NO.**
  - Yes Energy datalake: confirmed absent (this file is not mirrored; only name-only `contingency.csv.gz`).
  - ERCOT Public API (`skills/fetch-ercot-data` §4): serves **public** reports only; CRR Network Model is Secure-Area.
    (NP7-430-M is *public* but it is the **PCRR Eligibility List**, NOT contingencies — checked, wrong product.)
  - No NDA/cert path in our stack. Could not retrieve. Did NOT fabricate.
- **What Minsu needs to obtain it:** an ERCOT Market Participant account with the **CRR Account Holder** role + a
  valid **digital certificate (USCERT)** to log into the MIS Secure Area / CRR MUI, then download the monthly
  "CRR Network Model – Contingencies" zip. (Alternative authoritative copies — EMS Network Operations Model / SSWG
  planning cases — are CEII/NDA-restricted, heavier lift.) Once pulled, that file gives the exact element set per
  `DWAP_OB5 / DPHRCTR5 / DWPWFWP5 / DBLBYWF5 / …` and ends the INSUFFICIENT-DATA flag above.

## STEP 2 — Empirical fallback (this is what produced the final answer this run)
Method: day-level panel 2023-01-01..2026-06-08 (1253 outage-days, REAL `transmission/outages/actual/` midday snapshots,
KV≥345 & FROMZONE∈{HOUSTON,SOUTH} = the import corridor, 3,795 distinct facilities, 418k facility-day rows) joined to
DA day-level binding. Metric = **seasonality-adjusted lift** = days_out_bind / Σ(month-of-year base rate on out-days).
Raw flat-base lift is rejected as the headline (binding is strongly seasonal → flat lift just rewards being out in
summer; verified: co-active corridor outages are actually *fewer* on binding days, 273 vs 354 for STP, 383 vs 430 MDO).

**Big structural finding (limits the method):** the contingency LEAD-stations are *chronically partially out* —
WA PARISH out 740/1253 d, STP 824, HILLJE 1130, OASIS 746, WHITEPOINT 999 — so "station has a 345 outage" is
**uninformative** (seas_lift≈1.0). The true contingency members are *simulated N-1s, not real outages*, so outage
co-occurrence cannot recover the NMMS member list. STEP 2 yields a **weakening-outage signature** (which real outages
leave the corridor exposed so the studied N-1 overloads), which is a *different object* than membership — the practical
proxy, explicitly not the authoritative set.

### STP-WAP (STPWAP39_1) — seasonality-adjusted outage→binding lift (base P(bind/day)=0.247, summer Jun-Aug 0.61-0.67)
| Outaged facility (345kV) | zone | out-days | co-bind | P(bind\|out) | seas_lift | robustness |
|---|---|---|---|---|---|---|
| OBRIEN F210/F220/F470 brkr | HOUSTON | 27-30 | 17-18 | .59-.63 | 4.3-4.4 | spans 2023-26, small-n |
| OBRIEN F215 DSC / AT3H xfmr | HOUSTON | 39 | 19 | .49 | 3.6 | multi-yr |
| LYTTON SPRINGS AT2H xfmr | SOUTH | 67 | 20 | .30 | 3.2 | multi-yr |
| FAYETTE PLANT 1 (9T210/GCB/DSW) | SOUTH | 50-52 | 16 | .31-.32 | 3.0 | multi-yr |
| **HILLJE B560 brkr** | SOUTH | 33 | 10 | .30 | 2.85 | **validates chronic-parallel mechanism** |
| HUTTO 10380 brkr/DSC | SOUTH | 58 | 21 | .36 | 2.6 | multi-yr |
| BRISITA SERDEV1 | SOUTH | 33 | 20 | .61 | 2.6 | **2025-only — single-episode, discount** |
| JEANETTA AT1 xfmr | HOUSTON | 46 | 15 | .33 | 2.55 | — |
Interpretation: discriminating real-outage signature = south/south-central injection-corridor (LYTTON SPRINGS, FAYETTE,
HUTTO near Austin/La Grange) + a specific HILLJE breaker + Houston-area O'BRIEN. Loss of a parallel south/coastal path
shifts flow onto STP-WAP — consistent with validated driver #1. Counts are small (16-21 co-bind); treat as directional.

### MDO-PHR (MDOPHR99_A) — WEAK / SATURATED (base P(bind/day)=0.569 in 2025+; May-Jul 0.94-1.0)
Binds on the majority of in-season days regardless of which corridor element is out → outage presence barely
discriminates; max seas_lift only ~1.5-1.9. Top (all modest, multi-yr): WHITE OAK (224d, lift1.75), RIO NOGALES,
DEER PARK ENERGY, CENTER, HORNSBY (Austin), CEDAR BAYOU PLANT, TOMBALL. **Conclusion: MDO-PHR is a structural
in-season load-pocket constraint, not outage-discriminated** — its 2025 existence is the regime signal, not any single
parallel outage. (Matches earlier finding: MDO-PHR is a 2025 regime-change constraint.)

## Method that produced the final answer + residual uncertainty
- **Final answer source = STEP 2 (empirical), because STEP 1 is access-blocked.** The authoritative element set per
  contingency remains **INSUFFICIENT-DATA** pending the Secure-Area CRR Network Model pull.
- **Residual uncertainty = HIGH and named:** (1) co-occurrence ≠ causation; (2) the empirical signal is a weakening-
  outage signature, NOT the contingency member list; (3) lead-stations chronically out → method blind to true members;
  (4) small co-bind counts (10-21) and some single-episode facilities (BRISITA 2025-only); (5) MDO-PHR essentially
  undiscriminated. Use the STP-WAP lift table as a corridor watch-list / Stage-2 feature, not as ground-truth membership.
- **Stage-2 feature takeaway (updated):** do NOT use "lead-station-has-outage" (uninformative — chronic). DO use
  specific-equipment outage flags for the south/south-central injection corridor (LYTTON SPRINGS, FAYETTE, HUTTO,
  HILLJE-specific-breaker, OBRIEN) + month-of-year seasonal base. Authoritative membership still requires the CRR
  Network Model file.

---

# OPERATIONAL THRESHOLDS — per-factor binding triggers (2026-06-09 run)

**Goal:** turn validated drivers into operator-usable numeric breakpoints. REAL data only.
Scripts: `shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts/build_threshold_panel.py` (panel) +
`thresholds.py` (binning). Derived: `derived/threshold_panel_2023_2026.parquet` (30,116 hourly rows, full
load/wind/solar coverage, 94% Galveston temp) + `derived/trigger_tables.json` (all binned P(bind)+λ tables).

**Method:** hourly panel 2023-01-01..2026-06-08 = COAST-zone load (WZ 10002211345) + Galveston/Hobby/Victoria
drybulb + **regional renewable ACTUALS** + DA binding flag/λ per constraint. Fixed-width bins → conditional
P(bind|bin) + median/P90 λ|bind. "on" breakpoint = first bin (n≥30) where P(bind) ≥ max(2×base, 20%);
"strong-λ" = first bin where median λ ≥ 2× global binding median (MDO $8.2→$16.4, STP $20.3→$40.6);
λP90-cross = first bin where per-bin λ-P90 ≥ global λ-P90 (MDO $42.8, STP $111.5).

**NEW DATA UNLOCK (upgrades prior INSUFFICIENT/PARTIAL flags):** regional renewable actuals ARE reachable —
`gen/wind_rti` has geographic-region objects **GR_COASTAL (10004189446)** + **GR_SOUTH (10004189447)**;
`gen/generation_solar_rt` has **SouthEast solar region (10017006228)**. (OBJECTID→name via `metadata/objects/all.csv.gz`.)
So coastal/south wind + south solar are now QUANTIFIED, not just shift-factor-inferred.

## MDO-PHR (MDOPHR99_A) — 2025+ regime is the usable population (pre-2025 ≈ zero binding)
Base P(bind): **2025+ all-hrs 17.0%, 2025+ summer 31.0%**.
| Factor | "on" breakpoint | strong-λ threshold | P(bind) below→above | cond. median λ (P90) | n | confidence |
|---|---|---|---|---|---|---|
| **COAST load (MW)** | **≥17,000** (35%) | ≥19–20,000 | <14k:<14% / 15–17k:19–26% / 17–19k:35–43% / 19–21k:64–72% / >21k:81% | $13–23 ($50–90) | 12,575 | **HIGH** (monotone) |
| **Galveston temp (°F)** | **≥85°F** (65%) | ≥80°F | <75:<11% / 80–85:24% / 85–90:65% / >90:88% | $16 ($53–83 @80–85) | 11,900 | **HIGH** (hot mode); minor cool-shoulder floor (outage-driven dual mode) |
| South solar SE (MW, HE12-19) | ≥1,000–1,500 (33–40%) | ≥1,000 (λP90) | 0–250:1% / 500–1000:21% / 1000–1500:33% / >2500:54% | $10–14 ($43–68) | ~3.4k | **MEDIUM** (confounds w/ load+hour; monotone after peak-hr cut → supports SW-injection-loads-pocket mechanism) |
| Coastal wind (MW, HE12-19) | ≥750 (35%) | — | 0–250:22% / >2000:48% | $8–15 ($45–58) | ~3.4k | MEDIUM-LOW (weak, saturates in summer) |
| South wind (MW, HE12-19) | ≥500 | ≥2,000 | 0–500:26% / 1500–2000:56% | $16–17 ($69–73) | ~5k | MEDIUM |
Summer-only shifts: load "on" → ≥19,000 (66% @19–20k), temp ≥85°F → 69%.

## STP-WAP (STPWAP39_1) — full 2023-2026 + summer
Base P(bind): **all-yr 6.2%, summer (Jun-Aug) 16.6%**.
| Factor | "on" breakpoint | strong-λ threshold | P(bind) below→above | cond. median λ (P90) | n | confidence |
|---|---|---|---|---|---|---|
| **COAST load (MW)** | **≥19,000** annual / **≥20,000** summer (42%) | ≥21,000 (med $47.5, P90 $151) | <14k:~0% / 16–17k:8% / 18–19k:17% / 19–20k:29% / 20–21k:42% / 21–22k:59% | rises to $48 ($151) | 30,116 | **HIGH** |
| **Galveston temp (°F)** | **≥85°F** (27%) | **≥90°F** (med $41–44, **P90 $269–292**) | <80:<5% / 80–85:5% / 85–90:27% / 90–95:51–54% | $28→$44 | 30,116 | **HIGH** (heat-wave extreme-λ mode = Aug-2023) |
| **South wind (MW, HE12-19, summer)** | **≥500–1,000** (37–51%) | ≥1,500 (med $42, P90 $214) | 0–500:15% / 500–1000:37% / 1000–1500:51% / 1500–2000:72% | $23→$42 | ~2.3k | **HIGH** — cleanest renewable; CONFIRMS injection driver #2 quantitatively |
| **Coastal wind (MW, HE12-19, summer)** | **≥1,000** (36%) | λP90≥2,000 ($123) | 0–250:7% / 1000–1500:36% / 1500–2000:45% / >2000:63% | $19→$32 | ~2.3k | **HIGH** |
| South solar SE (MW, HE12-19) | non-monotone | — | 0–250:64%(n=14!) / 1000–1500:26% / >2500:70% | noisy | ~2.6k | **LOW — CONFOUNDED** (no-solar bin = late-afternoon peak-load hrs; wind is the clean injection signal, not solar) |

## Outage trigger (categorical, folded from STEP-2 lift; day-level)
- **STP-WAP** — specific south/coastal corridor element OUT lifts P(bind/day) well above base (0.247 annual / 0.61 summer):
  OBRIEN F210/F220/F470 brkr .59–.63 (lift 4.3, small-n) · OBRIEN F215 DSC .49 (3.6) · LYTTON SPRINGS AT2H .30 (3.2) ·
  FAYETTE PLANT-1 .31 (3.0) · HILLJE B560 brkr .30 (2.85) · HUTTO brkr .36 (2.6). Use as corridor watch-list, NOT membership.
- **MDO-PHR** — outage-UNDISCRIMINATED (structural in-season load pocket; max seas-lift only 1.5–1.9). The 2025-regime
  *existence* is the signal, not any single parallel outage.

## Combined rules of thumb (operational read)
- **STP-WAP**: *summer + COAST > 19–20k MW + (Galveston ≥ 90°F OR south wind > 1.5 GW HE12-19) + a south-corridor
  345 element out (OBRIEN / LYTTON SPRINGS / FAYETTE / HILLJE)* ⇒ **P(strong bind) ≈ 60–85%, median λ $40–48, P90 $150–270.**
  Single most predictive trio: COAST load, Galveston ≥90°F (extreme-λ), south wind.
- **MDO-PHR**: *2025+ regime + COAST > 17k MW (summer > 19k) + Galveston ≥ 85°F + midday south solar > 1.5 GW* ⇒
  **P(bind) ≈ 50–75%, median λ $13–23, P90 $50–90.** Post-contingency N-1 is always studied so outage is non-discriminating here.

## Honesty / caveats
- **Post-contingency interaction:** both constraints bind only as N-1; the standing N-1 study is always active in DAM, so
  the load/temp/wind thresholds are effectively *conditional on the enabling contingency set* — they ARE the usable trigger.
  A continuous threshold conditioned on a *specific real outage being present* was NOT built: the outage panel is day-level
  and corridor lead-stations are chronically partially out (uninformative, per STEP-2). Use the categorical outage table for that.
- **Confounding:** wind/solar/load/hour co-vary. Renewable bins are computed within HE12-19 (binding window) to de-confound;
  even so, treat MDO coastal-wind and STP south-**solar** as confounded/directional (solar's "no-solar high-P" bin is a
  late-afternoon-peak-load artifact). South/coastal **WIND** for STP survives conditioning cleanly = real driver.
- **Small-n flags:** MDO summer renewable bins (n 40–100), STP solar 0–250 bin (n=14), wind >3000 MW bins. Directional only.
- **Leakage / operationalization:** thresholds are fit on ACTUALS. For a leakage-clean D+1 trigger feed the *forecast vintages*
  available before 10:00 CT cutoff — COAST load_forecast_wz, wind WGRPP SOUTH_HOUSTON (10000821210), solar STPPF — into the
  SAME MW/°F breakpoints. The breakpoint levels carry over; only the input source changes.

---

# RT SHADOW PRICE + SEASONALITY (2026-06-09 run) — RT energy-trading priority

**Goal:** add the RT/SCED shadow-price view (prior stats were DA-centric) + month×hour seasonality, for RT energy
positions. REAL data only. Scripts: `scripts/scan_rt_full.py` (full RT history scan) + `scripts/analyze_rt_da_seasonality.py`.
Derived: `derived/rt_binding_mdophr_stpwap.parquet` (51,103 raw RT rows) + `derived/seasonality_month_hour_matrices.json`
(8 grids: 2 constraints × {DA,RT} × {p_bind, median_λ}, each 12-month × 24-hour, dashboard-ready).

## Method / definitions
- RT source = `ercot/transmission/constraints/rt/{yyyymmddhh}.csv.gz` (NP6-86-CD SCED 5-min). Full window scanned:
  2023-01-01 00 → 2026-06-08 23 = 30,120 hourly files. CONFIRMED RT (5-min SCED timestamps, flow=limit at peaks), not DA.
- **BINDING = PRICE>0.** The RT rt/ file lists monitored/active constraints incl. PRICE==0 (slack, not actually binding);
  DA file lists priced rows only. Of 51,103 RT rows, only 15,587 have PRICE>0 — the rest (35,516) are listed-but-slack
  and are NOT binding. Using all rows would falsely report RT median λ=$0. **Filter PRICE>0 for any RT binding stat.**
- $4500 = ERCOT max transmission shadow-price cap (scarcity). STP-WAP RT hits exactly $4500 in 203 intervals; MDO-PHR
  >$1000 in 8. Genuine RT scarcity tail, not a data error.
- RT P(bind) denominator = days_in_window_bucket × 12 (≈12 SCED/hr). Hour = DATETIME hour == ERCOT HE (DA peak hr14==HE14).
- CONTINGENCY text blank in YE rt/ variant (unchanged caveat; decode via DA CONTINGENCYID).

## RT vs DA side-by-side (2023-01-01..2026-06-08, binding = PRICE>0)
| Constraint | Mkt | binding (hrs / RT-equiv) | mean λ | median | P90 | P99 | max |
|---|---|---|---|---|---|---|---|
| MDOPHR99_A | DA | 2,596 h | $16.6 | $8.2 | $42.8 | $122.5 | $160.1 |
| MDOPHR99_A | **RT** | 5,361 intervals (~447 h) | $72.9 | **$36.8** | $164.9 | $569.3 | **$4500** |
| STPWAP39_1 | DA | 2,066 h | $47.0 | $20.3 | $111.5 | $412.3 | $828.6 |
| STPWAP39_1 | **RT** | 10,226 intervals (~852 h) | $195.6 | **$53.4** | $209.3 | **$4500** | **$4500** |

**Actionable gap (the whole point for RT energy):**
1. **RT λ materially exceeds DA when binding.** MDO median RT/DA 4.5×, P99 4.6×, max 28×. STP median 2.6×, **P99 10.9×
   (RT P99 = the $4500 cap vs DA $412), max 5.4×.** DA prices the constraint broadly at low λ; RT realizes the tail.
2. **RT binds FEWER hours than DA** (MDO ~447 vs 2,596; STP ~852 vs 2,066) but **much harder per event.** DAM SCED is
   conservative/proactive (prices the N-1 across many hours at single-digit λ); RT only binds when physically congested,
   then λ is several-fold higher and reaches the cap. ⇒ RT congestion P&L is event-driven + fat-tailed, not broad.
3. STP-WAP RT is the bigger RT prize: 852 binding-hrs, mean $196, and the cap repeatedly. MDO-PHR RT is spring-only & lower.

## Seasonality — month-of-year (P(bind); median λ | P90)
**MDO-PHR = SPRING (Apr-Jun), quantified.** DA P(bind): Apr 11.9% → **May 21.3% / Jun 21.0%** → Jul 13.6% → Aug 8.0%.
RT P(bind): **May 4.4% / Jun 4.2%**, Apr 2.7%. RT median λ peaks Apr-May ($46-80). Near-zero Nov-Feb. Spring = outage season.
**STP-WAP = SUMMER (Jun-Aug), quantified.** DA P(bind): **Jun 19.7% / Jul 20.1%**, Aug 16.3%. RT P(bind): **Jun 8.9% /
Jul 8.4%**. **Aug is the extreme-λ month** — RT Aug P90 = $4500 (the heat-wave scarcity regime, cf. Aug-2023 max). Near-zero Dec-Mar.
⇒ Two different seasons: trade MDO-PHR RT congestion Apr-Jun, STP-WAP RT congestion Jun-Aug (Aug for the tail).

## Seasonality — hour-of-day (HE == DATETIME hour)
**MDO-PHR midday-early: DA peak HE12-17 (max HE14 25.7%), RT peak HE13-16 (max HE15 5.3%).** RT median λ peaks HE15 ~$52.
**STP-WAP midday-LATE: DA peak HE15-18 (max HE17 23.7%, λ climbs to $34), RT peak HE13-17 (max HE15-16 ~10%), RT λ keeps
climbing through afternoon (HE16 $75.8).** Confirms validated mechanism: **MDO earlier (solar+AC pocket loading), STP
later (load/import peak).** Both dead outside HE08-19 (RT effectively zero overnight). RT congestion is a daytime-only play.

## Month × hour matrices (KEY DELIVERABLE)
`derived/seasonality_month_hour_matrices.json` — `{meta, grids:[{constraint, market, metric, rows:"month_1_12",
cols:"hour_0_23", matrix[12][24]}]}`. Drives heatmaps directly. The bright cells: MDO-PHR ≈ (Apr-Jun)×(HE11-17);
STP-WAP ≈ (Jun-Aug)×(HE13-18), with the Aug×afternoon cells carrying the $4500 RT tail.

## Caveats
- RT P(bind) assumes ~12 SCED intervals/hr for the denominator (standard; flagged). λ stats use actual PRICE>0 rows (exact).
- $4500 cap compresses RT P99/max for STP-WAP (both = cap) — the true uncapped severity is unobservable; report as "hits cap".
- 2023-24 MDO-PHR RT is tiny (23/27 intervals) — consistent with the 2025 regime-onset finding; MDO RT stats are effectively 2025+.
- CONTINGENCY blank in rt/ (unchanged); RT here is λ/frequency/seasonality only, not RT contingency attribution.
