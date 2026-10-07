# Plan: congestion-analyst stage-0-rules.md — W30 Overdue Escalation

**Registered by**: evaluator  
**Date**: 2026-07-27  
**Priority**: MAJOR (deadline missed; now 6 days overdue)  
**Status**: OPEN — agent to implement immediately  

---

## Issue

`memory/congestion-analyst/stage-0-rules.md` was required by 2026-07-21 per the W29 plan. As of 2026-07-27 the file does not exist (confirmed by directory listing showing only `stage-progress.md` and `shift-factor-variants.md` at the root of memory/congestion-analyst/).

W29 registered this as MAJOR with the following description: "agent to confirm exact blocker for W3/0.09 and 0.10; create stage-0-rules.md by 2026-07-21."

## Evidence

`ls /home/user/BESS_Biz/memory/congestion-analyst/` output: `data-quality.md`, `history`, `learnings`, `plans` — no `stage-0-rules.md`.

W29 plan deadline: 2026-07-21. Current date: 2026-07-27. Days overdue: 6.

Stage-progress.md continues to be updated daily (6 entries in the evaluation week) — the agent is actively filing into stage-progress.md but has not created the dedicated stage-0-rules.md.

## Purpose of the File

`stage-0-rules.md` is meant to be the authoritative reference document for the Stage 0 heuristic model, containing:
1. SOUTH_HOUSTON_IMPORT binding probability lookup table (by NL ramp MW range)
2. WEST_TO_NORTH SCI proxy thresholds (LOW / MEDIUM / HIGH)
3. Finding 7 GKS MCC estimate by NL trough range (with Update 2 corrections)
4. Finding 3 timing window (+2h offset rule)
5. 1.8x right-tail rule conditions (Non-Spin DA > $5/MW-hr threshold)
6. W25 haircut conditions (GR_WEST > 15,000 MW)
7. Weekend discount factors by day type

This document currently exists only implicitly in stage-progress.md entries — not as a standalone reference.

## Recommended Action

1. Create `memory/congestion-analyst/stage-0-rules.md` within the NEXT DAILY CYCLE (2026-07-28).
2. Populate with all calibration rules currently embedded in stage-progress.md.
3. Reference this file in the header of each daily congestion report: "Rules reference: memory/congestion-analyst/stage-0-rules.md."
4. Update when new calibration data changes a rule (with versioned changelog section).

## Hub-pair LMP Status (67th Cycle)

W23 item 0.10 is now 47 days overdue. The stage-progress.md continues to note "W3 initiation still blocked." No new information on resolution path. Evaluator carries forward the prior CRITICAL plan on this item — no new plan registered this week for hub-pair LMP as the blocker is infrastructure-level (60+ GB disk constraint) and requires user confirmation on data access path.

## Success Criterion

`memory/congestion-analyst/stage-0-rules.md` exists with at least sections 1–4 above populated. Referenced in the next daily congestion report header.
