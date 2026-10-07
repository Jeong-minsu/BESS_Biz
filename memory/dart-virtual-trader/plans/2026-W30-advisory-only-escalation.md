# Plan: dart-virtual-trader advisory-only-mode.md — W30 Escalation (3rd Consecutive Miss)

**Registered by**: evaluator  
**Date**: 2026-07-27  
**Priority**: CRITICAL  
**Status**: OPEN — 3rd consecutive deadline missed  

---

## Issue

`memory/dart-virtual-trader/advisory-only-mode.md` has not been created. This file was required by:
- W28 plan deadline: 2026-07-18 — MISSED
- W29 plan deadline: 2026-07-21 (W30 Day 1) — MISSED
- W30 check: 2026-07-27 — STILL ABSENT (confirmed by `find` command returning empty)

The file was also referenced in learnings for 2026-07-13, 07-17, 07-19 as "outstanding" — the agent has known about this obligation for 4+ weeks without acting.

## Evidence

`find /home/user/BESS_Biz/memory/dart-virtual-trader/ -name "advisory-only-mode.md"` — no output (file does not exist).

## Purpose of the File

The `advisory-only-mode.md` document is needed to formally define the dart-virtual-trader's operational mode: all positions are ADVISORY ONLY, no submissions to ERCOT, dart_virtual_revenue = $0 is the expected normal state. Without this document:
- Reporter lacks a stable specification of what the dart-virtual-trader section represents
- Approach axis scoring remains suspended by evaluator (cannot score advisory-only positions against settlement actuals)
- When pnl-manager sees dart_virtual_revenue = $0, it has no authoritative reference document explaining the advisory-only mode

## Required Content

The file must contain:
1. Statement that dart-virtual-trader operates in ADVISORY ONLY mode as of W28 (2026-07-13)
2. Reason: execution scope unconfirmed; user has not confirmed ERCOT submission path
3. Implications: dart_virtual_revenue = $0 is expected; hit rate is non-computable against settlements
4. Reversion criteria: user confirms execution scope + Tenaska DART virtual endpoint accessible
5. Date created and evaluator plan reference

## Action

Create `memory/dart-virtual-trader/advisory-only-mode.md` immediately in the NEXT DAILY CYCLE (2026-07-28 or earlier).

## Escalation Trigger

If not created by W31 evaluation (2026-08-03), evaluator will recommend removing dart-virtual-trader section from Daily Reports pending user review. This will be the fourth consecutive miss.

## Success Criterion

File exists at `memory/dart-virtual-trader/advisory-only-mode.md` and is cited in the next daily position report and learnings file.
