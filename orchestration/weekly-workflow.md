# Weekly Workflow

매주 월요일 07:30 CT (Houston) 에 실행. Daily 워크플로우와 병행 (월요일은 Daily + Weekly 둘 다).

---

## 1. Sequence

```
T-180m (04:30)  pnl-manager
                  ├─ ERCOT 全 BESS energy/AS revenue dashboard ('26.01.01 ~ latest)
                  └─ ERCOT 全 BESS DART virtual revenue dashboard
                  → reports/weekly/bess-revenue-dashboard/{YYYY-WW}.html
                  → reports/weekly/bess-dart-virtual-dashboard/{YYYY-WW}.html

T-150m (05:00)  market-analyst
                  └─ Structural / 정책 / 발전소 mix update
                  → reports/weekly/structural-update/{YYYY-WW}.md

T-120m (05:30)  evaluator
                  ├─ 7개 에이전트 weekly evaluation (지난 7일 산출물 lookback)
                  ├─ 개선 plan을 각 memory/<agent>/plans/ 에 등록
                  └─ Critical 이슈 사용자 보고용
                  → reports/weekly/evaluator/{YYYY-WW}.md

[…이후 Daily 워크플로우 (T-90m부터) 동일하게 실행]

T-15m  (07:15)  reporter (Weekly Report)
                  └─ 위 4개 + Daily 누적 7일 + Daily Report 통합
                  → reports/weekly/{YYYY-WW}.md
                  → reports/weekly/{YYYY-WW}.html
```

---

## 2. Weekly-only Outputs

| 산출물 | 담당 | 위치 |
|---|---|---|
| ERCOT 全 BESS energy/AS revenue dashboard | pnl-manager | `reports/weekly/bess-revenue-dashboard/{WW}.html` |
| ERCOT 全 BESS DART virtual dashboard | pnl-manager | `reports/weekly/bess-dart-virtual-dashboard/{WW}.html` |
| Structural / 정책 update | market-analyst | `reports/weekly/structural-update/{WW}.md` |
| Evaluator scorecard | evaluator | `reports/weekly/evaluator/{WW}.md` |
| Weekly Report (통합) | reporter | `reports/weekly/{WW}.html` |

---

## 3. Monthly Outputs (월말 추가)

| 산출물 | 담당 | 빈도 | 위치 |
|---|---|---|---|
| Top 10 BESS operator 벤치마크 | bess-optimizer | 월 1회 | `reports/monthly/operator-benchmark/{YYYY-MM}.md` |

---

## 4. Annual / Long-term

매년 첫 주에 추가:
- `reports/annual/strategic-review/{YYYY}.md` — 1년 전체 운영 review (모든 에이전트 합작)
- `reports/annual/cohort-comparison/{YYYY}.md` — Top 10 operator 대비 1년 ranking
