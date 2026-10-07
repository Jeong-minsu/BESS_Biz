# Plan: DA vs RT Venue — Week 22 Follow-Up

**Issue**: The 2026-21 plan required a direct inquiry to Tenaska/Operations to confirm whether GKS_BESS_RN submits explicit DA Energy sell offers. No confirmation has been received as of Week 22. However, the 2026-05-29 actuals (the only new data point with Tenaska settlement this week) show that DA sales occurred (100.20 MWh at HE21-22) alongside large RT Energy revenue (+$3,830.36), suggesting a hybrid model where both DA and RT dispatch occur simultaneously.

**Priority**: CRITICAL (unchanged from 2026-21; partial new evidence but venue question still unresolved)

**Week 22 evidence**:
- 2026-05-29 actuals: DA_Sales_Qty = 100.20 MWh (one full discharge hour in DA). RT_Generation_Qty = 69.75 MWh (additional RT dispatch). Both occurred on the same day, which is consistent with the hypothesis that GKS submits a DA discharge at one or two hours and also dispatches in RT.
- bess-optimizer correctly applied 0.80x Smartbidder haircut across all recommendations this week. This is the right interim behavior.
- The DA Energy net was -$2,474.12 on 2026-05-29 despite large RT revenue (+$3,830), because DA purchases (323.9 MWh) exceeded DA sales (100.2 MWh). This is the normal pattern for a charge-heavy strategy day — not an indication that DA sell was absent.

## Updated Actions

1. **User confirmation still needed**: Ask Tenaska/Operations whether 2026-05-29's DA_Sales_Qty (100.20 MWh at HE21-22) represents explicit DA Energy bid submissions, or whether it reflects the co-optimizer's DA scheduling of physical dispatch. This distinction determines whether bess-optimizer's DA-sell strategy is being executed at all.
2. **Interim calibration accepted**: The 0.80x Smartbidder haircut (calibrated from 2026-05-22 and 2026-05-24 actuals) continues to be the appropriate correction factor. On 2026-05-29, the actual energy outcome was mixed (strong RT component alongside moderate DA), suggesting the 0.80x factor may be slightly too conservative for days with strong DA clearing. Monitor.
3. **2026-05-29 new lesson**: RRS actual ($1,140.30) was 4.7x the estimate (~$242). bess-optimizer has already applied Action from this in the 2026-05-31 schedule (RRS 30 MW at HE19). This is correct.

## Success Criteria

- Tenaska confirms the DA Energy bid submission structure for GKS_BESS_RN (user action).
- Revenue projection MAE (plan vs actual) < 20% across any 3 consecutive data points with Tenaska settlement.

## Owner

User (Tenaska confirmation) + bess-optimizer (continued calibration)
