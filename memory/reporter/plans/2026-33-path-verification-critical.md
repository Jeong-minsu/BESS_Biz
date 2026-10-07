# Plan: Path Verification — Escalated to Critical (Fourth Consecutive Miss)

Week: 2026-33
Priority: Critical (escalated from Major per W32 plan escalation clause: "W33 miss → Critical")
Issue: Path verification was not implemented for the fourth consecutive week (W30 Minor, W31 Minor, W32 Major, W33 Critical). The W32 plan required a formal "Cycle Health — Path Verification" section with [WRONG DIR] flags in all 7 W33 daily reports. Partial improvement observed: reporter now cites full file paths in source headers (e.g., "`reports/daily/bess-schedule/2026-08-11.md`", "`reports/daily/dart/2026-08-11.md`") — this is an improvement over W32's ambiguous citations. However, no [WRONG DIR] flag was raised for any misfiled file, and no formal path verification section was added.

## W33 Evidence

- 2026-08-10 report: bess-optimizer source = "bess-optimizer 2026-08-10.md" (path ambiguous, filed in bess-schedule/ — not flagged)
- 2026-08-11 report: bess-optimizer source = "`reports/daily/bess-schedule/2026-08-11.md`" (wrong dir cited, not flagged as wrong)
- 2026-08-11 report: dart-virtual-trader source = "`reports/daily/dart/2026-08-11.md`" (wrong dir cited, not flagged as wrong)
- No report includes a formal "Cycle Health — Path Verification" section or [WRONG DIR] notation.

## Miss History

| Week | Plan | Priority |
|---|---|---|
| W30 | 2026-W30-path-verification.md | Minor (Miss 1) |
| W31 | 2026-W31-path-verification-final.md | Minor (Miss 2, escalation warning) |
| W32 | 2026-W32-path-verification-major-escalation.md | Major (Miss 3, escalated) |
| W33 | This plan | Critical (Miss 4, escalated per W32 clause) |

## Action

- Agent must implement a formal "Cycle Health — Path Verification" section in every W34 daily report (7/7).
- Format per the W32 plan:
  1. Expected path: `reports/daily/<agent>/YYYY-MM-DD.md`
  2. Actual path found
  3. Status: CORRECT or [WRONG DIR — expected: X, found: Y]
- The partial improvement (full path citation) is acknowledged. The remaining gap is adding the [WRONG DIR] flag notation and the structured section.

Success criteria: Path verification section present in 7/7 W34 daily reports. At least one [WRONG DIR] flag raised if any upstream agent misfiled (statistically expected given trajectory).
Owner: reporter
Deadline: W34 evaluation (2026-08-24).

## Note to User

The W32 plan's escalation trigger has been met. The evaluator is formally escalating this to Critical. However, this is an agent-executable issue — no user action is required beyond awareness. The agent must implement this in the next cycle.
