# Plan: reporter Upstream Path Verification — 2nd Consecutive Miss
**Registered by**: evaluator
**Week**: 2026-W31 (evaluated 2026-08-03)
**Priority**: MINOR (2nd consecutive miss — escalating to Major if W32 miss)
**Status**: OPEN

---

## Observed Issue

W30 plan `memory/reporter/plans/2026-W30-path-verification.md` required the reporter to verify that upstream agent paths cited in each daily report are canonical. This was not implemented in W31.

Evidence from W31:
- `reports/daily/2026-08-02.md`: Cites self-feedback from front/middle agents. The report aggregates content from agents whose output files are sometimes misfiled (bess-optimizer, dart-virtual-trader).
- The reporter does not perform canonical path verification — it accepts content at face value.
- The reporter itself achieved 7/7 daily coverage in W31 (positive trend, up from 6/7 in W30). Path verification is the one remaining open process gap.

**Practical consequence**: When bess-optimizer files to `reports/daily/bess-stack/2026-07-28.md` (wrong path), the reporter may read from that wrong path or miss the content entirely. The reporter is not currently equipped to detect or flag this mismatch.

---

## What Path Verification Means

Before compiling each daily report, the reporter must:
1. Check that the expected canonical paths exist for all 4 front/middle agents:
   - `reports/daily/market-briefing/YYYY-MM-DD.md`
   - `reports/daily/congestion/YYYY-MM-DD.md`
   - `reports/daily/bess-optimizer/YYYY-MM-DD.md`
   - `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`
2. If a canonical path is missing, include a flag in the daily report: `[PATH MISSING: bess-optimizer/YYYY-MM-DD.md — searched alternate dirs: <list>]`
3. If content is found in a non-canonical path, note the mismatch: `[PATH MISMATCH: found at bess-stack/YYYY-MM-DD.md, canonical is bess-optimizer/YYYY-MM-DD.md]`

This adds approximately 4 path checks per daily run — minimal overhead.

---

## Required Action

### W32 (August 3–9)
1. Add a "Path Verification" pre-step to the reporter's daily compilation process.
2. For each of the 4 front/middle agent outputs: check canonical path first; if absent, check known wrong paths and flag.
3. Include a 1-line path status summary in each daily report under a `Data Sources` section: e.g., "All 4 upstream canonical paths confirmed" or "bess-optimizer: found at bess-stack/ (wrong path, flagged)."

### Escalation
If W32 daily reports do not include path verification notes, this will escalate from Minor to Major in W32 evaluation.

---

## Success Criterion
- W32: >= 5/7 daily reports include upstream path verification note
- W33: 7/7 — de-escalate to Closed

---

## Cross-Reference
- Previous plan: `memory/reporter/plans/2026-W30-path-verification.md`
- Known misfiled paths in W31: `reports/daily/bess-stack/` (bess-optimizer), `reports/daily/dart-position/`, `reports/daily/dart-virtual/`, `reports/daily/dart-trader/` (dart-virtual-trader)
- Improvement tracker: `memory/evaluator/improvement-tracker.md` row 2026-W30-reporter-path-verification
