---
description: ERCOT D+1 daily cycle 자동 실행 (페치 → 5개 에이전트 → Reporter)
---

오늘 ERCOT D+1 daily cycle을 실행해줘. 다음 시퀀스로 자동 진행 (각 단계마다 사용자 확인 받지 말고 자동으로):

## Step 1. 데이터 페치 (Bash, 순차)

```bash
python shared/scripts/fetch_pnl_data.py     # 어제 실적
python shared/scripts/fetch_market_data.py  # 내일 시황
```

각 명령의 stdout 마지막 5줄만 보여주고 다음 단계로.

## Step 2. P&L 정리

Task 도구로 `pnl-manager` 호출:
- Input: `shared/data/pnl/gks/hourly/{어제}_summary.json`
- Expected output: `reports/daily/pnl/{어제}.md`

## Step 3. 시황·혼잡 분석 (병렬)

단일 메시지로 다음 두 Task를 동시 호출:
- Task → `market-analyst`: D+1 ERCOT 시황 브리핑
- Task → `congestion-analyst`: D+1 hub-pair basis / binding constraint outlook

각각의 결과는 `reports/daily/market-briefing/{내일}.md`, `reports/daily/congestion/{내일}.md` 에 저장됨. 또 `shared/data/forecasts/market-view/{내일}.md`, `shared/data/forecasts/congestion/{내일}.md` 에 downstream 사본.

## Step 4. 트레이딩 결정 (병렬)

위 step 3 결과를 input으로, 단일 메시지로 두 Task 동시 호출:
- Task → `bess-optimizer`: GKS DA/RT Energy + AS revenue stack
- Task → `dart-virtual-trader`: DART virtual short/long 포지션

## Step 5. 자가 피드백

Front/Middle 5개 에이전트 self-review (병렬):
- `market-analyst`, `congestion-analyst`, `bess-optimizer`, `dart-virtual-trader`, `crr-trader` (옥션 시기만)

각자 `memory/<agent>/learnings/{어제}.md` 작성.

## Step 6. Reporter 통합

Task → `reporter`: 위 모든 산출물 (P&L, 시황, 혼잡, BESS stack, DART, self-review) 통합 → `reports/daily/{내일}.md` + `.html`.

## 출력

마지막에 다음 두 줄만 사용자에게:
```
✅ Daily cycle 완료 — D+1 (YYYY-MM-DD)
[View Daily Report](computer://...{내일}.html)
```

## 실패 시

- fetch 스크립트 401/timeout → 즉시 멈추고 에러 메시지 보여줌
- 특정 에이전트 산출물 누락 → 1회 retrigger, 두 번째 실패 시 partial report (해당 섹션 "N/A" 표기)
- self-review 스킵 가능 (첫 실행 시)
