# `shared/scripts/` — Production Fetch Scripts

샌드박스 환경 밖(사용자 로컬 / 회사 서버 / GitHub Actions)에서 실행할 데이터 페치 스크립트. **샌드박스 proxy가 ERCOT 데이터 벤더 도메인을 차단**하므로 반드시 외부 환경에서 실행해야 한다.

---

## 0. 0회성 setup (Windows PowerShell 기준)

```powershell
# 1. 작업 위치
cd 'C:\Users\00904\ERCOT Projects\BESS_Biz'

# 2. 의존성 설치
pip install requests pandas msal

# 3. .env 점검 (아래 §3 참고)
```

`.cache/` 폴더가 자동 생성됨 — token 캐시·Tenaska endpoint 매핑 저장. 이 폴더는 절대 git push 하지 말 것 (자격 증명 포함).

---

## 1. `fetch_market_data.py` — Market Analyst (D+1 시황)

매일 아침 사이클의 첫 단계. 다음날(D+1) bidclose + 가격 예측 페치.

### 실행

```powershell
# 내일 (D+1) 자동
python shared\scripts\fetch_market_data.py

# 명시적 날짜
python shared\scripts\fetch_market_data.py --target-date 2026-05-01

# Smartbidder 건너뛰기 (Yes Energy만)
python shared\scripts\fetch_market_data.py --skip-smartbidder
```

### 필요 .env 키

| 키 | 용도 | 필수? |
|---|---|---|
| `YES_ENERGY_USERNAME`, `YES_ENERGY_PASSWORD` | Yes Energy DataSignals | ✅ |
| `APPLICATION_ID`, `CLIENT_ID`, `CLIENT_SECRET` | Smartbidder MSAL | (Smartbidder 사용 시) |
| `SMARTBIDDER_CLIENT` (default `apex`), `SMARTBIDDER_RESOURCE` (default `Kiskadee Storage`) | account 식별 | 선택 |

### 산출물

- `shared/data/raw/yes-energy/{date}.csv` — 9개 bidclose 항목 hourly
- `shared/data/raw/yes-energy/{date}_summary.json` — 24h mean / top2 / bot2 HE
- `shared/data/raw/smartbidder/{date}_Energy_Price_Forecasts.csv`
- `shared/data/raw/smartbidder/{date}_Ancillary_Price_Forecasts.csv`

---

## 2. `fetch_pnl_data.py` — P&L Manager (전일 실적)

매일 아침 사이클에서 self-review를 위해 필요. 어제(D-1) 정산 결과 + Smartbidder benchmark.

### 첫 실행 — Tenaska endpoint 디스커버리

Tenaska PTP는 viewport(endpoint slug)가 사용자 account별로 다르므로 1회 디스커버리 필요. 첫 실행 시 인터랙티브 프롬프트가 떠서 endpoint 4개를 선택하게 됨:

```powershell
python shared\scripts\fetch_pnl_data.py

# 출력 예시:
#   Markets (1):
#     [0] name='ERCOT'  id=...
#   Pick market index (default 0): 0
#
#   Endpoints (12):
#     [0] name='Energy & AS Details'  id=...
#     [1] name='DA Energy Bid Market Result'  id=...
#     ...
#   Pick index for 'Energy & AS Details' (yesterday's actuals: energy + AS): 0
#   Pick index for 'DA Energy Bid Market Result' (DA energy bid clearing): 1
#   ...
```

선택한 매핑이 `shared/scripts/.cache/tenaska_endpoints.json` 에 저장되며, 이후 실행은 자동.

매핑 다시 하려면:
```powershell
python shared\scripts\fetch_pnl_data.py --rediscover
```

### 일상 실행

```powershell
# 어제 (D-1) 자동
python shared\scripts\fetch_pnl_data.py

# 명시적 날짜
python shared\scripts\fetch_pnl_data.py --flowday 2026-04-29

# Smartbidder benchmark 건너뛰기
python shared\scripts\fetch_pnl_data.py --skip-smartbidder
```

### 필요 .env 키

