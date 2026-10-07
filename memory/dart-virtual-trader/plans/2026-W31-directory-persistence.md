# Plan: dart-virtual-trader Directory Compliance — 5th Consecutive Critical
**Registered by**: evaluator
**Week**: 2026-W31 (evaluated 2026-08-03)
**Priority**: CRITICAL (5th consecutive week)
**Status**: OPEN

---

## Observed Failure

W31 directory compliance: **2/7 = 29%** (up from 14% in W30, but still Critical)

Evidence by day:
- 2026-07-27: CORRECT — `reports/daily/dart-virtual-trader/2026-07-27.md`
- 2026-07-28: WRONG — `reports/daily/dart-position/2026-07-28.md`
- 2026-07-29: WRONG — `reports/daily/dart-position/2026-07-29.md`
- 2026-07-30: Not found (DEGRADED — no output)
- 2026-07-31: WRONG — `reports/daily/dart-virtual/2026-07-31.md`
- 2026-08-01: CORRECT — `reports/daily/dart-virtual-trader/2026-08-01.md`
- 2026-08-02: WRONG — `reports/daily/dart-trader/2026-08-02.md` (NEW variant — 4th distinct wrong directory)

**Pattern**: Agent uses correct directory on some days and reverts to wrong directories on others. No memory mechanism persists the directory rule across outputs. W31 introduced a new wrong-directory variant (`dart-trader/`) not seen before, indicating the proliferation is continuing.

**History of Critical escalation**: Weeks W25, W26, W27, W28, W29 (per improvement-tracker). Now W30 + W31 = 7 consecutive Critical designations.

---

## Root Cause Analysis

The agent lacks a persistent, runtime-readable rule that is unconditionally checked before writing each output. Improvements noted in memory/learnings have not translated to consistent execution because the rule is not enforced at the file-write moment — it is referenced in plans that require recall.

The advisory-only-mode.md (created 2026-07-28, resolving W30 Critical item 3) demonstrates that the agent CAN create persistent memory files when prompted. The same mechanism is not yet applied to directory enforcement.

---

## Required Action

### Immediate (W32, every day)
1. Create `memory/dart-virtual-trader/OUTPUT_DIRECTORY.md` — a single canonical file containing only:
   ```
   CANONICAL PATH: reports/daily/dart-virtual-trader/YYYY-MM-DD.md
   ALL OTHER PATHS ARE WRONG. Do not use:
   - dart-position/
   - dart-virtual/
   - dart-trader/
   - reports/daily/ (root)
   Any other directory variant is incorrect.
   ```
2. Every daily output session: read `OUTPUT_DIRECTORY.md` as the FIRST action before writing any file.
3. After writing: verify the file path contains the substring `dart-virtual-trader/` — if not, move the file.

### Structural (before W33)
4. Add to the agent's `.claude/agents/dart-virtual-trader.md` definition (under "Output"): the canonical path repeated in bold.

---

## Success Criterion
- W32: >= 5/7 correct directory (from whatever days have output)
- W33: >= 6/7
- W34: 7/7 = sustained, de-escalate to Major watch

---

## Escalation Note

If W32 compliance < 5/7, the evaluator will flag this to the user as requiring agent definition update (hard-coded path in agent system prompt). Five consecutive Critical weeks without resolution is a signal the memory/plan mechanism alone is insufficient.

---

## Cross-Reference
- Previous plan: `memory/dart-virtual-trader/plans/2026-W30-directory-final-escalation.md`
- advisory-only-mode.md: `memory/dart-virtual-trader/advisory-only-mode.md` (RESOLVED W30 issue)
- Improvement tracker: `memory/evaluator/improvement-tracker.md` row 2026-W30-dart-directory
