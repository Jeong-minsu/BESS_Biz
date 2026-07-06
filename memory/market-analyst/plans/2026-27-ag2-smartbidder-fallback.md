# Plan: market-analyst — AG2 CSV Parse Gap + Smartbidder Fallback Formalization
**Week**: 2026-27 | **Priority**: MINOR | **Registered by**: evaluator

---

## Issue

Two related resource gaps identified in W27:

**Gap 1 — AG2 CSV not parsed:**
The W26 plan `2026-26-ag2-provenance.md` was PARTIALLY CLOSED: market-analyst added data vintage timestamps (partial compliance). However, in the 2026-06-29 market briefing, AG2/WSI paths are referenced but "CSV 본문 미제공" — the CSV content was not parsed or included. The AG2 wind forecast is cited as a source but its numerical contribution cannot be verified.

**Gap 2 — Smartbidder D+1 return not formalized:**
Smartbidder DA-RT probability CSV returned for the first time in 43+ cycles during W27 (reported in 2026-07-05 daily). Market-analyst applied a 70% size cap (dart-virtual-trader reference), but no formal procedure exists for:
- How to assess whether a returning Smartbidder CSV is reliable after a long absence
- What calibration trust threshold applies before treating the CSV as primary vs secondary source
- How many consecutive production cycles are required before restoring full trust

**Impact:**
- AG2 gap: minor — other wind sources (Yes Energy, Enverus) are present; wind forecast range documented
- Smartbidder gap: medium — without a calibration trust rule, agents may over-rely on a noisy signal

---

## Action Items

1. **Agent action (by 2026-07-13)**:
   - For AG2: In the next briefing where AG2 is listed as a source, include at minimum the key numerical output (wind generation MWh or range) from the CSV. If AG2 CSV cannot be parsed in the cloud environment, document this as a BLOCKED resource and identify an alternative.
   - For Smartbidder return: Write `memory/market-analyst/learnings/smartbidder-calibration-trust-rule.md` documenting: (a) what constitutes a "trust restoration" cycle count (proposed: 5 consecutive production days), (b) interim weighting during probation period (proposed: 50% weight vs Yes Energy), (c) trigger for reverting to ABSENT status if CSV disappears again.

2. **Agent action (ongoing)**: When citing AG2 or WSI, include the actual number fetched — not just "AG2 CSV path referenced." Minimum: source, vintage, key metric value.

---

## Success Metric

- AG2 numerical value included in next briefing where AG2 is cited: CLOSED on Gap 1
- Smartbidder calibration trust rule documented by 2026-07-13: CLOSED on Gap 2