| 키 | 용도 | 필수? |
|---|---|---|
| `TENASKA_USERNAME`, `TENASKA_PASSWORD` | Tenaska PTP | ✅ |
| `APPLICATION_ID`, `CLIENT_ID`, `CLIENT_SECRET` | Smartbidder MSAL | ✅ |
| `SMARTBIDDER_CLIENT`, `SMARTBIDDER_RESOURCE` | account 식별 | 선택 |

> **현재 `.env`에 `TENASKA_USERNAME`/`TENASKA_PASSWORD`가 없음.** 추가 필요. (확인 결과 §3)

### 산출물

- `shared/data/pnl/gks/hourly/{flowday}_energy_as_detail.json`
- `shared/data/pnl/gks/hourly/{flowday}_hsl.json`
- `shared/data/pnl/gks/hourly/{flowday}_da_energy_bid.json`
- `shared/data/pnl/gks/hourly/{flowday}_da_energy_offer.json`
- `shared/data/pnl/gks/hourly/{flowday}_summary.json`
- `shared/data/benchmarks/smartbidder/daily/{flowday}_daily.json`
- `shared/data/benchmarks/smartbidder/daily/{flowday}_hourly.json`

---

## 3. `.env` 형식 — 섹션 헤더 기반

USERNAME/PASSWORD가 여러 벤더에서 중복으로 쓰이므로, **섹션 헤더(주석 라인)**로 그룹화 필요. 우리 `_env_loader.py`가 다음 헤더 키워드를 인식해 자동 분리한다 (대소문자 무관, 부분 매칭):

| 섹션 키워드 (주석에 포함) | 인식되는 섹션 이름 |
|---|---|
| `Yes Energy Datalake` | `yes_energy_s3` |
| `Yes Energy` (API) | `yes_energy` |
| `ERCOT` | `ercot` |
| `Enverus` | `enverus` |
| `AG2` | `ag2` |
| `Smartbidder` (또는 `smartbid`) | `smartbidder` |
| `Tenaska` | `tenaska` |

### 권장 `.env` 레이아웃 (현재 구조 그대로 유지하면 됨)

```
# Yes Energy Datalake Credentials
YES_ENERGY_ACCESS_KEY=...
YES_ENERGY_SECRET_KEY=...

# ERCOT API Credentials
ERCOT_USERNAME=...
ERCOT_PASSWORD=...
ERCOT_SUBSCRIPTION_KEY=...

# Yes Energy API Credentials
YES_ENERGY_USERNAME=...
YES_ENERGY_PASSWORD=...

# Enverus API Credentials
USERNAME=...
PASSWORD=...

# AG2 API Credentials
USER=...
PASSWORD=...
Profile=...

# Smartbidder API Credentials
APPLICATION_ID=...
CLIENT_ID=...
CLIENT_SECRET=...
_TENANT=...
Resource=Kiskadee Storage
Node=GKS_BESS_RN

# Tenaska portal Credentials
TENASKA_USERNAME=...
TENASKA_PASSWORD=...
```

> 각 섹션 안의 `USERNAME`/`PASSWORD`는 그 섹션의 자격증명으로 인식됩니다. 명명을 바꿀 필요 없음.

### 매핑 (섹션 → 코드 lookup)

| 코드가 찾는 키 | 섹션 | 우선순위 |
|---|---|---|
| Yes Energy creds | `yes_energy` | `YES_ENERGY_USERNAME`, `YES_ENERGY_PASSWORD` |
| Smartbidder MSAL | `smartbidder` | `APPLICATION_ID`, `CLIENT_ID`, `CLIENT_SECRET`, `_TENANT` |
| Smartbidder client (account name) | `smartbidder` | `SMARTBIDDER_CLIENT` → default `apex` |
| Smartbidder resource | `smartbidder` | `Resource` → `SMARTBIDDER_RESOURCE` → default `Kiskadee Storage` |
| Tenaska creds | `tenaska` | `TENASKA_USERNAME`/`TENASKA_PASSWORD` → fallback to generic `USERNAME`/`PASSWORD` |
| Tenaska resource filter | `smartbidder` (`Node`) | `Node` → `TENASKA_NODE` → default `GKS` substring |
| Enverus creds | `enverus` | `USERNAME`, `PASSWORD` (섹션 분리로 AG2 PASSWORD와 충돌 없음) |
| AG2 creds | `ag2` | `USER`, `PASSWORD`, `Profile` |

