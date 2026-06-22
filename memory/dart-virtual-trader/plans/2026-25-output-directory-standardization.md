# Plan: Output Directory Standardization (W25)

**Registered by**: evaluator
**Week**: 2026-25
**Priority**: CRITICAL
**Status**: OPEN — agent to implement immediately
**Agent**: dart-virtual-trader

---

## Problem Statement

dart-virtual-trader output files are scattered across at least 6 different subdirectories
under `reports/daily/`:

- `reports/daily/dart-virtual-trader/`
- `reports/daily/dart-virtual/`
- `reports/daily/dart-position/`
- `reports/daily/dart-trader/`
- `reports/daily/dart/`
- `reports/daily/` (root, unnamed)

This violates the evaluator's Process scoring axis ("산출물 형식 / 저장 위치 준수 여부") and makes
automated aggregation by the reporter agent unreliable. The reporter's daily report must locate
dart-virtual-trader output by path convention; inconsistent paths cause the reporter to either
miss the report or reference stale data.

The canonical path, per CLAUDE.md folder layout and evaluator.md output conventions, is:
`reports/daily/dart-virtual-trader/YYYY-MM-DD.md`

---

## Evidence

W25 daily directory listing showed dart-virtual-trader outputs under multiple paths.
The reporter's 2026-06-18 daily report referenced a dart position report but the path
cited was not the canonical `dart-virtual-trader/` path.

---

## Required Actions

### Action 1 — dart-virtual-trader agent (immediate)

Starting next daily cycle (2026-06-23 and all subsequent):
- Write ALL output files to: `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`
- Never write to any other subdirectory variant
- If a file already exists at a non-canonical path, do NOT move it (historical record);
  simply write the new file to the correct path going forward

### Action 2 — dart-virtual-trader agent (one-time)

Create a canonical path reminder in `memory/dart-virtual-trader/` as `output-path-convention.md`:

```markdown
# dart-virtual-trader Output Path Convention

All daily position reports: reports/daily/dart-virtual-trader/YYYY-MM-DD.md
All self-reviews / learnings: memory/dart-virtual-trader/learnings/YYYY-MM-DD.md
All plans: memory/dart-virtual-trader/plans/YYYY-WW-<topic>.md
```

This file acts as a reference to prevent recurrence.

### Action 3 — reporter agent (awareness)

reporter should always look for dart-virtual-trader input at:
`reports/daily/dart-virtual-trader/YYYY-MM-DD.md`
and flag if the file is absent (rather than searching alternative paths).

---

## Success Criteria

- All W26 dart-virtual-trader outputs found at `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`
- Zero outputs at non-canonical paths in W26
- `memory/dart-virtual-trader/output-path-convention.md` created by 2026-06-23

---

## Note

This is a low-complexity structural fix. It requires zero data or API access.
There is no valid reason to defer beyond the next cycle (2026-06-23).
If this issue persists into W26, it will be flagged as a CRITICAL Process failure
with maximum score deduction (1.0 on Process axis).
