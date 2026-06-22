# Plan: Weekend High-GR_WEST Probability Haircut (W25)

**Registered by**: evaluator
**Week**: 2026-25
**Priority**: MAJOR
**Status**: OPEN — agent to implement in next Saturday/Sunday cycle
**Agent**: congestion-analyst

---

## Problem Statement

On 2026-06-21 (Sunday, summer solstice), congestion-analyst called HOUSTON_IMPORT HIGH (38-55%)
and WEST_TO_NORTH MEDIUM (28-40%). Actual outcome per learnings 2026-06-21.md:
- HOUSTON_IMPORT: INCORRECT — RT prices crashed in HE20-21 instead of spiking
- WEST_TO_NORTH: PARTIAL — timing 1 hour early (systematic bias)

The simultaneous conditions on 2026-06-21 were:
- GR_WEST forecast at HE24: 18,103 MW (series record — highest in 30-cycle history)
- NL ramp: elevated (+10,000+ MW from trough to peak)
- Non-Spin DA: elevated ($8-18/MWh range, evening hours)

The 1.8x right-tail rule (evaluator-registered in prior cycles) was designed for the NL ramp condition
but does not account for the simultaneous high-GR_WEST wind suppression of RT prices.

When GR_WEST wind is very high (>15,000 MW forecast), it:
1. Suppresses evening DA prices (excess supply → DA clears lower)
2. Creates high RT price volatility (as wind varies 15-min interval, RT spikes or crashes)
3. Makes HOUSTON_IMPORT less likely to bind (because wind export from West can flow North,
   partially relieving the South-to-Houston pressure)

The current Stage 0 heuristic does not incorporate GR_WEST level in the probability estimate.

---

## Required Actions

### Action 1 — Add GR_WEST Haircut Condition

Add to the daily congestion analysis workflow, after computing base probability:

```
IF GR_WEST_forecast[HE_window] > 15,000 MW:
    APPLY haircut: HOUSTON_IMPORT probability × 0.85 (i.e., −15 ppt at each tier)
    APPLY haircut: WEST_TO_NORTH probability × 0.90 (−10 ppt — wind flows north, relieves WEST constraint)
    FLAG: "HIGH GR_WEST HAIRCUT APPLIED — probabilities reduced from base heuristic"
```

Threshold evidence:
- 2026-06-21: GR_WEST 18,103 MW → HOUSTON_IMPORT HIGH call failed
- Prior high-wind days (>12,000 MW): WEST_TO_NORTH partially confirmed but with timing error
- Threshold of 15,000 MW is conservative (well above typical 8,000-12,000 MW summer range)

### Action 2 — Add WEST_TO_NORTH Timing Correction

Per 2026-06-21 learnings and prior cycles: WEST_TO_NORTH binding occurs 1 hour earlier than
the heuristic predicts. Current heuristic targets HE01-05; actual binding center appears to be HE24-HE03.

Adjustment: shift the WEST_TO_NORTH binding window from "HE01-05 peak" to "HE24-04 peak".
Update the downstream output to downstream agents accordingly.

### Action 3 — Document in Stage 0 Heuristic Notes

In `memory/congestion-analyst/` (or the CONGESTION_PROJECT notes), add a section:

```markdown
## Stage 0 Heuristic Adjustments (as of 2026-W25)

### GR_WEST High-Wind Haircut
- Trigger: GR_WEST forecast max in HE19-24 window > 15,000 MW
- Effect: HOUSTON_IMPORT probability × 0.85; WEST_TO_NORTH probability × 0.90
- Rationale: High West wind suppresses evening DA; reduces import constraint binding pressure
- Evidence: 2026-06-21 solstice — 18,103 MW GR_WEST → HOUSTON_IMPORT HIGH failed

### WEST_TO_NORTH Timing Shift
- Current heuristic: binding peak at HE01-05
- Corrected: binding peak at HE24-04 (1-hour earlier)
- Evidence: 2026-06-21 learnings, consistent with 3-prior-cycle timing error
```

### Action 4 — Coordinate with dart-virtual-trader

When HIGH GR_WEST haircut is applied, add to the "Downstream Agent Input" section:
"CAUTION: GR_WEST haircut active — evening spike confidence reduced; dart-virtual-trader
should consider reducing INC position size by 25-50% or skip if below-floor threshold"

---

## Success Criteria

- Next Saturday/Sunday with GR_WEST > 15,000 MW forecast: haircut applied and documented in report
- WEST_TO_NORTH binding window updated to HE24-04 in next congestion report
- Stage 0 heuristic notes document updated in memory
- dart-virtual-trader receives explicit GR_WEST haircut flag on relevant days

---

## Long-Term Note

This haircut is a Stage 0 heuristic fix. Once W3 Item 0.10 (hub-pair LMP) is available,
the empirical relationship between GR_WEST level and HOUSTON_IMPORT binding probability
should be estimated from data, replacing the 15% heuristic with a regression coefficient.
