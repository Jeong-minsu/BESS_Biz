# Plan: W3 Item 0.10 Hub-Pair LMP — CRITICAL Final Escalation (W25)

**Registered by**: evaluator
**Week**: 2026-25
**Priority**: MAJOR (escalating to CRITICAL if not started by 2026-06-29)
**Status**: OPEN — agent to start immediately; user to confirm disk/access
**Agent**: congestion-analyst
**Supersedes**: `memory/congestion-analyst/plans/2026-24-w3-item010-final-escalation.md`

---

## Problem Statement

W3 Item 0.10 (hub-pair LMP 15-min history backfill) has been:
- Evaluator deadline: 2026-06-11 (set in W23 evaluation)
- Current status as of 2026-06-22: 0% started
- Consecutive blocked cycles: 32 (per congestion-analyst learnings 2026-06-21.md)
- Total cycles since item was first registered: 30+

This item is the prerequisite for:
1. congestion-analyst basis calibration (MCC magnitude estimates)
2. congestion-analyst binding probability calibration beyond Stage 0 heuristic
3. dart-virtual-trader hub-pair basis magnitude validation (WEST_TO_NORTH, HOUSTON_IMPORT)
4. Stage 2 training data accumulation (congestion-analyst CONGESTION_PROJECT Stage 2)

Without item 0.10, ALL of the following remain permanently blocked:
- Binding hit rate calculation (32nd consecutive cycle of 0 confirmed realizations)
- lambda MAE (mean absolute error) computation
- MCC magnitude validation beyond estimated ranges
- Hub basis P&L attribution for dart-virtual-trader

---

## W25 Performance Context

Congestion-analyst's 6/21 learnings document confirms:
- HOUSTON_IMPORT HIGH call was INCORRECT on 6/21 (RT prices crashed instead of spiking)
- WEST_TO_NORTH: timing systematic 1-hr early bias (partial credit only)
- HOUSTON_SOUTH_MIDDAY_LOCAL: direction wrong (MCC went negative not positive)

These errors CANNOT be corrected without realized lambda data. Without item 0.10,
the calibration loop is permanently broken regardless of how many cycles run.

---

## Required Actions

### Action 1 — User Confirmation Needed

Confirm one of:
(a) S3 bucket `s3://bess-biz-data/` contains hub-pair LMP CSVs from Yes Energy or AG2 — if yes,
    provide exact bucket path and file naming convention
(b) Yes Energy Datalake API endpoint for hub-pair 15-min LMP — confirm credentials in `.env`
    under `Yes Energy Datalake` section are valid and the endpoint is `hub_lmp_15min` or equivalent
(c) AG2 API endpoint for hub-pair historical settlement LMP — confirm endpoint URL and auth method

**This user action is the single gating dependency.** If confirmed, the agent can implement within 1-2 cycles.

### Action 2 — congestion-analyst agent (start immediately)

Read `agensts/CONGESTION_PROJECT.md` Section W3 Item 0.10 definition.
Implement the hub-pair LMP fetch regardless of data availability concern — begin with:

1. Check `shared/data/raw/` for any existing hub-pair LMP files
2. Attempt Yes Energy Datalake API call for `HB_HOUSTON`, `HB_NORTH`, `HB_WEST`, `HB_PAN` 15-min LMP
   for the period 2026-04-01 through 2026-06-21 (full backfill)
3. If API call succeeds, write raw data to `shared/data/raw/hub-lmp-15min/YYYY-MM-DD.csv`
4. If API call fails, document the specific error in learnings and escalate to user with exact error message

The "I cannot proceed because I do not know if disk space is available" reasoning is not valid.
Disk space check: `df -h /home/user/BESS_Biz` — takes 2 seconds.

### Action 3 — congestion-analyst agent (once data is available)

Once hub-pair LMP data is fetched:
1. Build lookup table: date × HE × hub-pair → DA LMP, RT LMP, spread
2. For the 32+ cycles with congestion reports, compute ex-post binding hit rate:
   - HOUSTON_IMPORT: did HB_HOUSTON DA/RT spreads show congestion pattern?
   - WEST_TO_NORTH: did HB_NORTH − HB_WEST spread widen during predicted hours?
3. Report binding hit rate to evaluator in next learnings file
4. Apply empirical correction to probability estimates starting W26

---

## Escalation Notice

If W3 Item 0.10 is not started by 2026-06-29 (Monday, W26 evaluation):

- congestion-analyst Approach score will be capped at 2.0 (Stage 0 heuristic with no calibration)
- congestion-analyst Resource score will be capped at 2.0 (critical data source absent for 38+ cycles)
- Issue will be escalated to CRITICAL priority

The evaluator has flagged this item in W22, W23, W24, and now W25. The pattern identified in
`memory/evaluator/cross-agent-patterns.md` Pattern 15 applies: structural infrastructure changes
are deferred indefinitely unless given a hard deadline with explicit consequences.

**The hard deadline is: 2026-06-29. Start the fetch. Report the result.**
