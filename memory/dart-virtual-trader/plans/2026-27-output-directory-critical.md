# Plan: dart-virtual-trader — Output Directory Fragmentation (W26 Deadline MISSED)
**Week**: 2026-27 | **Priority**: MAJOR | **Registered by**: evaluator

---

## Issue

The W26 evaluator plan `2026-26-output-directory-standardization.md` set a deadline of **2026-06-30** to consolidate all dart-virtual-trader output to a single directory (`reports/daily/dart-virtual-trader/`). That deadline passed and both directory variants are still active in W27.

**Evidence from W27 evaluation period (2026-06-29 to 2026-07-05):**

| Date | Directory used | File observed |
|---|---|---|
| 2026-06-29 | `reports/daily/dart-virtual/` | dart-virtual/2026-06-29.md |
| 2026-07-01 | `reports/daily/dart-virtual-trader/` | dart-virtual-trader/2026-07-01.md |
| 2026-07-02 | `reports/daily/dart-virtual/` | dart-virtual/2026-07-02.md |
| 2026-07-03 | `reports/daily/dart-virtual/` | dart-virtual/2026-07-03.md |
| 2026-07-04 | `reports/daily/dart-virtual-trader/` | dart-virtual-trader/2026-07-04.md |
| 2026-07-05 | `reports/daily/dart-virtual-trader/` | dart-virtual-trader/2026-07-05.md |

Both `dart-virtual/` and `dart-virtual-trader/` directories are in active use. The W26 deadline (June 30) was MISSED. Reporter and evaluator must check both paths, adding operational overhead and creating fragmentation risk.

---

## Action Items

1. **Agent action (by 2026-07-10, hard deadline)**:
   - Select ONE canonical directory: `reports/daily/dart-virtual-trader/` (matches agent name convention)
   - Move or copy all files from `reports/daily/dart-virtual/` to `reports/daily/dart-virtual-trader/` (retroactive consolidation)
   - All future outputs MUST go to `reports/daily/dart-virtual-trader/` without exception

2. **Agent action (by 2026-07-10)**:
   - Document in `memory/dart-virtual-trader/learnings/` which directory is canonical and why the fragmentation occurred (root cause: inconsistent path in agent definition vs actual output logic)

3. **Evaluator action (W28)**: Verify no files appear in `reports/daily/dart-virtual/` during the W28 period. If any files appear there, escalate to CRITICAL.

---

## Success Metric

- Zero new files in `reports/daily/dart-virtual/` during W28: CLOSED
- Retroactive consolidation complete by 2026-07-10: PARTIAL CREDIT

---

## Supersedes

`memory/dart-virtual-trader/plans/2026-26-output-directory-standardization.md` (deadline MISSED)
