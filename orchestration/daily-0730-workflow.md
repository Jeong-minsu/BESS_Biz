# Daily 07:30 CT Workflow

매일 **Houston 시간 오전 07:30 CT** (America/Chicago, DST 자동) 에 실행되는 daily run.

> **목표**: D+1 ERCOT operating day에 대한 의사결정 패키지 (BESS stack + DART positions + 시황 + 실적 lookback)를 단일 Daily Report로 사용자에게 전달.

> **DAM bid cutoff**: ERCOT D 10:00 CT (D+1 trading day 용).
> 07:30 CT 시작 → 10:00 CT cutoff 까지 **2.5시간 검토 버퍼**. ERCOT 운영 native time, 한국에서 보면 21:30 (DST) / 22:30 (winter) KST.

---

## 1. Sequence Diagram

```
Wall Clock (CT)    Agent                        Output
───────────────────────────────────────────────────────────────
T-90m  (06:00)     pnl-manager                  shared/data/pnl/gks/{D-1}
                                                shared/data/benchmarks/smartbidder/{D-1}
                                                reports/daily/pnl/{D-1}.md
                       │
                       ▼
T-75m  (06:15)     market-analyst               reports/daily/market-briefing/{D+1}.md
                                                shared/data/forecasts/market-view/{D+1}.md
                   congestion-analyst    [parallel]
                                                reports/daily/congestion/{D+1}.md
                                                shared/data/forecasts/congestion/{D+1}.md
                       │
                       ▼
T-60m  (06:30)     bess-optimizer               reports/daily/bess-stack/{D+1}.md
                   dart-virtual-trader   [parallel]
                                                reports/daily/dart-position/{D+1}.md
                       │
                       ▼
T-45m  (06:45)     crr-trader  [conditional — 옥션 D-7 시기에만]
                                                reports/daily/crr-opps/{D+1}.md
                       │
                       ▼
T-30m  (07:00)     [Front/Middle 5개 에이전트 self-review]
                   (각자 memory/<agent>/learnings/{D-1}.md 작성)
                       │
                       ▼
T-15m  (07:15)     reporter                     reports/daily/{date}.md
                                                reports/daily/{date}.html
                       │
                       ▼
T-0    (07:30)     사용자에게 computer:// 링크 전달 ✅
```

---

## 2. Agent Trigger 순서 & 의존성

| 단계 | Time | Agent(s) | Depends on | Output 위치 |
|---|---|---|---|---|
| ① | T-90m | `pnl-manager` | — (Tenaska / Smartbidder 직접 호출) | `shared/data/pnl/`, `reports/daily/pnl/` |
| ② | T-75m | `market-analyst` | (pnl-manager 결과는 self-review용으로 참조) | `shared/data/forecasts/market-view/`, `reports/daily/market-briefing/` |
| ② | T-75m | `congestion-analyst` | — (market-analyst와 병렬) | `shared/data/forecasts/congestion/`, `reports/daily/congestion/` |
| ③ | T-60m | `bess-optimizer` | ②(둘 다) + ① | `reports/daily/bess-stack/` |
| ③ | T-60m | `dart-virtual-trader` | ②(둘 다) + ① | `reports/daily/dart-position/` |
| ④ | T-45m | `crr-trader` (조건부) | ② congestion-analyst | `reports/daily/crr-opps/` |
| ⑤ | T-30m | Front/Middle 5개 self-review | ① pnl-manager (전일 실적) | `memory/<agent>/learnings/` |
| ⑥ | T-15m | `reporter` | ①②③④⑤ 전부 | `reports/daily/{date}.md`, `.html` |

> **데이터 prep (Bash, ① 직전)**: `fetch_pnl_data.py` → `fetch_market_data.py` → `recommend_as_position.py` 가 에이전트 호출 전 순차 실행된다. `recommend_as_position.py` 는 `fetch_market_data.py` 산출물(`shared/data/raw/yes-energy/{D+1}.csv`)을 소비해 fine playbook 시간별 AS 추천(`shared/data/forecasts/as-playbook/{D+1}.json`)을 생성 — ③ `bess-optimizer` 의 AS 배분 prior로 쓰인다 (in-sample 학습 → 절대 룰 아닌 prior).

