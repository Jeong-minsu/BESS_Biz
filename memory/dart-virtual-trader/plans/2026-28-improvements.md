# Plan: dart-virtual-trader — W28 Improvements
**Week**: 2026-28 | **Priority**: CRITICAL | **Registered by**: evaluator

---

## Issue 1 (CRITICAL): ADVISORY ONLY Reclassification Now in Effect

**Trigger**: W27 plan `2026-27-execution-final-deadline.md` deadline was 2026-07-13. No user response received. Per the plan's success metric, dart-virtual-trader is officially reclassified to "ADVISORY ONLY — Approach axis suspended."

**What this means for the agent**:
- Approach axis score will not be computed in future weekly scorecards until user confirms execution scope.
- Hit-rate-related plans from W21 through W27 are considered infrastructure-unresolvable. They remain on record but will not receive new escalation deadlines.
- The agent should continue issuing positions with full methodology (v3+v4, energy floor, calibration schedule) — these have advisory analytical value.
- The agent should create `memory/dart-virtual-trader/advisory-only-mode.md` documenting: (a) ADVISORY ONLY status, (b) what metrics are tracked in this mode (e.g., E[P50] directional bias, floor hit rate by week), (c) what user action re-activates performance scoring.

**Agent action (by 2026-07-18, end of W29)**:
1. Create `memory/dart-virtual-trader/advisory-only-mode.md` with the above three sections.
2. In each W29 daily report header, include one line: "Status: ADVISORY ONLY — execution scope unconfirmed. Approach axis suspended."

---

## Issue 2 (MAJOR → RESOLVED, MONITORING): Output Directory Proliferation

**W28 status**: 4 directories used (dart-position/, dart/, dart-virtual/, dart-virtual-trader/). Resolved Jul 11 with explicit agent statement.

**W29 requirement**: Every day, without exception, output to `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`. No other path is acceptable.

**Monitoring**: If any W29 output is found outside this path, this issue escalates to CRITICAL on the next evaluation.

**Agent action**: Add to the daily cycle checklist (first line before any analysis begins): "Output path: reports/daily/dart-virtual-trader/[date].md — verify before writing."

---

## Issue 3 (INFRASTRUCTURE — user action required): dart_virtual_revenue Null Field

**Current status**: 30th+ consecutive cycle (as of Jul 12). Tenaska settlement does not isolate DART virtual revenue from DA+RT Energy. This is separate from the execution scope issue.

**Impact**: Even if execution scope is confirmed, hit rate computation requires isolated settlement data. Both infrastructure gaps must be resolved to enable quantitative performance scoring.

**No agent action available**: This requires user contact with Tenaska to request a separate virtual settlement endpoint or report field. Evaluator has escalated this as part of CRITICAL 1 in W28 scorecard.

---

## Issue 4 (MINOR): Below-Floor Exception Documentation

**W28 observation**: Jul 11 HE21 position was 20 MW (below 45 MW ceiling) citing floor miss of $0.023 below the $4.00 floor with a judgment exception for "calibration context." This is a reasonable exception but needs a documented decision rule, not an ad hoc judgment, to be consistent across cycles.

**Agent action (by W29 Day 1)**:
- Formalize the below-floor override rule in standing model documentation: "If E[spread] is within $0.10 of floor AND calibration cycle ≤ 5, position may be taken at 50% of ceiling size. Document the shortfall amount in the report."
- Apply this rule consistently in W29.

---

## Success Metrics for W28 Plan

| Item | Success Criterion | Deadline |
|---|---|---|
| advisory-only-mode.md created | File exists at the path | 2026-07-18 |
| W29 output directory compliance | 7/7 days in dart-virtual-trader/ | End of W29 |
| Below-floor override rule documented | In standing model notes | 2026-07-14 (W29 Day 1) |
| dart_virtual_revenue null | User contacts Tenaska | User-dependent |
| Execution scope confirmed | User response | User-dependent |
