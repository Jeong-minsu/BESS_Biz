# Plan: DART Virtual Settlement Infrastructure Gap (W25)

**Registered by**: evaluator
**Week**: 2026-25
**Priority**: MAJOR
**Status**: OPEN — agent to implement; user action required for Tenaska endpoint
**Agent**: dart-virtual-trader
**Supersedes**: `memory/dart-virtual-trader/plans/2026-24-settlement-infrastructure-gap.md`

---

## Problem Statement

As of W25 end (2026-06-21):
- DART virtual settlement revenue in Tenaska data: $0.00 (persistent, all cloud-execution days)
- Number of unresolved virtual positions: 40+ (spanning W22 through W25)
- Hit rate (confirmed settlements): uncalculable — insufficient data
- Smartbidder-estimated hit rate (proxy): not reliably confirmed against Tenaska

From pnl-manager 2026-06-15 report:
"DART Virtual | 945.92 | 69.06 | +876.86"
The $945.92 Tenaska figure is the total; the Tenaska DART-specific endpoint likely aggregates
virtual + physical in a way that does not isolate virtual positions.

From pnl-manager 2026-06-21 report: DART Virtual = $269.25 from Smartbidder only; Tenaska: N/A.

---

## W24 Plan Status

The W24 plan had two agent actions:
1. Fix Non-Spin vs ECRS label bug — **STATUS UNKNOWN** (no confirmation in W25 outputs)
2. Implement ECRS INC modifier formally — **STATUS UNKNOWN**

User action (Smartbidder submission scope confirmation) remains outstanding.

---

## Required Actions

### Action 1 — User Confirmation Required

Confirm whether Smartbidder submits DART virtual bids/offers to ERCOT on GKS's behalf:
- If YES: Smartbidder's virtual positions appear in Tenaska settlement as separate line items;
  the current 0-row result for virtual-specific endpoints is a query issue, not an absence of positions
- If NO: GKS does not participate in DART virtual market through Smartbidder;
  dart-virtual-trader's position recommendations are not executed at all

This is the highest-priority user confirmation needed for the dart-virtual-trader accuracy assessment.

### Action 2 — dart-virtual-trader agent (immediately)

Stop issuing positions without knowing if they are executed. Until user confirms Hypothesis A or B:

1. In each daily report, add a mandatory data quality line:
   "DART settlement confirmation status: UNCONFIRMED (40+ positions pending, no Tenaska isolation)"

2. Track estimated P&L using Smartbidder benchmark as the proxy:
   - At each end-of-day, check `reports/daily/pnl/YYYY-MM-DD.md` for DART Virtual line
   - Extract both Tenaska and Smartbidder DART Virtual figures
   - Log to `memory/dart-virtual-trader/history/hit-rate-log.md`:
     Date | Positions | Smartbidder Est. | Tenaska Actual | Match? | Notes

3. If Smartbidder estimate consistently matches Tenaska DART Virtual line within ±$50:
   Use Smartbidder as the hit rate proxy until Tenaska endpoint is fixed.

### Action 3 — pnl-manager agent (coordinate)

pnl-manager to explicitly isolate DART Virtual revenue in the daily P&L summary:
- Add a note clarifying whether the Tenaska DART Virtual figure includes or excludes physical energy
- If the Submissions-DA-Settlement-Amounts endpoint is available, attempt a call for DART-specific lines
- Report: "DART Virtual Tenaska (isolated): $X" vs "DART Virtual Smartbidder (estimate): $Y"

### Action 4 — dart-virtual-trader agent (cap enforcement)

The W25 evaluation found a below-floor override cap violation on 2026-06-18:
4 discretionary below-floor overrides were used; the maximum cap is 2 per day.

Rule (re-stated): Maximum 2 below-floor-threshold discretionary overrides per daily cycle.
Any additional override candidates must be listed in the SKIP table with reason "cap exceeded".
This cap must appear as a checklist item in each report:
"Below-floor override count: N / 2 (MAX). [Over-cap positions moved to SKIP table]"

---

## Success Criteria

- hit-rate-log.md created in `memory/dart-virtual-trader/history/` with W22-W25 backfill
- User confirms whether Smartbidder executes virtual positions
- Below-floor override cap (≤2/day) enforced in all W26 reports
- Non-Spin vs ECRS label bug confirmed resolved or documented as unresolved

---

## Hit Rate Calculation (Once Data Available)

For each settled virtual position:
- WIN: realized spread direction matches predicted direction AND |spread| > $2/MWh
- LOSS: direction wrong OR spread < $2/MWh (below meaningful threshold)
- Target hit rate: ≥55% over rolling 10-position window
- Target win/loss ratio: ≥1.3:1
- W25 proxy estimate based on learnings 2026-06-21: ~14-25% — far below target; full data required
