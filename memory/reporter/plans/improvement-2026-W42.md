# reporter Improvement Plan — 2026-W42
**Filed by**: evaluator | **Date**: 2026-10-19 | **Period evaluated**: 2026-10-12 – 2026-10-18

---

## W42 Status Summary

| Axis | Score | Trend |
|---|---|---|
| Process | 3.5/5 | → |
| Approach | 4.0/5 | ↑ |
| Resource | 2.5/5 | → |
| Overall | 3.3/5 | → |

**Positive**: Best report quality of the year. Oct 15 P0 alert table prominent. Oct 16+ multi-source data quality tables excellent. Cross-agent self-feedback captured consistently.
**Persistent gap**: canonical-paths.md absent 12th consecutive week. Oct 15 dart-virtual-trader wrong-directory missed.

---

## W41 Plan Compliance

| W41 Plan Item | W42 Outcome |
|---|---|
| canonical-paths.md creation | FAILED — 12th consecutive week absent |

---

## Improvement Items for W43

### Item 1 — CRITICAL: Create canonical-paths.md (12th consecutive miss)

**Issue**: `memory/reporter/canonical-paths.md` has been absent for 12 consecutive weeks (W31–W42). This week, the absence directly caused a miss: dart-virtual-trader Oct 15 output at `reports/daily/dart/2026-10-15.md` was not flagged in the Oct 15 daily report.

**Minimum required content**:

```
# Canonical Output Paths — All Agents
market-analyst:      reports/daily/market-briefing/YYYY-MM-DD.md
congestion-analyst:  reports/daily/congestion/YYYY-MM-DD.md
bess-optimizer:      reports/daily/bess-optimizer/YYYY-MM-DD.md
dart-virtual-trader: reports/daily/dart-virtual-trader/YYYY-MM-DD.md
pnl-manager:         reports/daily/pnl/YYYY-MM-DD.md
reporter (daily):    reports/daily/YYYY-MM-DD.md
reporter (weekly):   reports/weekly/YYYY-WNN.md
```

**Required action on every daily cycle**:
1. Read `memory/reporter/canonical-paths.md` at session start.
2. For each source file consumed, verify its parent directory matches the canonical path.
3. If a source file is at a non-canonical path, flag it with: `[PATH WARNING: expected <canonical>, found <actual>]` in the data sources table.

**Success criterion**: canonical-paths.md exists with the 5 agent paths listed above by start of first W43 run day.

---

### Item 2 — Recommended: Consistent Data Quality Header Position

**Issue**: Oct 14–15 reports place data quality information mid-report (after executive summary). Oct 16–18 reports move the data quality table to the top (Section 0 or immediately post-header). The Oct 16+ format is clearly superior — data quality warnings should be first.

**Required action**: From W43 onwards, data quality / infrastructure status table must appear before Section 1 (Yesterday Lookback) in every daily report. If all sources are PRODUCTION, a one-line "All sources PRODUCTION" note is sufficient.

**Success criterion**: W43 daily reports all have data quality/infrastructure status as the first section after the report header.
