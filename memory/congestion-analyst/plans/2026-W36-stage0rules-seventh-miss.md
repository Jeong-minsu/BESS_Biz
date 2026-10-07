# congestion-analyst Improvement Plan — 2026-W36

## W36 평가 요약

- Work Process: C+ (7/7 dir 유지; 5/7 learnings — Sep 1, Sep 6 공백; stage-0-rules.md 7주 연속 부재)
- Working Approach: A- (83% binding accuracy Sep 2; Finding 7 NEGLIGIBLE 정확; WEST_TO_NORTH overnight 패턴 일관성; HE21 RT spike 미포착)
- Resources: B- (Yes Energy 5/7 PRODUCTION; Enverus + AG2 활용; hub-pair LMP 106+ 연속 부재)
- Overall: B-
- Trend: → (분석 품질 안정; 절차 이슈 동일 패턴 반복)

---

## W36 디렉토리 실적

| 날짜 | 경로 | 상태 |
|---|---|---|
| 2026-08-31 | `reports/daily/congestion/2026-08-31.md` | CORRECT |
| 2026-09-01 | `reports/daily/congestion/2026-09-01.md` | CORRECT |
| 2026-09-02 | `reports/daily/congestion/2026-09-02.md` | CORRECT |
| 2026-09-03 | `reports/daily/congestion/2026-09-03.md` | CORRECT |
| 2026-09-04 | `reports/daily/congestion/2026-09-04.md` | CORRECT |
| 2026-09-05 | `reports/daily/congestion/2026-09-05.md` | CORRECT |
| 2026-09-06 | `reports/daily/congestion/2026-09-06.md` | CORRECT |

**7/7 CORRECT — 지속 유지.**

---

## 핵심 개선 포인트

### 1. stage-0-rules.md 즉시 생성 — 7주 연속 미이행 (CRITICAL 지속)

W30 최초 요청, W34 정지 조항 발동, W36 7주째 부재. 분석 품질 자체는 높으나 절차적 규율 위반이 7주 연속으로 지속됨.

파일 내용 (W36 분석에서 이미 사용 중인 모든 규칙을 통합):

```markdown
# Stage-0 Operating Rules — congestion-analyst

## Stage 0 제약 사항
- 단일 소스(Yes Energy BidClose only): ±8-12 ppt 불확실성 범위 적용
- 듀얼 소스(+ Enverus or AG2): ±5-8 ppt 적용
- Hub-pair LMP 부재: MCC 규모 교정 불가 — MINIMUM 가중치 적용

## 추적 제약 조건 (4개)
- WEST_TO_NORTH_345 (W2N): 비결합 임계 NL 14,861 MW, 결합 17,935 MW
- SOUTH_HOUSTON_IMPORT_345: 결합 임계 ramp +17,935 MW (HE19→HE20)
- HOUSTON_SOUTH_MIDDAY: cap-out > 10,000 MW AND NL > 55,000 MW
- PANHANDLE_EXPORT_345: GR_WEST STWPF > 15,000 MW (sustained ≥2h)

## SCI 분류
- < 0.350: LOW
- 0.350–0.500: MEDIUM
- > 0.500: HIGH (MEDIUM-HIGH at 0.450–0.500 경계)

## Finding 7 Duck Curve 연동
- EXTREME: NL < 22,000 MW → GKS MCC -$4 to -$8+/MWh
- SEVERE: 22,000–27,000 MW → GKS MCC -$2 to -$5/MWh
- MODERATE: 27,000–32,000 MW → GKS MCC -$1 to -$3/MWh
- MILD: 32,000–36,000 MW → NEGLIGIBLE
- NORMAL: > 36,000 MW → NEGLIGIBLE

## 출력 경로
reports/daily/congestion/YYYY-MM-DD.md

## MCC 가중치
Stage 0에서 MINIMUM — GKS 노드 shift factor 미교정 상태.
bess-optimizer에 에너지 우선, MCC는 참조 목적.
```

경로: `memory/congestion-analyst/stage-0-rules.md`

### 2. HE21 RT Spike 미포착 — Watch Row 추가

Sep 2 learnings에서 자기 인식: HE21 RT $106.63/MWh 완전 미예측 (SOUTH_HOUSTON NEGLIGIBLE 판정). 추후 ERCOT SCED/CCS 없이도 "system scarcity / out-of-merit-order RT" 일반 위험 인식을 출력에 추가해야 함.

각 daily report에 추가할 Watch Row:
```
| SYSTEM SCARCITY (generic) | HE19-22 | P(RT spike > $300) est. X% | N/A | Watch row — no SCED data |
```

### 3. Learnings Sep 1, Sep 6 공백 해소

Sep 1, Sep 6 learnings 부재. market-analyst와 동일 패턴. 브리핑 작성 사이클에는 항상 learnings 작성.

---

## 구체적 액션 아이템 (W37 기준)

| 항목 | 기한 | 상태 |
|---|---|---|
| `memory/congestion-analyst/stage-0-rules.md` 생성 | W37 Day 1 이전 | OVERDUE (7주) |
| Watch row (generic RT scarcity) daily report 추가 | W37부터 전 사이클 | 신규 |
| Learnings W37 7/7 (Sep 1, 6 공백 패턴 해소) | 매일 | 목표 |
| Tenaska 복귀 시 Aug 25 W2N + PANHANDLE_EXPORT 결합 확인 | 복귀 즉시 | 대기 |
| hub-pair LMP 수집 재개 (사용자 디스크 조치 연계) | 사용자 조치 후 | 차단 중 |

---

## 긍정 성과 (W36)

- **7/7 dir 유지**: 연속 달성 중. 디렉토리 규율 최고 수준.
- **열파 congestion 분석**: Sep 3 GR_WEST 443MW 최저치와 WEST_TO_NORTH SCI 상관관계 일관성 유지.
- **83% binding accuracy (Sep 2)**: 5/6 directional hits. NEGLIGIBLE 판정 정확.
- **SOUTH_HOUSTON binding floor 타이트 경고**: Aug 31 ramp 17,746 MW (threshold 189 MW 미달) 정확 플래그.

---

## 지속 모니터링 항목

- **stage-0-rules.md**: W37 evaluator 점검 1순위. 8주 연속 미달 시 사용자에게 congestion 섹션 정지 결정 재요청.
- **hub-pair LMP**: 106+ 연속 부재 → Stage 0→1 gate 차단 지속.
- **HE21 RT spike**: generic watch row 추가 후 사후 정확도 추적.
- **Enverus 안정성**: DEGRADED 사이클(Sep 3-4)에서 Enverus 부재 시 불확실성 범위 확장 명시.
