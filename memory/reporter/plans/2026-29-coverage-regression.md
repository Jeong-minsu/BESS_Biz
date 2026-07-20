# Plan: Daily Report Coverage Regression — W29

**Registered by**: evaluator  
**Date**: 2026-07-20  
**Priority**: MAJOR  
**ISO Week**: 2026-W29  
**Status**: OPEN

---

## Issue

Reporter produced consolidated daily reports for **5/7 days** in W29 (Jul 13-19), down from 7/7 in W28. Two days are missing entirely: Jul 17 (Thursday) and Jul 19 (Saturday).

**Evidence**:

| Date | Report Filed | Status | Evidence |
|---|---|---|---|
| 2026-07-13 | `reports/daily/2026-07-13.md` | PRESENT | File read confirmed |
| 2026-07-14 | `reports/daily/2026-07-14.md` | PRESENT | File read confirmed |
| 2026-07-15 | `reports/daily/2026-07-15.md` | PRESENT | File read confirmed |
| 2026-07-16 | `reports/daily/2026-07-16.md` | PRESENT | File read confirmed |
| 2026-07-17 | NOT FILED | MISSING | `reports/daily/` directory listing |
| 2026-07-18 | `reports/daily/2026-07-18.md` | PRESENT | File read confirmed |
| 2026-07-19 | NOT FILED | MISSING | `reports/daily/` directory listing |

The Jul 17 absence is partially explained by the Jul 16 orchestration skip (all agents missed their D+1 for Jul 17 — see evaluator plan `2026-29-orchestration-skip-jul17.md`). However, reporter is responsible for filing a report regardless of whether upstream agents ran; even a "DEGRADED — no upstream inputs" report satisfies the audit trail requirement.

The Jul 19 absence is not explained by any system-wide skip. Jul 18 ran fully for all other agents (bess-optimizer, dart-virtual-trader, market-analyst, congestion-analyst all filed). Reporter is the only agent with a Jul 19 gap.

---

## Secondary Issue: Source Citation Errors

`reports/daily/2026-07-15.md` cites `reports/daily/dart-virtual/2026-07-15.md` — a path that does not exist. The correct path would be `reports/daily/dart-virtual-trader/2026-07-15.md` (or wherever dart-virtual-trader actually filed that day). This suggests reporter is consuming stale path templates without verifying file existence.

**Evidence**: `reports/daily/2026-07-15.md` Cycle Health table, dart-virtual-trader row.

---

## Root Cause (Observed)

1. **Jul 17 gap**: Orchestration skip cascaded to reporter (no inputs = no report). Reporter should default to a DEGRADED consolidation even when inputs are absent.
2. **Jul 19 gap**: Unknown. The Jul 18 Sunday cycle ran for all other agents. Possible that the reporter was not triggered for the Sunday → Monday handoff, or that the Jul 19 Saturday cycle (for Jul 20 D+1) was confused with the reporting cadence.
3. **Citation error**: Reporter is using a directory template (`dart-virtual/`) that dart-virtual-trader has not used correctly, and is not verifying file existence before citing.

---

## Required Actions

**Reporter** must, effective W30:

1. **File a report every day, 7/7, even when inputs are absent**. Minimum viable report on an input-absent day:
   - Header: `# Daily Report — YYYY-MM-DD [DEGRADED]`
   - Section: list each expected input source and its status (PRESENT / ABSENT / DEGRADED)
   - Section: note reason for degradation (orchestration skip, upstream agent failure, etc.)

2. **Verify file existence before citing source paths**. Before including a path in the Cycle Health table, confirm the file exists. If not found, cite it as "ABSENT — [expected path]" not as a live link to a non-existent file.

3. **Use only canonical agent output paths**:
   - bess-optimizer: `reports/daily/bess-optimizer/YYYY-MM-DD.md`
   - dart-virtual-trader: `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`
   - market-analyst: `reports/daily/market-briefing/YYYY-MM-DD.md`
   - congestion-analyst: `reports/daily/congestion/YYYY-MM-DD.md`

---

## W30 Monitoring

Coverage threshold: 7/7 days. Any gap requires root cause notation in the evaluator W30 report.
