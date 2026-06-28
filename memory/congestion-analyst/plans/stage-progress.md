# CONGESTION_PROJECT — Stage Progress Tracker

**Source of truth**: `agensts/CONGESTION_PROJECT.md`
**Maintained by**: `congestion-analyst` agent
**Updated**: 2026-06-28 (no stage transition; W3 initiation still blocked; 38th consecutive cycle with hub-pair LMP unavailable; evaluator W23 improvement plan deadline for item 0.10 was 2026-06-11 — OVERDUE by 27 days; 2026-06-29 flowday outlook: HOUSTON_IMPORT MEDIUM-HIGH 35-50% (NL ramp HE18→HE21 +22,658 MW YE — similar to Jun 27 +22,652 MW; Monday weekday no weekend discount — primary upgrade driver vs Jun 27-28 MEDIUM; GR_WEST HE17-19 all BELOW 15,000 MW; W25 haircut active HE20-24 only — partial window haircut, new pattern; P50=$32, P90=$90; Smartbidder DA spike $30-35 corroborating); PANHANDLE_EXPORT LOW-MEDIUM 15-22% (HE01-06: GR_WEST = 17,670–18,015 MW, identical profile to Jun 28; no change from prior call); WEST_TO_NORTH LOW-MEDIUM 16-25% (GR_WEST HE22-24 = 15,707 / 16,195 / 16,564 MW; SCI 0.52-0.55 all above MEDIUM threshold; Monday — no weekend discount; W25 haircut ×0.90; window HE22-04); HOUSTON_SOUTH LOW 8-14% (single-hour thin breach: HE13 = 10,033 MW only; no dual trigger; Finding 7 applied — GKS MCC negative); Monday weekday; 4 PRODUCTION data files (YE hourly + YE summary + Smartbidder Energy + Smartbidder DA-RT); Enverus files referenced but not parsed this cycle; hub-pair LMP ABSENT 38th cycle; W25 partial haircut active (HE17-19 below 15k, HE20-24 above — first partial-window haircut pattern; zero settlement validation cycles); Jun 27 settlement expected T+2 ~Jun 29 — first potential W25 haircut validation cycle)

- **2026-06-27** (no stage transition; W3 initiation still blocked; 37th consecutive cycle with hub-pair LMP unavailable; evaluator W23 improvement plan deadline for item 0.10 was 2026-06-11 — OVERDUE by 26 days; 2026-06-28 flowday outlook: HOUSTON_IMPORT MEDIUM 28-40% (NL ramp HE18→HE21 +23,425 MW YE — 2nd highest in series, 1,012 MW below Jun 25 record; 773 MW above Jun 27 Saturday; Sunday weekend discount -7 ppt; GR_WEST HE19-24 all above 15,000 MW → W25 haircut ×0.85; Finding 3 window HE20-23; Non-Spin DA ABSENT); PANHANDLE_EXPORT LOW-MEDIUM 15-22% (UPGRADE from Jun 27 12-20%; GR_WEST HE01-06 = 17,662-18,005 MW — HE01=18,005 MW is series HIGH for overnight; all well above 15,000 MW threshold; Sunday overnight low demand); WEST_TO_NORTH LOW-MEDIUM 14-23% (SLIGHT DOWNGRADE from Jun 27 18-28%; GR_WEST HE22-24 = 17,085-17,725 MW — slightly lower than Jun 27 ~17,548-17,935 MW; SCI 0.38-0.49 all above MEDIUM 0.35; W25 haircut ×0.90 + Sunday -5 ppt; window HE22-04); HOUSTON_SOUTH VERY LOW <5% (DOWNGRADE from Jun 27 LOW 8-15%; cap-out MAX = 8,884 MW at HE10-11 — NO hour above 10,000 MW trigger; weakest midday cap-out profile in June series; Finding 7 applied); Sunday; 4 PRODUCTION data files; hub-pair LMP ABSENT 37th cycle; W25 GR_WEST haircut active 2nd consecutive cycle — 0 settlement validation cycles; Jun 27 settlement expected T+2 ~Jun 29; Jun 25/26 settlements pending)

- **2026-06-26** (no stage transition; W3 initiation still blocked; 36th consecutive cycle with hub-pair LMP unavailable; evaluator W23 improvement plan deadline for item 0.10 was 2026-06-11 — OVERDUE by 25 days; 2026-06-25 flowday outlook: HOUSTON_IMPORT HIGH 52-70% (NL ramp HE18→HE21 +24,437 MW YE — NEW SERIES RECORD, exceeds Jun 24 +22,371 MW by 2,066 MW; Enverus ramp +19,173 MW also extreme; load peak 80,744 MW HE17; cap-out max 10,080 MW HE11 — ABOVE 10,000 MW threshold vs Jun24 9,343 MW; Non-Spin DA ABSENT — 1.8x rule not applied; window shifted to HE20-23 applying Finding 3); WEST_TO_NORTH MEDIUM 28-40% (GR_WEST HE19-24 = 17,500-17,915 MW — SERIES HIGH; SCI proxy 0.39-0.46, ABOVE MEDIUM threshold 0.35; window HE19-24 applying Finding 2; MAJOR UPGRADE from Jun24 LOW-MEDIUM 12-20%); HOUSTON_SOUTH_MIDDAY_LOCAL LOW-MEDIUM 15-25% (cap-out max 10,080 MW — above 10,000 MW trigger; GKS MCC sign corrected to negative applying Finding 7); PANHANDLE NEGLIGIBLE (GR_WEST HE01-04 = 11,000-14,046 MW — BELOW 15,000 MW threshold; downgraded from LOW 5-10%); Thursday weekday; all 6 source files PRODUCTION; hub-pair LMP ABSENT 34th cycle; self-review for Jun 23 completed today (Tenaska T+2 available): HOUSTON_IMPORT direction correct HE20-21, timing offset 2h confirmed 4th consecutive cycle; HOUSTON_SOUTH MCC sign wrong 4th consecutive cycle — Finding 7 now applied; three learning items (2, 7, 8) applied in Jun 25 forecast for first time)

