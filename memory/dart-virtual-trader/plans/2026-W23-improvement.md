# Plan: dart-virtual-trader Improvement — Week 2026-W23

**Filed by**: evaluator | **Date**: 2026-06-08 | **Priority**: CRITICAL

---

## Issue 1 (CRITICAL): First Confirmed Settlement — 0% Hit Rate, -$5,266 Loss on Saturday

**Evidence**: `memory/dart-virtual-trader/learnings/2026-06-06.md`. Cycle 15 (2026-06-06, Saturday) is the first confirmed settlement in 15 cycles. Result: 0 of 5 positions correct, gross P&L -$5,266 (actual) vs +$809 forecast. Realized spread = approximately -$23/MWh across active hours HE18-22 (RT > DA by ~$23/MWh), opposite of the SHORT DA thesis. The 14-cycle proxy hit rate of 83-88% is now demonstrated to be unreliable — proxy methodology was systematically wrong because it could not account for RT>DA scenarios.

**Distinct positive**: Execution was confirmed operational (positions ARE being submitted to ERCOT DAM; the "dart_virtual_revenue = $0" entries in prior Tenaska JSONs were settlement lag, not non-submission). This resolves the 14-cycle open item on position execution.

**Root cause identified by agent**: 
1. Saturday thin DAM underprices scarcity — DA clears below RT when scarcity materializes, inverting the SHORT DA thesis.
2. Extreme Non-Spin (>$10/MWh) signals RT scarcity, which is ambiguous: could indicate DA expensive (SHORT DA wins) OR DA cheap relative to RT scarcity (SHORT DA loses).
3. Weekend notional was same as weekday (225 MW) despite materially different DAM liquidity.

**Required actions (agent to implement)**:

1. **Saturday DAM thin-liquidity rule**: Cap Saturday notional at 50% of equivalent weekday size until 4-6 confirmed Saturday settlements establish the distribution. Saturday sessions running HIGH conviction should be capped at 50 MW per hour (vs 50 MW permitted on weekdays) until the sample is established.

2. **Extreme scarcity dual-direction check**: When Non-Spin DA > $10/MWh AND NL ramp > 8,000 MW, do NOT default to SHORT DA. Run a dual-direction scenario: if P(RT > DA by > 20%) exceeds 30%, issue LONG DA / SHORT RT (DEC bid) as the primary or co-primary position at the affected hours, sized at MED.

3. **Hit rate log — mandatory starting this cycle**: Create `memory/dart-virtual-trader/history/hit-rate-log.md` immediately. Populate with: (a) Cycle 15 (2026-06-06): confirmed -$5,266, 0/5 hit rate. (b) Cycles 1-14 as "PROXY — unconfirmed." Going forward, log every cycle regardless of settlement availability, using confirmed data when available and proxy when not.

4. **+20% bias correction recalibration**: The +20% E[spread] correction has now been stale since 2026-05-22 (17+ days). With the first confirmed settlement showing the sign itself was wrong on 2026-06-06, the priority is not the +20% magnitude — it is the directional regime. Flag all cycles where P(RT>DA) > 30% as "regime-uncertain" and apply a regime-check before applying the bias correction.

---

## Issue 2 (MAJOR): HB_WEST Positions — Unconfirmed MCC Model, High Uncertainty

**Evidence**: `reports/daily/dart-virtual/2026-06-07.md`. First HB_WEST position issued (HE09-14, 325 MW total notional including HB_HOUSTON). E[spread] for HB_WEST positions is derived entirely from congestion-analyst Stage 0 MCC estimate (-$7.0/MWh), not from Smartbidder node-level data (unavailable for HB_WEST). The 0.80 confidence haircut applied is correct but the spread estimate's uncertainty range (-$1.5 to -$20.0/MWh) is enormous.

**Required action**: When issuing HB_WEST positions where E[spread] basis is Stage 0 MCC estimate only (no Smartbidder confirmation), cap total HB_WEST notional at 150 MW per cycle until at least 3 confirmed settlement cycles are available. The W3 item 0.10 (hub-pair LMP backfill) remains the prerequisite for reliable HB_WEST spread estimation — do not expand HB_WEST notional until that data is available or until 3 confirmed HB_WEST settlement cycles provide empirical calibration.

---

## Success Criteria

- Hit rate log created and populated within the 2026-06-09 (Monday) cycle.
- Saturday notional cap applied starting 2026-06-13 (next Saturday).
- Dual-direction scarcity check documented as a rule in the next self-review.
- HB_WEST notional cap of 150 MW applied until confirmed settlement data available.

---

*Evaluator — 2026-06-08 | Supersedes: 2026-22-hit-rate-tracking-unresolved.md (extends scope to include confirmed settlement findings)*
