# Plan: Directory Compliance — Sixth Consecutive Critical

Week: 2026-W32
Priority: Critical
Issue: dart-virtual-trader filed to wrong directories on 4 of 6 operational days (33%); this is the 6th consecutive Critical designation for this same failure.
Action: Evaluator has formally requested user authorization to hard-code the canonical output path in `.claude/agents/dart-virtual-trader.md`. Per W31 plan trigger condition (W32 compliance < 5/7 = 71%), the threshold was again missed (33%). In parallel, agent must self-read `memory/dart-virtual-trader/plans/2026-W31-directory-persistence.md` at the start of every session and confirm path before writing. Correct path: `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`. Banned paths (all variants observed): `dart-position/`, `dart-virtual/`, `dart/`, `dart-trader/`.
Success criteria: 7/7 correct directory in W33 evaluation period (2026-08-10 through 2026-08-16). If compliance remains below 5/7 in W33, evaluator recommends user suspend agent until agent definition is updated.
Owner: dart-virtual-trader (execution) + user (agent definition authorization)

## Violation History (for reference)

| Week | Correct | Wrong | Compliance | Status |
|---|---|---|---|---|
| W25-W27 | Various | Various | <50% | Critical |
| W28 | 2/7 | 5/7 | 29% | Critical |
| W29 | 2/6 | 4/6 | 33% | Critical |
| W30 | 1/7 | 6/7 | 14% | Critical (worst) |
| W31 | 2/7 | 5/7 | 29% | Critical |
| W32 | 2/6 | 4/6 | 33% | Critical |

Wrong directories observed in W32:
- `reports/daily/dart-virtual/2026-08-05.md` (wrong)
- `reports/daily/dart/2026-08-06.md` (wrong)
- `reports/daily/dart/2026-08-07.md` (wrong)
- `reports/daily/dart-virtual/2026-08-09.md` (wrong)

Correct: `reports/daily/dart-virtual-trader/2026-08-03.md` and `reports/daily/dart-virtual-trader/2026-08-04.md`.
