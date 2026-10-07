# bess-optimizer Standing Rules

**Last updated**: 2026-06-23
**Created to fulfill**: W25 plan `2026-25-standing-rules-gap.md` (deadline 2026-06-24)
**Consult this document at the start of every schedule generation, before reading market data.**

---

## Rule 1: ECRS Inclusion (Summer Heat Season)

- **Condition**: June 1 – September 30 AND DA Non-Spin or ECRS price signal exists (even without Smartbidder forecast, default to include during summer)
- **Action**: Include ECRS as a co-offer product at 15-30 MW in HE20-24 (evening peak) and HE07-10 (morning ramp) unless capacity is fully committed to energy discharge
- **Override**: Never exclude ECRS solely because it cleared $0 on prior day(s) during June–September. Pattern 14 (evaluator W24): ECRS cleared 4/7 weekdays in W24. The 2026-06-22 actual showed ECRS $756 at HE21-24 — significant missed revenue when not offered
- **Exception**: If SoC at those hours is fully committed to energy discharge (SoC < 30 MWh), then ECRS offering is constrained by physical capacity; document as "ECRS excluded: SoC insufficient"
- **Source**: evaluator Pattern 14 (W24); 2026-06-22 actuals ECRS $756; 2026-06-22 self-review Action 4

---

## Rule 2: RT Dispatch Haircut on Revenue Projections

- **Condition**: All DA Energy revenue projections
- **Action**: Apply 0.80x multiplier to DA Energy revenue projections when stated as "Expected Revenue" (RT execution systematically differs from DA plan; RT imbalance charges offset a portion of DA revenue)
- **Note**: Calibrated on 2026-05-24 data. Update when 3+ new PRODUCTION days available (Rule 4 applies)
- **Do NOT apply haircut to**: AS (Non-Spin, ECRS, RRS) — these settle on DA price independent of RT dispatch

---

## Rule 3: Non-Spin DA Overnight Premium

- **Condition**: Confirmed PRODUCTION data showing Non-Spin DA price > $8/MWh at HE20-24 in prior cycle
- **Action**: Flag as high-scarcity environment; prioritize Non-Spin DA in HE20-24 as primary revenue source ahead of energy arbitrage
- **Action**: Coordinate with dart-virtual-trader — reduce INC virtual recommendation to 50% of standard size (Non-Spin high = scarcity signal; INC exposure in same hours creates adverse correlation)
- **Threshold triggers**: Non-Spin HE22-24 DA > $5/MWh = elevated; > $8/MWh = high; > $15/MWh = extreme (seen 2026-06-22 actuals: HE22 Non-Spin $448/75MW = $5.97/MWh, HE23 $450/75MW = $6.00/MWh)
- **Source**: 2026-06-22 learnings Action 2; W23 plan Issue 2

---

## Rule 4: 3-Data-Point Calibration Threshold

- **Condition**: Before updating any multiplier (0.80x haircut, Non-Spin premium thresholds, charge window hours)
- **Requirement**: 3+ new PRODUCTION-quality confirmed Tenaska data points required
- **Do not update** based on 1-2 data points or Smartbidder benchmark-only (benchmark is PRODUCTION_ESTIMATE, not settled)
- **Exception**: User-confirmed structural change (e.g., Tenaska endpoint format change, new asset registration) may trigger immediate update with 1 data point

---

## Rule 5: DA Energy Row-Count Discrepancy

- **Status**: UNRESOLVED — GKS DA Energy P&L frequently exists in Battery-Settlement-Details without matching DA bid/offer rows from Tenaska PTP Submissions endpoints (0 rows returned)
- **Interim rule**: Do not adjust recommendations based on this discrepancy; flag in each report as "DA Energy bids submitted via Smartbidder/Ascend; Tenaska PTP Submissions endpoint returns 0 rows (expected)"
- **Escalate to user** if: Tenaska PTP returns 0 rows for Battery-Settlement-Details (the primary endpoint) for 3+ consecutive cycles
- **Source**: W22 open issue; W23 plan; 2026-06-22 pnl report data quality note