### 검증 방법

```powershell
python shared\scripts\_env_loader.py
```

→ 모든 섹션과 키 카운트만 출력 (값 마스킹). 예상 결과:

```
[yes_energy]    2 keys (USERNAME, PASSWORD)
[smartbidder]   6 keys (APPLICATION_ID, CLIENT_ID, CLIENT_SECRET, _TENANT, Resource, Node)
[tenaska]       2 keys (TENASKA_USERNAME, TENASKA_PASSWORD)
[enverus]       2 keys
[ag2]           3 keys
[ercot]         3 keys
```

---

## 4. 일일 운영 순서

매일 아침 (07:30 CT, Houston 직전) 두 스크립트를 차례로 실행:

```powershell
cd 'C:\Users\00904\ERCOT Projects\BESS_Biz'

# 1) 어제 실적 (P&L Manager용 input)
python shared\scripts\fetch_pnl_data.py

# 2) 내일 시황 (Market Analyst용 input)
python shared\scripts\fetch_market_data.py
```

→ 산출물이 `shared/data/raw/`, `shared/data/pnl/`, `shared/data/benchmarks/` 에 저장됨.

→ 그 다음 Cowork에서 다음과 같이 호출:

```
"P&L manager, shared/data/pnl/gks/hourly/2026-04-29_summary.json 기준으로
 어제 GKS 실적 정리해줘"

"Market analyst, shared/data/raw/yes-energy/2026-05-01_summary.json 기준으로
 내일 ERCOT 시황 브리핑해줘"

"Reporter, 위 둘 + bess-optimizer + dart-virtual-trader 합쳐 Daily Report"
```

---

## 5. 향후 추가 스크립트 (Phase 2)

| 스크립트 | 담당 에이전트 | 페치 대상 |
|---|---|---|
| `fetch_ag2_forecasts.py` | market-analyst (보강) | AG2 WSI Trader load / wind / weather |
| `fetch_enverus.py` | market-analyst (보강) | Enverus Mosaic outages / PRC / fuel mix |
| `fetch_congestion_data.py` | congestion-analyst | Yes Energy hub-pair basis, CRR auction history (Stage 0/1) |
| `fetch_bess_revenue_dashboard.py` | pnl-manager (주 1회) | ERCOT 全 BESS 60-day disclosure 가공 |

`fetch_market_data.py` + `fetch_pnl_data.py`가 사용자 환경에서 정상 동작 확인된 후 같은 패턴으로 확장.

---

## 6. 흔한 이슈

| 증상 | 원인 / 해결 |
|---|---|
| `ProxyError: Tunnel connection failed: 403` | 네트워크 환경의 proxy 정책. 회사 VPN / 다른 네트워크 시도. |
| `401 Unauthorized` (Yes Energy / Tenaska) | 자격 증명 만료 또는 IP 미등록. 벤더에 갱신/등록 요청. |
| Tenaska 403 (previously-working) | `client` / `resource` 문자열 정확 매칭 점검 + Ascend 측 IP 화이트리스트 |
| Smartbidder 빈 응답 (204) | 해당 flowday에 데이터 없음. publish 시간 후 재시도. Smartbidder는 보통 D+1 새벽 publish. |
| Smartbidder MSAL `secret expired` | client_secret이 12개월 만료. Ascend rep에 재발급 요청. |
| Tenaska validation `[Error 2106]` | over-filter — `elementFilter`에 'GKS' 매칭 안 됨. `--rediscover`로 endpoint 재선택. |
| `.env` PASSWORD 충돌 (AG2 vs Enverus) | section-aware 파서 (`parse_env_sections()` in `fetch_market_data.py`) 사용 또는 `.env` 키 명 분리 (`AG2_PASSWORD`, `ENVERUS_PASSWORD` 등). |

---

## 7. 보안 / git 

다음 파일들은 절대 commit 하지 말 것 — `.gitignore`에 추가 권장:

```
.env
shared/scripts/.cache/
shared/data/raw/
```
