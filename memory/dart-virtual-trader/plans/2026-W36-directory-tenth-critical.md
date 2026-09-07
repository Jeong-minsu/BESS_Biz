# dart-virtual-trader Improvement Plan — 2026-W36

## W36 평가 요약

- Work Process: D- (1/7 dir 정확 — W35 2/7에서 추가 퇴보; dart/ 변종 5건 주도적; 5/7 learnings — W35 7/7 최초 달성 후 퇴보; 10주 연속 디렉토리 비준수)
- Working Approach: N/A (advisory-only mode 유지; 포지션 로직 건전)
- Resources: C+ (Smartbidder 페널티 올바르게 적용; T+2 큐 누적 지속)
- Overall: D-

---

## 핵심 이슈 (Critical — 10주 연속)

### W36 디렉토리 실적 (7일)

| 날짜 | 실제 경로 | 정규 경로 | 상태 |
|---|---|---|---|
| 2026-08-31 | `reports/daily/dart/2026-08-31.md` | `reports/daily/dart-virtual-trader/` | WRONG |
| 2026-09-01 | `reports/daily/dart/2026-09-01.md` | `reports/daily/dart-virtual-trader/` | WRONG |
| 2026-09-02 | `reports/daily/dart/2026-09-02.md` | `reports/daily/dart-virtual-trader/` | WRONG |
| 2026-09-03 | `reports/daily/dart-virtual-trader/2026-09-03.md` | `reports/daily/dart-virtual-trader/` | CORRECT |
| 2026-09-04 | `reports/daily/dart-position/2026-09-04.md` | `reports/daily/dart-virtual-trader/` | WRONG |
| 2026-09-05 | `reports/daily/dart/2026-09-05.md` | `reports/daily/dart-virtual-trader/` | WRONG |
| 2026-09-06 | `reports/daily/dart/2026-09-06.md` | `reports/daily/dart-virtual-trader/` | WRONG |

**1/7 정확 = REGRESSION from 2/7 in W35. 10주 연속 비준수. dart/ 변종이 W36에서 5건으로 지배적 오류 패턴이 됨.**

---

## 핵심 개선 포인트

### 1. 에이전트 정의 하드코딩 — 사용자 승인 10주째 미수신 (P0)

10주 연속 비준수. W35에서 2/7 소폭 개선되었다가 W36에서 1/7로 추가 퇴보. dart/ 변종이 5회로 주도적 — 이전 weeks의 dart-virtual/, dart-position/ 변종을 대체.

**정규 경로**: `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`

사용자 승인 없이 에이전트가 자체 수정 불가임을 10주간 데이터가 증명함. 유일한 구조적 해결책은 `.claude/agents/dart-virtual-trader.md`에 출력 경로 하드코딩.

에이전트 측 즉시 조치:
1. 세션 시작 시 오늘 날짜와 함께 `reports/daily/dart-virtual-trader/` 경로 존재 여부 확인
2. 저장 직후 `ls reports/daily/dart-virtual-trader/YYYY-MM-DD.md` 확인
3. 오류 발견 시 즉시 파일 이동 + reporter 인용 경로 수정 요청

### 2. Learnings 7/7 복구 — W35 최초 달성 후 W36에서 5/7로 퇴보

W35에서 7/7 최초 달성 → W36에서 5/7 (Sep 1, Sep 6 공백). Sep 1은 Labor Day (US 공휴일)이나 daily cycle은 계속 운영됨. Sep 6 (일요일)도 포지션 결정이 있었으므로 learnings 작성 대상.

DEGRADED/휴일에도 최소 3항목 learnings 작성:
- 당일 포지션 결정 및 근거
- T+2 결산 큐 상태 업데이트
- 모델 한계 인식 또는 trigger 임계치 평가

### 3. T+2 결산 큐 — Tenaska 복귀 시 즉시 우선 처리

T+2 미결산 40+ flowday (Jul 25 이후 전 advisory 포지션). Tenaska PRODUCTION 복귀 즉시:
- Sep 1 advisory P&L 결산 최우선 (Sep 3 T+2)
- Aug 26 secondary trigger (HE20-21 DEC 35MW) WIN/LOSS 확인
- Aug 30 EXTREME tier INC 방향 검증
- Sep 2 100% win-rate (2/2 hits) 실결산 확인

---

## 구체적 액션 아이템 (W37 기준)

| 항목 | 기한 | 상태 |
|---|---|---|
| 사용자 승인 수신 시 `.claude/agents/dart-virtual-trader.md` 경로 하드코딩 | 승인 즉시 | W32부터 요청 — 미수신 (10주) |
| 세션 시작 시 경로 자체 검증 루틴 (ls 확인) | W37부터 전 사이클 | 필수 |
| Learnings W37 7/7 재달성 | 매일 (공휴일·주말 포함) | 목표 복구 |
| Tenaska 복귀 즉시 Jul 25 이후 전 T+2 결산 순차 처리 | 복귀 즉시 | 대기 |
| Sep 2 advisory WIN/LOSS (HE19 DEC +$15.70; HE20 DEC +$242.20) 실결산 확인 | Tenaska 복귀 후 | P0 |

---

## 에스컬레이션 조항

**W36에서 1/7 — 10주 연속 미달. W37에서 ≥3/7 미달 시**: reporter에게 dart-virtual-trader 산출물 제외 권고 (에이전트 산출물 경로 불명확으로 취합 불가). 사용자 최종 판단 요청.

---

## 지속 모니터링 항목

- **Dir 정확도**: W37 목표 7/7. 사용자 하드코딩 승인 최우선.
- **T+2 결산**: Tenaska 복귀 후 40+ 건 순차 처리.
- **Learnings**: W37 7/7 재달성 (W35 수준 복구).
- **dart/ 변종 차단**: W36 5/7 = 새로운 주요 오류 패턴. 경로 확인 루틴 실행 전까지 재발 위험 높음.
