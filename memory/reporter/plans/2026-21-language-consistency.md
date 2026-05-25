# Plan: Report Language and Section Consistency — 2026-21

**Issue**: Daily reports switch between English (2026-05-22, 2026-05-23) and Korean (2026-05-24 onward) without a stated policy. Section ordering and naming differ across reports (e.g., "Watch Items" vs "주요 리스크 & 모니터링 포인트"; cross-agent check section appears as Section 7 in some reports, as Section 6 in others). This does not affect content quality but reduces readability and cross-report comparability.

**Priority**: MINOR

## Actions

- Establish and document the language policy in `memory/reporter/` or `shared/config.md`: either full English or full Korean per report, consistently applied. (User decision required — flag in weekly review.)
- Fix section numbering: the Daily Report template has 8 defined sections. Enforce the fixed order in every report:
  1. Data Status / Yesterday P&L
  2. D+1 Market View
  3. D+1 Congestion
  4. D+1 BESS Recommendation
  5. D+1 DART Positions
  6. Self-Review Summary
  7. Cross-Agent Consistency / Watch Items
  8. Action Items / Operating Checklist
- reporter's self-review compliance: confirm each report ends with "no independent analysis added" attribution line. This was present on 2026-05-23 but absent from the 2026-05-24 and 2026-05-26 report footers — re-add.
