# Plan: stage-0-rules.md — Fifth Consecutive Miss / Suspension Consequence Triggered

Week: 2026-34
Priority: CRITICAL
Issue: `memory/congestion-analyst/stage-0-rules.md` was not created in W34 for the fifth consecutive week. W33 plan (`2026-33-stage0rules-fourth-miss.md`) explicitly stated: "consequence clause: recommend suspending daily output if W34 also missed."

## Miss History

| Week | Deadline | Status |
|---|---|---|
| W29 | 2026-07-21 | MISSED |
| W30 | 2026-07-28 | MISSED |
| W31 | 2026-08-08 (hard deadline) | MISSED |
| W32 | 2026-08-11 (hard deadline) | MISSED |
| W33 | Before next daily cycle | MISSED |
| W34 | Before W34 evaluation | MISSED (5th consecutive) |

## What stage-0-rules.md Must Contain

This file is a consolidation of rules already established in learnings files. It is not new work — it is organizing existing documented knowledge into one reference file. Required sections:

1. Stage 0 active constraint set (SOUTH_HOUSTON_IMPORT, WEST_TO_NORTH_345, PANHANDLE_EXPORT_345, HOUSTON_SOUTH_MIDDAY — binding floor thresholds, SCI thresholds)
2. Directional hit-rate log (cumulative, from learnings history)
3. Settlement queue status (what is confirmed vs pending)
4. W3 infrastructure blockers (hub-pair LMP unavailability — cycle count, root cause, workaround)
5. Known calibration anchors (Jun 17, Jul 1, Jul 2 binding/non-binding events)

## Consequence Clause Execution

Per W33 plan, the evaluator recommends the following to the user for W35:

- If `memory/congestion-analyst/stage-0-rules.md` is NOT created by the first W35 daily cycle (2026-08-25 07:30 CT), the congestion-analyst daily report should be suppressed from the consolidated Daily Report (reporter to note "congestion-analyst: output suspended pending stage-0-rules.md creation") until the file exists.
- The daily report structure remains valid; only the congestion section is suppressed.
- Suspension is lifted immediately upon creation of the file.

This is a process discipline consequence only. Analytical quality in W34 was sound (7/7 correct directory, strong heuristic heat wave analysis). The suspension targets the specific recurring procedural failure.

## W35 Action Items

1. Create `memory/congestion-analyst/stage-0-rules.md` BEFORE first W35 daily cycle. This is estimated 30-60 minutes of consolidation work using existing learnings content.
2. Read stage-0-rules.md at the start of each subsequent cycle and update the settlement queue and hit-rate entries weekly.

Success criteria: File exists at `memory/congestion-analyst/stage-0-rules.md` by 2026-08-25 07:30 CT.
Deadline: W35 Day 1 (2026-08-25).
Owner: congestion-analyst. User authorization for suspension consequence required.
