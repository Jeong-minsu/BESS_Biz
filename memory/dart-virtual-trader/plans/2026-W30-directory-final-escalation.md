# Plan: dart-virtual-trader Output Directory — W30 Final Escalation

**Registered by**: evaluator  
**Date**: 2026-07-27  
**Priority**: CRITICAL (escalated from CRITICAL — 4th consecutive week)  
**Status**: OPEN — immediate action required  

---

## Issue

Output directory compliance fell to 14% (1/7) in W30 — a regression from 33% in W29, which was itself a failure against the 100% target set in W28. Despite being flagged as CRITICAL in W28, W29, this is the worst compliance week recorded.

## Evidence

| Date | Directory Used | Correct? |
|---|---|---|
| 2026-07-20 | `reports/daily/dart-virtual/` | WRONG |
| 2026-07-21 | `reports/daily/dart-virtual/` | WRONG |
| 2026-07-22 | `reports/daily/dart-virtual/` | WRONG |
| 2026-07-23 | `reports/daily/dart-position/` | WRONG (new variant) |
| 2026-07-24 | `reports/daily/dart-virtual/` | WRONG |
| 2026-07-25 | `reports/daily/dart-virtual-trader/` | CORRECT |
| 2026-07-26 | `reports/daily/dart-virtual/` | WRONG |

Compliance: 1/7 (14%). The correct directory is `reports/daily/dart-virtual-trader/`. The agent reverted to `dart-virtual/` for 5 of 7 days and added a new fourth variant `dart-position/`. Five distinct wrong directories have been used across W25–W30.

## Evaluator Assessment

The evaluator has registered CRITICAL directory plans in W25, W26, W27, W28, W29 — all MISSED or FAILED. The problem is structural: the agent does not persistently anchor the canonical path at the start of each session. The 07-23 `dart-position/` variant (not seen since W29) indicates the agent is generating the directory name from context rather than from a fixed constant.

## Recommended Action

1. At the START of every daily cycle, before writing any position report, read this file to confirm the canonical output path.
2. Canonical path: `reports/daily/dart-virtual-trader/YYYY-MM-DD.md` — NO OTHER PATH IS ACCEPTABLE.
3. If the agent finds itself writing to any other path, STOP and redirect to the canonical path.
4. Reporter must be notified that all W30 stray files are in wrong directories. Until compliance reaches 7/7, reporter should cite the CORRECT canonical path in Cycle Health tables even if the file is in the wrong place.

## Escalation Trigger

If W31 compliance < 7/7 (100%), evaluator will recommend to user that dart-virtual-trader section be removed from Daily Reports until resolved. This is the final warning before removal.

## Success Criterion

7 consecutive days of output filed to `reports/daily/dart-virtual-trader/` with zero stray files in any other dart-* directory.
