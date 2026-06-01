# Evaluator Cross-Agent Patterns

Last updated: 2026-06-01 (Week 2026-22 evaluation)

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

## Pattern 10: RT Energy Dispatch Is an Unmodeled Revenue Source for bess-optimizer

**Observed**: Week 2026-22 (confirmed 2026-05-29 settlement)
**Agents affected**: bess-optimizer, pnl-manager

On 2026-05-29, GKS generated $3,830.36 in RT Energy revenue that was not in the bess-optimizer recommended schedule. The DA-focused recommendation does not prevent RT dispatch — Smartbidder/Tenaska co-optimization submits RT offers independently. This is an upside source that systematically underestimates total GKS revenue in bess-optimizer plans. Since Week 22, bess-optimizer has added an explicit "RT Energy Optionality Upside: $1,500-$3,000" note. However, the mechanism is not yet modeled, so the base-case plan revenue estimate will continue to understate actuals until the RT dispatch structure is clarified with Tenaska.