---

## Current Stage

**Stage 0 — Infrastructure** (in progress / datalake-only, 3-4 weeks)

> **2026-05-26 결정 (jms2527 + main thread)**: Stage 0 데이터 페치는 **Yes Energy Datalake (S3, bucket=`yedatalake`) 단독**으로 진행. ERCOT MIS direct 의존 0개로 확정. 사용자가 "PTDF = shift factor" 라는 ERCOT 용어 동치를 정확히 짚어준 덕분에 datalake의 4종 shift factor 경로 검증으로 NMMS direct extraction이 불필요해졌다. 9개 Stage 0 체크리스트 항목 전부 datalake에서 페치 가능함이 실측 확인됨.

---

## Stage 0 Checklist — datalake 매핑

각 항목 옆에 (소스 S3 경로 / 추정 소요 / 의존성 / deliverable) 4종 메타 포함.

### [W1] 자격증명·인프라·메타데이터·DA constraints — ✅ COMPLETED 2026-05-26

> **Historical window decision (2026-05-26)**: 학습 시작일을 **2020-02-01** 로 확정. `settle_shift_factors_ercot` 가 2020-02 이전 데이터를 보유하지 않아 그 이전 DA constraint history 는 shift factor 정합이 불가능함. 모든 W1 backfill 은 2020-02-01 이후만 처리.

#### 0.1 Datalake client + ddl.json 파서 — [x] 2026-05-26
- **데이터**: 없음 (코드 작업)
- **소스**: `.env::yes_energy_s3` → `_env_loader.load_env_sections()["yes_energy_s3"]`
- **소요**: 0.5d
- **의존성**: 없음 (cold start)
- **Deliverable**:
  - `src/ingestion/_datalake_client.py` — boto3 클라이언트 팩토리 + `read_csv_gz(key)` + `read_ddl(folder)` 헬퍼
  - `tests/test_datalake_client.py` — `list_objects_v2` smoke test ✅ PASS (16 prefixes found)

#### 0.2 Network metadata (static) — facility/contingency/plant/unit — [x] 2026-05-26
- **소스**: `yedatalake://ercot/metadata/objects/{facility,contingency,ercot_plant,ercot_unit}.csv.gz`
- **소요**: 0.5d
- **의존성**: 0.1
- **Deliverable**:
  - `src/ingestion/datalake_metadata.py` ✅
  - `data/raw/ercot/metadata/objects/facility.parquet` (172,492 rows) ✅
  - `data/raw/ercot/metadata/objects/contingency.parquet` (6,711 rows) ✅
  - `data/raw/ercot/metadata/objects/ercot_plant.parquet` (1,318 rows) ✅
  - `data/raw/ercot/metadata/objects/ercot_unit.parquet` (2,739 rows) ✅
  - `memory/congestion-analyst/learnings/2026-05-26-metadata-schema.md` ✅
- **Note**: contingency.csv.gz + facility.csv.gz join 결과 — null 0개 (100% 커버)

#### 0.3 DA binding constraints backfill (2020-02-01 → 2026-05-26) — [x] 2026-05-26
- **소스**: `yedatalake://ercot/transmission/constraints/da/{YYYYMMDD}.csv.gz`
- **실제 window**: 2020-02-01 ~ 2026-05-26 (2,307일, 16yr→6yr 로 변경, 이유: settle_shift_factors 정합)
- **소요**: 완료 (ThreadPoolExecutor max_workers=16, throttling 0건)
- **의존성**: 0.1, 0.2 ✅
- **Deliverable**:
  - `src/ingestion/datalake_constraints.py` ✅
  - `data/interim/constraint_binding_history.parquet` ✅
    - Rows: **2,030,085**
    - Date range: 2020-02-01 → 2026-05-26
    - Coverage: **100.0%** (2,307/2,307 days)
    - PRICE: min=0.001, max=31,029.1, mean=28.2, median=2.7 $/MWh
    - Unique constraints (CONSTRAINTNAME): 2,649
    - Null facility_name: 0 | Null contingency_name: 0
- **Risk 실측**: throttling 발생 없음. 16 workers parallel = 약 4분 소요.

**W1 종료 기준 충족**: DA constraints 가 (YYYY, constraint_id) 로 쿼리 가능한 parquet 으로 정착. ✅

