# GKS Cluster E deep-dive — GTC interfaces VALEXP + WESTEX

**Created**: 2026-06-09 | **Author**: congestion-analyst | **Status**: COMPLETE (Step-2 list confirmed by Minsu)
**Scope**: full deep-dive of 2 Generic Transmission Constraints (interfaces, NOT single physical lines) impacting GKS_BESS_RN.
**Data**: REAL Yes Energy Datalake (S3 `yedatalake`). Window 2024-07-03 → 2026-06-08 (~23 mo, GKS node lifetime).
**Code**: `shared/data/adhoc/2026-06-09_gks-congestion-impact/scripts/deepdive_clusterE_gtc.py`
**Derived**: same folder `/derived/clusterE_*.json`, `clusterE_hourly_panel.parquet`
**Sign convention**: impact($/MWh) = −SF×λ. Pos = raises GKS LMP (discharge-favorable), Neg = lowers (charge-favorable).

## Identity (datalake metadata `objects/{facility,interface,contingency}.csv.gz`)
- **VALEXP** = RTI 345kV, FACILITYTYPE=RTI, NORTH EDINBURG (SOUTH) → LON HILL (SOUTH). Valley Export interface = part of ERCOT Greater Valley Area GTC family (7 of 16 ERCOT stability GTCs are in the LRGV). Interface objectid 10016657233 ("Valley Export").
- **WESTEX** = RTI 345kV, RILEY (WEST) → KRWSW (NORTH). West Texas Export GTC (live since 2020-10-01; the single largest ERCOT GTC, ~36GW wind behind it). Interface objectid 10016469330 ("West Texas Export").
- **BOTH bind in CONTINGENCYNAME = "BASE CASE"** (contingency 10000756754) → pre-contingency / steady-state stability limits, NOT N-1. Key distinction from the N-1 Houston corridor constraints.

## Cross-check (task-requested, PASSED)
`market_shift_factors` RT SHADOWPRICE == `transmission/constraints/rt/` PRICE, verified at VALEXP 2025-04-07 06:50 → both = 3551.898. (rt/ files are hour-ENDING keyed: file ...HH holds (HH-1):00–(HH-1):55.) RT VALUEMW≈LIMITMW (794.7≈794.8) confirms interface pinned at limit when binding. RT method validated.

## Binding stats (23 mo)
| GTC | Mkt | bind-hrs | dist-days | λ med | λ P90 | λ P99 | λ max | mean|SF| | cum $ |
|---|---|---|---|---|---|---|---|---|---|
| VALEXP | DA | 1211 | 180 | 1.72 | 7.8 | 32.6 | 646.6 | 1.000 | −4,930 |
| VALEXP | RT | 358.5 | 128 | 16.6 | 83.8 | 219.3 | 4304 | 0.979 | −13,004 |
| WESTEX | DA | 2519 | 281 | 5.9 | 16.2 | 25.0 | 37.8 | 0.048 | −908 |
| WESTEX | RT | 1314.5 | 240 | 15.1 | 28.4 | 50.5 | 168.5 | 0.150 | +3,099 |

**Cum $ per 1 MW continuous position over 23 mo**: VALEXP −$17,934 (charge-favorable, DA+RT same sign). WESTEX net +$2,191 — but **DA & RT flip sign** (see below).

## WESTEX DA/RT sign-flip (FLAG — actionable)
DA and RT enforce DIFFERENT representative elements of the same GTC:
- DA facility 10016496336 = CLEARCRO→WILLOW CREEK (WEST internal), GKS SF **+0.048** → small charge-favorable (−$908).
- RT facility 10016463813 = RILEY→KRWSW (WEST→NORTH), GKS SF **−0.15** → discharge-favorable (+$3,099).
- Net positive, RT dominates. **The discharge tailwind is RT-only**; DA WESTEX is ~neutral/slightly opposite. Do not assume a DA WESTEX discharge signal.
VALEXP has no such issue: DA SF=+1.000 (pseudo-line "- 0KV VALEXP"), RT SF≈+0.98 — both strongly charge-favorable.

