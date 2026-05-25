# Plan: WEST_TO_NORTH Binding Probability Calibration — 2026-21

**Issue**: On 2026-05-24, congestion-analyst called WEST_TO_NORTH HIGH (~35-50%) based on near-zero GR_WEST wind (600 MW) + peak solar (28.5 GW). Settlement data showed near-flat GKS nodal spreads (HE10-14 DASPP vs RTSPP within $1-3), confirming the constraint did not materially bind at the GKS node. The HIGH call was a directional miss. This overstates confidence in the West binding thesis at Stage 0 without PTDF data.

**Priority**: MAJOR

## Actions

- Revise the binding probability ceiling for WEST_TO_NORTH at Stage 0: without PTDF data and hub-pair LMP, the maximum qualitative call is MEDIUM (~20-30%) regardless of wind/solar conditions. HIGH calls require at least hub-pair LMP evidence of West-North spread widening.
- Add an explicit heuristic rule to the congestion analysis template: "GR_WEST trough < 500 MW AND net load trough < 27,000 MW simultaneously required for MEDIUM-HIGH call. Above either threshold: cap at MEDIUM."
- Document the mechanism clarification: GKS congestion benefit appears primarily as DA price premium (DA-side congestion), not RT nodal shadow price. Update the briefing language to distinguish "DA-side congestion premium" from "RT nodal suppression."
- Prioritize hub-pair LMP ingestion (HB_NORTH, HB_WEST, HB_HOUSTON) as Stage 0 completion item. This single data addition converts most Stage 0 calls from qualitative to scorable.
