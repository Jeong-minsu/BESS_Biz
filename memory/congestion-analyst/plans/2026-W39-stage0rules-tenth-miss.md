# Improvement Plan — 2026-W39 — stage-0-rules.md Absent (10th Consecutive Week)
**Agent**: congestion-analyst
**Priority**: CRITICAL
**Registered by**: evaluator | 2026-09-28

---

## Status

`memory/congestion-analyst/stage-0-rules.md` confirmed absent as of 2026-09-28. Root memory directory contains only: history/, learnings/, plans/. The file is not present in any subdirectory.

Note: `stage-progress.md` was found at `memory/congestion-analyst/plans/stage-progress.md` (inside plans/) — consistent with an alternate location from what W38 described (root level). Stage 0 rules remain informally embedded within stage-progress.md and learnings, but the standalone formal ruleset does not exist.

## Miss Counter

| Week | Status |
|---|---|
| W30-W31 | First misses |
| W32 | Critical escalation |
| W34-W35 | Suspension clause triggered (W36) |
| W36-W37 | Suspension clause unenforced (2nd, 3rd time) |
| W38 | 9th miss — suspension clause unenforced 3rd time |
| **W39** | **10th miss — suspension clause unenforced 4th time** |

## Context

W39 produced 2 run-day congestion reports (Sep 21, Sep 26) — both correct directory (congestion/). Sep 24 learning was comprehensive and well-structured. Analytical quality on run days remains strong. The suspension clause has been formally triggered since W36 but has not been enforced.

As with BRIEFING_TEMPLATE.md, this file is agent-executable without user action. 10 consecutive misses is definitive evidence that AGENT IMMEDIATE instructions are insufficient.

## Required Actions

**AGENT IMMEDIATE** (no user authorization required):
1. Create `memory/congestion-analyst/stage-0-rules.md` at session start of next cycle.
2. Content: extract and formalize the SCI thresholds, constraint boundary conditions, D+2 continuity logic, duck curve tier classification rules, and HOUSTON_IMPORT floor already embedded in stage-progress.md and recent learnings. This is a consolidation task, not new analysis.
3. Reference stage-0-rules.md at the start of every congestion forecast cycle.

**USER REQUIRED (AUTHORIZATION — FINAL)**:
1. After 10 misses and 4 unenforced suspension clause triggers, confirm: implement suspension of congestion section from Daily Report, or formally waive.
2. Note: the suspension would be lifted immediately upon stage-0-rules.md creation. This is a zero-cost agent task that has simply not been done.
3. If hard-code is preferred (mandatory stage-0-rules.md check at session start), authorize agent definition update.

## Success Criterion

`memory/congestion-analyst/stage-0-rules.md` exists by W40 evaluation date (2026-10-05). File must contain: SCI threshold table, constraint tier classification logic (NEGLIGIBLE/LOW/MEDIUM/MODERATE/HIGH), D+2 carry-in rules, duck curve pre-condition parameters.
