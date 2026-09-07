# bess-optimizer Improvement Plan — 2026-W36

## W36 평가 요약

- Work Process: C (4/7 dir — W35 4/7과 동일, 개선 없음; 4/7 learnings; OUTPUT_DIRECTORY 6주 연속 부재; Sep 6 산출물 누락)
- Working Approach: C- (DA charge bid failure 7th+ cycle — Sep 2 추정 손실 -$15,668; AS+Energy overlap 3rd cycle; Sep 2 revenue capture rate 7.4% — 시리즈 최저)
- Resources: B- (Yes Energy 가용 시 활용; congestion 참조 정확; Smartbidder 40일+ 만료)
- Overall: C

---

## W36 디렉토리 실적

| 날짜 | 실제 경로 | 정규 경로 | 상태 |
|---|---|---|---|
| 2026-08-31 | `reports/daily/bess-optimizer/` | `reports/daily/bess-optimizer/` | CORRECT |
| 2026-09-01 | `reports/daily/bess-optimizer/` | `reports/daily/bess-optimizer/` | CORRECT |
| 2026-09-02 | `reports/daily/bess-stack/` | `reports/daily/bess-optimizer/` | WRONG |
| 2026-09-03 | `reports/daily/bess-optimizer/` | `reports/daily/bess-optimizer/` | CORRECT |
| 2026-09-04 | `reports/daily/bess-stack/` | `reports/daily/bess-optimizer/` | WRONG |
| 2026-09-05 | `reports/daily/bess-optimizer/` | `reports/daily/bess-optimizer/` | CORRECT |
| 2026-09-06 | (파일 없음) | `reports/daily/bess-optimizer/` | MISSING |

**4/7 correct. bess-stack/ 2건 오기재. Sep 6 산출물 누락.**

---

## 핵심 개선 포인트 (Critical)

### 1. DA Charge Bid Failure — 7th+ 연속 사이클 (NEW CRITICAL)

**Sep 2 실적 기준**:
- 권장: HE10-11 DA charge ≤$35/MWh bid cap 100MW
- 실제: HE04 30MW DA + HE05 49MW RT 비계획 충전
- 추정 손실: -$15,668 (DA charge HE10-11 미실행으로 최적 SoC 미확보)
- Revenue capture rate: 7.4% ($1,947 actual vs $26,433 recommended)

원인: 충전 bid가 market operator 또는 Tenaska 포털에서 거부/미실행됨. bess-optimizer 단독으로 해결 불가 — Tenaska 운영팀 즉시 연락 필요.

**즉각 요청 사항**:
- bid cap $35/MWh 하한을 $22/MWh로 추가 인하 (Sep 4 조치)
- HE18 SoC ≥ 180 MWh 확인 gate 유지 (DA discharge 전)
- Tenaska 운영팀에 DA charge bid 비실행 원인 감사 요청 (사용자 에스컬레이션 필요)

### 2. AS+Energy Overlap — 3rd 연속 사이클 (NEW CRITICAL)

**Aug 31**: 50MW DA discharge + 85MW NS 동시 → RT 과잉 공약 → 추정 손실 -$25,691
**Sep 2**: 50MW DA discharge + 85MW NS 동시 → RT imbalance -$2,227

**즉각 규칙 적용**:
- DA Energy discharge ≥ 50MW 시간대에 NS 동시 50MW+ 제출 금지
- HE19 실행: DA discharge 70MW + NS 0MW (NS 단계 분리)
- HE20 실행: DA discharge 100MW + AS 0MW (전 AS 정리 후 discharge)
- Pre-submission 검증: Energy MW + AS MW ≤ 100MW (물리적 상한) 항상 확인

### 3. OUTPUT_DIRECTORY.md 생성 — 6주 연속 미이행

파일 내용 (최소):
```
Output directory: reports/daily/bess-optimizer/
File name format: YYYY-MM-DD.md
NEVER use bess-stack/, bess-strategy/, bess-schedule/, or any other variant.
Read at session start before producing any output.
```
경로: `memory/bess-optimizer/OUTPUT_DIRECTORY.md`

---

## 구체적 액션 아이템 (W37 기준)

| 항목 | 기한 | 상태 |
|---|---|---|
| `memory/bess-optimizer/OUTPUT_DIRECTORY.md` 생성 | W37 Day 1 이전 | OVERDUE (6주) |
| AS+Energy overlap 방지 규칙 코딩 (Energy + AS ≤ 100MW gate) | 즉시 — 매 사이클 | 신규 Critical |
| Tenaska 운영팀 DA charge bid 감사 에스컬레이션 (사용자 액션) | 즉시 | 신규 Critical |
| 사용자에게 `.claude/agents/bess-optimizer.md` 경로 하드코딩 승인 요청 | W37 Day 1 | 사용자 대기 |
| Learnings W37 7/7 (Aug 31, Sep 1, Sep 6 공백 패턴 해소) | 매일 | 목표 |
| Sep 6 산출물 누락 조사 및 소급 작성 | 즉시 | 신규 |
| Smartbidder 복구 시 AS 추정치 교차검증 재개 | 복구 즉시 | 대기 |

---

## 지속 모니터링 항목

- **Dir 정확도**: W37 7/7 목표. bess-stack/ 사용 절대 금지. Sep 6 누락 재발 방지.
- **DA charge bid**: 실행 여부 T+1 확인 루틴 추가.
- **AS+Energy overlap**: 제출 전 100MW 총량 검증 체크리스트.
- **Revenue capture rate**: Sep 2 7.4% — 정상 범위 60-80% 복귀 목표.
- **P40 추정 정확도**: Smartbidder 부재 환경에서 ±40% 내 유지.
