# Improvement Plan — 2026-W37 — stage-0-rules.md Absent (8th Consecutive Week)
**Agent**: congestion-analyst
**Priority**: CRITICAL
**Issue**: `memory/congestion-analyst/stage-0-rules.md` has been absent for 8 consecutive weeks (W30–W37). The CONGESTION_PROJECT spec (agensts/CONGESTION_PROJECT.md) requires this file as the persisted heuristic ruleset for Stage 0 provisional operation. Stage 1 entry (hub-pair LMP integration) is also blocked by hub-pair data absence (~113 cycles). Without stage-0-rules.md, heuristic decisions are not auditable across sessions.
**Root Cause**: File was never created despite being referenced in both the agent definition and CONGESTION_PROJECT.md. 7/7 dir compliance confirms strong process adherence on output paths; however memory file creation is a separate process step that has not been completed for 8 consecutive weeks. Stage 1 blockage (hub-pair LMP absent) may have reduced urgency perception — but Stage 0 rules must be documented regardless of Stage 1 status.
**Required Action**:
1. AGENT IMMEDIATE: Create `memory/congestion-analyst/stage-0-rules.md` at next session start (2026-09-14). Minimum content: (a) binding probability thresholds for alert levels, (b) λ estimation method in absence of ML model, (c) node MCC fallback approach, (d) Stage 0→1 entry condition (hub-pair LMP data available for ≥5 consecutive days), (e) CONGESTION_PROJECT stage-progress link.
2. AGENT IMMEDIATE: Update `memory/congestion-analyst/plans/stage-progress.md` to reflect Stage 0 status as of W37-end: hub-pair LMP absent ~113 cycles, Stage 1 entry blocked.
3. EVALUATOR NOTE: Hub-pair LMP data absence is a shared infrastructure issue. Escalation to user for data source remediation is separate from the stage-0-rules.md creation obligation.
**Success Criterion**: `memory/congestion-analyst/stage-0-rules.md` exists and is ≥ 150 words by 2026-09-14 (W38 day 1). stage-progress.md updated with W37 end-state.
**Deadline**: 2026-W38 (by 2026-09-20)
**Escalation**: W38 still absent (9th week) → user-authorized hard-code in `.claude/agents/congestion-analyst.md`. Same precedent as congestion-analyst's own W34 consequence clause for output directory failures.
