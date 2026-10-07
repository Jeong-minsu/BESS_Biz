# Plan: bess-optimizer Directory Compliance — Regression + New Violation Type
**Registered by**: evaluator
**Week**: 2026-W31 (evaluated 2026-08-03)
**Priority**: CRITICAL (escalated from Major W30)
**Status**: OPEN

---

## Observed Failure

W31 directory compliance: **3/7 = 43%** — REGRESSION from 4/7 (57%) in W30.

Evidence by day:
- 2026-07-27: CORRECT — `reports/daily/bess-optimizer/2026-07-27.md`
- 2026-07-28: WRONG — `reports/daily/bess-stack/2026-07-28.md` (banned path, repeated violation)
- 2026-07-29: WRONG — `reports/daily/bess-stack/2026-07-29.md` (banned path, repeated violation)
- 2026-07-30: WRONG — `reports/daily/bess-stack/2026-07-30.md` (banned path, repeated violation)
- 2026-07-31: CORRECT — `reports/daily/bess-optimizer/2026-07-31.md`
- 2026-08-01: WRONG — `reports/daily/2026-08-01-bess-stack.md` (NEW TYPE: root dir + wrong naming)
- 2026-08-02: CORRECT — `reports/daily/bess-optimizer/2026-08-02.md`

**W30 plan result**: `memory/bess-optimizer/plans/2026-W30-directory-escalation.md` registered ban on `bess-stack/`. The ban was violated on 3 of 4 consecutive days (Jul 28-30), and a new violation appeared on Aug 1 — the agent filed to root `reports/daily/` with a wrong filename (`2026-08-01-bess-stack.md`), which is a previously unseen violation type.

Cross-reference: `2026-07-31.md` (correct) references `reports/daily/bess-stack/2026-07-30.md` as a prior SoC source — confirming the agent knew Jul 30 was in the wrong directory but still used that path, showing the agent does not self-correct.

---

## Root Cause Analysis

Two distinct failure modes in W31:
1. **`bess-stack/` reversion**: Agent defaults to this path when not actively checking the canonical rule. The plan file exists but is not read at execution time.
2. **Root-dir + wrong filename**: Aug 1 violation is qualitatively different — the agent filed to `reports/daily/` root with a hyphenated filename, suggesting a different generation path (possibly a different session or prompt context). This indicates the canonical path is not being checked reliably even within a single week.

---

## Required Action

### Immediate (W32, every day)
1. Create `memory/bess-optimizer/OUTPUT_DIRECTORY.md` with canonical path rule:
   ```
   CANONICAL PATH: reports/daily/bess-optimizer/YYYY-MM-DD.md
   BANNED PATHS (do not use under any circumstance):
   - reports/daily/bess-stack/
   - reports/daily/ (root, any file)
   - reports/daily/bess/ or any variant
   File naming: YYYY-MM-DD.md only. No prefix/suffix.
   ```
2. Read `OUTPUT_DIRECTORY.md` as first action in every daily output session.
3. After writing: verify path contains `bess-optimizer/` substring.

### W32 also required
4. The W31 misfiled reports (bess-stack/Jul 28-30, root/Aug 1) should be MOVED to the correct directory. Agent should move them at start of W32 session.

---

## Success Criterion
- W32: >= 5/7 correct (no `bess-stack/` violations, no root violations)
- W33: >= 6/7
- W34: 7/7 — de-escalate

---

## Escalation Note
This is the first Critical for bess-optimizer (escalated from Major W30). If W32 < 5/7, evaluator will flag to user for agent definition hard-code (same mechanism as dart-virtual-trader).

---

## Cross-Reference
- Previous plan: `memory/bess-optimizer/plans/2026-W30-directory-escalation.md`
- Improvement tracker: `memory/evaluator/improvement-tracker.md` row 2026-W30-bess-directory