---

### [W2] Shift factor 4종 backfill + 정규화 (= PTDF/LODF 통합) — ✅ COMPLETED 2026-05-27

> 4종 shift factor 모두 (CONSTRAINT, CONTINGENCY, RESOURCE|PNODE|SP) → SHIFTFACTOR 트리플. ERCOT가 base-case PTDF + post-contingency PTDF 를 한 테이블에 발행하므로 별도 LODF 행렬 계산 불필요.

> **2026-05-27 구현 메모**: ThreadPoolExecutor 16 workers → OOM kill 발생. 원인: 181개 future를 한꺼번에 submit하면 download가 write보다 빠를 때 모든 DataFrame이 동시에 메모리에 쌓임. 해결: `BATCH_SIZE=8` fixed-batch pattern으로 전환 (peak memory ≤ 8 DataFrames ≈ 1.2 GB). 10분 container 시간제한 대응: H1/H2 half-year chunking (`part-H1.parquet`, `part-H2.parquet`). 청크 단위 resume logic + corrupt file 자동 삭제 구현.

#### 0.4 DAM market shift factors (pricenode-level) — [x] 2026-05-27
- **소스**: `yedatalake://ercot/transmission/constraints/market_shift_factors/{YYYYMMDD}.csv.gz` (2016-01 → )
- **Window**: 2020-02-01 이후만 사용 (settle_shift_factors 정합 기준, 2026-05-26 결정)
- **Deliverable**: `data/raw/ercot/transmission/constraints/market_shift_factors/year=YYYY/part-H{1,2}.parquet` ✅
- **실측 결과**: **2,822,642,755 rows** | 2020~2026 전 연도 100% | 각 파일 valid ✅
  - year=2020: 276M | 2021: 281M | 2022: 390M | 2023: 396M | 2024: 478M | 2025: 694M | 2026: 304M
- **Use**: DAM binding/λ 모델의 PTDF projection — pricenode-level (Stage 2의 nodal MCC 재구성 1차 source)

#### 0.5 RT (SCED) shift factors (resource-level PTDF) — [x] 2026-05-27 (partial)
- **소스**: `yedatalake://ercot/transmission/constraints/ercot_sced_shift_factors/{YYYYMMDD}.csv.gz` (2011-12 → )
- **Window**: 2020-02-01 이후만 사용 (settle_shift_factors 정합 기준, 2026-05-26 결정)
- **Deliverable**: `data/raw/.../ercot_sced_shift_factors/year=YYYY/part-H{1,2}.parquet` ✅ (partial)
- **실측 결과**: **1,562,338,516 rows** | 2020-2025 H1 완료 ✅
  - year=2020: 154M | 2021: 162M | 2022: 240M | 2023: 259M | 2024: 403M | 2025 H1: 341M
  - **GAP**: 2025-H2 (Jul-Dec 2025) + 2026 (Jan-May 2026) 미완료 — 디스크 부족 (완료 시점 잔여 2.3 GB, H2 추가 예상 1.9 GB → 위험)
  - **우선순위**: W2 exit gate (0.4) 완료 후 비중요. W3 시작 전 디스크 확보 후 backfill 재개.

#### 0.6 Settlement shift factors (SP-level) — [x] 2026-05-27
- **소스**: `yedatalake://ercot/transmission/constraints/settle_shift_factors_ercot/{YYYYMMDD}.csv.gz` (2020-02 → )
- **Deliverable**: `data/raw/.../settle_shift_factors_ercot/year=YYYY/part-H{1,2}.parquet` ✅
- **실측 결과**: **1,816,938,146 rows** | 2020~2026 전 연도 완료 ✅
  - year=2020: 160M | 2021: 192M | 2022: 258M | 2023: 242M | 2024: 300M | 2025: 457M | 2026: 206M

#### 0.7 Generic shift factors (pricenode-level + QUALITY_METRIC) — [x] 2026-05-26
- **소스**: `yedatalake://ercot/transmission/constraints/shift_factors/{YYYYMMDD}.csv.gz` (2015-01 → )
- **Deliverable**: `data/raw/.../shift_factors/year=YYYY/part.parquet` ✅
- **실측 결과**: **28,780,477 rows** | 2020~2026 전 연도 완료 ✅

#### 0.8 정규화 — shift factor 4종의 용도 차이 문서화 — [x] 2026-05-26
- **Deliverables**:
  - `memory/congestion-analyst/plans/shift-factor-variants.md` ✅
  - `data/interim/shift_factors_unified_schema.md` ✅

**W2 종료 기준 충족**: ✅
- `src/ingestion/w2_sanity_check.py` 실행 완료 (2026-05-27)
- sample window 2026-05-19 ~ 2026-05-25: 1,103 unique pricenodes
- MCC = -Σ(SF × λ) 재구성: min=-$108.4, max=+$440.5, mean=$0.63/MWh
- Top node 10018248458: hourly congestion pattern 검증됨 (야간 음수, 주간 양수 — 전형적 ERCOT 서부 병목)
- NOTE: actual DAM LMP MCC 대조는 W3 (bus_lmp backfill) 완료 후 가능

---

### [W3] Price / Outage / CRR / GTC

