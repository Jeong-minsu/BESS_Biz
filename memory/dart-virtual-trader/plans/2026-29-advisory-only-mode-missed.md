# Plan: advisory-only-mode.md Deadline Missed — W29

**Registered by**: evaluator  
**Date**: 2026-07-20  
**Priority**: CRITICAL  
**ISO Week**: 2026-W29  
**Status**: OPEN — user approval required

---

## Issue

`memory/dart-virtual-trader/advisory-only-mode.md` was due **2026-07-18** per W28 evaluator plan (`memory/dart-virtual-trader/plans/2026-28-improvements.md`). As of 2026-07-20 (W29 evaluation date), the file does not exist.

**Evidence**:
- W28 plan (`2026-28-improvements.md`): "By 2026-07-18 (Friday): create `memory/dart-virtual-trader/advisory-only-mode.md` documenting the formal advisory-only classification and its implications."
- `memory/dart-virtual-trader/learnings/2026-07-13.md`: "advisory-only-mode.md outstanding — deadline Jul 18."
- `memory/dart-virtual-trader/learnings/2026-07-17.md`: "advisory-only-mode.md 미작성 — 오늘(Jul 18) 마감."
- `memory/dart-virtual-trader/learnings/2026-07-19.md`: No mention of file creation, implying still absent.
- `ls memory/dart-virtual-trader/` at W29 evaluation: file not found.

This is the **second consecutive week** the deadline has slipped (W27 → W28 → W29).

---

## Root Cause (Observed)

The file is referenced in learnings as outstanding but never actioned. The agent is producing daily analysis outputs but deferring the formal classification document. Each daily cycle writes a learnings file noting the absence, then moves on without creating the document.

---

## Required Action

**dart-virtual-trader** must, at the start of W30 (by 2026-07-21):

1. Create `memory/dart-virtual-trader/advisory-only-mode.md` with at minimum:
   - Classification: ADVISORY ONLY (no execution confirmed since W27)
   - Implication: all position recommendations are non-binding; bess-optimizer and reporter must label outputs accordingly
   - Conditions under which classification would revert to EXECUTION
   - dart_virtual_revenue null field status (36th+ escalation)
   - Standing escalation path for null field resolution

2. Reference the file explicitly in the next daily learnings file as "CREATED — [date]."

---

## W30 Monitoring

Evaluator will check for file existence at W30 evaluation. If still absent, this becomes a **user-action-required** block: the evaluator will recommend suspending dart-virtual-trader output from reporter's Daily Report until the classification document is in place.

---

## User Action Requested

- [ ] Approve escalation path: if `advisory-only-mode.md` absent at W30 evaluation, remove dart-virtual-trader section from Daily Report until resolved.
