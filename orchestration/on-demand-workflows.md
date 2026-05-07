# On-Demand Workflows

사용자가 ad-hoc 호출 시 사용하는 워크플로우. Daily/Weekly와 별개로 즉시 실행 가능.

---

## 1. CRR Trading Opportunity (사용자 호출)

> 트리거: "CRR 기회 3개 찾아줘", "CRR opportunity for next auction"

```
Step 1. crr-trader 호출
Step 2. (필요 시) congestion-analyst 결과 참조
Step 3. 산출: reports/ad-hoc/crr/YYYY-MM-DD-<topic>.md
```

---

## 2. Specific Agent Re-run

> 트리거: "오늘 시황 다시 분석해줘", "BESS stack 다시 검토해줘"

```
Step 1. 해당 에이전트만 단독 호출 (의존성 없는 경우)
   - market-analyst, congestion-analyst → 외부 데이터만 의존
Step 2. 의존성 있는 경우 (bess-optimizer, dart-virtual-trader)
   - 최신 market-analyst / congestion-analyst 결과가 있는지 확인
   - 없거나 stale (>4h)이면 그것부터 retrigger
Step 3. 결과 산출 후 reporter는 재실행하지 않음 (사용자가 명시 시에만)
```

---

## 3. Evaluator Ad-hoc

> 트리거: "<agent> 점검해줘", "어제 dart-virtual-trader 어떤지 평가해줘"

```
Step 1. evaluator 호출 (대상 명시)
Step 2. 지정 에이전트의 최근 산출물 + memory + 실적 데이터 read
Step 3. 평가 수행 + 산출 → reports/ad-hoc/evaluator/YYYY-MM-DD-<agent>.md
```

---

## 4. Backtest / What-if

> 트리거: "지난 주 우리 stack을 X 전략으로 했으면 어땠을까?"

```
Step 1. bess-optimizer (또는 dart-virtual-trader) 호출 with 지정 strategy
Step 2. pnl-manager가 해당 기간 실제 가격/AS 실적 데이터 제공
Step 3. Counterfactual 시뮬레이션 → expected revenue 비교
Step 4. 결과: reports/ad-hoc/backtest/YYYY-MM-DD-<topic>.md
```

> ⚠️ Counterfactual은 정밀도 한계 있음 (가격 영향, fill 가정 등). 결과에 명시 caveat 포함.

---

## 5. Top 10 Operator 벤치마크

> 트리거: "Top BESS 운영자들 어떻게 하고 있어?"

```
Step 1. bess-optimizer 호출 + pnl-manager의 ERCOT 全 BESS dashboard 데이터 활용
Step 2. Top 10 추출 (revenue 기준)
Step 3. 운용 패턴 분석 (AS weight, DA-RT 비중, 시즌별 전략)
Step 4. GKS 적용 가능 인사이트 3개 도출
Step 5. 결과: reports/monthly/operator-benchmark/YYYY-MM.md (월 1회 정기) 또는
              reports/ad-hoc/operator-benchmark/YYYY-MM-DD.md
```

---

## 6. CONGESTION_PROJECT Stage Transition

> 트리거: "CONGESTION_PROJECT Stage X로 넘어가자"

```
Step 1. congestion-analyst 호출
Step 2. 현 stage transition gate KPI 충족 여부 확인 (CONGESTION_PROJECT.md §4)
Step 3. 충족 시 → CONGESTION_PROJECT.md `Current stage` 필드 업데이트
Step 4. 다음 stage 작업 항목으로 plans 작성
Step 5. memory/congestion-analyst/plans/stage-progress.md 업데이트
```

---

## 7. Self-feedback Plan 시행 점검

> 트리거: "지난주 evaluator가 등록한 plan들 다 진행됐어?"

```
Step 1. evaluator 호출
Step 2. memory/evaluator/improvement-tracker.md 확인
Step 3. 각 plan의 시행 여부 점검
Step 4. 미시행 plan은 escalate
```