#### 0.9 Bus-level (nodal) LMP backfill — **critical path**
- **소스**: `yedatalake://ercot/prices/bus_lmp/{YYYYMMDD}.csv.gz` (2017-01 → )
- **소요**: 3.0d (다운로드 자체로 1.5d, partition+QA 1.5d)
- **의존성**: 0.2
- **Deliverable**: `data/raw/ercot/prices/bus_lmp/year=YYYY/month=MM/*.parquet`
- **Risk (Critical Path)**: ~10 MB/day gz × 3,200 days = **~30 GB gzipped, ~150 GB uncompressed parquet**. 전체 backfill 1회 다운로드 시간 + 디스크 + S3 egress 비용 모두 가장 큰 항목. → **W3 시작 전에 디스크 60GB+ 여유 확인 필수**.

#### 0.10 Hub/zone LMP 15-min
- **소스**: `yedatalake://ercot/prices/lmp/15min/{YYYYMMDDHH}.csv.gz` (2012-11 → )
- **소요**: 1.0d
- **의존성**: 0.1
- **Deliverable**: `data/raw/ercot/prices/lmp/15min/year=YYYY/*.parquet`
- **Use**: hub-pair basis history (Stage 1 baseline target) + 15min granularity feature.

#### 0.11 Transmission outages
- **소스**: `yedatalake://ercot/transmission/outages/actual/{YYYYMMDDHH}.csv.gz` (2017-01 → )
- **소요**: 1.0d
- **의존성**: 0.2 (facility join)
- **Deliverable**: `data/raw/ercot/transmission/outages/actual/year=YYYY/*.parquet`
- **Note**: hourly granular — outage event 가 binding 직전에 새로 들어왔는지 detect 가능.

#### 0.12 CRR/FTR auction history
- **소스**: `yedatalake://ercot/ftr/auction/{YYYY_MM_monthly,YYYY_annual}/{results,obligationmcp,optionmcp}.csv.gz` (2010-12 → )
- **소요**: 0.5d
- **의존성**: 0.1
- **Deliverable**: `data/raw/ercot/ftr/auction/year=YYYY/*.parquet`
- **Open decision 해소**: ✅ Datalake로 결정 (별도 ERCOT API subscription 불필요).

#### 0.13 GTC (Generic Transmission Constraints) DA/RT
- **소스**: `yedatalake://ercot/flow/ercot_{da,rt}_generic_constraints/` (2016-03 → )
- **소요**: 0.5d
- **의존성**: 0.2
- **Deliverable**: `data/raw/ercot/flow/ercot_{da,rt}_generic_constraints/year=YYYY/*.parquet`
- **Note**: CONGESTION_PROJECT.md §8 의 "GTBD (generic transmission constraints) ─ ERCOT-specific stability constraints" 항목 — 본 backfill로 별도 핸들링 ready.

**W3 종료 기준**: 가격·outage·CRR·GTC backfill 완료. bus_lmp 의 day-1 spot check (임의 일자 GK 노드 LMP 와 ERCOT settlement statement 대조) 통과.

---

### [W4] Vintage / Weather / Gas + 통합 스토리지 + QA

#### 0.14 Vintage forecasts (publish-time snapshots) — **leakage 자연 방지**
- **소스**: `yedatalake://ercot/vintage/...` (정확한 sub-path는 W4 시작 시 확인 — load forecast / wind STWPF / solar STPPF 등 vintage tree)
- **소요**: 2.0d (sub-path 탐색 0.5d + 페치 1.5d)
- **의존성**: 0.1
- **Deliverable**:
  - `src/ingestion/datalake_vintage.py`
  - `data/raw/ercot/vintage/<series>/year=YYYY/*.parquet`
- **Critical**: D-1 10:00 CT cutoff 룰 (CONGESTION_PROJECT.md §6) 을 **데이터 레벨에서** 강제하는 유일한 source. publish_time 컬럼이 cutoff < publish_time 인 row 를 자동 차단해줌. Stage 1+ feature engineering 의 안전망.

#### 0.15 Weather (forecast + actual, zone-level)
- **소스**: `yedatalake://ercot/weather/{forecast,actual}/{YYYYMMDD}.csv.gz` (forecast 2008+, actual 2006+)
- **소요**: 1.0d
- **의존성**: 0.1
- **Deliverable**: `data/raw/ercot/weather/{forecast,actual}/year=YYYY/*.parquet`
- **Open decision 해소**: Stage 0/1 한정 datalake zone-level 로 충분. ⏸ HRRR (NOMADS 직접 다운로드) 는 **Stage 2 로 deferred** — hub-height wind / GHI 가 universal constraint model (Stage 2) 에서 필요해질 때 재개.

#### 0.16 Henry Hub + Waha gas
- **소스**: `yedatalake://ercot/prices/gas/` (정확한 경로 W4 시작 시 확인 필요 — 아직 미검증)
- **소요**: 0.5d
- **의존성**: 0.1
- **Deliverable**: `data/raw/ercot/prices/gas/*.parquet`
- **Fallback**: 만약 datalake에 없으면 EIA API / external — W4 중반 escalation point.

