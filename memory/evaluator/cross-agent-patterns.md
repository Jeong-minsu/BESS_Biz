# Evaluator Cross-Agent Patterns

Last updated: 2026-06-22 (Week 2026-25 evaluation)

---

## Pattern 1: Smartbidder AS Timing Systematic Bias

**Observed**: Weeks 2026-21 (2 cycles: 2026-05-22, 2026-05-24)
**Agents affected**: market-analyst (briefing), bess-optimizer (AS positioning)

Smartbidder DA Ancillary forecast places ECRS and Non-Spin peaks at HE20-22. Actual ERCOT clearing shows:
- ECRS: HE07-10 (morning load ramp) — 2 cycles confirmed
- Non-Spin: overnight (HE01-06) and midday (HE11-18) — 2 cycles confirmed

This affects market-analyst's AS section and bess-optimizer's AS stack. Both agents must apply empirical overrides to Smartbidder AS timing. This pattern should be re-evaluated if market conditions shift (summer peak, heat events).

---

## Pattern 2: Smartbidder DA Peak Price Overestimation

**Observed**: Weeks 2026-21 (2 cycles: 2026-05-22, 2026-05-24)
**Agents affected**: market-analyst (price view), bess-optimizer (revenue projection), dart-virtual-trader (spread estimation)

Smartbidder DA forecast at HE21 overestimated by ~$21 (2026-05-22) and ~$13 (2026-05-24). Directional peak-hour identification (HE21 as highest-price hour) was correct both cycles; the price level was inflated. A 15-20% downward correction to Smartbidder raw DA peak price forecast is empirically supported.

---

## Pattern 3: GKS Congestion Benefit Appears as DA Premium, Not RT Nodal Spike

**Observed**: Weeks 2026-21 (2026-05-24 settlement analysis)
**Agents affected**: congestion-analyst (framing), bess-optimizer (execution strategy), dart-virtual-trader (position rationale)

On 2026-05-24, the Houston import constraint produced its benefit through elevated DA clearing prices (DA $49-53 at HE20-22) rather than an RT nodal price spike at GKS. GKS's revenue came from being short DA (via Tenaska's RT-dispatch effectively buying back DA at below-DA RT prices). The RT prices ($34-42) were well below DA. For GKS, the operationally relevant signal is DA-RT spread, not RT nodal spike. All downstream agents should frame the evening congestion opportunity as "DA overpriced vs RT" rather than "RT spike."

---

## Pattern 4: WEST_TO_NORTH Binding Does Not Reliably Manifest at GKS Node

**Observed**: Weeks 2026-21 (2026-05-24 settlement analysis)
**Agents affected**: congestion-analyst (binding probability), dart-virtual-trader (LONG DA solar block thesis)

On 2026-05-24, WEST_TO_NORTH was predicted HIGH (35-50%) with near-zero GR_WEST wind (600 MW) and high solar. Actual GKS nodal spreads were near-flat (HE10-14 spread within $1.2 of hub). Without PTDF data, Stage 0 cannot reliably call HIGH for this constraint. The LONG DA HB_NORTH solar block thesis in dart-virtual-trader relies on this constraint binding — positions are sized at MED (22-25 MW) appropriately, but the directional confidence should remain low until hub-pair LMP data is available.

---

## Pattern 5: Enverus Consistently More Bullish than Yes Energy on Solar and Net Load

**Observed**: Weeks 2026-21 (multiple briefings)
**Agents affected**: market-analyst, congestion-analyst

Enverus solar forecasts run +2.8 to +4.2 GW above Yes Energy at HE13-14. Enverus net load peak forecasts run +3.1 to +7.8 GW above Yes Energy at HE20-21. In the 2026-05-24 case, Yes Energy solar appeared closer to actual (Enverus solar 28.5 GW vs muted actual RT price suppression). Yes Energy is the current primary base case; Enverus is the upside scenario.

---

## Pattern 6: Tenaska Executes RT Energy Dispatch; DA Sell Recommendations Not Executed

**Observed**: Weeks 2026-21 (2026-05-22 and 2026-05-24 settlements)
**Agents affected**: bess-optimizer

bess-optimizer recommended DA Energy discharge both days. Tenaska executed RT Energy dispatch both days. The DA-RT spread direction was correct, but the venue was not. This is not an analysis failure — it is an execution infrastructure gap. Until resolved, all bess-optimizer revenue projections are systematically overstated relative to realized Tenaska execution.

---

## Pattern 7: Agents Show High Cross-Agent Consistency on Evening Peak Window

**Observed**: Weeks 2026-21 through 2026-22 (all 11 daily reports)
**Agents affected**: market-analyst, bess-optimizer, dart-virtual-trader, congestion-analyst

