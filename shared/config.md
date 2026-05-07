# Shared Config — Data Sources & Conventions

모든 에이전트가 공유하는 데이터 소스 정보, 자격 증명 위치, 시간/단위 컨벤션.

---

## 1. 자격 증명 (.env)

위치: 프로젝트 루트의 **`.env`** (= `BESS_Biz/.env`)

각 에이전트가 인증이 필요한 skill을 호출할 때, skill 내부 코드가 같은 루트의 `.env`에서 환경변수를 읽는다. 다른 폴더에 .env를 복제하지 않는다 (단일 source of truth).

`.env`에 들어있는 키 (skill 문서 기반):
- Yes Energy: `YES_ENERGY_USERNAME`, `YES_ENERGY_PASSWORD`
- Yes Energy S3: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- ERCOT API: `ERCOT_USERNAME`, `ERCOT_PASSWORD`, `ERCOT_SUBSCRIPTION_KEY`
- AG2 (WSI Trader): `USER`, `PASSWORD`, `Profile`
- Enverus: `USERNAME`, `PASSWORD`
- Smartbidder: `SMARTBIDDER_CLIENT_ID`, `SMARTBIDDER_CLIENT_SECRET`, `SMARTBIDDER_CLIENT`, `SMARTBIDDER_RESOURCE`
- Tenaska: `TENASKA_USERNAME`, `TENASKA_PASSWORD`

---

## 2. Data Source 우선순위 (decision rule)

ERCOT 시장 데이터를 어디서 가져올지 결정 시:

> **Yes Energy (REST + S3) > Enverus > AG2 > ERCOT Public API**

세부 결정표는 `skills/fetch-ercot-data/SKILL.md` 첫 페이지 참조.

| 데이터 종류 | 1차 | 2차 (백업/cross-check) |
|---|---|---|
| DA/RT LMP | Yes Energy DataSignals | ERCOT Public API |
| 시스템 load forecast | Yes Energy bidclose | AG2 WSI / ERCOT MTLF |
| Wind / Solar forecast | Yes Energy STWPF/COPHSL | AG2 WindCast IQ |
| 가격 forecast (DA/RT) | Smartbidder /plots/Energy Price Forecasts | (직접 모델 — bess-optimizer 영역 외) |
| AS forecast | Smartbidder /plots/DA Ancillary Prices | /plots/RT Ancillary Prices (5-min) |
| Outages, PRC | Enverus Mosaic | – |
| Weather | AG2 WSI Trader | NOAA HRRR (장기) |
| GKS 실적 | Tenaska PTP | (없음, 단일 source) |
| Smartbidder benchmark | Smartbidder /revenue | – |

---

## 3. 시간 / 단위 컨벤션

### 시간 — **모든 wall-clock 시간은 CT (Houston, America/Chicago, DST 자동)**

ERCOT 운영 native time. KST 또는 다른 타임존 사용 금지 — 보고서·로그·timestamp 모두 CT.

- **Daily cycle wall clock**: 매일 **07:30 CT** 시작 → DAM bid cutoff 10:00 CT 까지 2.5h 윈도우.
- **모든 ERCOT API**: Central Prevailing Time (CPT) = `America/Chicago` (DST 자동, CST UTC−6 / CDT UTC−5).
- **Yes Energy / ERCOT API**: `HOURENDING` (HE1 = 00:00–01:00). 변환: `dt.hour = HE - 1`.
- **Smartbidder**: period-ending. ISO-8601 with tz offset. CPT 기준.
- **Tenaska PTP**: `intervalStartUtc` / `intervalEndUtc` UTC. 로컬 변환 시 `America/Chicago`.
- **DST 경고**: 봄 spring-forward 23 HE / 가을 fall-back 25 HE. `len(day) == 24` 가정 금지.
- **AG2**: `timeutc=false` 기본 (local prevailing). 명시적으로 `false` 설정.
- **JSON 산출물 timestamp 필드**: `issued_at_ct` (또는 `issued_at_utc` UTC), 더 이상 `issued_at_kst` 사용 금지.

### Spread 부호 (DART)

> **`spread = DA − RT`**. positive ⇒ DA expensive ⇒ short DA / long RT signal.

이 부호 규칙은 모든 에이전트에 일관 적용. 출처: fetch-ercot-data SKILL.md gotchas #2.

### 단위

- 가격: `$/MWh`
- 에너지: MWh
- 전력: MW
- 시간 표기: HE (Hour Ending, 1-24)

### Vintage

- D+1 forecast 데이터는 **D-1 10:00 CPT 이전 publish**된 vintage만 사용 (DAM bid cutoff).
- Enverus: `as_of=prior_day_rolling`로 강제 가능.
- Yes Energy: 강제 안 됨 → 본인이 publish time check 필요.

---

## 4. 공유 데이터 저장 컨벤션

`shared/data/` 하위 구조:

```
shared/data/
├── forecasts/
│   ├── market-view/             ← market-analyst가 매일 작성
│   │   └── YYYY-MM-DD.md
│   └── congestion/              ← congestion-analyst가 매일 작성
│       └── YYYY-MM-DD.md
├── pnl/
│   └── gks/
│       ├── hourly/YYYY-MM-DD.parquet
│       └── daily/YYYY-MM.parquet
├── benchmarks/
│   └── smartbidder/
│       ├── hourly/YYYY-MM-DD.parquet
│       └── daily/YYYY-MM.parquet
├── crr/
│   ├── auction-results/YYYY-MM/<auction-type>.parquet
│   └── basis-history/YYYY-MM.parquet
└── raw/                         ← 원본 캐시 (vendor cache, gitignore 권장)
    ├── yes-energy/
    ├── smartbidder/
    └── tenaska/
```

쓰기/읽기 규칙:
- `shared/data/forecasts/`, `shared/data/pnl/`, `shared/data/benchmarks/`, `shared/data/crr/` — **에이전트 산출물**, 정형 형식
- `shared/data/raw/` — vendor cache. 재실행 비용 절감용. 형식 자유.

---

## 5. Skill 호출 규약

다른 폴더의 skill을 호출하기:
- 본 프로젝트 에이전트는 `skills/<skill-name>/SKILL.md` 를 `Read` 한 뒤 그 지침에 따라 코드를 작성/실행한다.
- **Skill 자체를 본 프로젝트 폴더 안에 복제하지 않는다** (single source of truth).

---

## 6. 외부 프로젝트 / 자산

| 자산 | 위치 | 본 프로젝트와의 관계 |
|---|---|---|
| API Docs (4종) | `API Docs/*.txt` | Read-only reference |
| skills (4종) | `skills/` | 호출 only |
| CONGESTION_PROJECT | `agensts/CONGESTION_PROJECT.md` | `congestion-analyst`가 수정 가능 |
| `.env` | `.env` | Skill이 읽음 (절대 노출 X) |