#### 0.17 통합 Parquet/DuckDB 스토리지
- **Deliverable**:
  - `data/interim/duckdb_views.sql` — 각 raw parquet을 view로 등록
  - `src/storage/duckdb_session.py` — `attach_all()` 헬퍼
- **소요**: 1.0d
- **의존성**: W1-W3 산출물 전부

#### 0.18 Data quality dashboard
- **Deliverable**:
  - `notebooks/qa_dashboard.ipynb` — missingness / drift / coverage timeline 시각화
  - `reports/ad-hoc/2026-MM-DD_congestion-stage0-qa.md` — Stage 0 → 1 전환 GO/NO-GO 판정용
- **소요**: 1.5d
- **의존성**: 0.17
- **Stage 0 → 1 게이트**: dashboard 가 14일 연속 green (CONGESTION_PROJECT.md §4 transition gate).

**W4 종료 기준**: 전체 데이터 인벤토리가 단일 DuckDB session 으로 쿼리 가능. QA 대시보드 첫 14일 모니터링 시작.

---

## Critical Path 식별

1. **0.9 bus_lmp** — 9년치 × 10MB/day = ~30 GB gzipped 다운로드. W3 의 절반 이상을 차지. → **W3 시작 전 디스크 60 GB+ 확보 / S3 egress rate-limit 확인**.
2. **0.5 ercot_sced_shift_factors** — 14년치, ~34 GB gzipped. W2 의 최대 risk.
3. **0.3 DA constraints + 0.4 DAM shift factors 정합성** — W1/W2 의 교차 sanity check (DAM MCC 재구성) 가 실패하면 Stage 1 baseline 진입 차단.

총 raw storage 예상: **~70 GB gzipped, ~300 GB uncompressed parquet (snappy)**. 압축 효율 고려해 columnar 변환 후 ~120 GB.

---

## Open Decisions (from CONGESTION_PROJECT.md §9)

- [x] **CRR data subscription path** — ✅ **datalake로 해소 (2026-05-26)**. `yedatalake://ercot/ftr/auction/`.
- [x] **HRRR weather pipeline** — ⏸ **Stage 0/1 한정 datalake zone-level 로 충분, HRRR 은 Stage 2 로 deferred (2026-05-26)**. Stage 2 의 universal constraint model 이 hub-height wind / GHI 를 요구할 때 NOMADS 직접 다운로드 vs commercial 재논의.
- [ ] Initial constraint subset for Stage 1 — full list vs top-N by historical binding frequency (W1 0.3 산출 후 결정)
- [ ] Online learning vs scheduled retraining cadence (Stage 2 이후 결정)
- [ ] Inference latency target for RTM 5-min cycle (Stage 3 이후 결정)

---

## Stage transition gates (unchanged)

| Stage | Trigger | KPI |
|---|---|---|
| 0 → 1 | All Stage 0 checklist done | Data quality dashboard green for 14 days |
| 1 → 2 | Hub-pair backtest end-to-end run | LightGBM beat naive 7-day persistence on 4/6 paths |
| 2 → 3 | Universal model stable on DAM | binding AUC ≥ 0.85, λ pinball loss ≤ baseline |
| 3 → 4 | Stage 3 has clear topology-failure cases | Stage 3 OOD test 3-month MAE > Stage 2 by ≥ 30% |

---

## Daily output during Stage 0 (unchanged)

본 stage 동안 congestion-analyst가 산출 가능한 것:
- Hub-pair basis 히스토리 (DALMP:WEST_HUB − DALMP:NORTH_HUB 등)
- Binding constraint 빈도 통계 (W1 0.3 산출물 활용)
- Top constraint list (Stage 1 후보군)

형식: D+1 outlook 의 `[Stage 0 — provisional]` 헤더 유지. shadow price 모델링은 Stage 2 진입 후.

---

## Weekly update template

```markdown
## Week YYYY-WW
- 완료: <0.x 항목 N개>
- 진행 중: <0.x>
- 블로커: <S3 throttling / 디스크 / ddl.json 불일치 / …>
- 다음주 목표: <0.x ~ 0.x>
```

---

## 변경 이력

- **2026-06-26** — cycle count updated (36th consecutive cycle without W3 initiation). Evaluator W23 improvement plan deadline for item 0.10 was 2026-06-11 — OVERDUE by 25 days. No stage transition. All four input data files confirmed PRODUCTION (YE hourly CSV + YE summary + Smartbidder Energy Prices). Smartbidder DA-RT file contains Date column only (no spread data) — ABSENT. Smartbidder Non-Spin DA ABSENT — right-tail condition (2) unverifiable. Saturday June 27 D+1 outlook: NL ramp HE18→HE21 +22,652 MW YE (2nd highest in series; below Jun 25 record +24,437 MW; above Jun 26 +20,721 MW). HOUSTON_IMPORT MEDIUM 27-38% (base HIGH downgraded by Saturday weekend discount -7 ppt and GR_WEST haircut ×0.85 per W25 plan; window HE20-23 Finding 3; P50=$28, P90=$80). PANHANDLE_EXPORT LOW-MEDIUM 12-20% (UPGRADE from Jun 26 LOW 8-15%; GR_WEST HE01-06 = 15,878-17,224 MW all above 15,000 MW threshold; Saturday overnight demand lower amplifies surplus). WEST_TO_NORTH LOW-MEDIUM 18-28% (GR_WEST HE22-24 = 17,548-17,935 MW near series max; SCI 0.38-0.66 all above MEDIUM 0.35; W25 haircut ×0.90; W25 timing correction window HE22-04). HOUSTON_SOUTH LOW 8-15% (weakest cap-out in series: only HE08 = 10,159 MW above 10,000 MW trigger; HE09-16 = 9,987-9,999 MW all below trigger; Finding 7 applied — GKS MCC negative). Saturday. Hub-pair LMP ABSENT 36th consecutive cycle. W25 GR_WEST haircut active (all hours above 15,000 MW). Self-review for Jun 25 (Tenaska T+2 expected today) pending — learnings/2026-06-25.md filed pre-settlement; follow-up KPI update to be filed as learnings/2026-06-27-followup.md.