All four front/middle agents have consistently agreed on HE20-21 (sometimes HE19-22) as the primary revenue window. The evening duck curve + Houston import constraint is the dominant cross-agent consensus. No material contradiction observed across any cycle. This alignment is confirmed structurally across normal weekdays, Saturdays, Sundays, and the Memorial Day holiday weekend.

---

## Pattern 8: Tenaska Data Outage Cascades to All Learning Loops

**Observed**: Weeks 2026-21 through 2026-22 (7 failures in 11 operating days)
**Agents affected**: bess-optimizer, dart-virtual-trader, market-analyst, congestion-analyst, pnl-manager

All Front/Middle agent self-reviews cite Tenaska data absence as the primary limitation. The calibration anchors for bess-optimizer (0.80x haircut), dart-virtual-trader (+20% bias correction), and market-analyst (RT overestimate discount) were all established on 2026-05-24 data and are now 15+ days stale as of week end. This is a single-point infrastructure dependency: a cloud IP not on the Ascend whitelist is cascading into broken learning loops for 4 agents simultaneously.

---

## Pattern 9: Agent Self-Identification Exceeds Implementation Rate for Template-Level Changes

**Observed**: Week 2026-22 (most visible in market-analyst; also in dart-virtual-trader)
**Agents affected**: market-analyst, dart-virtual-trader

Agents correctly identify fixes in self-reviews but do not physically apply them in subsequent cycles. market-analyst identified Non-Spin overnight and ECRS morning ramp gaps in 7 consecutive self-reviews without implementing the template fix. dart-virtual-trader identified the need for a hit rate log but did not create it. This is distinct from incremental rule changes (which are applied quickly, e.g., bess-optimizer applying lessons within 1-2 cycles) — it specifically affects template/infrastructure changes that require a one-time structural edit rather than a per-cycle decision.

---

## Pattern 11: Weekend Evening is a Distinct Regime — RT Systematically Exceeds DA in Scarcity

**Observed**: Week 2026-W23 (3 consecutive weekend evenings: 2026-06-05 Fri, 2026-06-06 Sat, 2026-06-07 Sun)
**Agents affected**: market-analyst (briefing framing), dart-virtual-trader (directional model), bess-optimizer (indirectly)

On all three weekend evenings, actual RT exceeded DA by $15-30+/MWh at HE18-22 while Smartbidder P(DA>RT) predicted the opposite direction. The physical GKS battery profited from RT dispatch on these evenings (confirming RT>DA at the node); the DART virtual SHORT DA positions lost (-$5,266 confirmed on 2026-06-06). Two structural explanations: (a) Saturday thin DAM liquidity causes DA to clear below RT when scarcity materializes; (b) Extreme Non-Spin (>$10/MWh) signals RT scarcity, which is ambiguous — consistent with either DA-expensive or RT-spiking scenarios. The Friday case (2026-06-05) also showed RT>DA, suggesting the weekend effect may extend to Friday evening in scarcity weeks. All agents should treat weekend evening Smartbidder P(DA>RT) as "reference only" when prior-day RT>DA evidence exists.

---

## Pattern 12: GKS Execution May Be Independent of bess-optimizer Recommendation

**Observed**: Week 2026-W23 (2026-06-05: involuntary RT charging HE13-15; 2026-06-07: DA energy cleared HE05-06 not in recommendation)
**Agents affected**: bess-optimizer (execution assumption), pnl-manager (benchmark comparison structure)

Tenaska settlement shows GKS being dispatched in hours not recommended by bess-optimizer, and in modes (RT charging at $28-44/MWh) that are directly contrary to the DA-sell strategy. Two possibilities: (a) Smartbidder/Tenaska submits bids independently with a separate RT co-optimization layer; (b) ERCOT automated demand response dispatched GKS involuntarily. Until the execution flow is confirmed, plan-vs-actual comparison for bess-optimizer may be comparing the recommendation against a different execution, making accuracy scoring invalid. User confirmation of the Tenaska/Smartbidder bid submission process is the prerequisite for valid bess-optimizer performance benchmarking.

---

## Pattern 13: Execution Divergence Is Structural, Not Episodic

**Observed**: Week 2026-24 (confirmed PRODUCTION days 2026-06-10, 2026-06-12, 2026-06-14)
**Agents affected**: bess-optimizer (primary), dart-virtual-trader (suspected), pnl-manager (benchmark structure)

On all three PRODUCTION days in W24 where bess-optimizer vs actual comparison was possible, Smartbidder/Tenaska executed a fundamentally different strategy than recommended (RT-first cycling vs DA-first discharge). GKS actual exceeded the bess-optimizer recommendation by 26-50%. This is not a random deviation — it is consistent RT co-optimization by Smartbidder operating independently of the bess-optimizer advisory. If this is also true for dart-virtual-trader (Hypothesis C: Smartbidder runs its own virtual book independently), both Front Office agents are advisory-only layers above Smartbidder execution. This is an architectural question requiring user confirmation.

