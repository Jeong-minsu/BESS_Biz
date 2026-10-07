# Plan: congestion-analyst stage-0-rules.md — Final Deadline (3rd Escalation)
**Registered by**: evaluator
**Week**: 2026-W31 (evaluated 2026-08-03)
**Priority**: MAJOR (approaching Critical — 3rd consecutive escalation)
**Status**: OPEN

---

## Observed Failure

`memory/congestion-analyst/stage-0-rules.md` is **ABSENT**.

Timeline of escalation:
- W28 (evaluator): First required — "Stage 0 must document binding rules before Stage 1 gate"
- W29 (evaluator): Deadline set 2026-07-14
- W30 (evaluator): Deadline missed. New deadline 2026-07-21. Plan file: `2026-W30-stage0rules-overdue.md`
- W31 (evaluator): Deadline 2026-07-21 missed. **File still absent as of 2026-08-03 — 13 days overdue.**

The congestion-analyst produces correct directory outputs (7/7 in W31, CORRECT) and the SOUTH_HOUSTON_IMPORT directional accuracy is well-documented in learnings. The stage-0-rules.md is purely a formalization task — no new analysis required.

The learnings files already contain all the content needed:
- Heuristic model description
- Binding floor thresholds (NL ramp, wind deviation)
- Directional accuracy tracking (13/13 confirmed in Jul 31 learnings)
- T+2 settlement queue logic

The missing step is consolidation into a standing reference file.

---

## What stage-0-rules.md Must Contain (minimum specification)

1. **Model type**: heuristic (rule-based, not ML) — Stage 0 definition
2. **Binding criteria**: NL ramp threshold, wind deviation threshold, historical binding floor
3. **Primary constraint tracked**: SOUTH_HOUSTON_IMPORT (and any others actively monitored)
4. **Direction accuracy tracking method**: cumulative log format
5. **Hub-pair LMP status**: absent since [date] — note data gap and workaround
6. **T+2 settlement queue**: how pending verifications are tracked
7. **Stage 1 transition criteria**: what metric/threshold gates upgrade

---

## Required Action

### Week of 2026-W32 (August 3–9) — HARD DEADLINE: 2026-08-08
1. Write `memory/congestion-analyst/stage-0-rules.md` using content from:
   - `memory/congestion-analyst/learnings/2026-07-31.md` (most complete structural summary)
   - `memory/congestion-analyst/plans/stage-progress.md`
   - Any other learnings from W30-W31 period
2. Minimum length: 200 words. Maximum: 500 words. Brevity is acceptable — completeness is required.
3. Confirm completion in `memory/congestion-analyst/learnings/2026-08-08.md` with line: "stage-0-rules.md written [date]."

---

## Escalation Trigger

If stage-0-rules.md is still absent at W32 evaluation (2026-08-10), evaluator will escalate to CRITICAL and flag to user for manual intervention. The content is already documented in learnings — the only missing step is writing the file.

---

## Cross-Reference
- Previous plan: `memory/congestion-analyst/plans/2026-W30-stage0rules-overdue.md`
- Primary evidence source: `memory/congestion-analyst/learnings/2026-07-31.md`
- Stage progress tracker: `memory/congestion-analyst/plans/stage-progress.md`
- Improvement tracker: `memory/evaluator/improvement-tracker.md` row 2026-W30-congestion-stage0rules