- **2026-06-25** — cycle count updated (35th consecutive cycle without W3 initiation). Evaluator W23 improvement plan deadline for item 0.10 was 2026-06-11 — OVERDUE by 24 days. No stage transition. All six input data files confirmed PRODUCTION (YE hourly CSV + YE summary + Enverus load/net_load/wind/solar). Smartbidder ABSENT — right-tail condition (2) unverifiable; 1.8x rule not applied. Friday June 26 D+1 outlook: NL ramp HE18→HE21 +20,721 MW YE (+17,224 MW Enverus, 16.9% divergence) — below Jun 25 series record (+24,437 MW) by 15%; load peak 82,027 MW HE17. HOUSTON_IMPORT MEDIUM 30-45% (window HE20-23 per Finding 3; NL peak HE21 both sources). WEST_TO_NORTH LOW-MEDIUM 15-28% (GR_WEST HE19-24 = 13,208-16,481 MW — below Jun 25 series high; SCI mixed: HE19=0.411 MEDIUM, HE20-22=0.289-0.319 LOW-MED, HE23-24=0.364-0.414 MEDIUM; window HE22-24). PANHANDLE_EXPORT LOW 8-15% (GR_WEST HE01-04 = 15,124-16,459 MW — ABOVE 15,000 MW threshold for first time since Jun 21; UPGRADE from NEGLIGIBLE). HOUSTON_SOUTH_MIDDAY_LOCAL LOW 10-18% (cap-out HE09-12 = 10,051-10,069 MW; Finding 7 applied — GKS MCC negative). Friday weekday. Hub-pair LMP ABSENT 35th consecutive cycle. Self-review for Jun 25 filed as learnings/2026-06-25.md (pre-settlement; Tenaska T+2 expected ~2026-06-27; Jun 24 settlement expected ~2026-06-26).