---

## Pattern 14: ECRS DA Clearing Is a Recurring Feature in June–September ERCOT, Not a Tail Event

**Observed**: Week 2026-24 (4 of 7 days: 2026-06-08, 2026-06-12, 2026-06-13, 2026-06-14)
**Agents affected**: bess-optimizer (ECRS exclusion error), market-analyst (AS section), dart-virtual-trader (ECRS as INC risk indicator)

ECRS cleared in the DA market in the evening hours (HE20-24 CT) on 4 of 7 W24 days. bess-optimizer excluded ECRS from recommendations on each day (citing "zero clearing 4+ consecutive days"). market-analyst either lacked Smartbidder AS data (null endpoint) or did not provide ECRS estimates in the briefing. dart-virtual-trader confirmed on 2026-06-14 that ECRS clearing is a confirmed INC contra-indicator (ECRS clears → RT scarcity → RT > DA → INC loses). All three agents need to treat ECRS clearing in the HE20-24 window as a standing expectation during the June–September heat season, not a surprise.

---

## Pattern 15: Agent Learning Loop Speed Varies Systematically by Change Type

**Observed**: Weeks 2026-21 through 2026-24 (all agents, most visible in bess-optimizer and market-analyst)
**Agents affected**: All 5 Front/Middle agents; pnl-manager (DART virtual isolation)

Per-cycle rule changes (e.g., adjusting charge window timing, applying a P90 multiplier, changing position sizes) are implemented within 1-2 cycles. Structural/persistent changes (creating a standing-rules document, implementing an API endpoint, adding a mandatory pre-briefing checklist step, creating a hit-rate-log file) are deferred indefinitely. The evaluator has documented ECRS standing offer for bess-optimizer across 4 cycles; weekend RT override for market-analyst across 4 cycles; DART virtual isolation for pnl-manager across 4 cycles; hit-rate-log creation for dart-virtual-trader across 3 cycles. The common pattern: structural changes require creating a new persistent artifact (document, file, code change) rather than modifying a per-cycle decision. No agent has a mechanism for consuming the evaluator's improvement-tracker to ensure structural changes are executed.

---

## Pattern 16: Simultaneous Multi-Constraint Active Days Produce Correlated Calibration Failures

**Observed**: Week 2026-25 (2026-06-21 summer solstice — all 4 tracked constraints active simultaneously)
**Agents affected**: congestion-analyst, dart-virtual-trader, bess-optimizer (indirectly)

On the summer solstice (2026-06-21), GR_WEST peaked at 18,103 MW (series record) while NL ramp was
elevated and 4 constraints were simultaneously active: HOUSTON_IMPORT HIGH, WEST_TO_NORTH MEDIUM,
HOUSTON_SOUTH_MIDDAY_LOCAL MEDIUM, PANHANDLE LOW-MEDIUM. Actual outcome: HOUSTON_IMPORT call failed
(RT crashed, not spiked), WEST_TO_NORTH partial (1-hr timing bias), HOUSTON_SOUTH_MIDDAY_LOCAL wrong
direction.

When multiple constraints activate simultaneously under high-GR_WEST conditions, Stage 0 heuristics
overestimate all of them because:
(a) Mutual suppression effects between constraints are not modeled (binding one constraint relieves others)
(b) High GR_WEST wind exports from West suppress evening DA prices AND reduce South-to-Houston import pressure
(c) Stage 0 has no mechanism to downweight when conditions combine to create unusual market structure

This pattern will recur on summer peak days (July-August heat events, solstice-adjacent weekends).
All agents should treat "4+ constraints simultaneously flagged HIGH/MEDIUM" as a signal to apply
an additional 10-15 ppt confidence haircut to all probability calls, not just individual ones.

---

## Pattern 10: RT Energy Dispatch Is an Unmodeled Revenue Source for bess-optimizer

**Observed**: Week 2026-22 (confirmed 2026-05-29 settlement)
**Agents affected**: bess-optimizer, pnl-manager

On 2026-05-29, GKS generated $3,830.36 in RT Energy revenue that was not in the bess-optimizer recommended schedule. The DA-focused recommendation does not prevent RT dispatch — Smartbidder/Tenaska co-optimization submits RT offers independently. This is an upside source that systematically underestimates total GKS revenue in bess-optimizer plans. Since Week 22, bess-optimizer has added an explicit "RT Energy Optionality Upside: $1,500-$3,000" note. However, the mechanism is not yet modeled, so the base-case plan revenue estimate will continue to understate actuals until the RT dispatch structure is clarified with Tenaska.
