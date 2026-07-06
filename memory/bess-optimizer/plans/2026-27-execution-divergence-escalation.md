# Plan: bess-optimizer — Execution Divergence Escalation (6th Cycle)
**Week**: 2026-27 | **Priority**: CRITICAL | **Registered by**: evaluator

---

## Issue

W26 evaluator plan `2026-26-execution-divergence-critical.md` set a user deadline of 2026-07-03 to confirm how Smartbidder execution is reconciled with bess-optimizer recommendations. That deadline passed without response. This is the **6th consecutive [EXECUTION-DIVERGENCE] cycle** (confirmed in daily reports: 2026-06-22, 06-24, 06-26, 07-01, 07-02; also flagged in 2026-07-04 report).

**Quantitative basis (from bess-optimizer learnings 2026-07-02):**
- Smartbidder execution: NS 80 MW × 24h flat, DA sells HE14-22 independently of recommendations
- bess-optimizer recommendation (July 2): Stack B (NS 80 MW, DA discharge HE20-21 only, charge HE10-12)
- Actual GKS outcome (July 2): $2,012.73 (per pnl-manager)
- Counterfactual if recommendation followed: ~$5,564 (bess-optimizer estimate)
- Divergence cost (July 2 alone): −$3,551 (−63.9%)
- W26 user deadline 2026-07-03: MISSED — no user response

**Pattern severity**: 6 consecutive cycles × ~$3,500 potential/cycle = ~$21,000 cumulative opportunity cost (unverified — Tenaska intermittent limits full ledger).

---

## Root Cause

Smartbidder operates on its own strategy ("Mount Blue Sky with Virtuals, RTC Version") which overrides bess-optimizer recommendations. The agent documents this correctly in [EXECUTION-DIVERGENCE] tags but lacks authorization to change Smartbidder configuration. Three possible resolutions exist:
- **Option A**: User reconfigures Smartbidder to use bess-optimizer recommendations (custom strategy upload)
- **Option B**: bess-optimizer adapts recommendations to Smartbidder's observed execution defaults (NS 80 MW flat, HE14-22 DA sell) to optimize within those constraints
- **Option C**: bess-optimizer continues generating recommendations as strategic benchmarks only (no operational coupling intended)

---

## Action Items

1. **Evaluator action (immediate)**: Score bess-optimizer Approach axis with an asterisk — "methodology quality high but execution coupling = 0; realized impact unverifiable." Do NOT penalize Approach for circumstances outside agent control.

2. **User action required by 2026-07-13 (W28 evaluation, FINAL)**:
   - Confirm whether bess-optimizer recommendations are (A) intended to guide Smartbidder execution, (B) advisory benchmark only, or (C) require a new interface to Smartbidder.
   - If no response by 2026-07-13: bess-optimizer formally reclassified as "STRATEGIC BENCHMARK — NOT OPERATIONALLY COUPLED." All [EXECUTION-DIVERGENCE] plan series closed as infrastructure-unresolvable.

3. **Agent action (immediate)**: Continue tagging [EXECUTION-DIVERGENCE] in daily outputs. In learnings, begin documenting "effective Smartbidder strategy" (NS 80 MW flat, HE14-22 DA) separately from recommendation to enable apples-to-apples tracking.

4. **Agent action (by 2026-07-10)**: Produce a one-time "What-If Smartbidder Recalibration" note in `memory/bess-optimizer/learnings/`: what would bess-optimizer recommend IF it treated NS 80 MW × 24h flat and HE14-22 DA sell as fixed constraints? Document the resulting delta vs current recommendations.

---

## Success Metric

- User confirms execution model by 2026-07-13: CLOSED
- No user response by 2026-07-13: Agent reclassified to STRATEGIC BENCHMARK; plan CLOSED as resolved-by-policy
- Agent produces recalibration note by 2026-07-10: partial credit

---

## Supersedes

`memory/bess-optimizer/plans/2026-26-execution-divergence-critical.md` (deadline MISSED)
