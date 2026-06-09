# GKS_BESS_RN congestion impact — identification (Pos/Neg top-5, DA & RT, seasonal)

**Created**: 2026-06-09 | **Author**: congestion-analyst | **Status**: STEP 1 IDENTIFICATION ONLY (awaiting Minsu confirm before deep-dive)
**Scope**: rank the constraints with the largest cumulative congestion impact on GKS_BESS_RN, DA & RT separately, with monthly/seasonal breakdown. NOT a deep-dive (no driver/threshold/outage work yet).
**Data**: REAL Yes Energy Datalake (S3 `yedatalake`), not mock.
**Code/derived**: `shared/data/adhoc/2026-06-09_gks-congestion-impact/` (scripts + derived JSON/parquet).

## Method (verified before mass compute)
- **Node**: GKS_BESS_RN CONFIRMED = `price_node` OBJECTID **10017907494**, zone SOUTH, subtype GENERATOR
  (metadata `objects/all.csv.gz`). Great Kiskadee Storage, deep South Texas / Rio Grande Valley. Resource = GKS_BESS_ESR1.
- **Source = `transmission/constraints/market_shift_factors/{YYYYMMDD}.csv.gz`** (DDL via `.../market_shift_factors/ddl.json`).
  Cols: PRICENODEID, FACILITYID, CONTINGENCYID, DATETIME, TIMEZONE, **MARKET (DA/RT)**, **SHIFTFACTOR**, **SHADOWPRICE**, LIMIT, CONSTRAINTID, CONSTRAINTNAME, LOADID.
  This table **pre-joins pricenode SF × shadow price for BOTH markets** at the exact GKS price node — cleanest nodal-MCC source (CONGESTION_PROJECT §0.4 "DAM pricenode-level + SHADOWPRICE").
- **DEVIATION from task prescription (FLAG for Minsu)**: task asked RT = `ercot_sced_shift_factors` × `rt/` PRICE join.
  Instead used `market_shift_factors` MARKET='RT', because (a) it is pricenode-level at GKS_BESS_RN exactly (SCED SF is
  resource-level → needs resource→node mapping), (b) SF and λ already aligned, (c) only priced (binding) rows are
  listed so "RT binding = PRICE>0" is satisfied implicitly. SHADOWPRICE(RT) = SCED shadow price (same ERCOT feed).
  Recommend a sample cross-check vs `rt/` PRICE at deep-dive. SCED resource-level table remains the route for
  per-generator attribution later.
- **Fetch**: S3 **Select** server-side filter `WHERE _1='10017907494'` → only GKS rows (1.5s/day). Full window 1255 days scanned in 47s.
- **SIGN CONVENTION (verified)**: nodal MCC contribution of constraint k = **−SHIFTFACTOR(k→GKS) × SHADOWPRICE(λ_k)**
  (ERCOT MCC = −Σ SF·λ; CONGESTION_PROJECT.md L32). **Pos = RAISES GKS LMP (favors DISCHARGE)** ⇔ SF<0 (GKS relieves);
  **Neg = LOWERS GKS LMP (favors CHARGE)** ⇔ SF>0 (GKS aggravates). Verified on sanity case **VALEXP SF≈+1.0**
  (GKS export fully loads the Valley-export interface → impact negative → GKS priced down — correct ERCOT sign);
  relieving local lines (BURNS_HEIDLBRG SF−0.09) → positive. Magnitudes sane ($/MWh).
  (Full LMP-component reconstruction not done: `prices/bus_lmp` carries only total LMP, no MCC split — structural sign check used instead.)
- **Cum $ impact = time-weighted**: DA row = 1 h, RT row = 1/12 h (5-min). Units $/MWh·h (per 1 MW continuous position).

## Data window REALITY (FLAG)
GKS_BESS_RN first appears **2024-07-03**; window = 2024-07-03 → 2026-06-08 (~23 months), NOT 2023→. GKS BESS COD ≈ Jul-2024.
"Full available history" = full history of the node's existence. 1.26M binding constraint-intervals (RT 794k, DA 468k).

