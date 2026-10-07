# Plan: Reporter Format Stabilization — Week 22

**Issue**: The 2026-21 language consistency plan was registered but its status as implemented or unimplemented cannot be confirmed from evidence. The Week 22 daily reports (2026-05-25 through 2026-05-31) are uniformly in Korean, which resolves the language flip issue identified in Week 21. However, two structural issues remain:

1. Section numbering and naming still varies across reports. The 2026-05-27 report uses Section 0 ("실행 요약") not present in other reports. The 2026-05-28 report omits a standalone "어제 학습 요약" section and integrates it into Section 6. Section 8 in some reports is "Cross-Agent 일관성" vs "Self-Feedback Summary" ordering in others.

2. The attribution footer line ("reporter: 자체 분석 없음 — 에이전트 산출물 취합·요약만") is present in some reports (2026-05-26, 2026-05-27, 2026-05-28, 2026-05-31) but the exact wording and positioning varies.

**Priority**: MINOR (language issue resolved; structural consistency still incomplete)

**Evidence**: Comparison of reports/daily/2026-05-25.md through 2026-05-31.md. 2026-05-25: 8 sections, no Section 0. 2026-05-27: adds Section 0 "실행 요약". 2026-05-28: Section 6 integrates self-review content from previous-day learnings differently than 2026-05-27.

## Actions

1. **Establish fixed 8-section template with locked numbering**:
   - Section 1: 어제 실적 (P&L lookback)
   - Section 2: D+1 시황 (market view)
   - Section 3: D+1 혼잡 (congestion)
   - Section 4: BESS 운영 제안 (BESS recommendation)
   - Section 5: DART Virtual 포지션
   - Section 6: Self-Review 요약 (prior day learnings)
   - Section 7: Cross-Agent 일관성 및 Watch Items
   - Section 8: 운영 알림 / 액션 아이템
   - Optional Section 0: 실행 요약 (3줄) — may be added before Section 1 on days with high information density; do not use for routine days.

2. **Fix attribution footer**: All reports must end with: "*Reporter: 자체 분석 없음 — 에이전트 산출물 취합·요약만*" as the last line.

3. **DATA STATUS 테이블**: All reports must include the data status summary table at the top (after the header block), with all 5-6 data lines and their statuses.

## Success Criteria

- Section numbering consistent (1-8) across the next 5 daily reports.
- Attribution footer present in all 5 reports.
- Data status table present in all 5 reports.

## Owner

reporter (format is fully within agent control)