---

## 3. Conditional Triggers

### CRR Trader 호출 조건
- **월간 PCRR 옥션 D-7 ~ D-1** 기간 일일 호출 (옥션 stage tracking)
- 그 외에는 **사용자 ad-hoc 호출** 시에만 (e.g., "내일 조회 ad-hoc CRR view")

### Weekly-only 산출물 (월요일 추가)
- `pnl-manager`: ERCOT 全 BESS revenue dashboard ('26.01.01 ~ latest)
- `pnl-manager`: ERCOT 全 BESS DART virtual dashboard
- `market-analyst`: 시장 구조 / 정책 update
- `evaluator`: 7개 에이전트 weekly evaluation
- `reporter`: Weekly Report 생성 (위 4개 + 일간 누적 통합)

---

## 4. 데이터 가용성 체크 (Pre-flight)

매일 ① 단계 시작 직전, 다음 데이터 ready 여부 확인:

| 데이터 | 가용성 시간 (CT, Houston) |
|---|---|
| Tenaska 전일 실적 (final) | D 04:00 CT (D-1 정산 마감 후) |
| Smartbidder 전일 revenue | D 02:00 CT |
| Yes Energy DAM bidclose | D-1 10:00 CT |
| Yes Energy load/wind/solar bidclose | D-1 10:00 CT |
| ERCOT 60-day disclosure (전전날) | D 00:00 CT |

D 07:30 CT 시점에서 위 모두 가용하므로 ✅. 단, 정산 지연(holidays) 시 `pnl-manager`가 quality issue 기록.

---

## 5. Self-Review 단계 상세 (T-30m)

Front/Middle 5개 에이전트가 각자 본인 memory에 self-review 파일 작성:

```
memory/market-analyst/learnings/{D-1}.md         ← 어제 본인 view vs 실측
memory/congestion-analyst/learnings/{D-1}.md     ← 어제 binding 예측 vs 실측
memory/bess-optimizer/learnings/{D-1}.md         ← 어제 stack 추천 vs 실현 + vs Smartbidder
memory/dart-virtual-trader/learnings/{D-1}.md    ← 어제 포지션 hit rate, 손익비
memory/crr-trader/learnings/                     ← 옥션 후에만 (대부분 N/A)
```

각 self-review는 4-5줄 자연어 요약 + 2-3개 정량 지표 + 다음번 적용할 1-2 액션.

> Self-review 의무·내용 규약의 SoT는 `ORGANIZATION.md §6`. 본 절은 daily cycle 상의 타이밍·파일 경로만 정의한다.

---

## 6. Reporter 합치기 절차 (T-15m)

```
Step A. 의존 산출물 6종 (① ~ ④) 존재 여부 확인
Step B. self-review 5종 존재 여부 확인 (T-30m 마감 후)
Step C. 누락 발견 시 → 해당 에이전트 retrigger (1회 재시도)
Step D. 모두 ready → reporter 통합
Step E. Cross-agent 모순 check (e.g., market-analyst peak HE vs bess-optimizer top hour 일치 여부)
Step F. dashboard-report skill 호출 → HTML 생성
Step G. 사용자에게 link 전달
Step H. memory/reporter/history/{D+1}.md 사본 저장
```

---

## 7. 실행 방법

### 옵션 A: 자연어 호출 (가장 간단)

```
"오늘 daily cycle 돌려줘"
```

→ Claude Code가 다음 시퀀스를 자동 진행 (각 단계 결과 노출):

```python
# 1. 데이터 페치 & D+1 AS 추천 (Bash)
Bash("python shared/scripts/fetch_pnl_data.py")
Bash("python shared/scripts/fetch_market_data.py")
Bash("python shared/scripts/recommend_as_position.py")   # fine playbook → as-playbook/{D+1}.json

# 2. P&L 정리 (Task — 단일 sub-agent)
Task(subagent_type="pnl-manager", prompt="...")

# 3. 시황·혼잡 분석 (Task — 병렬 호출, 단일 메시지에 두 Task)
[Task(subagent_type="market-analyst",      prompt="..."),
 Task(subagent_type="congestion-analyst",  prompt="...")]

# 4. 트레이딩 결정 (Task — 병렬, 위 결과를 input)
[Task(subagent_type="bess-optimizer",      prompt="..."),
 Task(subagent_type="dart-virtual-trader", prompt="...")]

# 5. 통합 (Task)
Task(subagent_type="reporter", prompt="...")
```

각 Task 호출은 격리된 컨텍스트에서 sub-agent 실행 → 요약 결과만 메인으로 반환. 컨텍스트 폭발 방지.

### 옵션 B: Slash Command (반복 사용 시)

`/daily-cycle` 한 줄로 호출. 명령 정의는 `.claude/commands/daily-cycle.md` 에 있다.
실행 시퀀스의 **single source of truth는 본 문서 §1~§2** — `daily-cycle.md` 는 그 구현이며, 시퀀스를 여기 다시 적지 않는다 (drift 방지).

### 옵션 C: OS-level 스케줄링

매일 07:30 자동 실행.

```powershell
# Windows Task Scheduler
schtasks /create /tn "ERCOT Daily Cycle" `
  /tr "claude -c '/daily-cycle'" `
  /sc daily /st 07:30
```

```bash
# macOS / Linux cron
30 7 * * * cd ~/BESS_Biz && claude -c "/daily-cycle"
```

### 옵션 D: Hooks (Phase 2)

`.claude/settings.json`의 hook으로 특정 prompt 패턴 매칭 시 사전 작업 자동 실행. 운영 안정화 후 도입.

---

## 8. Failure Handling

| 실패 시나리오 | 대응 |
|---|---|
| Tenaska 전일 데이터 미게시 | pnl-manager가 `data-quality.md`에 기록 + `evaluator`에 알림. Daily Report 진행 (실적 N/A로 표기). |
| Smartbidder 401 (인증 만료) | `.env`의 `SMARTBIDDER_CLIENT_SECRET` 재발급 필요. 사용자에 알림 후 일시 중단. |
| Yes Energy 429 (rate limit) | Skill 내장 backoff (5/10/15s) 시도. 5분 후 재시도. 그래도 실패 시 사용자에 알림. |
| Reporter T-15m 도착 시 의존 산출물 누락 | 누락 에이전트 1회 retrigger. 두 번째 실패 시 partial report (누락 섹션 명시) + 사용자에 escalate. |
| Self-review 미작성 | Daily Report에 "self-review pending" 표기. Evaluator weekly run에서 패널티 점수. |

---

## 9. 시간대 노트

**모든 wall-clock 시간은 CT (Central Time, America/Chicago, DST 자동)** = Houston 로컬 시간.
- Standard (winter): CST = UTC−6
- Daylight (summer): CDT = UTC−5
- ERCOT 운영 native time. 모든 vendor (ERCOT API, Yes Energy, Smartbidder, Tenaska 의 로컬 변환) 도 동일 기준.

**Cycle 타이밍**:
- D 07:30 CT 사이클 시작
- D 10:00 CT DAM bid cutoff (= 트레이딩 데이 D+1 용)
- D+1 00:00 CT ERCOT operating day D+1 시작
- 즉 cycle은 트레이딩 D+1 의 DAM bid 를 D 10:00 CT 마감 직전 2.5h 윈도우에서 준비

**KST 환산** (한국에서 모니터링용 참고):
- DST 시즌 (Mar–Nov): D 07:30 CDT = D 21:30 KST
- Standard 시즌 (Nov–Mar): D 07:30 CST = D 22:30 KST

리포팅 단순화: Daily Report의 "D+1"은 항상 **다음 ERCOT operating day** (트레이딩 데이) 를 의미. 모든 timestamp 는 CT/CPT로 표기.
