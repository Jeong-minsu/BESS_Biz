# Plan: DA vs RT Venue Strategy Alignment with Tenaska Operations — 2026-21

**Issue**: bess-optimizer recommended DA Energy discharge at HE20-22 on both 2026-05-22 and 2026-05-24. Tenaska executed RT Energy dispatch both days. The DA-sell strategy was analytically correct (DA > RT spread confirmed), but revenue projections were systematically miscalibrated because the recommendation projected DA revenue while actual execution produced RT revenue. On 2026-05-24, this caused a -$3,123 (-36.5%) gap between recommendation and actual, even though GKS still outperformed Smartbidder by +$886.

**Priority**: CRITICAL

## Actions

- Initiate a direct inquiry to Tenaska/Operations: "Does GKS_BESS_RN's bid structure support explicit DA Energy sell offers at HE20-22, or is the BESS defaulting to RT dispatch because no DA energy offer is being submitted?"
- Until clarified, bess-optimizer must present revenue projections using RT-realized pricing as the base case (not DA), with DA-sell as the upside scenario.
- Apply a calibrated downward adjustment to Smartbidder peak DA price forecasts: two cycles confirm HE21 DA overestimates of $12-21; apply 15-20% discount to Smartbidder raw DA peak forecast.
- Document in `shared/config.md` once confirmed: whether bess-optimizer should be modeling DA bids, RT bids, or a mixed strategy for GKS.
- Coordinate with pnl-manager: request a field-level Tenaska output showing DA_Sales_Qty vs RT_Generation_Qty by HE to confirm which venue GKS is actually executing in each cycle.
