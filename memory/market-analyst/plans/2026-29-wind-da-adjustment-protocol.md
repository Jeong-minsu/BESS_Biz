# Plan: Wind Source Divergence → DA Evening Adjustment Protocol — W29

**Registered by**: evaluator  
**Date**: 2026-07-20  
**Priority**: MAJOR  
**ISO Week**: 2026-W29  
**Status**: OPEN

---

## Issue

market-analyst produced a materially incorrect DA evening forecast for 2026-07-19 due to using Smartbidder's YE-based wind forecast (9.9 GW) while the market cleared on a higher wind basis (AG2/Enverus: 12-15 GW). The DA overforecast caused directional errors in HE20-21, which are exactly the hours bess-optimizer uses for discharge timing decisions.

**Evidence** (`memory/market-analyst/learnings/2026-07-19.md`):
- DA 24h average MAE: -$3.21/MWh (-14% overforecast overall)
- HE20 DA error: -$12.32/MWh (forecast DA premium, actual DA-RT spread was large negative: RT $28.26 vs DA $17.61 = -$10.65/MWh)
- HE21 DA error: -$18.61/MWh (forecast DA > RT; actual RT $32.72 vs DA $15.60 = -$17.12/MWh)
- Root cause identified by the agent: "Smartbidder used YE wind (9.9 GW); market bid on AG2/Enverus (12-15 GW)."
- Agent's own proposed protocol: "when AG2 > YE by 2+ GW, apply -$5 to -$15/MWh DA evening adjustment."

---

## Significance

The wind source divergence issue affects the exact window (HE18-22) where bess-optimizer determines physical discharge timing and dart-virtual-trader evaluates DART opportunities. A systematic overforecast of DA prices in these hours will cause both downstream agents to underestimate the probability of high-RT / low-DA events.

On Jul 19, the actual outcome was a +207.7% GKS outperformance day precisely because physical discharge at HE21-22 captured RT prices $32-34/MWh — which the market-analyst forecast had underweighted.

---

## Required Actions

**market-analyst** must, effective W30:

1. **Formalize the AG2 vs YE wind divergence check** as a standing step in the daily analysis process (not just a post-hoc learning):
   - Before publishing DA evening price view, compare AG2 wind forecast vs YE wind forecast for HE18-23.
   - If AG2 > YE by 2+ GW: apply a documented downward adjustment to DA forecast in HE18-23.
   - State the adjustment explicitly in the daily output: "AG2 wind [X] GW vs YE wind [Y] GW — applying -$Z/MWh DA evening adjustment."

2. **Propagate the signal to downstream agents**: When the adjustment is applied, add a flag in the market-briefing output: "Wind source divergence flag: AG2 > YE by [X] GW in HE18-23. Downstream agents (bess-optimizer, dart-virtual-trader) should note elevated probability of DA-premium reversal in evening hours."

3. **Calibrate the adjustment range**: The agent proposed -$5 to -$15/MWh. This is a reasonable starting range based on the Jul 19 error. The agent should document the basis for the range selection after 3-4 more observations.

---

## W30 Monitoring

Evaluator will check:
- Whether the AG2 vs YE wind comparison appears explicitly in market-analyst daily outputs for W30
- Whether the adjustment flag was triggered on any day (if not, state "AG2-YE delta below 2 GW threshold, no adjustment applied")
- Comparison of forecast vs actual DA evening prices for any day where the adjustment was triggered

---

## Note on Overall Market-Analyst Performance

Despite this directional miss on HE20-21 DA, the market-analyst correctly identified SOUTH_HOUSTON_IMPORT binding risk for HE19-22 (referenced in congestion-analyst learnings), and RT forecast MAE for HE20-23 was $2.10/MWh (accurate). The wind divergence protocol addresses the specific DA evening systematic bias; overall approach quality is 3.5 (MAJOR issue, not CRITICAL).
