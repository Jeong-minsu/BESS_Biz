# Improvement Plan — 2026-W39 — Directory Compliance (CRITICAL Regression — Escalated from Major)
**Agent**: bess-optimizer
**Priority**: CRITICAL (escalated from Major in W38)
**Registered by**: evaluator | 2026-09-28

---

## W39 Compliance Breakdown

- bess-optimizer/ (CORRECT): 0 files
- bess-stack/ (WRONG): 2026-09-21.md (Mon), 2026-09-26.md (Sat) = 2 files
- bess-strategy/: 0 files
- **W39 result: 0/2 correct on run days. 0/7 correct overall.**

## Regression from W38

W38 achieved 4/7 (bess-optimizer/ Mon Sep 14 – Thu Sep 17 correct; bess-stack/ Sep 18-20 wrong). The W38 pattern showed a DEGRADED-data correlation — wrong-dir files appeared when data was degraded or on weekends.

W39 eliminates the weekday-compliance holdout: Sep 21 (Monday, same as Sep 14-17 in W38) now lands in bess-stack/. The DEGRADED-data trigger has propagated to fully degraded the weekday session path selection. 0/2 correct is a full regression to near-W37-level compliance.

## History

| Week | Correct/Total | Pattern |
|---|---|---|
| W37 | 4/7 (same as W38) | Mon-Wed correct, others wrong |
| W38 | 4/7 | Mon-Thu correct (improvement from weekday-only right); Fri-Sun wrong |
| **W39** | **0/2 on run days** | **Mon AND Sat both wrong — full regression** |

## Root Cause Assessment

The correlation with DEGRADED data (Smartbidder + Tenaska both down) is strong. In W38, DEGRADED sessions used bess-stack/. In W39, ALL sessions (including Sep 21 Monday with the same DEGRADED conditions as W38 Mon) used bess-stack/. The DEGRADED-mode path selection has now permanently displaced correct path selection — the agent no longer defaults to bess-optimizer/ under any operational condition observed in W39.

## Required Actions

**AGENT IMMEDIATE**:
1. Every session, before any schedule generation, write: `OUTPUT PATH: reports/daily/bess-optimizer/YYYY-MM-DD.md` — mandatory first step, including DEGRADED cycles.
2. bess-stack/, bess-strategy/ are INCORRECT paths. No files should ever be written to these directories.
3. Implement path self-check before file creation. The directory component must be exactly `bess-optimizer`.
4. DEGRADED data conditions do not change the output path. Degraded cycles still output to bess-optimizer/ with appropriate DEGRADED header flags.

**USER REQUIRED (AUTHORIZATION)**:
1. **Hard-code canonical path**: Add one line to `.claude/agents/bess-optimizer.md` Section Process: `Save to: reports/daily/bess-optimizer/YYYY-MM-DD.md (canonical — no exceptions)`. The pattern of DEGRADED-mode regression makes agent self-correction unreliable under the exact conditions (infrastructure outage) when correct output labeling is most important.
2. **Evaluate bess-stack/ and bess-strategy/ archive**: These directories contain historically wrong-dir files. Consider renaming or removing to prevent future confusion.

## Success Criterion

W40 = all run days produce bess-optimizer/ output. Zero bess-stack/ or bess-strategy/ files on any day of the week, under any data conditions.
