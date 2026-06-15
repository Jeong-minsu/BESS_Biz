# Plan: bess-optimizer — ECRS Exclusion Rule Failure + Execution Divergence

**Filed by**: evaluator | **Date**: 2026-06-15 | **Week**: 2026-24 | **Priority**: MAJOR (two items require user action)

---

## Issue 1 (MAJOR): ECRS Exclusion Rule Failed 4 Consecutive Times — Cumulative ~$1,400 Opportunity Loss

**Evidence**: `memory/bess-optimizer/learnings/2026-06-14.md` (Section 3, "틀린 것" item 2).

The agent has missed ECRS clearing on:
- 2026-06-08: ECRS $962.56 cleared unexpectedly. Action logged: "include ECRS standing offer."
- 2026-06-12: ECRS $962 cleared again. Action re-logged (carry-forward 1).
- 2026-06-13: Action carry-forward 2.
- 2026-06-14: ECRS $612.48 cleared again. Action carry-forward 3 — now 4th consecutive miss.

**Agent self-identified cumulative cost**: ~$1,400 opportunity loss across 4 cycles. The action has been re-derived from learnings each time but not incorporated into the standing schedule template.

**Root cause**: The agent documents improvement actions in per-cycle learnings but does not have a persistent standing rule document that the next cycle's schedule generation consults. Each cycle starts from scratch and re-discovers the ECRS gap.

**Required action (agent)**: 
1. Create `memory/bess-optimizer/learnings/standing-rules.md` (or `as-standing-rules.md` per the W23 plan) as a persistent operational checklist.
2. The first rule in that document: "ECRS HE20-24 CT: always include 94 MW standing offer. Exclude from base revenue projection but include in every schedule. No cycle exceptions."
3. The second rule: "NonSpin HE20-24 CT: use $5-10/MWh evening prior (not overnight $0.45 prior)."
4. Consult this document at the start of every schedule generation, before reading market data.

---

## Issue 2 (MAJOR, USER ACTION REQUIRED): Execution Divergence — bess-optimizer Recommendations Are Not Being Executed

**Evidence**: bess-optimizer learnings 2026-06-10 through 2026-06-14 show systematic divergence:

| Date | Recommended | Actual (Tenaska) | Pattern |
|---|---|---|---|
| 2026-06-10 | DA discharge HE19-20 | DA sell HE15-17, HE21-22 | +2 hour shift; partial execution |
| 2026-06-12 | DA sell HE20-21 | DA buy 425 MWh HE10-13; RT sell HE20-22 | Sign reversal on energy |
| 2026-06-14 | DA discharge HE21-22 | DA row_counts = 0; RT cycling only | No DA energy participation |

GKS actual revenue exceeded the bess-optimizer recommendation on all three PRODUCTION days (+26.4% on 2026-06-12, +50.4% on 2026-06-14), suggesting Smartbidder/Tenaska has a superior real-time co-optimization layer. However, the divergence also means the bess-optimizer recommendation does not reflect what is actually being executed.

**User action required**: 
1. Confirm whether the bess-optimizer recommendation is (a) directly configuring Smartbidder bid submissions, (b) advisory input to a Smartbidder optimizer, or (c) completely independent of Smartbidder execution.
2. Confirm the DA Energy row_counts = 0 anomaly on 2026-06-14: Tenaska records DA_Energy_Amt = -$1,867 but endpoint returned 0 rows. Is this a settlement lag, DART virtual embedded in DA_Energy_Amt, or a data reporting artifact?
3. This question has been open since W22 (2026-22-da-rt-venue-follow-up.md). Target resolution was 2026-06-15 per W23 plan. It has now passed that deadline without resolution.

**If confirmation comes that bess-optimizer is purely advisory**: the evaluation framework for bess-optimizer must change. Plan-vs-actual comparison becomes meaningless; the relevant metric becomes how often the recommendation's directional call (DA sell vs hold; charge hour selection) is aligned with what Smartbidder actually executes.

---

## Issue 3 (MINOR): DA-RT Direction Default Needs to Flip — Three PRODUCTION Days Confirmed RT > DA

**Evidence**: bess-optimizer learnings 2026-06-10, 2026-06-12, 2026-06-13.

On 2026-06-10, 2026-06-12, and 2026-06-14, the operator-executed strategy was RT-primary (Smartbidder captured RT revenue while the bess-optimizer recommended DA-primary). All three actual days outperformed the recommendation.

The agent self-identified (2026-06-12 learning, Action 2): "Flip the prior: assume GKS RT > DA at HE19-22 unless congestion-analyst confirms HOUSTON_IMPORT P(binding) < 10%."

This action has been carried forward but not implemented in subsequent recommendations (2026-06-13 and 2026-06-14 plans still recommend DA discharge at peak hours as the primary strategy).

**Agent action required**: Apply the conditional RT/DA framing proposed in the 2026-06-12 learning:
- If congestion-analyst HOUSTON_IMPORT P(binding) > 25%: hold SOC for RT dispatch; do not recommend DA sell at peak hours.
- If P(binding) < 10%: DA sell is primary strategy.
- Between 10-25%: hybrid — recommend DA sell with explicit RT optionality flag.

---

## Success Criteria

- `memory/bess-optimizer/learnings/standing-rules.md` created by 2026-06-16 cycle.
- ECRS HE20-24 appearing in schedule for 2026-06-16 (next cycle).
- User confirms execution flow with Tenaska/Smartbidder by 2026-06-22.
- DA-RT conditional framing (HOUSTON_IMPORT P(binding) switch) applied starting 2026-06-17.

---

*Evaluator — 2026-06-15 | Extends: 2026-W23-improvement.md Issues 1-3. ECRS carry-forward is now the most urgent agent-actionable item; execution divergence remains the most urgent user-actionable item.*
