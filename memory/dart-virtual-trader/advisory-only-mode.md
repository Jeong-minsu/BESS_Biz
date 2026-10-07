# dart-virtual-trader — Advisory-Only Mode

**Created**: 2026-07-28
**Effective as of**: W28 (2026-07-13)
**Evaluator plan reference**: `memory/dart-virtual-trader/plans/2026-W30-advisory-only-escalation.md`
**Status**: ACTIVE

---

## 1. Statement

The dart-virtual-trader operates in **ADVISORY ONLY mode** as of Week 28 (effective 2026-07-13). All position recommendations filed in daily cycle reports and history files are advisory and have not been submitted to ERCOT as live DART virtual bids or offers.

---

## 2. Reason

The execution scope for DART virtual positions has not been confirmed by the user (jms2527@gmail.com). Specifically:
- No confirmed ERCOT submission path for INC offers / DEC bids from this agent
- No confirmed counterparty or account through which DART virtual positions would be physically settled
- The Tenaska `dart_virtual_revenue` data field in `shared/data/pnl/gks/hourly/YYYY-MM-DD.parquet` has returned null for 40+ consecutive cycles, preventing any verification that positions are being executed or settled

Advisory-only mode was adopted as a precautionary measure to prevent unintended live market submissions while the execution infrastructure remains unverified.

---

## 3. Implications

- `dart_virtual_revenue` in Tenaska parquet files is expected to be **$0** (or null) under advisory-only mode — this is normal operating state, not a data error
- Hit rate is **non-computable against settlement actuals** — all reported P&L figures are advisory E[P50] estimates using the formula (2P−1) × MW × E[|spread|]
- Evaluator approach-axis scoring for dart-virtual-trader is **suspended** pending live settlement confirmation
- Reporter should label DART virtual positions as "advisory" in daily and weekly reports

---

## 4. Reversion Criteria

Advisory-only mode will be deactivated when ALL of the following are confirmed by the user:

1. **Execution scope confirmed**: User explicitly confirms that DART virtual positions should be submitted to ERCOT (via designated QSE or trading platform)
2. **Tenaska DART virtual endpoint accessible**: `dart_virtual_revenue` field in `shared/data/pnl/gks/hourly/YYYY-MM-DD.parquet` returns non-null values for at least 3 consecutive flowdays
3. **Position sizing limits confirmed**: User approves the MW caps (25 MW full-size weekday, 15 MW half-size) for live submission
4. **Risk limits confirmed**: User approves the energy floor ($4.00/MWh minimum), P(win) threshold (≥55%), and RT spike veto parameters for live market operation

---

## 5. Note on Settlement Gap

The `dart_virtual_revenue` null field has been escalated in 40+ consecutive daily cycles. Resolution requires the user to contact Tenaska Ascend to isolate the DART virtual revenue component in the GKS hourly P&L feed. This is the primary blocker for both settlement validation and deactivation of advisory-only mode.

---

*Filed by dart-virtual-trader | 2026-07-28 | Overdue since W28 (2026-07-13) — created in response to W30 evaluator escalation plan*
