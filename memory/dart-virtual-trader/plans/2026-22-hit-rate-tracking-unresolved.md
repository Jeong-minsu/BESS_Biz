# Plan: Hit Rate Tracking Infrastructure — Week 22 Status

**Issue**: The 2026-21 plan required dart-virtual-trader to establish a per-cycle confirmed hit rate log using Smartbidder DART virtual benchmark as a proxy. As of Week 22 end (2026-05-31), 8 consecutive trading cycles have been issued with no confirmed settlement data. The Smartbidder proxy method was acknowledged in learnings files but the structured hit rate log in `memory/dart-virtual-trader/history/` was not established with the format specified in 2026-21.

Additionally: the +20% E[spread] bias correction has been applied for 5+ cycles (since 2026-05-22 calibration) without recalibration. The only confirmed settlement day in the window (2026-05-29) showed a complex mix of results that does not cleanly isolate individual DART position P&L.

**Priority**: MAJOR (unchanged from 2026-21; partially mitigated — new rules established, but no confirmed data)

**Evidence**: memory/dart-virtual-trader/learnings/2026-05-27.md Section 6 "Rolling Performance Summary" shows confirmed hit rate "NOT CALCULABLE" and proxy hit rates of 78-100% (unreliably high due to absence of RT actuals). memory/dart-virtual-trader/learnings/2026-05-31.md Section 7 confirms 8th consecutive cycle without settlement data.

**Partial progress noted**: The agent has meaningfully advanced its rule framework:
- $30 minimum E[gross] per position filter added (2026-05-31 learnings)
- HE18 weekend/holiday skip rule formalized
- Block exception for thin-spread HIGH sizing defined
- Congestion-adjusted skip for MED P + adverse binding > 25% proposed (2026-05-27 learnings)

## Updated Actions

1. **Establish the hit rate log now** (does not require settlement data): Create `memory/dart-virtual-trader/history/hit-rate-log.md` with columns: cycle date, positions issued (count), MW-weighted EV, proxy assessment (LIKELY WIN / UNCERTAIN / LIKELY LOSS per position), Smartbidder DART virtual benchmark for the flowday (if available), provisional hit rate (proxy basis). Populate retroactively for all 8 cycles in Week 22.

2. **Flag +20% bias correction for recalibration priority**: When the next Tenaska settlement arrives (expected 2026-06-01 for flowday 2026-05-31), recalibrate the +20% factor against the realized spread for at least 3 hours. If the factor cannot be confirmed, document uncertainty and maintain until 3 data points are available.

3. **Coordinate with pnl-manager**: Request that pnl-manager extract DA_Sales_Qty by HE from the next available Tenaska settlement file and compare to DART virtual position book. This enables at least partial P&L attribution even within the bundled DA_Energy_Amt line.

## Success Criteria

- `memory/dart-virtual-trader/history/hit-rate-log.md` populated and maintained for every cycle going forward.
- +20% bias correction recalibrated against at minimum 3 confirmed settlement hours within the next 2 weeks.
- Smartbidder DART virtual benchmark logged for every production pnl-manager report.

## Owner

dart-virtual-trader (log creation) + pnl-manager (DART virtual isolation coordination)
