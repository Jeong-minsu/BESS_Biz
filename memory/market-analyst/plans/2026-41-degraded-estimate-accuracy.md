# Plan: market-analyst DEGRADED-Mode Estimate Accuracy Protocol
# Week 2026-41 | Priority: MAJOR | Registered: 2026-10-12

## Issue

Oct 6 DEGRADED briefing (no Yes Energy, no Smartbidder) produced significantly inaccurate estimates:

| Variable | Oct 6 Estimate | Oct 8 Actual | Error |
|---|---|---|---|
| Solar HE12 | 19–22 GW | 30,472 MW | −8 to −11 GW (underestimate) |
| Wind avg | 13–17 GW | 4,132 MW | +9 to +13 GW (overestimate) |
| Outage | 10.5–12.5 GW | ~20,000 MW | −7.5 to −9.5 GW (underestimate) |
| DA avg | $28–38/MWh | (not confirmed) | N/A |

The Oct 6 estimate used "Sep 30 actuals + Oct seasonality." This approach:
1. Did NOT use ERCOT wind/solar forecast data (available via public ERCOT API or Yes Energy public endpoints)
2. Did NOT cite outage data from any source (ERCOT outage reports are public)
3. Used seasonal averages instead of day-ahead public signals

## Root Cause

When Yes Energy is unavailable, the current DEGRADED protocol relies on:
- Historical actuals (lagged by several days)
- Seasonal pattern application

The DEGRADED protocol does NOT include:
- ERCOT public forecast API (wind/solar 7-day ahead, publicly accessible without Yes Energy subscription)
- ERCOT outage reports (publicly accessible)
- AG2/Enverus forecasts (available independently of Yes Energy)

## Required Protocol Change

### Tiered DEGRADED fallback (in priority order):
1. **Tier 1 (PRODUCTION)**: Yes Energy Datalake — full resolution
2. **Tier 2 (DEGRADED-A)**: Yes Energy unavailable → AG2/Enverus forecast + ERCOT public forecast API + ERCOT outage reports
3. **Tier 3 (DEGRADED-B)**: Yes Energy + AG2 both unavailable → ERCOT public forecasts + outage reports + 7-day MA
4. **Tier 4 (FULLY DEGRADED)**: All sources unavailable → prior day actuals + season pattern; MUST disclose confidence as LOW

In W41, Oct 6 used Tier 4 despite AG2 and ERCOT public APIs being available. This is a process gap.

## Action Required

### Agent (immediately):
1. Document the 4-tier DEGRADED fallback in `memory/market-analyst/briefing-template.md` (or BRIEFING_TEMPLATE.md if named differently).
2. Add explicit AG2/Enverus call as MANDATORY for every cycle (confirmed W40 plan still open: AG2 not called for 4+ consecutive run days in W41).
3. Add ERCOT public forecast API check as Tier 2 step for wind/solar.
4. For ERCOT public outage data: use `https://www.ercot.com/gridmktinfo/dashboards/outages` as fallback.

### Cross-agent impact:
- bess-optimizer and dart-virtual-trader received Oct 6 DEGRADED estimates. Both agents applied additional DEGRADED penalties (correct behavior), but the input data accuracy was worse than disclosed confidence levels.
- Evaluator notes: downstream agents applied appropriate caution; the primary failure is upstream in market-analyst.

## Success Criteria

W42 evaluation:
- AG2/Enverus called on all run days (including DEGRADED days)
- DEGRADED-mode briefings explicitly cite which tier is in use
- No Tier 4 briefing issued when Tier 2 or 3 sources are available
- Solar/wind/outage estimates include ERCOT public data as floor cross-check

## References

- W40 plan: `memory/market-analyst/plans/2026-W40.md` (AG2 not called — 3rd consecutive miss)
- Oct 6 briefing: `reports/daily/market-briefing/2026-10-06.md`
- Oct 8 actuals (comparison): `reports/daily/market-briefing/2026-10-08.md`
- BRIEFING_TEMPLATE.md: `memory/market-analyst/BRIEFING_TEMPLATE.md` (verify current content)
