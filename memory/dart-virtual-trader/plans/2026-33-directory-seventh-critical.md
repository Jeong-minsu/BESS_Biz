# Plan: Output Directory — Seventh Consecutive Critical

Week: 2026-33
Priority: Critical (7th consecutive week below 71% compliance threshold)
Issue: W33 directory compliance = 4/7 (57%). Aug 10 and Aug 11 filed to `reports/daily/dart/`. Aug 15 filed to `reports/daily/dart-virtual/`. Aug 13 has a duplicate: one correct (`dart-virtual-trader/`) and one wrong (`dart-virtual/`) filed simultaneously. Only Aug 12, 14, and 16 were fully correct. Despite 7/7 learnings (improvement), directory compliance remains structurally non-convergent.

## W33 Directory Record

| Date | Path | Status |
|---|---|---|
| 2026-08-10 (Mon) | reports/daily/dart/2026-08-10.md | WRONG |
| 2026-08-11 (Tue) | reports/daily/dart/2026-08-11.md | WRONG |
| 2026-08-12 (Wed) | reports/daily/dart-virtual-trader/2026-08-12.md | CORRECT |
| 2026-08-13 (Thu) | reports/daily/dart-virtual-trader/2026-08-13.md + dart-virtual/2026-08-13.md | CORRECT + WRONG DUPLICATE |
| 2026-08-14 (Fri) | reports/daily/dart-virtual-trader/2026-08-14.md | CORRECT |
| 2026-08-15 (Sat) | reports/daily/dart-virtual/2026-08-15.md | WRONG |
| 2026-08-16 (Sun) | reports/daily/dart-virtual-trader/2026-08-16.md | CORRECT |

Compliance: 4/7 = 57% (up from 33% in W32, but still below 71% threshold for the 7th consecutive week).

## Escalation History

| Week | Compliance | Status |
|---|---|---|
| W27 | — | Critical |
| W28 | — | Critical |
| W29 | 33% | Critical |
| W30 | 14% | Critical |
| W31 | 29% | Critical |
| W32 | 33% | Critical; W31 plan trigger condition met (< 5/7); user authorization for agent definition hard-code formally requested |
| W33 | 57% | Critical (7th consecutive); user authorization still not received |

## Action Items

- Agent: The canonical output path is `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`. No other path is acceptable. The wrong-path variants (`dart/`, `dart-virtual/`, `dart-position/`, `dart-positions/`, `dart-trader/`) are all banned. Read this file at the start of every daily cycle before producing output. Do not create duplicate files in wrong directories.

- User (still pending from W32): Authorize and implement hard-coded canonical path in `.claude/agents/dart-virtual-trader.md` as a mandatory first-line constraint. Seven consecutive Critical weeks have demonstrated agent-side plans alone are insufficient to fix this.

Success criteria: 7/7 correct directory in W34. Zero wrong-directory variants. Zero duplicate files.
Owner: dart-virtual-trader (agent); user authorization required for definition update.
Deadline: W34 evaluation (2026-08-24).
