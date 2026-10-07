# Plan: Output Directory — Eighth Consecutive Critical

Week: 2026-34
Priority: CRITICAL (8th consecutive week; 0/7 compliance — worst on record)
Escalation status: User authorization for agent definition hard-code STILL PENDING (requested since W32; no response received as of W34 evaluation 2026-08-24)

## W34 Directory Record

| Date | Path | Status |
|---|---|---|
| 2026-08-17 (Mon) | reports/daily/dart-position/2026-08-17.md | WRONG (new variant: "dart-position") |
| 2026-08-18 (Tue) | reports/daily/dart/2026-08-18.md | WRONG |
| 2026-08-19 (Wed) | reports/daily/dart/2026-08-19.md | WRONG |
| 2026-08-20 (Thu) | reports/daily/dart/2026-08-20.md | WRONG |
| 2026-08-21 (Fri) | reports/daily/dart/2026-08-21.md | WRONG |
| 2026-08-22 (Sat) | reports/daily/dart-virtual/2026-08-22.md | WRONG |
| 2026-08-23 (Sun) | reports/daily/dart-virtual/2026-08-23.md | WRONG |

Compliance: 0/7 = 0%. Lowest compliance since tracking began. New wrong-path variant introduced: `dart-position/` (Aug 17).

## Escalation History (W27–W34)

| Week | Compliance | Notes |
|---|---|---|
| W27 | — | Critical |
| W28 | — | Critical |
| W29 | 33% | Critical |
| W30 | 14% | Critical |
| W31 | 29% | Critical; W31 trigger condition met |
| W32 | 33% | Critical; user authorization for hard-code formally triggered |
| W33 | 57% | Critical (7th); user authorization still pending |
| W34 | 0% | Critical (8th); regression to worst-ever compliance; user authorization still pending |

## Status of Parallel Issues

- Advisory-only mode: MAINTAINED (positive; `memory/dart-virtual-trader/advisory-only-mode.md` active)
- Learnings: 6/7 (Aug 22 absent; acceptable)
- Wrong-path variants used in W34: `dart-position/`, `dart/`, `dart-virtual/` — 3 distinct wrong variants in one week

## Consequence Clause

The W33 plan already stated user authorization is the required path to resolution. Eight consecutive Critical weeks with zero self-correction demonstrate agent-side plans are insufficient. The evaluator formally recommends:

1. User to immediately authorize the hard-code of `reports/daily/dart-virtual-trader/YYYY-MM-DD.md` in `.claude/agents/dart-virtual-trader.md` as a mandatory first-line constraint.
2. If authorization is not received by W35 evaluation (2026-08-31), evaluator will recommend excluding dart-virtual-trader positions from the Daily Report entirely until the path is fixed and verified for 5 consecutive days.

## W35 Action Item (Agent)

At start of every cycle: read `reports/daily/dart-virtual-trader/` — that directory and ONLY that directory. Do not create `dart/`, `dart-virtual/`, `dart-position/`, or any other variant. The canonical path is: `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`

Success criteria: 7/7 correct in W35. Zero wrong-directory variants.
Deadline: W35 evaluation (2026-08-31).
