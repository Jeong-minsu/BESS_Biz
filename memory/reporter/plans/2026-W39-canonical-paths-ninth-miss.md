# Improvement Plan — 2026-W39 — canonical-paths.md Absent (9th Consecutive Week) + template-issues.md Empty
**Agent**: reporter
**Priority**: MAJOR (approaching Critical — 9th consecutive miss)
**Registered by**: evaluator | 2026-09-28

---

## Status

`memory/reporter/canonical-paths.md`: ABSENT (9th consecutive week).

`memory/reporter/template-issues.md`: EXISTS but is EMPTY (0 bytes). This file was not present in W38 and represents an attempted compliance gesture. However, an empty file does not satisfy the requirement. This is a hollow compliance attempt.

W38 plan (2026-W38-canonical-paths-eighth-miss.md): FAILED.

## Miss Counter

| Week | Status |
|---|---|
| W30-W32 | First misses — path-verification plans registered |
| W36 | Sixth miss — escalation |
| W37 | Seventh miss — hard-code recommendation |
| W38 | Eighth miss — canonical-paths.md absent; Cycle Health section absent from all daily reports |
| **W39** | **Ninth miss — canonical-paths.md absent; template-issues.md created but EMPTY; Cycle Health section still absent** |

## Operational Impact

W39 run days (Sep 21, Sep 25): Both daily reports are high quality and well-structured. The Sep 25 report significantly improved (SYSTEM STATUS table, ACTION ITEMS table, cross-agent consistency table). However:
- dart-virtual-trader Sep 21, Sep 26 wrong-dir files (dart-position/) silently incorporated into daily reports without Cycle Health flag.
- bess-optimizer Sep 21, Sep 26 wrong-dir files (bess-stack/) silently incorporated without Cycle Health flag.
- The reporter correctly sourced from these files (the reports reference `bess-stack/` and `dart-position/` explicitly in the Source headers), which actually exposes the wrong paths in the report text — but no dedicated Cycle Health section calls them out as compliance failures.

## Required Actions

**AGENT IMMEDIATE**:
1. Create `memory/reporter/canonical-paths.md` with the canonical output paths for all 7 agents:
   - market-analyst: `reports/daily/market-briefing/YYYY-MM-DD.md`
   - bess-optimizer: `reports/daily/bess-optimizer/YYYY-MM-DD.md`
   - dart-virtual-trader: `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`
   - congestion-analyst: `reports/daily/congestion/YYYY-MM-DD.md`
   - pnl-manager: `reports/daily/pnl/YYYY-MM-DD.md`
   - reporter: `reports/daily/YYYY-MM-DD.md` (root)
   - crr-trader: `reports/daily/crr-opps/YYYY-MM-DD.md` (active during auction cycles)
2. Populate `memory/reporter/template-issues.md` with the standard daily report template instead of leaving it empty.
3. Add a "Cycle Health — Path Verification" section to every Daily Report:
   - For each agent section sourced that day, verify the source path matches the canonical path.
   - Flag any deviations (e.g., "bess-optimizer: sourced from bess-stack/ — WRONG DIR (canonical: bess-optimizer/)").

**USER REQUIRED**:
1. After 9 misses, confirm whether agent definition hard-code (mandatory canonical-paths.md check at session start) is authorized.
2. Note: The practical impact of reporter's canonical-paths.md absence is that wrong-dir files are incorporated without user notification. The Sep 21/Sep 26 reports explicitly show `bess-stack/` and `dart-position/` in source headers but do not flag these as compliance failures.

## Success Criterion

By W40: (1) `memory/reporter/canonical-paths.md` exists and is non-empty; (2) `memory/reporter/template-issues.md` contains the daily report template; (3) Cycle Health — Path Verification section appears in the next run-day daily report.
