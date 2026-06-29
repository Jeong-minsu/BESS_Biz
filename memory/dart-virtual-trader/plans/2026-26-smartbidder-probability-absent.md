# Plan: Smartbidder DA-RT Probability CSV Absent — 13+ Cycles
**Agent**: dart-virtual-trader
**Week**: 2026-W26
**Priority**: MAJOR
**Registered by**: evaluator (2026-06-29)
**Deadline**: User action required; agent fallback protocol due 2026-07-06

---

## Issue

The Smartbidder DA-RT probability CSV has been absent for **13+ consecutive cycles** as of W26. This CSV is dart-virtual-trader's primary quantitative input for position sizing and direction confidence. Without it:

- Position sizing defaults to the minimum cap (25 MW per direction)
- Direction confidence cannot be quantified (agent relies entirely on own qualitative assessment)
- No probability-weighted expected value can be computed for INC vs DEC positions

This is a persistent data gap that directly degrades the Approach axis score for dart-virtual-trader.

---

## Evidence

From W26 daily reports (Jun 22-28): Every briefing notes Smartbidder DA-RT probability CSV as "absent" or "null" in the data sources section. The pattern was first noted in W24 (at minimum).

In `reports/daily/pnl/2026-06-25.md` (DEGRADED day): "DA-RT Forecast probabilities (2026-06-27): null (Date column only, no probability values)."

This confirms the CSV is structurally present (file exists, date column populated) but probability values are unpopulated.

---

## Root Cause Hypothesis

The Smartbidder DA-RT probability CSV may have changed format or the relevant columns may have been renamed or removed in a Smartbidder API update. The file structure should be compared against the API documentation in `API Docs/Smartbidder/`.

---

## Required Actions

### Action 1 (User): Verify Smartbidder CSV Format
Check whether the Smartbidder DA-RT probability CSV format has changed. Relevant API docs: `API Docs/Smartbidder/`. The specific columns expected by dart-virtual-trader should be documented in `memory/dart-virtual-trader/` or in the `shared/data/raw/smartbidder/` file headers.

### Action 2 (dart-virtual-trader): Implement Probability Fallback Protocol
Until the Smartbidder probability CSV is restored, dart-virtual-trader must document a fallback protocol in `memory/dart-virtual-trader/learnings/`:
1. When CSV is absent: state explicitly that position sizing is at minimum cap (25 MW)
2. Cite the direction-reason gate outcome as the primary direction signal
3. Note the AG2 vs Yes Energy price forecast divergence as a secondary signal (if available)
4. Document expected value range under minimum-cap sizing (do not extrapolate to full 50 MW without probability input)

### Action 3 (dart-virtual-trader): Streak Counter
Add a running count of consecutive absent cycles to every daily output: "Smartbidder DA-RT probability: ABSENT [N consecutive cycles]." This ensures the streak is visible to reporter and evaluator without requiring a separate read of memory files.

---

## Success Criteria

- [ ] User investigates Smartbidder CSV format change by 2026-07-06
- [ ] Fallback protocol documented in dart-virtual-trader learning file by 2026-06-30
- [ ] Absent-cycle streak counter added to all future daily outputs starting 2026-06-30
- [ ] If CSV restored, confirm probability values are non-null and sizing resumes at full scale

---

## History

- W24: First confirmed absent cycles (at minimum 3 cycles noted)
- W25: Pattern noted in evaluator report; not separately planified
- W26: 13+ consecutive cycles; filing as formal MAJOR plan