## Seasonality / timing (RT)
- **VALEXP**: WINTER + spring. Dec −$3,753 / Jan −$2,041 / Nov −$1,548 + Apr −$2,831 spike; summer ~0. Hour profile **bimodal**: overnight HE2–6 (peak HE5=25h) + evening HE17–20 (HE18=23.8h); **midday trough HE10–16**.
- **WESTEX**: SPRING-heavy, steady most of year, **summer trough** (Jul−Sep ≈10–40 h/mo vs Mar−May ≈180 h/mo). Hour profile: overnight peak HE23–HE2 (HE24=71.5h) + midday secondary; morning trough HE4–7.

## Driver 5-lens
### VALEXP (Valley Export)
(a) **Export volume / net-load — CONFIRMED but INVERTED**: binds when SouthEast solar ≈ 0 (bind median 0 MW vs nonbind 32, nonbind-P90 2529) = overnight/evening, AND when GR_SOUTH wind is *moderate-low* (bind median 1023 vs nonbind 1281 MW). P(bind) DECREASES as GR_SOUTH wind rises (0.05 at <500MW → 0.014 at 2–3GW). Read: driver = **low Valley net-load** (load low + solar off) letting modest wind export north into the very low stability limit; high daytime solar locally absorbs and RELIEVES the interface. NOT a high-wind-surge story.
(b) **Binding limit — CONFIRMED, dynamic & low**: operator limit ranged 625→935→690→920→1075→**1140** MW over the window; 2026-02 Greater Valley GTC update (ERCOT enforced 2026-02-04) lifted it. Day-level limit also varies (e.g. 794.8 MW on 2025-04-07). The ~800–1140 MW limit is so low that modest net export binds it.
(c) Outages lowering limit — INSUFFICIENT (no element-membership/outage parse; limit-history captures net operator effect).
(d) Temp/load — CONFIRMED indirectly via winter-overnight low-load seasonality (no zonal load in datalake, system-only).
(e) Renewable regime — CONFIRMED: winter+spring; solar diurnal strongly modulates (midday relief).

### WESTEX (West Texas Export)
(a) **Export volume — CONFIRMED, STRONG**: West-basin wind (GR_WEST+GR_PANHANDLE) bind median **16.7 GW** vs nonbind **7.2 GW**; DA corr(λ, basin-wind)=+0.29; P(bind) ~0 below ~4GW bucket, jumps to **12–19%** in the >4GW (effectively >~14GW) regime. Classic high-West-wind export.
(b) **Binding limit — CONFIRMED, seasonal**: limit 10,630–11,810 MW; lower in spring/fall (e.g. 10,630 Apr-2025/Nov) coincident with peak binding.
(c) Outages — INSUFFICIENT.
(d) Temp/load — HYPOTHESIS: overnight low-load + high wind (not separable from wind signal here).
(e) Renewable regime — CONFIRMED: spring high-wind peak, summer wind trough.

## Operational thresholds (actionable for a Valley BESS)
- **VALEXP charge window**: solar-off hours (HE1–7, HE18–22) in Nov–May with low Valley load → high P(bind). Sharpened by low/uncertain GTC limit (≤~900 MW). Highest-value: Dec/Jan/Apr overnight & evening. (RT λ tail to $4304 = transmission shadow-price scarcity, rare.)
- **WESTEX discharge window (RT only)**: West-basin wind > ~14 GW (strongest >16–17 GW), spring (Mar–May) overnight/midday, when GTC limit is at the lower 10.6 GW seasonal setting. Modest magnitude (λ median $15, P99 $50).

## GTC CAVEAT (must flag in any forward use)
GTC limits are operator/seasonally adjusted from ERCOT Quarterly Stability Assessments + new-generation interconnections — NOT a fixed physical rating. VALEXP limit moved 625→1140 MW and WESTEX 10.6→11.8 GW within 23 months. Binding frequency/timing can shift step-wise with each ERCOT GTC parameter update (e.g. 2026-02-04 Greater Valley update). Any binding-probability model must treat the GTC limit as a time-varying feature, not a constant.

## Derived files
`derived/clusterE_binding_stats.json`, `clusterE_month_hour.json`, `clusterE_limit_history.json`, `clusterE_drivers.json`, `clusterE_hourly_panel.parquet`. Related: [[gks-node-identity]], [[houston-congestion-mdophr-stpwap]], plan `gks-congestion-impact.md`.
