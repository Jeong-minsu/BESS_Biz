# pnl-manager Improvement Plan — 2026-W36

## W36 평가 요약

- Work Process: D+ (7/7 reports; 1/7 learnings — 4주 연속 0~1/7; PRODUCTION 데이터 3일 수신 후에도 learnings 1건)
- Working Approach: B (PRODUCTION reports 정확; DEGRADED 적절히 처리; 수치 조작 없음; 포맷 일관성 유지)
- Resources: C (Tenaska PRODUCTION Aug 31-Sep 2 = 3일, DEGRADED Sep 3-6 = 4일; Smartbidder Day 40+ 만료)
- Overall: C-

---

## W36 Tenaska 데이터 가용성

| Flowday | Tenaska 상태 | Learnings 작성 여부 |
|---|---|---|
| 2026-08-31 | PRODUCTION | **없음** (공백) |
| 2026-09-01 | PRODUCTION | **있음** (`learnings/2026-09-01.md`) |
| 2026-09-02 | PRODUCTION | **없음** (공백) |
| 2026-09-03 | DEGRADED | — |
| 2026-09-04 | DEGRADED | — |
| 2026-09-05 | DEGRADED | — |
| 2026-09-06 | DEGRADED | — |

**1/7 learnings. PRODUCTION 3일 중 1일만 learnings 작성 (33%). 4주 연속 0-1/7 — W33: 1/7, W34: 0/7, W35: 0/7, W36: 1/7.**

---

## 핵심 개선 포인트 (Critical)

### 1. Learnings 작성 — PRODUCTION 날 즉시 의무화

PRODUCTION 데이터 수신 날 learnings 작성은 선택이 아닌 의무. Aug 31, Sep 2 모두 PRODUCTION 데이터 가용 상태에서 learnings 미작성. 이는 평가 시스템이 추적할 수 있는 근거 없는 누락.

**W37 Action**: PRODUCTION 데이터 수신 시 당일 내 learnings 작성. 미작성 시 다음 날 소급 작성 금지 (T+0 의무 명시).

최소 learnings 구성:
- 당일 GKS 실적 (4개 항목: DA Energy, RT Energy, AS total, Grand Total)
- 전일 대비 주요 변화 및 원인 1-3줄
- Smartbidder benchmark 비교 (N/A면 N/A 명시)
- DA charge bid 실행 여부 (현재 W36 7th+ 연속 실패 추적 중)
- bess-optimizer 권장안 대비 실적 delta (P&L 피드백 루프)

### 2. 누락 Learnings 소급 처리

Aug 31, Sep 2 Tenaska PRODUCTION 데이터가 이미 수신됨. 해당 날짜 learnings 소급 작성 가능.
소급 작성 시 상단에 `[RETROACTIVE — filed YYYY-MM-DD, original data available]` 태그 필수.

### 3. DA charge bid failure 추적 테이블 생성

W36에서 DA charge bid failure가 7th+ 연속으로 확인됨. pnl-manager가 이를 실데이터 기반으로 추적하는 적합한 에이전트.

`memory/pnl-manager/da-charge-tracking.md` 생성:
- 각 flowday DA Energy 실행 여부 (실청산 $0 또는 정상)
- bess-optimizer 권장 충전 시간대 vs 실제 충전 시간대
- 추정 opportunity cost (매 실패 사이클)

---

## 구체적 액션 아이템 (W37 기준)

| 항목 | 기한 | 상태 |
|---|---|---|
| W37 PRODUCTION 날 당일 learnings 작성 | 해당 데이터 수신일 | 의무 — 4주 연속 실패 |
| Aug 31, Sep 2 learnings 소급 작성 | 즉시 | 신규 — OVERDUE |
| `memory/pnl-manager/da-charge-tracking.md` 생성 | W37 Day 1 이전 | 신규 |
| Tenaska 화이트리스트 에스컬레이션 재확인 (사용자 액션) | 즉시 | W31부터 open |
| Smartbidder 복구 시 benchmark 비교 즉시 재개 | 복구 즉시 | 대기 |
| 누적 실적 추적 테이블 (`shared/data/pnl/2026-cumulative.md`) 초안 | 2026-09-14 (W37 말) | W35 계획 미이행 |

---

## 에스컬레이션 조항

**4주 연속 0~1/7 learnings**. W37에서도 ≤1/7이면: pnl-manager process 정지 권고 및 사용자 재정의 요청. 에이전트 definition에 "PRODUCTION 데이터 수신일 learnings 작성 의무" 명문화 요청.

---

## 지속 모니터링 항목

- **Learnings**: W37 PRODUCTION 날 전부 당일 작성. 목표 ≥3/7 (최소), 이상적 7/7.
- **Tenaska IP 화이트리스트**: 매일 fetch 시도 상태 기록.
- **DA charge bid failure**: 실데이터로 bess-optimizer 이슈 추적 지원.
- **Smartbidder Day 40+**: 복구 즉시 benchmark 비교 재개.
