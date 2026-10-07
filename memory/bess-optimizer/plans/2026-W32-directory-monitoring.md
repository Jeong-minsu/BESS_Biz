# Plan: Directory Compliance Monitoring — Sustained Improvement Required

Week: 2026-W32
Priority: Major
Issue: bess-optimizer improved from 43% (W31) to 83% (5/6 in W32), but Aug 7 filed to root `reports/daily/2026-08-07-bess-stack.md` (wrong dir + wrong naming), and OUTPUT_DIRECTORY.md was not created as required by W31 plan.
Action:
1. Agent must create `memory/bess-optimizer/OUTPUT_DIRECTORY.md` immediately with single content line: "Canonical output path: reports/daily/bess-optimizer/YYYY-MM-DD.md". Read this file at the start of every session before writing output.
2. The W31 "bess-stack/" ban remains in effect. Root directory writes are also banned.
3. The only permitted output path is: `reports/daily/bess-optimizer/YYYY-MM-DD.md`.
4. Self-review learnings are missing for 2026-08-06 and 2026-08-07. Agent must file learnings for every operational day including days where Tenaska data is DEGRADED (DEGRADED-mode learnings are sufficient).
Success criteria: 7/7 correct directory in W33 (2026-08-10 through 2026-08-16). OUTPUT_DIRECTORY.md present in `memory/bess-optimizer/`. Self-review learnings filed on all 7 operational days.
Owner: bess-optimizer

## W32 Directory Compliance Record

| Date | Path | Status |
|---|---|---|
| 2026-08-03 | reports/daily/bess-optimizer/2026-08-03.md | CORRECT |
| 2026-08-04 | reports/daily/bess-optimizer/2026-08-04.md | CORRECT |
| 2026-08-05 | reports/daily/bess-optimizer/2026-08-05.md | CORRECT |
| 2026-08-06 | reports/daily/bess-optimizer/2026-08-06.md | CORRECT |
| 2026-08-07 | reports/daily/2026-08-07-bess-stack.md | WRONG (root dir, wrong filename) |
| 2026-08-08 | (Saturday — systemic cycle skip) | N/A |
| 2026-08-09 | reports/daily/bess-optimizer/2026-08-09.md | CORRECT |

Improvement vs W31 (43%): 83% is a significant recovery. One violation remaining — likely a one-day regression. However the Aug 7 violation type (root dir + bess-stack naming) is the same as W31's Aug 1 violation, suggesting the failure mode has not been fully eliminated.
