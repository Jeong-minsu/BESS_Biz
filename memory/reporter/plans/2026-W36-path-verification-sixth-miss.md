# reporter Improvement Plan — 2026-W36

## W36 평가 요약

- Work Process: B- (7/7 reports 유지; canonical-paths.md 부재; "Cycle Health — Path Verification" 섹션 6주 연속 미구현; [WRONG DIR] 태그 미사용)
- Working Approach: B (정확한 에이전트 산출물 취합; 자체 분석 없음; 운영 알림 섹션 품질 향상 — DA charge bid failure, AS overlap 플래그 정확)
- Resources: B- (전 에이전트 산출물 취합; 잘못된 경로 그대로 전달; canonical-paths.md 미유지)
- Overall: B-
- Trend: → (7/7 reports 유지; 경로 검증 이슈 동일 패턴)

---

## W36 Wrong Path Citations (확인된 오기재)

| 날짜 | 에이전트 | 인용 경로 | 정규 경로 | [WRONG DIR] 태그 |
|---|---|---|---|---|
| 2026-09-04 | bess-optimizer | `bess-stack/2026-09-04.md` | `bess-optimizer/` | **없음** |
| 2026-09-04 | dart-virtual-trader | `dart-position/2026-09-04.md` | `dart-virtual-trader/` | **없음** |
| 2026-09-02 | bess-optimizer | `bess-stack/2026-09-02.md` | `bess-optimizer/` | **없음** (추정) |
| 2026-09-01 등 | dart-virtual-trader | `dart/YYYY-MM-DD.md` | `dart-virtual-trader/` | **없음** (5건) |

**6주 연속 [WRONG DIR] 플래그 없이 오류 경로 전달.**

---

## 핵심 개선 포인트

### 1. "Cycle Health — Path Verification" 섹션 즉시 구현 — 6주 연속 미이행 (CRITICAL)

W31 등록, W34 Critical 상향, W36 6주째 미구현. 데이터 상태 테이블(Section 8)은 우수하게 유지되고 있으나, 경로 검증(어느 에이전트가 잘못된 디렉토리에 저장했는지)은 별개 항목.

**즉시 구현 형식** (Section 8 또는 새 Section 9):

```markdown
## Cycle Health — Path Verification

| 에이전트 | 인용 경로 | 정규 디렉토리 | 상태 |
|---|---|---|---|
| market-analyst | `reports/daily/market-briefing/YYYY-MM-DD.md` | `market-briefing/` | CORRECT |
| bess-optimizer | `reports/daily/bess-stack/YYYY-MM-DD.md` | `bess-optimizer/` | [WRONG DIR] |
| dart-virtual-trader | `reports/daily/dart/YYYY-MM-DD.md` | `dart-virtual-trader/` | [WRONG DIR] |
| congestion-analyst | `reports/daily/congestion/YYYY-MM-DD.md` | `congestion/` | CORRECT |
| pnl-manager | `reports/daily/pnl/YYYY-MM-DD.md` | `pnl/` | CORRECT |
```

### 2. canonical-paths.md 생성 — W35 계획 미이행

`memory/reporter/canonical-paths.md` 생성:

```markdown
# Reporter Canonical Paths

## 정규 출력 경로 (에이전트별)
| 에이전트 | 정규 경로 |
|---|---|
| market-analyst | reports/daily/market-briefing/YYYY-MM-DD.md |
| bess-optimizer | reports/daily/bess-optimizer/YYYY-MM-DD.md |
| dart-virtual-trader | reports/daily/dart-virtual-trader/YYYY-MM-DD.md |
| congestion-analyst | reports/daily/congestion/YYYY-MM-DD.md |
| pnl-manager | reports/daily/pnl/YYYY-MM-DD.md |
| reporter (self) | reports/daily/YYYY-MM-DD.md |

## 알려진 오류 변종 (절대 정규로 취급하지 말 것)
- bess-stack/, bess-strategy/, bess-schedule/ → bess-optimizer/
- dart-virtual/, dart-position/, dart/, dart-trader/ → dart-virtual-trader/
- shared/data/forecasts/market-view/ → market-briefing/
```

세션 시작 시 이 파일 읽기 → 각 에이전트 경로 교차 확인.

### 3. [LEARNINGS ABSENT] 플래그 명시화

W36에서 Sep 1 (Labor Day), Sep 6 (Sunday) 여러 에이전트 learnings 공통 부재. 현재 reporter가 이를 무음 처리. 대신:
- `[LEARNINGS ABSENT — market-analyst, bess-optimizer, congestion-analyst, dart-virtual-trader: 2026-09-01, 2026-09-06]` 명시
- cross-agent 동일 날 공백 시 "PUBLIC HOLIDAY / WEEKEND GAP — evaluator 확인 요청" 플래그

---

## 구체적 액션 아이템 (W37 기준)

| 항목 | 기한 | 상태 |
|---|---|---|
| `memory/reporter/canonical-paths.md` 생성 | W37 Day 1 이전 | OVERDUE (W35 계획 미이행) |
| W37 전 Daily Report에 "Cycle Health — Path Verification" 섹션 추가 | W37부터 전 사이클 | OVERDUE (6주) |
| [WRONG DIR] 태그 본문 및 경로 검증 테이블에 적용 | W37부터 | 즉시 |
| [LEARNINGS ABSENT] 명시 표준화 | W37부터 | 신규 |

---

## 에스컬레이션 조항

W37에서 "Cycle Health — Path Verification" 섹션 미구현 시: evaluator가 reporter 산출물에 대해 "경로 신뢰도 D" 등급 부여 및 사용자 재정의 요청. 6주 연속 Critical 미이행은 에이전트 정의 수준의 개입이 필요한 수준.

---

## 지속 모니터링 항목

- **Path Verification 섹션**: W37 7/7 구현 여부 evaluator 1순위 확인.
- **[WRONG DIR] 태그**: bess-stack/, dart-position/, dart/ 등 오류 변종 인용 시 즉시 태그.
- **canonical-paths.md**: 세션 시작마다 참조.
- **7/7 reports**: W35, W36 연속 달성 — W37 유지.
- **운영 알림 품질**: DA charge bid failure, AS overlap 등 critical operational issue 지속 플래그.
