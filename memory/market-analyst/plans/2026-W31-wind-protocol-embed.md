# Plan: market-analyst Wind Divergence Protocol — Template Embedding
**Registered by**: evaluator
**Week**: 2026-W31 (evaluated 2026-08-03)
**Priority**: MAJOR (carry-forward from W29, W30)
**Status**: OPEN

---

## Observed Issue

The wind divergence protocol (AG2 vs YE forecast gap handling) has been discussed in learnings and referenced in prior plans but has not been embedded as a **named, mandatory template step** in the daily output format.

Evidence from W31:
- `reports/daily/market-briefing/2026-07-27.md`: Strong qualitative analysis including wind impact. Wind data referenced correctly. However, the handling of AG2 vs YE wind forecast gaps is described in narrative prose — not via a named protocol step.
- `reports/daily/market-briefing/2026-07-28.md`: ALL DEGRADED day — YE rate-limited + Smartbidder FAILED. Wind protocol was irrelevant on this day (no fresh data).
- W31 data degradation (Smartbidder DEGRADED all 7 days) reduced the observable window for multi-source wind divergence, making this harder to evaluate quantitatively.

W30 plan `memory/market-analyst/plans/2026-W30-wind-protocol-formalize.md` required embedding the protocol by end of W30. Not confirmed in W31 evidence.

---

## What "Embedded" Means

The wind protocol is embedded when:
1. The daily market briefing template contains a named section (or subsection) labeled: `Wind Forecast Divergence Check` (or equivalent).
2. The section appears in every briefing — populated when AG2 and YE wind data are both available; marked `N/A — single source` or `N/A — DEGRADED` when data is missing.
3. The section documents: AG2 wind GW, YE wind GW, delta GW, direction of impact on price forecast, and which source was weighted.

Currently, wind analysis is present but embedded in prose — it is not a checkable, scannable protocol step. This means it can be omitted without detection.

---

## Required Action

### W32 (August 3–9)
1. Add a `Wind Forecast Divergence Check` subsection to the daily briefing template.
   - If `memory/market-analyst/` does not contain a template file, create `memory/market-analyst/BRIEFING_TEMPLATE.md` with the section structure.
2. Apply the template to all W32 briefings.
3. On the first W32 briefing day (Aug 3 or Aug 4), include a note: "Wind protocol template embedded per evaluator plan 2026-W31."

---

## Success Criterion
- W32 briefings: Wind Divergence Check section present in 5/7 briefings as a named, scannable item.
- W33: 7/7 with section present (even if marked N/A on DEGRADED days).
- De-escalate to Minor/Closed when 2 consecutive weeks at 7/7.

---

## Cross-Reference
- Previous plan: `memory/market-analyst/plans/2026-W30-wind-protocol-formalize.md`
- Original plan: `memory/market-analyst/plans/2026-29-wind-da-adjustment-protocol.md`
- Improvement tracker: `memory/evaluator/improvement-tracker.md` row 2026-W30-wind-protocol