- **2026-06-24** — cycle count updated (34th consecutive cycle without W3 initiation). Evaluator W23 improvement plan deadline for item 0.10 was 2026-06-11 — OVERDUE by 23 days. No stage transition. All six input data files confirmed PRODUCTION (YE hourly CSV + YE summary + Enverus load/net_load/wind/solar). Smartbidder ABSENT — right-tail condition (2) unverifiable. Thursday June 25 D+1 outlook: NL ramp HE18→HE21 +24,437 MW YE — NEW SERIES RECORD (exceeds Jun 24 +22,371 MW by 2,066 MW; Enverus +19,173 MW also extreme). HOUSTON_IMPORT HIGH 52-70% (window shifted to HE20-23 per Finding 3). WEST_TO_NORTH MEDIUM 28-40% — MAJOR UPGRADE from Jun24 LOW-MEDIUM (GR_WEST HE19-24 = 17,500-17,915 MW series high; SCI proxy 0.39-0.46 above MEDIUM threshold; window HE19-24 per Finding 2). HOUSTON_SOUTH_MIDDAY_LOCAL LOW-MEDIUM 15-25% (cap-out max 10,080 MW above 10,000 MW; GKS MCC corrected to negative per Finding 7). PANHANDLE NEGLIGIBLE (GR_WEST HE01-04 = 11,000-14,046 MW, below 15,000 MW threshold). Self-review for Jun 23 completed: HOUSTON_IMPORT direction correct (RT +$1,410 HE21); HOUSTON_SOUTH MCC sign wrong (4th consecutive cycle — Finding 7 now applied); Findings 2, 3, 7 all applied in Jun 25 forecast for first time (first cycle with all identified systematic errors corrected). Jun 23 GKS total revenue $8,439.93 (Tenaska PRODUCTION). Jun 24 settlement expected T+2 ~2026-06-26.
- **2026-06-23** — cycle count updated (33rd consecutive cycle without W3 initiation). Evaluator W23 improvement plan deadline for item 0.10 was 2026-06-11 — OVERDUE by 22 days. No stage transition. All six input data files confirmed PRODUCTION (YE hourly CSV + YE summary + Enverus load/net_load/wind/solar). Smartbidder ABSENT — right-tail condition (2) unverifiable. Wednesday June 24 D+1 outlook: NL ramp HE18→HE21 +22,371 MW YE — NEW SERIES RECORD (exceeds Jun 23 +20,385 MW by 1,986 MW). HOUSTON_IMPORT upgraded to HIGH 50-68% (new series high). WEST_TO_NORTH downgraded to LOW-MEDIUM 12-20% (GR_WEST HE22-24 = 14,082-14,945 MW — materially lower than Jun23). HOUSTON_SOUTH_MIDDAY_LOCAL maintained LOW-MEDIUM 12-22% (cap-out max 9,343 MW, below 10,000 MW primary trigger). PANHANDLE LOW 5-10% (GR_WEST HE01-04 above 15,000 MW). Solar peak HE15 (YE) 29,569 MW / HE14 (Enverus) 30,482 MW. Large YE-Enverus NL divergence at HE18 (11,413 MW); both converge at HE21 (~53,000-55,000 MW). Self-review for Jun 22 pending Tenaska T+2 ~2026-06-24.
- **2026-06-22** — cycle count updated (32nd consecutive cycle without W3 initiation). Evaluator W23 improvement plan deadline for item 0.10 was 2026-06-11 — OVERDUE by 21 days. No stage transition. All six input data files confirmed PRODUCTION (YE hourly CSV + YE summary + Enverus load/net_load/wind/solar). Smartbidder ABSENT — right-tail condition (2) unverifiable. Tuesday June 23 D+1 outlook: NL ramp HE18→HE21 +20,385 MW YE — NEW SERIES RECORD (prior high: +19,639 MW Jun 22; +18,627 MW Jun 21). HOUSTON_IMPORT upgraded to HIGH 45-62% (highest range in series). WEST_TO_NORTH upgraded to MEDIUM 22-35% (GR_WEST HE23-24 = 16,669-17,186 MW — near Jun 17 series high of 16,805 MW). HOUSTON_SOUTH_MIDDAY_LOCAL downgraded to LOW-MEDIUM 18-28% (cap-out 10,493-10,982 MW, lower than Jun 22). PANHANDLE upgraded to LOW 5-10% (GR_WEST HE01 = 18,627 MW). Solar peak 28,166 MW HE17 (equal to Jun 22 max). Self-review for Jun 21 solstice (issued Jun 20) now due — Tenaska T+2 should be available today.
- **2026-06-20** — cycle count updated (30th consecutive cycle without W3 initiation). Evaluator W23 improvement plan deadline for item 0.10 was 2026-06-11 — OVERDUE by 9 days. No stage transition. All six input data files confirmed PRODUCTION (YE hourly CSV + YE summary + Enverus load/net_load/wind/solar). Smartbidder ABSENT — right-tail condition (2) unverifiable. Sunday June 21 D+1 outlook: record GR_WEST HE24 18,103 MW (series max; prior 15,633 MW Saturday); SCI 0.503 (new series high); NL ramp HE18→HE21 +18,627 MW YE (new series record; Enverus cross-validates +12,591 MW — 32% divergence, largest in series, structural source difference); cap-out 12,934 MW (series max) at HE13-14; 9-hour dual-trigger breach HE09-17. All four tracked constraints activate simultaneously for first time in series: HOUSTON_IMPORT HIGH 38-55%, WEST_TO_NORTH MEDIUM 28-40%, HOUSTON_SOUTH_MIDDAY_LOCAL MEDIUM 22-32%, PANHANDLE_EXPORT LOW-MEDIUM 15-22%. June 21 = summer solstice — highest solar generation day of year (solar peak 28,824 MW YE / 26,717 MW Enverus). Self-review for Saturday June 20 pending Tenaska T+2 availability ~2026-06-23.
- **2026-06-19** — cycle count updated (29th consecutive cycle without W3 initiation). Evaluator W23 improvement plan deadline for item 0.10 was 2026-06-11 — OVERDUE by 8 days. No stage transition. All six input data files confirmed PRODUCTION (YE hourly CSV + YE summary + Enverus load/net_load/wind/solar). Smartbidder ABSENT — right-tail condition (2) unverifiable; single-condition assessment only. Saturday flowday June 20 primary signal: WEST_TO_NORTH LOW-MEDIUM 18-26% — GR_WEST 15,633 MW overnight, SCI 0.426, Panhandle threshold first approached (15,633 MW vs ~15,000 MW threshold). HOUSTON_IMPORT MEDIUM 20-30% — NL ramp cross-source tight alignment (YE +10,424 MW, Enverus +10,218 MW, < 2.2% gap). HOUSTON_SOUTH_MIDDAY_LOCAL LOW 10-16% (2-hour cap-out breach). PANHANDLE_EXPORT LOW 6-10% (series first). Weekend Saturday discount applied to all evening calls. Self-review for Friday June 19 pending Tenaska T+2 ~2026-06-21.
- **2026-06-17** — cycle count updated (27th consecutive cycle without W3 initiation). Evaluator W23 improvement plan deadline for item 0.10 was 2026-06-11 — OVERDUE by 6 days. No stage transition. YE hourly CSV and summary.json confirmed PRODUCTION for 2026-06-18 flowday. Enverus files REFERENCED in summary.json but not parsed this cycle — NL ramp cross-validation absent. Smartbidder ABSENT — right-tail condition (2) unverifiable; applied 1.8x on condition (1) alone (NL ramp +17,935 MW >> 9,000 MW threshold). Three new series records for 2026-06-18: load peak 84,362 MW, NL ramp HE18->HE21 +17,935 MW, NL at HE21 56,003 MW. HOUSTON_IMPORT upgraded to HIGH (35-50%) — first HIGH-tier call in the series. HOUSTON_SOUTH_MIDDAY_LOCAL upgraded to MEDIUM (20-32%) with dual trigger active 7 consecutive hours HE09-15. WEST_TO_NORTH reverts to NEGLIGIBLE in all windows (GR_WEST HE22-24 = 12,076-12,599 MW, NL 45,485-53,728 MW, SCI 0.225-0.267 — well below LOW threshold). GR_WEST trough of 4,787 MW at HE14 is series absolute minimum. Solar peak 29,178 MW at HE13 is series high. W2.5 DuckDB top-20 binding frequency query: still not executed (27 cycles).
- **2026-06-16** — cycle count updated (26th consecutive cycle without W3 initiation). Evaluator W23 improvement plan deadline for item 0.10 was 2026-06-11 — OVERDUE by 5 days. No stage transition. All five input data files confirmed (YE hourly CSV + YE summary + Enverus load/wind/solar/net_load + Smartbidder 3 files — PRODUCTION). Smartbidder DA Ancillary Prices available for first time in series: Non-Spin DA HE21 = $12.45/MWh — activates 1.8x right-tail rule on BOTH trigger conditions for first time. YE vs Enverus load divergence < 0.5% — primary input uncertainty closed. HOUSTON_IMPORT upgraded to MEDIUM (25-38%) for 2026-06-17; HOUSTON_SOUTH_MIDDAY_LOCAL dual trigger active with series-high cap-out 13,088 MW (upgraded to LOW-MEDIUM 18-28%); WEST_TO_NORTH HE22-24 confirmed LOW (8-14%) second consecutive cycle (GR_WEST 15,627-16,805 MW). 2026-06-17 is the highest-probability congestion day in the 26-cycle series. W2.5 DuckDB top-20 binding frequency query: still not executed (26 cycles).
- **2026-06-15** — cycle count updated (25th consecutive cycle without W3 initiation). Evaluator W23 improvement plan deadline for item 0.10 was 2026-06-11 — OVERDUE by 4 days. No stage transition. YE hourly CSV and Enverus load_fc / net_load_fc confirmed for 2026-06-16 flowday (PRODUCTION data). New structural signal: GR_WEST overnight surge forecasts 12,221 MW at HE24 (vs 4,529 MW max in yesterday's cycle) — WEST_TO_NORTH_345 HE22-24 appears as LOW (8-14%) probability constraint for the first time in the current series. Cap-out dual trigger active (12,096 MW at HE11, HE8-16 all above 11,500 MW) — HOUSTON_SOUTH_MIDDAY_LOCAL upgraded from VERY LOW to LOW-MEDIUM (7-12%). HOUSTON_IMPORT evening window remains primary at LOW-MEDIUM (15-22%); NL ramp +8,770 MW just below 9,000 MW MEDIUM threshold. W2.5 DuckDB top-20 binding frequency query: still not executed (25 cycles).
- **2026-06-13** — cycle count updated (23rd consecutive cycle without W3 initiation). Evaluator W23 improvement plan deadline for item 0.10 was 2026-06-11 — OVERDUE by 2 days. No stage transition. Positive: Enverus solar STPF confirmed parsed for second consecutive cycle (2026-06-13 fetch for 2026-06-14 flowday) — pattern now consistent. YE hourly forecast CSV absent for 2026-06-14 (file not present); only YE summary.json available; Enverus hourly CSVs used as primary NL/ramp source. GKS midday MCC sign correction operational for 3rd consecutive cycle (positive central estimate). W2.5 DuckDB top-20 binding frequency query: still not executed (23 cycles).
- **2026-06-12** — cycle count updated (22nd consecutive cycle without W3 initiation). Evaluator W23 improvement plan deadline for item 0.10 was 2026-06-11 — OVERDUE by 1 day. No stage transition. One positive development: Enverus solar STPF confirmed parsed for the first time in the 2026-06-12 cycle (for 2026-06-13 flowday); Enverus-YE solar divergence small this cycle (+1,241 MW at peak vs prior 4,000-5,500 MW gaps). Tenaska IP-whitelist failure now at 12 confirmed occurrences — settlement validation blocked for 11 backfill days plus current flowday. GKS midday MCC sign correction operationalized (first cycle: 2026-06-12 forecast issued 2026-06-11). W2.5 DuckDB top-20 binding frequency query: still not executed (22 cycles).
- **2026-06-10** — cycle count updated (20th consecutive cycle without W3 initiation). Evaluator W23 improvement plan deadline for item 0.10 flagged as overdue (target was by 2026-06-11). No stage transition.
- **2026-05-26** — datalake-only 전면 재작성. 9개 체크리스트를 0.1–0.18 의 18개 sub-task 로 분해. W1–W4 milestone 정의. Critical path 식별 (bus_lmp / sced_shift_factors). Open decision 2개 해소.
- **2026-04-30** — initial scaffold.
