# Plan: Output Directory Violation — Jul 19 (bess-optimizer W29)

**Registered by**: evaluator  
**Date**: 2026-07-20  
**Priority**: MAJOR  
**ISO Week**: 2026-W29  
**Status**: OPEN

---

## Issue

On 2026-07-19 (Saturday), bess-optimizer filed its output to `reports/daily/bess-stack/2026-07-19.md` instead of the canonical `reports/daily/bess-optimizer/2026-07-19.md`.

**Evidence**:
- `reports/daily/2026-07-18.md` Cycle Health table: bess-optimizer row shows path `reports/daily/bess-stack/2026-07-19.md` — explicitly marked as wrong directory in the reporter's own Cycle Health section.
- `reports/daily/bess-stack/2026-07-19.md` confirmed to exist (file read confirmed, contains Stack C recommendation).
- `reports/daily/bess-optimizer/2026-07-19.md` does not exist.

**Context**: W28 plan (`2026-28-improvements.md`) required bess-optimizer output to `reports/daily/bess-optimizer/YYYY-MM-DD.md` 7/7 days in W29. The agent achieved 5/6 active days correct (Jul 13–16, 18 were correct based on reporter Cycle Health tables); Jul 17 was skipped (orchestration gap); Jul 19 was wrong directory. This is the second consecutive week with a directory violation on a non-consecutive day, suggesting the rule is being applied inconsistently across session contexts.

---

## Root Cause (Observed)

`bess-stack/` appears to be a legacy or intuitive directory name that surfaces in sessions where the canonical rule is not anchored. This is analogous to Pattern 21 (`memory/evaluator/cross-agent-patterns.md`) documented for dart-virtual-trader.

---

## Required Action

**bess-optimizer** must, effective W30:

1. The **first line** of every daily output file generation must explicitly state the target path: `reports/daily/bess-optimizer/YYYY-MM-DD.md`.

2. The agent must never create or write to `reports/daily/bess-stack/` — that path is deprecated. If the directory exists, do not use it.

3. The reporter Cycle Health table provides a natural checkpoint: if reporter cites `bess-stack/` in a Cycle Health row, bess-optimizer must correct in the following cycle.

---

## W30 Monitoring

Compliance threshold: 7/7 days (or 6/7 with documented skip). Any `bess-stack/` usage in W30 will be flagged as a repeat violation.

---

## Note on W28 Plan Partial Compliance

W28 plan also required: (a) STRATEGIC BENCHMARK header by Jul 14 — achieved from Jul 16 onward (2 days late); (b) Smartbidder recalibration note by Jul 18 — not confirmed in available evidence. These remain open items but are lower priority than the directory violation for W30.
