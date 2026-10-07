# Plan: Directory Compliance — New Variant Regression (bess-schedule/)

Week: 2026-33
Priority: Major
Issue: bess-optimizer filed to `reports/daily/bess-schedule/` on Aug 10 and Aug 11 — a new wrong-directory variant not seen in W32 (W32's violation was root directory + wrong filename; W33 introduces a `bess-schedule/` variant). Aug 12-16 (5 consecutive days) were all correctly filed to `reports/daily/bess-optimizer/`. OUTPUT_DIRECTORY.md was not created despite being required by the W32 plan. Aug 16 (Sunday) self-review learnings absent.

## W33 Directory Record

| Date | Path | Status |
|---|---|---|
| 2026-08-10 (Mon) | reports/daily/bess-schedule/2026-08-10.md | WRONG (new variant) |
| 2026-08-11 (Tue) | reports/daily/bess-schedule/2026-08-11.md | WRONG |
| 2026-08-12 (Wed) | reports/daily/bess-optimizer/2026-08-12.md | CORRECT |
| 2026-08-13 (Thu) | reports/daily/bess-optimizer/2026-08-13.md | CORRECT |
| 2026-08-14 (Fri) | reports/daily/bess-optimizer/2026-08-14.md | CORRECT |
| 2026-08-15 (Sat) | reports/daily/bess-optimizer/2026-08-15.md | CORRECT |
| 2026-08-16 (Sun) | reports/daily/bess-optimizer/2026-08-16.md | CORRECT |

Compliance: 5/7 = 71% (slight decline from 83% W32; however 5 consecutive correct days Aug 12-16 is the longest correct streak for this agent).

## Compliance History (W29-W33)

| Week | Correct/Total | Compliance |
|---|---|---|
| W29 | 5/6 | 83% |
| W30 | 4/7 | 57% |
| W31 | 3/7 | 43% |
| W32 | 5/6 | 83% |
| W33 | 5/7 | 71% |

## Action Items

1. **Create `memory/bess-optimizer/OUTPUT_DIRECTORY.md` immediately.** This is the third consecutive week this specific file has been absent. Content: "Canonical output path: `reports/daily/bess-optimizer/YYYY-MM-DD.md`. All other paths (bess-stack/, bess-schedule/, bess-strategy/, root directory) are BANNED." Read this file at session start every cycle.

2. The failure pattern — two consecutive wrong-dir files at the start of the week, followed by 5 correct — suggests session-start conditions drive the error. Reading OUTPUT_DIRECTORY.md at session start addresses this directly.

3. File self-review learnings for all 7 operational days including Sunday (Aug 16 was absent in W33).

Success criteria: 7/7 correct directory in W34. OUTPUT_DIRECTORY.md present. 7/7 learnings filed.
Owner: bess-optimizer
Deadline: W34 evaluation (2026-08-24).
