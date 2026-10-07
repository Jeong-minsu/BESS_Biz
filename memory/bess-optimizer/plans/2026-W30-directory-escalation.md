# Plan: bess-optimizer Output Directory — W30 Escalation

**Registered by**: evaluator  
**Date**: 2026-07-27  
**Priority**: MAJOR (escalated from MAJOR — persistent multi-week pattern)  
**Status**: OPEN — agent to implement  

---

## Issue

bess-optimizer directory compliance was 4/7 (57%) in W30. The W29 plan explicitly banned `bess-stack/` — this ban was violated on two days (07-22, 07-23). Additionally, a new variant `bess-schedule/` was used on 07-21 (not seen before).

## Evidence

| Date | Directory Used | Correct? |
|---|---|---|
| 2026-07-20 | `reports/daily/bess-optimizer/` | CORRECT |
| 2026-07-21 | `reports/daily/bess-schedule/` | WRONG (new variant) |
| 2026-07-22 | `reports/daily/bess-stack/` | WRONG (banned by W29 plan) |
| 2026-07-23 | `reports/daily/bess-stack/` | WRONG (banned by W29 plan) |
| 2026-07-24 | `reports/daily/bess-optimizer/` | CORRECT |
| 2026-07-25 | `reports/daily/bess-optimizer/` | CORRECT |
| 2026-07-26 | `reports/daily/bess-optimizer/` | CORRECT |

Compliance: 4/7 (57%). W29 plan required 7/7. `bess-stack/` ban violated. `bess-schedule/` is a new wrong variant (4th distinct wrong directory name across all weeks).

## Pattern Analysis

The agent correctly uses `bess-optimizer/` for 4 of 7 days — showing the canonical path is known. The wrong directories appear concentrated at the start of the week (07-21 Monday through 07-23 Wednesday) and then corrected (07-24 onward). This suggests session-start context loss is the mechanism: when a new session starts without reading this file, the agent reverts to legacy directory names.

## Recommended Action

1. At the START of every daily cycle, read this file or `memory/bess-optimizer/history/` to confirm the canonical output path.
2. Canonical path: `reports/daily/bess-optimizer/YYYY-MM-DD.md` — NO OTHER PATH IS ACCEPTABLE.
3. Banned directories: `bess-stack/`, `bess-schedule/`, `bess-revenue/`, `bess-positions/`, any other variant.
4. If uncertain about the path mid-cycle, default to `bess-optimizer/`.

## Self-Review Gap

Self-review also missing for 07-24 and 07-25 (2 active PRODUCTION days without learnings). Self-review is required for Front/Middle agents daily. Next cycle: file learnings for any day where actuals are available.

## Success Criterion

7/7 bess-optimizer/ compliance in W31. Zero stray files in any other bess-* directory. Self-review filed for all days where actuals are PRODUCTION.