## RESULTS — Pos top5 / Neg top5 (sign as above)
### DA — POS (raise LMP / discharge-favorable)
| Constraint | Element | mean|SF| | cum $ | bind-hrs(rows) | bind-int | mean λ | peak season | top months |
|---|---|---|---|---|---|---|---|---|
| HAINE__LA_PAL1_1 | LA PALMA–HAINE DR 138 | .029 | +10,874 | 7207 | 5624 | $43 | Spring | Mar/Apr/Feb |
| 1710__C | BELCNTY–SALSW 138 | .025 | +9,814 | 1728 | 1698 | $225 | Summer | Aug/Oct/May |
| 421__A | BCESW–SNDSW 345 | .193 | +5,680 | 1182 | 932 | $24 | Spring | Apr/May/Nov |
| BLESSING_1382 | BLESSING 345 | .075 | +3,857 | 4171 | 4079 | $12 | Winter | Apr/Jan/Feb |
| 15060__B | VEALMOOR–KOCHTAP 138 | .008 | +2,872 | 4611 | 4610 | $78 | Fall | Sep/Oct/Aug |
### DA — NEG (lower LMP / charge-favorable)
| Constraint | Element | mean|SF| | cum $ | bind-hrs | bind-int | mean λ | peak season | top months |
|---|---|---|---|---|---|---|---|---|
| E_PASP | PAWNEE–CALAVERAS 345 (interface) | .244 | −56,360 | 4539 | 4539 | $54 | Winter | Jan(−20.5k)/Aug/Jul |
| LARDVN_LASCRU1_1 | LAREDOVNTH–LASCRUCE 138 | .083 | −24,070 | 4948 | 4020 | $53 | Summer | Jul/Aug/Apr |
| BRUNI_69_1 | BRUNI 138 | .013 | −10,343 | 4022 | 3249 | $182 | Spring | Apr/Dec/Jan |
| LOYOLA_69_1 | LOYOLA 138 | .012 | −6,770 | 4435 | 3338 | $109 | Spring | May/Apr/Nov |
| LASCRU_MILO1_1 | LASCRUCE–MILO 138 | .091 | −5,052 | 1774 | 1439 | $30 | Fall | Nov/Jan/Oct |
### RT — POS
| Constraint | Element | mean|SF| | cum $ | bind-hrs | bind-int | mean λ | peak season | top months |
|---|---|---|---|---|---|---|---|---|
| HAINE__LA_PAL1_1 | LA PALMA–HAINE DR 138 | .036 | +10,931 | 1735 | 19994 | $186 | Spring | Apr/Mar/Feb |
| 1710__C | BELCNTY–SALSW 138 | .013 | +5,870 | 608 | 7191 | $815 | Summer | Aug/Oct/May |
| STPELM27_1 | STP–ELMCREEK 345 | .055 | +4,457 | 116 | 1389 | $795 | Winter | Dec/Jan/Nov |
| 421__A | BCESW–SNDSW 345 | .118 | +4,239 | 415 | 4981 | $87 | Spring | Apr/Nov/Dec |
| WESTEX | RILEY(W)–KRWSW(N) West→North export GTC | .150 | +3,099 | 1315 | 15774 | $16 | Spring | May/Mar/Apr |
### RT — NEG
| Constraint | Element | mean|SF| | cum $ | bind-hrs | bind-int | mean λ | peak season | top months |
|---|---|---|---|---|---|---|---|---|
| LARDVN_LASCRU1_1 | LAREDOVNTH–LASCRUCE 138 | .090 | −25,799 | 1246 | 14917 | $236 | Summer | Jul/Aug/Apr |
| E_PASP | PAWNEE–CALAVERAS 345 (interface) | .223 | −22,983 | 776 | 9314 | $140 | Winter | May/Jan/Aug |
| VALEXP | NORTH EDINBURG–LON HILL **Valley Export interface (RTI/GTC)** | .979 | −13,004 | 359 | 4302 | $37 | Winter | Dec/Apr/Jan |
| CATARI_PILONC1_1 | PILONCILLO–CATARINA 138 | .061 | −10,577 | 469 | 5625 | $370 | Winter | Jan/May/Feb |
| LOYOLA_69_1 | LOYOLA 138 | .017 | −7,343 | 782 | 9239 | $576 | Spring | May/Apr/Jan |

**Overlap DA∩RT**: POS {HAINE, 1710__C, 421__A}; NEG {E_PASP, LARDVN_LASCRU1_1, LOYOLA_69_1}. Consistent across markets.

## Read (identification-level, not deep-dive)
- **GKS = deep South Texas / RGV (Valley) generator node.** Dominant LMP-LOWERING (charge) congestion = export-out-of-South-Texas
  paths where GKS injection aggravates: **Valley Export interface (VALEXP, SF≈1.0)**, PAWNEE–CALAVERAS (E_PASP), Laredo
  (LARDVN–LASCRUCE), BRUNI, LOYOLA, CATARINA–PILONCILLO. LMP-RAISING (discharge) = local RGV 138 lines GKS relieves
  (LA PALMA–HAINE, BELCNTY–SALSW, BCESW–SNDSW) + STP–ELMCREEK + West→North GTC (WESTEX).
- **Frequency vs severity**: E_PASP & HAINE rank by FREQUENCY (low λ, thousands of hrs); 1710__C, BRUNI, CATARINA, LOYOLA,
  STPELM27 rank by SEVERITY (few hundred hrs, RT mean λ $200–$815). Note 1710__C single biggest Aug spike.
- **Seasonality**: South-Texas export NEG cluster broad but Jan/summer-heavy (E_PASP Jan −$20.5k DA = a specific Jan-2026
  episode to investigate). Local POS lines = Spring (Feb–May). STP-ELMCREEK POS = Winter (Dec–Jan). VALEXP = Dec/Apr.

## FLAGS for Minsu before deep-dive
1. RT method deviation (market_shift_factors RT vs SCED+rt join) — confirm acceptable; recommend sample cross-check.
2. Window = 2024-07 → 2026-06 only (node COD). OK as "full history of node"?
3. VALEXP/WESTEX are RTI interfaces (GTCs), not single physical lines — treat separately in deep-dive.
4. E_PASP Jan-2026 −$20.5k DA concentration — confirm whether single-episode (regime) vs recurring.
5. Ranking unit = CONSTRAINTNAME (summed across contingencies); per (name+contingency) detail retained in raw parquet.

## Derived files
`shared/data/adhoc/2026-06-09_gks-congestion-impact/derived/`: `gks_msf_raw.parquet` (1.26M rows, all GKS binding
constraint-intervals), `ranking_{DA,RT}_{pos,neg}.json`, `monthly_matrix_{DA,RT}.json` (constraint×month $), `meta.json`.
