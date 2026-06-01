# Plan: AS Template Persistent Gap — Non-Spin Overnight + ECRS Morning Ramp — Week 22

**Issue**: The AS section of the market-analyst daily briefing template has failed to include two structurally confirmed patterns for 7 consecutive cycles (2026-05-22 through 2026-05-31):
1. Non-Spin overnight HE01-06 clearing — confirmed in 2026-05-25 Smartbidder benchmark and multiple Tenaska settlement files
2. ECRS morning ramp HE07-10 — confirmed in 2026-05-24 Tenaska settlement (HE07-10 ECRS clearing)

The 2026-21 plan (2026-21-as-timing-correction.md) required a template-level fix, but the learnings files confirm this was not physically applied to the template. The market-analyst recognized the miss in every self-review and still produced briefings without the fix. This is a clear gap between identifying the correction and implementing it.

**Priority**: MAJOR (escalated from 2026-21 due to 7-cycle persistence)

**Evidence**: memory/market-analyst/learnings/2026-05-27.md Section 5 cumulative pattern tracker shows Non-Spin overnight and ECRS morning ramp both at "5 cycles" as of 2026-05-27; memory/market-analyst/learnings/2026-05-31.md Section 5 shows "7 cycles" still. The 2026-05-29 self-review notes partial improvement (Smartbidder peak adjustment applied starting 2026-05-30), but Non-Spin and ECRS bullets remain absent.

## Actions

1. **Immediately add two fixed bullets to the AS section template** (apply starting next cycle after this plan is registered):
   - Bullet A (first in AS section): "Non-Spin overnight (HE01-06): $[X]/MWh — structural clearing window confirmed. BESS SoC=0 AS eligible."
   - Bullet B (second in AS section): "ECRS morning ramp (HE07-10): $[X]/MWh — structural clearing window confirmed. Morning ramp reserve demand."
   - Populate with actual Smartbidder DA prices from the day's fetch; do not leave blank.

2. **Lock template section order** per ORGANIZATION.md and the 2026-21 plan:
   - AS section order: overnight → morning ramp → midday low → evening spike

3. **AG2 windcast integration**: Market-analyst has now confirmed AG2 windcast file exists and was parsed once (2026-05-30). Treat AG2 as a mandatory third source alongside Yes Energy and Enverus for each briefing starting 2026-06-02.

## Success Criteria

- Both AS bullets (Non-Spin overnight + ECRS morning ramp) present in the next 3 consecutive daily briefings with actual price values filled in, not placeholder text.
- AG2 windcast cross-validation present in 3 of next 5 briefings.

## Owner

market-analyst (template is fully under agent control; no external dependency)
