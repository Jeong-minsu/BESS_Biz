# Getting Started — 운영 가이드 (Claude Code 환경)

프로젝트 골격이 준비되었으니 첫 사이클을 돌리는 방법.

> **실행 환경**: Claude Code (VS Code 또는 CLI). Cowork 환경에서는 ERCOT 데이터 벤더 도메인이 차단되어 데이터 페치가 막힘.

---

## 1. 매일 아침 운영 (07:30 CT, Houston 기준)

### 가장 간단한 방법: 자연어로 호출

```
"오늘 daily cycle 돌려줘"
```

→ Claude가 다음 시퀀스로 진행:
1. Bash → `python shared/scripts/fetch_pnl_data.py` (어제 실적)
2. Bash → `python shared/scripts/fetch_market_data.py` (내일 시황)
3. Task → `pnl-manager` (어제 실적 정리)
4. Task → `market-analyst`, `congestion-analyst` (병렬 실행)
5. Task → `bess-optimizer`, `dart-virtual-trader` (병렬, 위 결과 input)
6. Task → `reporter` (Daily Report 통합)

### 자동화: Hook 또는 cron

OS 레벨에서 매일 07:30 CT에 Claude Code 세션 자동 실행 (Windows Task Scheduler 또는 launchd).

```powershell
# Windows 예시 — schtasks
schtasks /create /tn "ERCOT Daily Cycle" /tr "claude 'daily cycle 돌려줘'" /sc daily /st 07:30
```

---

## 2. 개별 에이전트 호출 (ad-hoc)

Claude Code의 Task 도구가 `.claude/agents/<name>.md` 의 sub-agent를 격리 컨텍스트에서 실행. 자연어로 요청하면 Claude가 알아서 적절한 에이전트로 위임:

| 상황 | 자연어 | Claude의 동작 |
|---|---|---|
| 시황만 빠르게 | "내일 시황 브리핑" | Task → market-analyst |
| BESS stack 재검토 | "내일 GKS stack 다시 짜줘" | Task → bess-optimizer |
| DART 포지션 보수적 | "내일 DART, conviction 60% 이상만" | Task → dart-virtual-trader |
| CRR 옥션 D-7 | "다음 CRR 옥션 기회 3개" | Task → crr-trader |
| 어제 실적 | "어제 GKS 실적 정리" | Bash 페치 → Task → pnl-manager |
| 에이전트 점검 | "지난주 dart-virtual-trader 점검" | Task → evaluator |

---

## 3. 첫 실행 시 체크리스트

### Step 1. 자격 증명 확인
`.env`에 다음 키가 모두 있는지 확인:
- Yes Energy: `YES_ENERGY_USERNAME`, `YES_ENERGY_PASSWORD`
- Smartbidder: `SMARTBIDDER_CLIENT_ID`, `SMARTBIDDER_CLIENT_SECRET`, `SMARTBIDDER_CLIENT`, `SMARTBIDDER_RESOURCE`
- Tenaska: `TENASKA_USERNAME`, `TENASKA_PASSWORD`
- AG2: `USER`, `PASSWORD`, `Profile`
- Enverus: `USERNAME`, `PASSWORD` (Enverus 전용 블록)
- (선택) AWS S3, ERCOT API

### Step 2. Tenaska endpoint 디스커버리 (1회만)
`pnl-manager` 첫 실행 시 Tenaska PTP의 `{ROOT}` / `{ENDPOINT}` slug을 디스커버리하고 `shared/config.md` 또는 별도 파일에 기록. (skill 문서 §PTP hierarchy 참고)

### Step 3. Smoke test
각 에이전트를 1회씩 단독 호출해 데이터 가져오기 OK인지 확인:
- "Market analyst, 어제 ERCOT 데이터 가져와봐" — Yes Energy + AG2 인증 확인
- "P&L manager, 어제 GKS 실적 가져와봐" — Tenaska + Smartbidder 인증 확인
- "Congestion analyst, 어제 hub-pair basis 보여줘" — Yes Energy 확인

### Step 4. 첫 Daily Report 생성
"Reporter, 오늘 Daily Report 만들어줘"

---

## 4. 흔한 첫 사이클 이슈

| 이슈 | 원인 | 해결 |
|---|---|---|
| 401 Unauthorized | 자격 증명 만료 / IP 미등록 | Smartbidder는 12개월마다 secret 회전. Tenaska는 IP 화이트리스트 점검. |
| 빈 데이터 | publish 시간 전 / 휴일 | 위 §3 가용성 시간표 확인 |
| Tenaska endpoint slug 모름 | 디스커버리 미완료 | `GET /ptp` → `GET /ptp/{root}` 한 번 호출해 ID 매핑 확보 |
| Self-review 비어있음 | 에이전트가 어제 실행 X | 어제 산출물 부재 시 self-review skip 가능 (defaults to "first run, no prior") |
| Reporter HTML 깨짐 | dashboard-report skill 미호출 | reporter.md §7 가이드 참고, dashboard-report skill을 명시적으로 invoke |