---

## Rule 6: HOUSTON_IMPORT Congestion — DA-RT Venue Switch

- **Condition**: congestion-analyst HOUSTON_IMPORT_345 P(binding) level
- **Action thresholds**:
  - P(binding) < 10% (LOW): DA Energy sell at peak hours is primary strategy (DA venue locks in congestion premium)
  - P(binding) 10-35% (LOW-MEDIUM / MEDIUM): Hybrid — DA Energy sell at HE19 + hold SoC for RT optionality at HE20-21. Document as "Hybrid DA-RT"
  - P(binding) > 35% (HIGH): Hold majority of SoC for RT dispatch; limit DA Energy sell to 30-50% of available SoC at peak hours; Non-Spin DA as primary product
- **Rationale**: When HOUSTON_IMPORT binds, GKS node (South/Houston area) receives nodal MCC premium (+$4 to +$18/MWh estimated). RT LMP at GKS during binding events historically exceeds DA clearing price. Bias to RT-primary when congestion probability HIGH
- **Applied to**: HE19-22 only (evening ramp window). Morning and midday hours: always DA-primary for charging
- **Source**: evaluator W24 Issue 3; bess-optimizer learnings 2026-06-12 Action 2; 2026-06-22 actual pattern (HE22 RT Energy $1,468 surge)

---

## Rule 7: SoC Initialization — Missing Tenaska Data

- **Condition**: Tenaska PTP returns 0 rows (degraded) — cannot confirm terminal SoC from prior day
- **Action**: Assume SoC = 100 MWh (50% DoD midpoint) as default
- **Override**: If prior-day recommendation targeted terminal SoC = 0 MWh and battery was expected to discharge fully, use SoC = 20-40 MWh (partial residual assumption) instead of 100 MWh
- **Override 2**: If Tenaska returns PRODUCTION data for the prior day showing net_energy_mwh, back-calculate SoC from known start SoC + (energy_consumption_mwh - energy_injection_mwh)
- **Flag in every report**: Current SoC source (PRODUCTION / DEGRADED / ASSUMED)

---

## Rule 8: Unresolved RT Dispatch Risk Disclosure

- **Status**: OPEN (since W23 plan — user action required; unresolved as of 2026-06-23)
- **Action**: Include the following risk line in every recommendation until mechanism is confirmed by user:
  "UNRESOLVED RISK: Involuntary RT dispatch at non-recommended hours observed on 2026-06-05 (estimated -$4,520 impact). Origin unconfirmed (Smartbidder RT layer override vs. ERCOT auto-dispatch vs. settlement artifact). Base-case revenue estimate does not account for this risk. Recommend confirming execution flow with Tenaska/Smartbidder."
- **Source**: W23 plan Issue 1; 2026-06-07 learnings

---

## Model Constants (confirmed, do not change without 3 PRODUCTION data points per Rule 4)

| Parameter | Value | Source | Last confirmed |
|---|---|---|---|
| Round-trip efficiency (RTE) | 85% (0.85) | CLAUDE.md asset spec; Smartbidder default | Always |
| GKS capacity | 100 MW / 200 MWh | Asset spec | Always |
| DA Energy projection haircut | 0.80x | W22 calibration | 2026-05-24 |
| Non-Spin DA MW default | 88 MW (HE01-18) | 2026-06-22 actual: 75 MW avg cleared | 2026-06-22 |
| ECRS co-offer MW | 15-30 MW (summer, evening) | Rule 1 | 2026-06-23 |

---

*bess-optimizer | standing-rules.md | Created 2026-06-23 to fulfill W25 plan deadline 2026-06-24*
*Next review: 2026-07-07 (bi-weekly) or when 3+ new PRODUCTION data points available per Rule 4*
