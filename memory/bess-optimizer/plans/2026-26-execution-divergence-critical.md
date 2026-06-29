# Plan: DA Execution Divergence — CRITICAL (Open Issue 1)
**Agent**: bess-optimizer
**Week**: 2026-W26
**Priority**: CRITICAL
**Registered by**: evaluator (2026-06-29)
**Deadline**: 2026-07-06 (next weekly evaluation)

---

## Issue

bess-optimizer has documented "Open Issue 1" in multiple consecutive learning files: actual GKS DA energy positions differ significantly from recommendations. This divergence has persisted for **5+ consecutive cycles** without resolution, causing confirmed realized losses on Jun 24 (-$618.80 actual vs +$2,602.41 benchmark) and Jun 26 (-$95.89 actual vs +$349.78 benchmark).

The agent correctly identifies the divergence in self-review but cannot resolve it alone because the root cause is outside its control: either (a) a human operator is overriding recommendations, (b) BESS hardware/dispatch system constraints prevent execution of the recommended positions, or (c) a systems integration gap exists between recommendation output and bid submission.

---

## Quantitative Basis for CRITICAL Classification

| Flowday | GKS Actual | Benchmark | Delta | Driver |
|---|---|---|---|---|
| 2026-06-22 | +$5,945.31 | +$2,239.80 | +$3,705 | Outperformance (ECRS, RT NS) |
| 2026-06-23 | +$8,439.93 | +$987.38 | +$7,453 | Outperformance (DA sales + NS) |
| 2026-06-24 | -$618.80 | +$2,602.41 | -$3,221 | UNDERPERFORMANCE: DA charging unplanned |
| 2026-06-25 | N/A (DEGRADED) | N/A | N/A | — |
| 2026-06-26 | -$95.89 | +$349.78 | -$446 | UNDERPERFORMANCE: RT energy costs |

Confirmed underperformance: 2 of 4 production days in W26. Both underperforming days show DA energy position divergence from recommendation (GKS executing DA charging when recommendation specified DA sales or AS-only).

W26 cumulative net P&L (4 production days): +$13,670.55
W26 cumulative benchmark (4 production days): +$6,179.37
W26 realized delta vs benchmark: +$7,491.18

Note: The W26 aggregate is positive because Jun 22 and Jun 23 outperformance (+$11,158) more than offsets Jun 24 and Jun 26 underperformance (-$3,667). However, the divergence pattern on down-days indicates a systemic execution gap that could materially hurt P&L during less favorable market conditions.

---

## Root Cause Hypothesis (bess-optimizer to investigate)

The following hypotheses are ordered by likelihood based on W26 evidence:

1. **BESS software/optimizer override**: Smartbidder or the underlying BESS dispatch system is making real-time position adjustments that override the pre-DAM recommendation — likely triggered by RT price signals or SoC constraints not visible to bess-optimizer at time of recommendation.

2. **Human override at dispatch**: An operator at Ascend/Tenaska is manually adjusting positions post-DAM based on RT developments or operational constraints.

3. **Recommendation-to-bid transmission gap**: The bess-optimizer recommendation is not being transmitted to the bid system in time for the 10:00 CT DAM cutoff.

4. **Systematic SoC initialization error**: bess-optimizer Standing Rule 7 (SoC initialization) may be using incorrect starting SoC, causing position sizing errors that cascade into unplanned charging.

---

## Required Actions

### Action 1 (bess-optimizer + user): Root Cause Identification
bess-optimizer must document in the next learning file (2026-06-29 or 2026-06-30) which hypothesis best matches the available evidence, with quantitative reasoning. The user must confirm which of the 4 hypotheses applies.

**Question for user**: On Jun 24 (GKS DA Energy = -$4,005.31, i.e., net DA charging), did bess-optimizer's recommendation specify DA charging or DA selling at HE08-12 and HE15-20? Was the DA charging decision made by the BESS dispatch system, by an operator, or by the Smartbidder optimization?

### Action 2 (bess-optimizer): Divergence Documentation Protocol
Starting 2026-06-30, whenever the production DA Energy actual differs from the recommendation by more than $1,000 in magnitude:
1. Note the divergence in the learning file on D+1
2. Estimate the P&L impact of the divergence (actual vs what would have been realized if recommendation was followed)
3. Tag the learning file with `[EXECUTION-DIVERGENCE]` for evaluator tracking

### Action 3 (bess-optimizer): Recommendation Confidence Threshold
Until execution gap is resolved, bess-optimizer should append a "Execution Risk Disclosure" section to every daily recommendation (this is already covered by Standing Rule 8 — confirm it is being applied consistently).

---

## Success Criteria

- [ ] User confirms which root cause hypothesis applies by 2026-07-03
- [ ] bess-optimizer learning files include `[EXECUTION-DIVERGENCE]` tag on all days with >$1,000 DA position gap starting 2026-06-30
- [ ] Root cause documented and plan to resolve identified by 2026-07-06

---

## Notes

- The Jun 22 and Jun 23 outperformance days suggest the recommendation is sound when executed — the issue is specifically about days where DA charging positions appear in actuals that were not recommended
- Standing Rule 8 (RT dispatch risk disclosure) is the right instrument; confirm it is in every output
- This is an extension of Open Issue 1 first documented in bess-optimizer learning files W24/W25
