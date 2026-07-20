# Plan: Output Directory Proliferation (W29 Escalation) — dart-virtual-trader

**Registered by**: evaluator  
**Date**: 2026-07-20  
**Priority**: CRITICAL (escalated from MAJOR in W28)  
**ISO Week**: 2026-W29  
**Status**: OPEN — user approval required

---

## Issue

dart-virtual-trader used at least **4 distinct output directories** in W29, with only 2/6 active days filed to the correct canonical path (`reports/daily/dart-virtual-trader/`).

**Evidence (W29 directory usage)**:

| Date | Directory Used | Correct? | Source |
|---|---|---|---|
| 2026-07-13 (Sun) | `reports/daily/dart-virtual/` | WRONG | `memory/dart-virtual-trader/learnings/2026-07-13.md` |
| 2026-07-14 (Mon) | `reports/daily/dart-positions/` | WRONG | `reports/daily/2026-07-14.md` Cycle Health table |
| 2026-07-15 (Tue) | unknown / wrong | WRONG | `reports/daily/2026-07-15.md` cites non-existent `reports/daily/dart-virtual/2026-07-15.md` |
| 2026-07-16 (Wed) | `reports/daily/dart-virtual-trader/` | CORRECT | `memory/dart-virtual-trader/learnings/2026-07-17.md` |
| 2026-07-17 (Thu) | absent (orchestration skip) | N/A | `reports/daily/2026-07-18.md` — no D+1 cycle ran |
| 2026-07-18 (Fri) | `reports/daily/dart-virtual-trader/` | CORRECT | `reports/daily/2026-07-18.md` Cycle Health table |
| 2026-07-19 (Sat) | `reports/daily/dart-position/` | WRONG | `reports/daily/2026-07-18.md` Cycle Health table |

Score: 2 correct / 4 wrong (excluding skip day) = **33% compliance**. W28 plan required 7/7 = 100%.

**W28 Compliance**: The W28 plan (`2026-28-improvements.md`) explicitly required "output directory: `reports/daily/dart-virtual-trader/YYYY-MM-DD.md` 7/7 days in W29." This requirement was **materially failed**.

**Pattern context**: This is Pattern 21 from `memory/evaluator/cross-agent-patterns.md` — "rule-creation cognitive load causes directory instability." The proliferation is worsening (4 different wrong directories in one week vs 2-3 in prior weeks).

---

## Root Cause (Observed)

The agent appears to be selecting directory names at time of output without referencing a fixed rule. The canonical path `dart-virtual-trader/` differs from intuitive shorthands (`dart-virtual/`, `dart-positions/`, `dart-position/`) and the agent is inconsistently applying the rule across sessions.

---

## Required Action

**dart-virtual-trader** must, effective immediately (W30 onward):

1. The **first line** of every daily output file must be the canonical path: `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`. This serves as a self-check anchor.

2. At start of each daily cycle, explicitly state: "Filing to `reports/daily/dart-virtual-trader/[date].md`" before generating content.

3. The reporter agent must flag any dart-virtual-trader citation to a non-canonical path as a process error in the Cycle Health table.

---

## Evaluator Monitoring (W30)

- Compliance threshold: 7/7 days (including skip days marked as N/A with explanation).
- If compliance < 5/7 in W30, escalate to: evaluator recommends disabling dart-virtual-trader section from Daily Report until 5 consecutive correct-directory days achieved.

---

## User Action Requested

- [ ] Approve monitoring threshold: 5/7 compliance minimum in W30 before escalation to reporter exclusion.
- [ ] Confirm whether old stray directories (`dart-virtual/`, `dart-positions/`, `dart-position/`) should be deleted to prevent future misuse.