---

## 5. 한 사이클 직접 돌려보기 (수동 단계별)

각 에이전트의 산출물을 한 번씩 직접 만들어보며 시스템을 익히는 방법:

```
Day 0 (오늘):
  0. "shared/scripts/fetch_market_data.py 돌려서 내일 데이터 가져와"
     → Claude가 Bash로 실행, shared/data/raw/ 에 산출
  1. "내일 ERCOT 시황 브리핑"
     → Task → market-analyst → reports/daily/market-briefing/{tomorrow}.md
  2. "내일 hub-pair basis view"
     → Task → congestion-analyst → reports/daily/congestion/{tomorrow}.md
  3. "내일 GKS stack 추천"
     → Task → bess-optimizer → reports/daily/bess-stack/{tomorrow}.md
  4. "내일 DART 포지션"
     → Task → dart-virtual-trader → reports/daily/dart-position/{tomorrow}.md
  5. "위 4개 + 어제 P&L 합쳐서 Daily Report"
     → Task → reporter → reports/daily/{tomorrow}.html

Day 1 (내일 아침):
  6. "fetch_pnl_data.py 돌려서 어제 실적 가져와"
     → Bash 실행, shared/data/pnl/ 에 산출
  7. "어제 GKS 실적 정리"
     → Task → pnl-manager
  8. "Front/Middle 5개 에이전트에게 어제 결정 self-review 요청"
     → Task 5번 (병렬), 각 memory/<agent>/learnings/ 에 작성
  9. "오늘 daily cycle"
     → 정상 사이클 진입
```

---

## 6. 다음 단계 (Phase 2)

이번 골격에서 의도적으로 제외한 항목들:

- **별도 Orchestrator 에이전트** — 의존성 그래프 기반 자동 실행 (현재는 Reporter가 trigger 역할)
- **CONGESTION_PROJECT Stage 0 → 1 진입** — congestion-analyst의 본격적 모델링
- **외부 BESS revenue agent 연동** — pnl-manager의 全 BESS 랭킹은 60-day disclosure로 시작, Stage 2에서 외부 agent 연동
- **DART virtual 자체 모델 학습** — dart-virtual-trader의 Smartbidder 의존도 낮추기
- **Annual review template** — 1년 누적 리포트

이 항목들은 이번 골격이 안정화된 뒤 (≈ 4-6주 후) 단계적으로 추가.

---

## 7. 폴더 구조 한눈에 (BESS_Biz/ 단일 루트)

```
BESS_Biz/
├── .env                          ← 모든 벤더 인증
├── README.md / ORGANIZATION.md / GETTING_STARTED.md
│
│  ─── 외부 자산 (이미 존재) ────────────────────
├── API Docs/                     ← 4개 .txt (AG2, Smartbidder, Tenaska, S3 Datalake)
├── skills/                       ← 4개 skill (fetch-ercot-data, fetch-smartbidder-data, fetch-tenaska-ptp-data, dashboard-report)
├── agensts/                      ← CONGESTION_PROJECT.md (오타 그대로 보존)
│
│  ─── 멀티 에이전트 시스템 (Claude Code sub-agents) ──
├── CLAUDE.md                     ← Claude Code 매 세션 자동 로드
├── .claude/
│   └── agents/                   ← 8개 sub-agent (.md + YAML frontmatter)
│       ├── market-analyst.md / congestion-analyst.md
│       ├── bess-optimizer.md / dart-virtual-trader.md / crr-trader.md
│       ├── pnl-manager.md / evaluator.md / reporter.md
│       └── README.md
│
├── memory/                       ← 에이전트별 메모리 (정의와 분리; plan/history/learnings 폴더 분리)
│   └── <agent>/{history,learnings,plans}/   ← 8개 에이전트별
│
├── shared/                       ← 공유 인프라
│   ├── config.md                 ← 데이터 소스 / 시간·단위 컨벤션
│   ├── data/{forecasts,pnl,benchmarks,crr,raw}/
│   ├── prompts/ · schemas/
│
├── reports/                      ← 산출 리포트
│   ├── daily/{market-briefing,congestion,bess-stack,dart-position,pnl,crr-opps}/
│   ├── weekly/{structural-update,bess-revenue-dashboard,bess-dart-virtual-dashboard,evaluator}/
│   ├── monthly/operator-benchmark/
│   └── ad-hoc/{crr,evaluator}/
│
└── orchestration/
    ├── daily-0730-workflow.md
    ├── weekly-workflow.md
    └── on-demand-workflows.md
```

**주요 path 참조 규칙**:
- skill 호출: `skills/fetch-ercot-data/SKILL.md` (BESS_Biz/ prefix 없이)
- 자격 증명: `.env` (자동 로드)
- congestion 모델 명세: `agensts/CONGESTION_PROJECT.md` (오타 그대로)
