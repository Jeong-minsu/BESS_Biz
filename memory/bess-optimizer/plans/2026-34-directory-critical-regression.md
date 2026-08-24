# Plan: Output Directory — Critical Regression (1/7, Escalated to Critical)

Week: 2026-34
Priority: CRITICAL (escalated from Major; 1/7 compliance — regression from 5/7 W33 streak)
Issue: The 5-consecutive-correct-day streak from W33 (Aug 12-16) collapsed on the first day of W34 (Aug 17). bess-optimizer filed 1/7 correct in W34, introducing a new wrong-path variant (`bess-strategy/`).

## W34 Directory Record

| Date | Path | Status |
|---|---|---|
| 2026-08-17 (Mon) | reports/daily/bess-stack/2026-08-17.md | WRONG (bess-stack/ variant) |
| 2026-08-18 (Tue) | reports/daily/bess-strategy/2026-08-18.md | WRONG (bess-strategy/ — NEW variant) |
| 2026-08-19 (Wed) | reports/daily/bess-strategy/2026-08-19.md | WRONG |
| 2026-08-20 (Thu) | reports/daily/bess-strategy/2026-08-20.md | WRONG |
| 2026-08-21 (Fri) | reports/daily/bess-optimizer/2026-08-21.md | CORRECT |
| 2026-08-22 (Sat) | reports/daily/bess-stack/2026-08-22.md | WRONG |
| 2026-08-23 (Sun) | reports/daily/bess-stack/2026-08-23.md | WRONG |

Compliance: 1/7 = 14%. Wrong-path variants in W34: `bess-stack/` (3 days), `bess-strategy/` (3 days) — 2 distinct wrong variants.

## OUTPUT_DIRECTORY.md: Still Absent (4th Consecutive Miss)

`memory/bess-optimizer/OUTPUT_DIRECTORY.md` was required in W31, W32, W33, W34 plans and was not created in any of those weeks. This file's purpose is to serve as a session-start anchor. Its absence is likely the root cause of the repeated directory instability.

## Pattern Observed

The W33 5-day correct streak (Aug 12-16) suggests the agent CAN produce correct outputs when primed correctly — but the behavior does not persist across a week boundary or Saturday/Sunday cycle. The week-boundary reset is the key failure mode.

## Required Action — Agent

1. Create `memory/bess-optimizer/OUTPUT_DIRECTORY.md` IMMEDIATELY (before the next daily cycle). Content:
   ```
   Canonical output path: reports/daily/bess-optimizer/YYYY-MM-DD.md
   Banned paths: bess-stack/, bess-schedule/, bess-strategy/, root reports/daily/
   Read this file at the start of every session before producing any output.
   ```
2. At the start of every W35 session, read `memory/bess-optimizer/OUTPUT_DIRECTORY.md` as the first action.
3. Do not use `bess-stack/`, `bess-schedule/`, or `bess-strategy/` for any output.

## Escalation (User)

Four consecutive weeks of OUTPUT_DIRECTORY.md not being created despite explicit plans. The evaluator recommends the user consider adding the canonical path to `.claude/agents/bess-optimizer.md` as a hard-coded constraint, similar to the dart-virtual-trader authorization request.

Success criteria: 7/7 correct directory in W35. OUTPUT_DIRECTORY.md created by W35 Day 1. Zero new wrong-path variants.
Deadline: W35 evaluation (2026-08-31).
Owner: bess-optimizer. User escalation: consider agent definition update.
