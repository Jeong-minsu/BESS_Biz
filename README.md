# BESS_Biz — ERCOT 전력 트레이딩

ERCOT ESS 기반 전력 트레이딩 사업의 수익 극대화 및 운영 최적화를 위한 멀티 에이전트 운영 시스템. 8개 에이전트(Front/Middle/Back office) + 공유 데이터 인프라 + Daily/Weekly 오케스트레이션으로 구성.

---

## 1. 사업 개요

| 항목 | 내용 |
|---|---|
| 운영 자산 | **GKS BESS** (Great Kiskadee Storage) - 100MW / 200MWh, 100% Merchant |
| 추가 예정 | **Raven BESS** - 100MW / 200MWh ('26년 후반 운영 시작) |
| 사업 영역 | DA/RT Energy, DA/RT Ancillary Services (RRS, ECRS, Non-spin, Reg-up/down), DART Virtual, CRR |
| 확장 방향 | CRR Trading 등 Power Trading 영역 점진 확장 |

---

## 2. 조직 구조 (Multi-Agent)

```
┌────────────────────────────────────────────────────────────────┐
│                         REPORTER                                │
│      (Daily 07:30 / Weekly Report - 결과 취합 & 배포)           │
└────────────┬────────────────────────────────────────┬──────────┘
             │                                        │
   ┌─────────┴─────────┐                  ┌──────────┴──────────┐
   │   FRONT OFFICE    │                  │   MIDDLE OFFICE     │
   │ (Trading & Bid)   │ ◄──────INPUT──── │ (Market Intel)      │
   │                   │                  │                     │
   │ • BESS Optimizer  │                  │ • Market Analyst    │
   │ • DART Trader     │                  │ • Congestion Analyst│
   │ • CRR Trader      │                  │                     │
   └─────────┬─────────┘                  └─────────────────────┘
             │
             │ Self-feedback (전날 lookback)
             ▼
   ┌────────────────────────────────────────────────────────────┐
   │                    BACK OFFICE                             │
   │  • P&L Manager   (GKS 실적 / Smartbidder benchmark)        │
   │  • Evaluator     (전 에이전트 효과성·효율성 점검)          │
   └────────────────────────────────────────────────────────────┘
```

상세 R&R은 [`ORGANIZATION.md`](./ORGANIZATION.md) 참고.

---

## 3. 폴더 구조 (단일 BESS_Biz/ 루트)

```
BESS_Biz/                              ← 작업 루트 (모든 path가 여기 기준)
│
├── .env                               ← 모든 벤더 인증 (Yes Energy, AG2, Enverus, Smartbidder, Tenaska)
│
│  ─── 외부 자산 (skill/문서/모델 명세) ──────────────
├── API Docs/                          ← AG2, Smartbidder, Tenaska, S3 Datalake 원문 (4개 .txt)
├── skills/                            ← 데이터 페치 + 대시보드 skill (4개)
│   ├── fetch-ercot-data/
│   ├── fetch-smartbidder-data/
│   ├── fetch-tenaska-ptp-data/
│   └── dashboard-report.skill/
├── agensts/                           ← CONGESTION_PROJECT.md (오타 그대로 보존; congestion-analyst가 oversight)
│
│  ─── 멀티 에이전트 시스템 (Claude Code sub-agents) ────
├── CLAUDE.md                          ← Claude Code 자동 로드 (project-level 컨텍스트)
├── README.md                          ← 이 파일
├── ORGANIZATION.md                    ← 8개 에이전트 R&R 매트릭스 (RACI)
├── GETTING_STARTED.md                 ← 첫 사이클 운영 가이드
│
├── .claude/
│   └── agents/                        ← 8개 sub-agent 정의 (Claude Code Task 도구로 호출)
│       ├── README.md
│       ├── market-analyst.md
│       ├── congestion-analyst.md
│       ├── bess-optimizer.md
│       ├── dart-virtual-trader.md
│       ├── crr-trader.md
│       ├── pnl-manager.md
│       ├── evaluator.md
│       └── reporter.md
│
├── memory/                            ← 에이전트별 메모리 (정의와 분리; plan/history/learnings 폴더 분리)
│   ├── README.md
│   ├── market-analyst/{history,learnings,plans}/
│   ├── bess-optimizer/{history,learnings,plans}/
│   ├── dart-virtual-trader/{history,learnings,plans,model}/
│   ├── crr-trader/{history,learnings,plans,auction-history}/
│   ├── congestion-analyst/{history,learnings,plans}/  ← plans/stage-progress.md 필수
│   ├── pnl-manager/{history,plans} + data-quality.md
│   ├── evaluator/{history,plans} + cross-agent-patterns.md, improvement-tracker.md
│   └── reporter/{history,plans} + template-issues.md
│
├── shared/                            ← 공유 인프라 (모든 에이전트 동일 path 참조)
│   ├── config.md                      ← 데이터 소스 / 시간·단위 컨벤션
│   ├── data/
│   │   ├── forecasts/{market-view,congestion}/
│   │   ├── pnl/gks/{hourly,daily}/
│   │   ├── benchmarks/smartbidder/{hourly,daily}/
│   │   ├── crr/{auction-results,basis-history}/
│   │   └── raw/{yes-energy,smartbidder,tenaska}/
│   ├── prompts/
│   └── schemas/
│
├── reports/                           ← 산출 리포트
│   ├── daily/{market-briefing,congestion,bess-stack,dart-position,pnl,crr-opps}/
│   ├── weekly/{structural-update,bess-revenue-dashboard,bess-dart-virtual-dashboard,evaluator}/
│   ├── monthly/operator-benchmark/
│   └── ad-hoc/{crr,evaluator}/
│
└── orchestration/
    ├── daily-0730-workflow.md         ← 매일 07:30 CT (Houston) 워크플로우 (T-90m → T-15m 시퀀스)
    ├── weekly-workflow.md
    └── on-demand-workflows.md
```

---

## 4. 핵심 운영 원칙

1. **R&R 명확화**: 각 에이전트의 역할은 YAML frontmatter `description` 필드에 명시 — **겹침 금지**
2. **에이전트 ↔ 메모리 분리**: 에이전트 정의(plan/role)와 메모리(history)는 다른 폴더에 저장 — 섞이지 않게
3. **공유 인프라**: `shared/` 폴더 하나로 모든 에이전트가 동일 데이터에 접근
4. **자가 피드백**: Front/Middle 오피스 에이전트는 **매일 전날 lookback & self-review**를 통해 점진 발전
5. **오케스트레이션**: 매일 07:30 CT 워크플로우가 모든 에이전트를 정해진 순서로 트리거

---

## 5. 일일 워크플로우 (07:30 CT, Houston 기준)

| 단계 | 시각(목표) | 담당 에이전트 | 산출물 |
|---|---|---|---|
| 1 | T-90m | P&L Manager | 전일 GKS 실적 + Smartbidder 벤치마크 산출 |
| 2 | T-75m | Market Analyst | ERCOT 다음날 시황 브리핑 |
| 3 | T-75m | Congestion Analyst | 다음날 혼잡 / Constraint 분석 |
| 4 | T-60m | BESS Optimizer | 다음날 DA/RT Energy + AS revenue stack 제안 |
| 5 | T-60m | DART Virtual Trader | 다음날 DART virtual position 제안 |
| 6 | T-45m | CRR Trader | (조건부) CRR 트레이딩 기회 3개 |
| 7 | T-30m | Front/Middle 전 에이전트 | 전날 자기 결정에 대한 self-review 작성 |
| 8 | T-15m | Reporter | Daily Report 생성 → 사용자 전달 |

상세 흐름은 [`orchestration/daily-0730-workflow.md`](./orchestration/daily-0730-workflow.md) 참고.

---

## 6. 사용 데이터 소스 & 외부 자산

같은 루트 (`BESS_Biz/`) 안의 자산을 그대로 활용한다 (별도 path prefix 없음).

| 자산 | 위치 | 용도 |
|---|---|---|
| **fetch-ercot-data** skill | `skills/fetch-ercot-data/SKILL.md` | Yes Energy / Enverus / AG2 / ERCOT API → ERCOT 시장 데이터 |
| **fetch-smartbidder-data** skill | `skills/fetch-smartbidder-data/SKILL.md` | Smartbidder benchmark, DA/RT 가격 예측, P(DA<RT) |
| **fetch-tenaska-ptp-data** skill | `skills/fetch-tenaska-ptp-data/SKILL.md` | GKS 실적 (Energy/AS, DA bid/offer, HSL) |
| **dashboard-report** skill | `skills/dashboard-report.skill/SKILL.md` | TradingView-style 단일 HTML 리포트 |
| **CONGESTION_PROJECT** | `agensts/CONGESTION_PROJECT.md` | Constraint-level shadow price 예측 모델 (Stage 0 진행 중) |
| **API Docs** | `API Docs/*.txt` | AG2 / Smartbidder / Tenaska / S3 Datalake 원문 |
| **`.env`** | `.env` | 모든 벤더 인증 정보 (Yes Energy, AG2, Enverus, Smartbidder, Tenaska, AWS) |

데이터 소스 결정 규칙은 [`shared/config.md`](./shared/config.md), 데이터 우선순위·게터 결정표는 위 `fetch-ercot-data` skill 참고.

> **중요**: 위 자산(`API Docs/`, `skills/`, `agensts/CONGESTION_PROJECT.md`)은 멀티 에이전트 시스템의 **공유 입력**이다. skill/API doc은 직접 수정하지 말고 호출만 한다. CONGESTION_PROJECT.md는 `congestion-analyst`만 수정 권한.

---

## 7. 시작하기

```
1. 매일 아침 운영 → Reporter 에이전트 호출 (오케스트레이션이 자동으로 다른 에이전트 트리거)
2. 특정 분석 필요 → 해당 에이전트 직접 호출
   예: "Market Analyst, 내일 ERCOT 시황 브리핑해줘"
3. 평가/개선 → 매주 1회 Evaluator 실행 → 개선 포인트 도출
```
