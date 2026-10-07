# Plan: Model Calibration Drift Risk — Week 22

**Issue**: With Tenaska settlement data available for only 3 of 11 operating days (2026-05-22, 2026-05-24, 2026-05-29), all bess-optimizer calibration parameters are potentially stale. Specific parameters at risk:
- 0.80x Smartbidder DA peak haircut (calibrated from 2026-05-22 and 2026-05-24 only)
- 20% RT AS drag assumption (actual drag was 34.5% on 2026-05-29 for NonSpin)
- HE19 ECRS pattern (last confirmed 2026-05-24; zero ECRS on 2026-05-29)
- Starting SoC assumption (0 MWh has been used; 2026-05-29 analysis suggests SoC started at 0 and ended at ~200 MWh after heavy charging)

**Priority**: MAJOR

**Week 22 evidence**:
- 2026-05-29 actuals confirm: actual revenue $5,111.74 vs estimate $7,643 (-33% shortfall). RRS 4.7x underestimated. ECRS = $0 actual. RT Energy optionality not modeled (+$3,830 actual, not in base plan).
- bess-optimizer self-review (2026-05-30) correctly identified all four lessons and applied RRS upweighting and RT optionality note in the 2026-05-31 schedule. JSON calibration alignment also confirmed fixed.

## Actions

1. **Maintain per-settlement-day calibration log**: Each time Tenaska data is received, update the calibration table in `memory/bess-optimizer/learnings/` with: Smartbidder haircut implied from actual HE20-21 DA clearing, actual RT AS drag %, actual RRS vs estimate ratio, actual ECRS deployment.
2. **Three-data-point rule**: Any calibration parameter change requires at minimum 3 settlement data points showing the same direction. Current data: 2 for haircut (0.80x), 2 for ECRS overnight structural pattern, 1 for RRS underweighting. Proceed cautiously with RRS scaling until confirmed.
3. **RT Energy Optionality**: Include an explicit "RT Energy Upside: $1,500-$3,000" line in all future revenue summaries until the RT dispatch mechanism is clarified with Tenaska.
4. **NonSpin RT Drag**: Update assumption from 20% to 25% for next calibration review. Three data points are now available (2026-05-24: 19.6%, 2026-05-25 benchmark: ~20%, 2026-05-29: 34.5%). The range is wide — flag for refinement once more data is available.

## Success Criteria

- Revenue estimate vs actual MAE < 25% on any future settlement day with confirmed Tenaska data.
- All calibration parameters have >= 3 confirming data points before being treated as structural.

## Owner

bess-optimizer (agent-implementable; requires Tenaska data availability)
