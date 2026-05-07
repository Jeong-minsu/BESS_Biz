# Agent Memory

각 에이전트의 메모리 저장소. **에이전트 정의(`agents/`)와 메모리는 분리**하여 plan과 history가 섞이지 않도록 한다.

---

## 폴더 구조

```
memory/
├── README.md                          ← 이 파일
├── market-analyst/
│   ├── history/                       ← 과거 산출물 (날짜별, 일자별 1파일)
│   │   ├── 2026-04-30.md
│   │   └── ...
│   ├── learnings/                     ← Self-review 결과 (날짜별)
│   │   ├── 2026-04-30.md
│   │   └── ...
│   └── plans/                         ← 개선 계획 (토픽별, 자유 명명)
│       ├── peak-he-decision-rule.md
│       └── ...
│
├── bess-optimizer/
│   ├── history/
│   ├── learnings/
│   └── plans/
│
├── dart-virtual-trader/
│   ├── history/
│   ├── learnings/
│   ├── plans/
│   └── model/                         ← 자체 short/long probability 모델 버전 관리
│
├── crr-trader/
│   ├── history/
│   ├── learnings/
│   ├── plans/
│   └── auction-history/
│       └── 2026-05/                   ← 옥션별 cleared 결과 + 추천 vs 결과
│
├── congestion-analyst/
│   ├── history/
│   ├── learnings/
│   └── plans/
│       ├── stage-progress.md          ← CONGESTION_PROJECT stage tracking (필수)
│       └── ...
│
├── pnl-manager/
│   ├── history/
│   ├── data-quality.md                ← 벤더 데이터 이슈 누적 기록
│   └── plans/
│
├── evaluator/
│   ├── history/                       ← 주간 평가 사본 (YYYY-WW.md)
│   ├── cross-agent-patterns.md        ← 공통 발견 패턴
│   ├── improvement-tracker.md         ← 등록한 plan 시행 추적
│   └── plans/                         ← (optional)
│
└── reporter/
    ├── history/                       ← 일일 report 사본
    ├── template-issues.md
    └── plans/
```

---

## 분리 원칙 (Why)

1. **에이전트 정의 ≠ 메모리**
   - 정의 (`agents/<name>.md`): 에이전트의 R&R, 프로세스, 산출물 형식 — 변하지 않는 contract
   - 메모리 (`memory/<name>/`): 그날그날의 history, learning, plan — 시간에 따라 누적

2. **History ≠ Plan**
   - History: 과거 사실 (immutable)
   - Plan: 향후 개선안 (Evaluator로부터 부여받거나 self 도출)
   - 같은 폴더에 두면 plan이 history로 묻히거나, history가 plan처럼 읽혀 혼동됨

3. **Learnings는 별도**
   - Self-review의 결과물 — `next-day 적용할 인사이트`라는 명확한 목적
   - history에 묻혀 lookback 시 검색 비용 발생 방지

---

## 각 에이전트 메모리 작성 의무

| Agent | history | learnings | plans | 기타 |
|---|---|---|---|---|
| market-analyst | ✅ daily | ✅ daily | ✅ as needed | – |
| bess-optimizer | ✅ daily | ✅ daily | ✅ as needed | – |
| dart-virtual-trader | ✅ daily | ✅ daily | ✅ as needed | `model/` |
| crr-trader | ✅ per opp | ✅ per auction | ✅ as needed | `auction-history/` |
| congestion-analyst | ✅ daily | ✅ daily | ✅ + `stage-progress.md` 필수 | – |
| pnl-manager | ✅ daily | ❌ (self-review 의무 X) | ✅ data-source 추가 | `data-quality.md` |
| evaluator | ✅ weekly | ❌ | (optional) | `cross-agent-patterns.md`, `improvement-tracker.md` |
| reporter | ✅ daily | ❌ | ✅ template improvement | `template-issues.md` |

---

## Naming convention

- **Daily**: `YYYY-MM-DD.md` (예: `2026-04-30.md`)
- **Weekly**: `YYYY-WW.md` (ISO week, 예: `2026-W18.md`)
- **Monthly**: `YYYY-MM.md` (예: `2026-04.md`)
- **Topic**: `<kebab-case-topic>.md` (예: `peak-he-decision-rule.md`)
- **Auction**: `auction-history/YYYY-MM/<auction-type>.md` (예: `2026-05/monthly-pcrr.md`)
