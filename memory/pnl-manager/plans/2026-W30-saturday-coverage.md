# Plan: pnl-manager Saturday Coverage Gap

**Registered by**: evaluator  
**Date**: 2026-07-27  
**Priority**: MINOR  
**Status**: OPEN — user to confirm weekend coverage policy  

---

## Issue

No pnl report was filed for 2026-07-23 (Saturday). Similarly, a Saturday gap appeared in W29 (2026-07-17 orchestration skip). The W29 evaluator plan (`memory/evaluator/plans/2026-29-orchestration-skip-jul17.md`) requested user confirmation on whether Saturday D+1 coverage is required.

That user confirmation has not been received. Without it, pnl-manager has no policy basis for whether to attempt Saturday pnl reporting.

## Evidence

`ls reports/daily/pnl/ | grep 2026-07-2[0-6]` output: 07-20, 07-21, 07-22, 07-24, 07-25, 07-26 — 07-23 absent.

## Clarification Needed

1. Is Saturday D+1 operational coverage required? (The DAM bid cutoff for Saturday is also 10:00 CT Friday — so if Saturday coverage is needed, it must be planned Friday morning.)
2. If yes: the 07-23 Saturday pnl gap is a DEGRADED day (Tenaska likely unavailable from prior day's IP whitelist failure). A DEGRADED report should still be filed.
3. If no: document Saturday as excluded in `orchestration/daily-0730-workflow.md`.

## Note on Tenaska and Smartbidder Simultaneous Failures

W30 introduced a new degraded pattern: both Tenaska (IP whitelist, 27th-28th failure) AND Smartbidder (client_secret, 1st-2nd failure) failed simultaneously on 07-26. When both sources fail, the pnl report correctly shows DEGRADED. The agent's fallback protocol (filing a DEGRADED report with prior-day reference and recovery action) is appropriate. No new plan is needed for the dual-failure scenario — the existing DEGRADED template handles it correctly.

## Success Criterion

User confirms weekend pnl coverage policy. If coverage required: file DEGRADED report with known context on missing Saturday flowdays. If not required: document exception in `orchestration/daily-0730-workflow.md`.
