# Improvement Plan — 2026-W39 — BRIEFING_TEMPLATE.md Absent (9th Consecutive Week)
**Agent**: market-analyst
**Priority**: CRITICAL
**Registered by**: evaluator | 2026-09-28

---

## Status

`memory/market-analyst/BRIEFING_TEMPLATE.md` confirmed absent as of 2026-09-28. Root memory directory contains only: history/, learnings/, plans/.

This is the 9th consecutive week the file has been absent. W38 plan (2026-W38-briefing-template-eighth-miss.md) required creation by W39. Outcome: FAILED.

## Miss Counter

| Week | Status |
|---|---|
| W32-W34 | First misses recorded |
| W35-W36 | Escalated to Critical |
| W37 | 7th miss — hard-code recommendation issued |
| W38 | 8th miss — user authorization requested |
| **W39** | **9th miss — plan FAILED** |

## Context

W39 produced 2 run-day briefings (Sep 21, Sep 26) — both correct directory (market-briefing/). Sep 26 briefing demonstrated improvement (first implementation of Sep 17 actions 1 and 2: Duck curve pre-check table, HE18 independent row). The agent shows good operational capability on run days but continues to fail this infrastructure task.

The template file is agent-executable without any user action required. Its absence for 9 consecutive weeks despite being listed as AGENT IMMEDIATE in every plan since W32 represents a sustained self-compliance failure.

## Required Actions

**AGENT IMMEDIATE** (no user authorization required):
1. Create `memory/market-analyst/BRIEFING_TEMPLATE.md` at session start of the next cycle. This is a one-time, 15-minute task.
2. The template should contain: the 5-bullet briefing structure, DEGRADED fallback language, data source header format, Duck curve 3-check pre-condition table, HE18 independent price row format.
3. Reference the template at the start of every briefing cycle as Process Step 1. If the file does not exist, creation takes priority over briefing generation.

**USER REQUIRED (AUTHORIZATION — FINAL)**:
1. After 9 misses, confirm whether hard-coding a mandatory template-check as Process Step 1 in `.claude/agents/market-analyst.md` is authorized. Repeated AGENT IMMEDIATE instructions have not resulted in compliance.
2. If hard-code is not authorized, accept that the template may never be created and remove it from the plans/compliance tracking scope.

## Success Criterion

`memory/market-analyst/BRIEFING_TEMPLATE.md` exists by W40 evaluation date (2026-10-05). File must contain: briefing structure, DEGRADED fallback, Duck curve 3-check table, HE18 row convention.
