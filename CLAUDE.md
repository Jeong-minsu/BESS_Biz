# BESS_Biz — ERCOT 전력 트레이딩 Multi-Agent System

ERCOT ESS 기반 전력 트레이딩 사업 (GKS BESS 100MW/200MWh 운영 중, '26년 후반 Raven BESS 추가 예정)의 일일 운영 자동화. 8개 sub-agent가 Front/Middle/Back office 구조로 협업.

> **Owner**: Minsoo Jeong (jms2527@gmail.com) | **Today**: 2026-04-30

---

## Architecture (필수 컨텍스트)

```
Front Office (입찰·트레이딩)        Middle Office (시장 인텔리전스)
├ bess-optimizer      ◄────────── ├ market-analyst
├ dart-virtual-trader  (input)    └ congestion-analyst
└ crr-trader                           ▲
       │                               │
       │ self-feedback                 │ 어제 실적
       ▼                               │
Back Office
├ pnl-manager   (Tenaska 실적 + Smartbidder benchmark)
├ evaluator     (주 1회 7개 에이전트 점검)
└ reporter      (07:30 CT Daily Report 통합)
```

상세 R&R: [`ORGANIZATION.md`](./ORGANIZATION.md). 각 에이전트 정의: [`.claude/agents/<name>.md`](./.claude/agents/).

---

## 8 Sub-Agents (Task 도구로 호출)

| Agent | Office | 역할 |
|---|---|---|
| `market-analyst` | Middle | D+1 ERCOT 시황 5-6 bullet 자연어 브리핑 |
| `congestion-analyst` | Middle | Constraint binding probability + λ + 노드 MCC (`agensts/CONGESTION_PROJECT.md` 모델 운영) |
| `bess-optimizer` | Front | GKS DA/RT Energy + AS revenue stack 최적 제안 |
| `dart-virtual-trader` | Front | DART virtual short/long 포지션 + 승률·손익비 |
| `crr-trader` | Front | CRR 옥션 트레이딩 기회 3개 (옥션 사이클별) |
| `pnl-manager` | Back | 전일 GKS 실적 + Smartbidder benchmark + 全 BESS 랭킹 |
| `evaluator` | Back | 주 1회 7개 에이전트 work process / approach / resource 점검 |
| `reporter` | Back | Daily/Weekly 리포트 통합 (자체 분석 추가 X — 취합만) |

**R&R 절대 겹침 금지** — 각 .md 첫머리 "NOT in scope" 섹션 준수.

---

## Folder Layout

```
BESS_Biz/
├── .claude/
│   └── agents/                   ← 8개 sub-agent 정의 (.md + YAML frontmatter)
├── .env                          ← 자격증명 (절대 commit 금지)
├── .env.example                  ← 템플릿
├── agensts/CONGESTION_PROJECT.md ← Congestion 모델 명세 (오타 폴더명 보존)
├── API Docs/                     ← AG2 / Smartbidder / Tenaska / S3 원문
├── skills/                       ← fetch-ercot-data, fetch-smartbidder-data,
│                                   fetch-tenaska-ptp-data, dashboard-report
├── memory/<agent>/{history,learnings,plans}/   ← 에이전트별 메모리 (정의와 분리)
├── shared/
│   ├── config.md                 ← 데이터 소스 우선순위 / 시간·단위 컨벤션
│   ├── data/{forecasts,pnl,benchmarks,crr,raw}/   ← 공유 데이터
│   └── scripts/                  ← production fetch scripts (Python)
│       ├── _env_loader.py        ← section-aware .env 파서
│       ├── fetch_market_data.py  ← Yes Energy + Smartbidder
│       └── fetch_pnl_data.py     ← Tenaska + Smartbidder benchmark
├── reports/{daily,weekly,monthly,ad-hoc}/
└── orchestration/                ← 워크플로우 정의
```

---

## Setup (한 번만)

```bash
# Python 의존성
pip install requests pandas msal

# .env 검증 (7개 섹션 모두 정상 인식 확인)
python shared/scripts/_env_loader.py
```

**.env 형식 규약**: 섹션 헤더(`# Vendor Credentials`)로 그룹화 필수. USERNAME/PASSWORD가 여러 벤더에서 중복 — `_env_loader.py`가 헤더 기반으로 분리한다. 헤더 키워드: `Yes Energy Datalake`, `Yes Energy`, `ERCOT`, `Enverus`, `AG2`, `Smartbidder`, `Tenaska`. 자세한 매핑: [`shared/scripts/README.md`](./shared/scripts/README.md).

---

## Daily Cycle (07:30 CT, Houston 기준)

> 모든 wall-clock 시간은 **CT (America/Chicago, DST 자동)** — ERCOT 운영 native time.
> 07:30 CT 시작 → DAM bid cutoff 10:00 CT 까지 2.5h 검토 버퍼.

```
1. python shared/scripts/fetch_pnl_data.py     ← 어제 실적 (Tenaska + Smartbidder)
2. python shared/scripts/fetch_market_data.py  ← 내일 시황 (Yes Energy + Smartbidder)
3. Task → pnl-manager   "어제 실적 정리"
4. Task → market-analyst, congestion-analyst   (병렬)
5. Task → bess-optimizer, dart-virtual-trader  (병렬, 위 결과 input)
6. Task → reporter      "Daily Report 통합"
```

상세 시퀀스 / 의존성: [`orchestration/daily-0730-workflow.md`](./orchestration/daily-0730-workflow.md).

---

## Behavioral Guidelines (모든 에이전트 공통)

본 프로젝트의 8개 sub-agent (및 main thread)는 모든 코딩·분석 작업 시 [`skills/andrej-karpathy-skills.md`](./skills/andrej-karpathy-skills.md) 의 4가지 원칙을 준수한다:

1. **Think Before Coding** — 가정을 명시하고, 모호하면 물어본다.
2. **Simplicity First** — 요청 범위를 넘는 추상화·기능·에러 처리 금지.
3. **Surgical Changes** — 요청과 직접 연결되는 라인만 변경. 인접 코드 "개선" 금지.
4. **Goal-Driven Execution** — 검증 가능한 success criteria 설정 후 그것을 통과할 때까지 loop.

> Trivial 작업에는 판단으로 가볍게 적용 가능하나, R&R·메모리·자금이 걸린 산출물에서는 4원칙 모두 우선한다.

---

## 핵심 운영 규칙

1. **에이전트 ↔ 메모리 분리**: 정의는 `.claude/agents/`, 메모리는 `memory/<agent>/`. 절대 섞지 말 것.
2. **공유 인프라 단일 루트**: `shared/data/forecasts/`, `shared/data/pnl/` 가 에이전트 간 hand-off 지점.
3. **Skill 호출 패턴**: 외부 skill (`skills/<name>/SKILL.md`)을 `Read` 한 뒤 그 지침대로 코드 작성·실행. Skill 자체를 복제하지 않음.
4. **Self-review 의무**: Front/Middle 5개 에이전트는 매일 `memory/<agent>/learnings/YYYY-MM-DD.md` 작성. 어제 본인 결정 vs 실제 결과 delta 분석.
5. **Spread 부호 규칙**: `spread = DA − RT`. positive ⇒ DA expensive ⇒ short DA / long RT signal. 모든 에이전트 일관 적용.
6. **데이터 leakage 금지**: D+1 forecast 데이터는 D-1 10:00 CPT 이전 publish vintage만 사용 (DAM bid cutoff).
7. **Mock vs Production**: `shared/data/raw/`에 들어있는 데이터가 진짜 fetch 결과인지 mock인지 항상 확인. 산출물에 명시.

---

## 외부 환경 제약

- **ERCOT 데이터 벤더 도메인**: 일부 회사 네트워크/sandbox에서 차단될 수 있음. fetch 스크립트는 사용자 로컬 또는 회사 VPN에서 실행.
- **Tenaska PTP**: 사용자 IP가 Ascend 화이트리스트에 있어야 함. 첫 실행은 endpoint 4개 인터랙티브 디스커버리.
- **Smartbidder MSAL**: client_secret 12개월마다 만료 → Ascend rep에 갱신 요청.

---

## CONGESTION_PROJECT (별도 ML 프로젝트)

`agensts/CONGESTION_PROJECT.md` (오타 폴더명 의도적 보존)는 constraint-level shadow price 예측 모델 명세. 현재 **Stage 0 — Infrastructure** 단계. `congestion-analyst` 에이전트가 운영·진행. Stage 진행은 `memory/congestion-analyst/plans/stage-progress.md` 추적.

---

## 참고 문서

- 시작하기: [`GETTING_STARTED.md`](./GETTING_STARTED.md)
- R&R 매트릭스 (RACI): [`ORGANIZATION.md`](./ORGANIZATION.md)
- 데이터 소스 / 컨벤션: [`shared/config.md`](./shared/config.md)
- Daily/Weekly/On-demand 워크플로우: [`orchestration/`](./orchestration/)
- **Behavioral guidelines (모든 에이전트 공통)**: [`skills/andrej-karpathy-skills.md`](./skills/andrej-karpathy-skills.md)
