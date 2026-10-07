# Plan: Path Verification — Escalated to Major (Third Consecutive Miss)

Week: 2026-W32
Priority: Major (escalated from Minor per W31 escalation threshold)
Issue: Path verification was not implemented for the third consecutive week (W30, W31, W32). Reporter cited wrong paths without flagging: `dart/2026-08-06.md`, `dart/2026-08-07.md`, `dart-virtual/2026-08-05.md`, and `reports/daily/2026-08-07-bess-stack.md` — all wrong. None were flagged as misfiled.
Action: Add a "Cycle Health — Path Verification" section to every daily report. For each upstream agent's output, explicitly state:
  1. Expected path: `reports/daily/<agent>/YYYY-MM-DD.md`
  2. Actual path found: (from file listing)
  3. Status: CORRECT or [WRONG DIR — expected: X, found: Y]
This requires a `ls` or `find` check before citing the path. This section should be placed before Cross-Agent consistency checks and should take no more than 2 minutes per cycle.
Success criteria: Path verification section present in all 7 W33 daily reports. At least one wrong-path flag raised if any upstream agent misfiled during W33 (based on evidence from W32 trajectory, dart-virtual-trader and bess-optimizer are likely candidates).
Owner: reporter

## Miss History

| Week | Plan | Consequence |
|---|---|---|
| W30 | 2026-W30-path-verification.md | Miss 1 — Minor |
| W31 | 2026-W31-path-verification-final.md (escalation warning) | Miss 2 — Minor (final warning) |
| W32 | This plan — escalated | Miss 3 — Major |
| W33 | If missed again | Escalation to Critical |

Note: The W32 path verification failure had material impact — the Aug 7 daily report cited bess-optimizer's misfiled output without flagging it, which means downstream decisions were based on content from a wrong location. This is no longer a formatting issue; it is a data integrity risk.
