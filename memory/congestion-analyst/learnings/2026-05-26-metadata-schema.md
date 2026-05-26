# ERCOT Metadata Schema — 2026-05-26

Fetched from `yedatalake://ercot/metadata/objects/`. Static tables, infrequently updated.

## facility

**Source**: `yedatalake://ercot/metadata/objects/facility.csv.gz`  
**Rows**: 172,492  
**Fetched**: 2026-05-26

| Column | dtype | Non-null count | Sample values |
|--------|-------|---------------|---------------|
| `OBJECTID` | int64 | 172,492 | [10002849761, 10016442101] |
| `FACILITYNAME` | str | 172,492 | ['- 0KV AJO_ZO', '- 0KV BEARKT'] |
| `FACILITYTYPE` | str | 171,223 | ['LINE', 'RTI'] |
| `VOLTAGE` | float64 | 172,442 | [345.0, 345.0] |
| `ISO` | str | 172,492 | ['ERCOT', 'ERCOT'] |
| `FROMSTATIONID` | float64 | 172,479 | [10000699499.0, 10002383199.0] |
| `FROMSTATION` | str | 172,479 | ['AJO', 'W_BK_345'] |
| `FROMZONE` | str | 172,419 | ['SOUTH', 'WEST'] |
| `TOSTATIONID` | float64 | 38,417 | [10000703252.0, 10016993101.0] |
| `TOSTATION` | str | 38,417 | ['ZORILLO', 'BRNL_345'] |
| `TOZONE` | str | 38,399 | ['SOUTH', 'WEST'] |
| `FROMKV` | float64 | 0 | [] |
| `TOKV` | float64 | 0 | [] |
| `FROMBUSNAME` | float64 | 0 | [] |
| `TOBUSNAME` | float64 | 0 | [] |
| `EQUIPMENTID` | str | 66,748 | ['7604', '7605'] |
| `SEGMENTID` | float64 | 0 | [] |
| `STATUS` | str | 172,492 | ['Active', 'Active'] |

## contingency

**Source**: `yedatalake://ercot/metadata/objects/contingency.csv.gz`  
**Rows**: 6,711  
**Fetched**: 2026-05-26

| Column | dtype | Non-null count | Sample values |
|--------|-------|---------------|---------------|
| `OBJECTID` | int64 | 6,711 | [10017154116, 10017121010] |
| `ISO` | str | 6,711 | ['ERCOT', 'ERCOT'] |
| `CONTINGENCYNAME` | str | 6,711 | ['MHWKTNS8', 'MJRESA28'] |
| `TIMEZONE` | str | 6,711 | ['CPT', 'CPT'] |
| `STATUS` | str | 6,711 | ['Active', 'Active'] |

## ercot_plant

**Source**: `yedatalake://ercot/metadata/objects/ercot_plant.csv.gz`  
**Rows**: 1,318  
**Fetched**: 2026-05-26

| Column | dtype | Non-null count | Sample values |
|--------|-------|---------------|---------------|
| `OBJECTID` | int64 | 1,318 | [10017178984, 10018760490] |
| `OBJECTNAME` | str | 1,317 | ['0', '19599_1_PV'] |
| `ISO` | str | 1,318 | ['ERCOT', 'ERCOT'] |
| `SOURCE` | str | 1,318 | ['ERCOT', 'ERCOT'] |
| `OBJECTTYPE` | str | 1,318 | ['ercot_plant', 'ercot_plant'] |
| `ZONE` | float64 | 0 | [] |
| `SUBTYPE` | float64 | 0 | [] |
| `TIMEZONE` | str | 1,318 | ['CPT', 'CPT'] |
| `STATUS` | str | 1,318 | ['Active', 'Active'] |

## ercot_unit

**Source**: `yedatalake://ercot/metadata/objects/ercot_unit.csv.gz`  
**Rows**: 2,739  
**Fetched**: 2026-05-26

| Column | dtype | Non-null count | Sample values |
|--------|-------|---------------|---------------|
| `OBJECTID` | int64 | 2,739 | [10017176909, 10018759678] |
| `OBJECTNAME` | str | 2,739 | ['0', '19599_1_PV_A1'] |
| `ISO` | str | 2,739 | ['ERCOT', 'ERCOT'] |
| `SOURCE` | str | 2,739 | ['ERCOT', 'ERCOT'] |
| `OBJECTTYPE` | str | 2,739 | ['ercot_unit', 'ercot_unit'] |
| `ZONE` | float64 | 0 | [] |
| `SUBTYPE` | float64 | 0 | [] |
| `TIMEZONE` | str | 2,739 | ['CPT', 'CPT'] |
| `STATUS` | str | 2,739 | ['Active', 'Active'] |

## Notes

- `facility.OBJECTID` is the join key for `FACILITYID` in DA constraint files.
- `contingency.OBJECTID` is the join key for `CONTINGENCYID` in DA constraint files.
- `ercot_plant` / `ercot_unit` map generator → OBJECTID (used in Stage 2 PTDF projection).
- No `ddl.json` exists for `ercot/metadata/objects/` — schemas inferred from CSV headers.
