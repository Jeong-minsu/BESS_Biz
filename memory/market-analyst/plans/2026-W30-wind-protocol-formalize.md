# Plan: market-analyst Wind DA Adjustment Protocol — Formal Standing Step

**Registered by**: evaluator  
**Date**: 2026-07-27  
**Priority**: MAJOR  
**Status**: OPEN — agent to implement formalization  

---

## Issue

The W29 plan required the agent to "add AG2 vs YE wind divergence check as a standing step W30." The agent has been applying the protocol conceptually (07-20 and 07-24 learnings both discuss wind gap and downside DA adjustment) but the threshold has not been hardcoded as a formal standing step in the briefing process. The 07-20 briefing applied a qualitative "$3-5/MWh downside note" at a 1.9 GW gap but missed the actual -$27.79 HE21 DA correction needed.

## Evidence

- `memory/market-analyst/learnings/2026-07-20.md` Section 8, Item 3: "W29 OPEN (2 GW trigger) — NEEDS THRESHOLD REVISION. Lower trigger to 1.5 GW. 1.9 GW gap on 7/20 produced -$27.79 DA miss. Current 2 GW threshold too high." Agent acknowledged but did not yet update the briefing standing steps.
- `memory/market-analyst/learnings/2026-07-24.md` Section 4, Improvement 1: "풍력 gap 1,500 MW+ 시, Smartbidder DA 예측치에서 DA HE19-22 -$5~10 조정 구간을 명시적으로 제시." Again described in learnings but not yet confirmed in the briefing template.
- `reports/daily/market-briefing/2026-07-24.md`: Includes wind cross-source comparison in Demand & Supply section but the formal $-5 to $-10/MWh DA adjustment for HE19-22 is noted as "downside risk" rather than a primary scenario adjustment.

## Required Formalization

The protocol should be embedded as a named step in every briefing that has AG2 vs YE wind gap data available. Specifically:

**Standing Step: Wind Divergence DA Adjustment**

Trigger: AG2 WindCast avg vs YE COPHSL avg gap >= 1,500 MW for the D+1 operating day.

Action: For DA HE19-22 price view, apply a downside-adjusted scenario as the primary range (not just risk section):
- Gap 1.5–2.5 GW: DA HE19-22 = Smartbidder forecast minus $5–8/MWh
- Gap > 2.5 GW: DA HE19-22 = Smartbidder forecast minus $8–15/MWh
- For HE21 specifically: if DA spike forecast > $40/MWh AND wind gap > 1.5 GW, treat DA spike as unreliable (credibility gate per 07-20 learnings, Item 12)

Additional rule: If AG2 load diverges from YE by > 3 GW AND wind gap > 1.5 GW: both effects compound. Apply full $-10 to $-15/MWh adjustment at HE21.

This step should appear in the Price View section before the AS prices subsection on every high-load day (gross load > 80 GW or net load peak > 55 GW).

## Success Criterion

Seven consecutive briefings with a named "Wind Source Divergence Adjustment" subsection when the trigger condition is met. The DA HE19-22 price view shows the adjusted range as primary, not buried in the Risk section.
