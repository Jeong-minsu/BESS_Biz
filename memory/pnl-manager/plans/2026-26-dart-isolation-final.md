# Plan: DART Virtual P&L Isolation — Final Escalation
**Agent**: pnl-manager
**Week**: 2026-W26
**Priority**: MAJOR
**Registered by**: evaluator (2026-06-29)
**Deadline**: 2026-07-13 (user action required for Tenaska endpoint change)

---

## Issue

The Tenaska Battery-Settlement-Details endpoint does not provide a separate settlement line for DART virtual positions. All virtual activity (INC/DEC bids) is embedded in DA_Energy_Amt and RT_Energy_Amt. This makes it impossible to:

1. Compute dart-virtual-trader's actual P&L contribution
2. Validate dart-virtual-trader recommendations against settled outcomes
3. Report DART virtual revenue separately in the daily P&L table

This has been an open issue for **14+ cycles** (coinciding with the dart-virtual-trader execution confirmation gap). The Jun 24 analysis confirmed that "DART Virtual Net" as computed from DA_Energy_Amt + RT_Energy_Amt is dominated by physical BESS charging, not virtual positions.

---

## Evidence from W26

| Flowday | Tenaska "DART Virtual Net" | Physical Driver | Virtual Component |
|---|---|---|---|
| 2026-06-24 | -$3,964.90 | DA charging -$4,005 (physical) | Cannot isolate |
| 2026-06-26 | $0.00 (not separately isolable) | DA energy embedded in DA_Energy_Amt | Cannot isolate |
| 2026-06-23 | N/A (not reported) | Physical activity dominant | Cannot isolate |

Smartbidder benchmark does separately report virtual P&L (e.g., Jun 24: +$661.75 DEC at HE15). This creates an asymmetric comparison where pnl-manager cannot produce an apples-to-apples delta for the DART virtual line.

---

## Required Actions

### Action 1 (User + pnl-manager): Tenaska Endpoint Investigation
Ask the Ascend/Tenaska representative whether a separate settlement endpoint exists for DART virtual positions (INC/DEC bids). Relevant endpoint candidates:
- A separate "Virtual Bid Settlement" report
- The DA Energy Only Offer endpoint (currently returning 0 rows) — may include virtual offer details when data is present
- An ERCOT-side settlement report accessible via the same Tenaska PTP integration

### Action 2 (pnl-manager): Interim Reporting Flag
In every daily P&L report, the DART Virtual row must include a note explaining that the figure is NOT isolatable from physical BESS DA energy positions. Suggested note:
> "DART Virtual: Not separately isolable. DA_Energy_Amt and RT_Energy_Amt embed both physical BESS dispatch and any virtual positions. See memory/pnl-manager/plans/2026-26-dart-isolation-final.md for resolution path."

This note must appear in the table itself (not just in Data Quality Notes) so downstream agents (dart-virtual-trader, evaluator) see it prominently.

### Action 3 (pnl-manager): Smartbidder Virtual Comparison
On production days where Smartbidder benchmark is available and reports non-zero virtual P&L, pnl-manager should note the benchmark virtual figure in the Data Quality Notes section. This gives dart-virtual-trader a reference point even without isolated Tenaska data.

---

## Success Criteria

- [ ] User contacts Tenaska/Ascend about separate virtual settlement endpoint by 2026-07-06
- [ ] DART Virtual row note added to all future daily P&L reports starting 2026-06-30
- [ ] Smartbidder virtual comparison logged in Data Quality Notes on relevant days starting 2026-06-30

---

## History

- W24: Issue first identified in dart-virtual-trader Jun 24 learning file
- W25: Noted in evaluator W25 report as contributing to dart-virtual-trader Approach score degradation
- W26: 14 cycles without resolution; escalating to formal MAJOR plan with deadline
