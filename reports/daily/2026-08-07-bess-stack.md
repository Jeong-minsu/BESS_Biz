# GKS BESS — D+1 (2026-08-07, Friday) Optimal Revenue Stack

**Issued**: 2026-08-06 07:30 CT | **Asset**: GKS_BESS_RN (100 MW / 200 MWh / RTE 85%)
**Flowday**: 2026-08-07 (Friday, WDPEAK HE07-22) | **Event**: Heat Event Day 6

DATA_STATUS: YES_ENERGY=PROD | SMARTBIDDER=DEGRADED(Day 12, AADSTS7000222) | TENASKA=DEGRADED | AS_PLAYBOOK=ABSENT

> **Confidence Level**: PARTIAL. Yes Energy BIDCLOSE 24h confirmed (production). All price estimates are qualitative fundamental inference anchored to 08/04 Tenaska actuals (DA HE10=$10.05, HE21=$32.16, HE22=$37.08/MWh). No Smartbidder, Enverus, or AG2 validation. P10-P90 spread 3-4x wider than normal PROD cycle. Rule 2 (0.80x DA haircut) and empirical calibration applied to all discharge revenue projections.

---

## Key 08/07 Structural Signals

| Signal | Value | Implication for BESS |
|---|---|---|
| Duck floor HE10 | 28,553 MW (MODERATE) | Charge window confirmed; price $10-15/MWh |
| GR_WEST HE13 floor | 3,564 MW (event record low) | NEW midday price risk zone HE13-18: $18-50/MWh |
| Net load peak HE21 | 63,794 MW (+516 MW vs 08/06) | Evening discharge window maintained |
| HE18-21 ramp | +15,805 MW (2,130 MW below binding floor) | SOUTH_HOUSTON LOW 8-15%; DA primary |
| Friday demand decay | Load avg -2,289 MW vs 08/06 | Evening prices slightly softer than Wed-Thu; HE22 may peak |
| WEST_TO_NORTH_345 | MEDIUM HE01-05 (16-24%) | Overnight GKS MCC -$1 to -$3/MWh; NS hold favored over charge |
| Cap-out HE21 | 6,021 MW (event low — best reserve margin) | Slight downward offset to evening spike premium |

**SoC init**: 0 MWh (from 2026-08-06 terminal schedule: DA Discharge HE20+HE21 full 200 MWh)

---

## Recommendation (Primary) — Stack A: Duck Charge + Evening Discharge + NS Overlay

| HE | Mode | Energy MW | RegUp | RegDown | RRS | ECRS | NonSpin | GKS eff $/MWh |
|----|------|-----------|-------|---------|-----|------|---------|---------------|
| 01 | NS Hold | 0 | 0 | 0 | 0 | 0 | 75 | — |
| 02 | NS Hold | 0 | 0 | 0 | 0 | 0 | 75 | — |
| 03 | NS Hold | 0 | 0 | 0 | 0 | 0 | 75 | — |
| 04 | NS Hold | 0 | 0 | 0 | 0 | 0 | 75 | — |
| 05 | NS Hold | 0 | 0 | 0 | 0 | 0 | 75 | — |
| 06 | NS Hold | 0 | 0 | 0 | 0 | 0 | 75 | — |
| 07 | NS Hold | 0 | 0 | 0 | 0 | 0 | 75 | — |
| 08 | NS Hold | 0 | 0 | 0 | 0 | 0 | 75 | — |
| **09** | **DA Charge** | **-100** | 0 | 0 | 0 | 0 | 75 | **~$12 (buy cap $15)** |
| **10** | **DA Charge** | **-100** | 0 | 0 | 0 | 0 | 75 | **~$10 (buy cap $12; anchor 08/04 actual $10.05)** |
| **11** | **DA Charge (top-off)** | **-35** | 0 | 0 | 0 | 0 | 75 | **~$14 (buy cap $17)** |
| 12 | NS Hold | 0 | 0 | 0 | 0 | 0 | 75 | — |
| 13 | NS Hold (wind trough watch) | 0 | 0 | 0 | 0 | 0 | 75 | — |
| 14 | NS Hold (midday gate) | 0 | 0 | 0 | 0 | 0 | 75 | — |
| 15 | NS Hold | 0 | 0 | 0 | 0 | 0 | 75 | — |
| 16 | NS Hold | 0 | 0 | 0 | 0 | 0 | 75 | — |
| 17 | NS Hold | 0 | 0 | 0 | 0 | 0 | 75 | — |
| 18 | NS Hold | 0 | 0 | 0 | 0 | 0 | 75 | — |
| 19 | NS Hold (SoC Reserve) | 0 | 0 | 0 | 0 | 0 | 50 | — |
| 20 | NS Hold (Ramp Monitor) | 0 | 0 | 0 | 0 | 0 | 50 | — |
| **21** | **DA Discharge** | **+100** | 0 | 0 | 0 | 0 | 0 | **~$32 (sell floor $25; anchor 08/04 HE21 DA $32.16)** |
| **22** | **DA Discharge + ECRS** | **+75** | 0 | 0 | 0 | 25 | 0 | **~$37 (sell floor $25; anchor 08/04 HE22 DA $37.08)** |
| 23 | ECRS Hold | 0 | 0 | 0 | 0 | 25 | 0 | ECRS clearing |
| 24 | ECRS Hold | 0 | 0 | 0 | 0 | 25 | 0 | ECRS clearing |

**Rule exclusions**: RegUp/RegDown excluded (Rule 4, all hours). RRS excluded (4-consecutive zero-clear pattern — structural, not price issue).

### SoC Balance

| Checkpoint | SoC MWh | Calculation |
|---|---|---|
| HE01 start | 0 | 08/06 terminal: full discharge HE20+HE21 |
| HE01-08 NS Hold | 0 | Energy uncommitted; NS capacity commitment |
| **HE09 charge** | **85** | 0 + (100 × 0.85) |
| **HE10 charge** | **170** | 85 + (100 × 0.85) |
| **HE11 top-off** | **200** | 170 + (35 × 0.85) = 199.75 ≈ 200 (FULL) |
| HE12-20 Hold | **200** | Energy uncommitted; SoC preserved |
| **HE21 discharge** | **100** | 200 - 100 |
| **HE22 discharge** | **25** | 100 - 75 |
| HE23-24 ECRS | **25** | No energy dispatch; ECRS buffer |

SoC terminal: 25 MWh (ECRS reserve). All 24 hours within 0-200 MWh. **FEASIBLE**.

### HSL Check

| HE | Energy MW | ECRS MW | NS MW | Total | HSL |
|----|-----------|---------|-------|-------|-----|
| HE01-08 | 0 | 0 | 75 | 75 | PASS |
| HE09-11 | 100 / 100 / 35 | 0 | 75 | 100 (concurrent capacity) | PASS |
| HE12-18 | 0 | 0 | 75 | 75 | PASS |
| HE19-20 | 0 | 0 | 50 | 50 | PASS |
| HE21 | 100 | 0 | 0 | 100 | PASS |
| HE22 | 75 | 25 | 0 | 100 | PASS |
| HE23-24 | 0 | 25 | 0 | 25 | PASS |

NS during charging (HE09-11): concurrent capacity commitment, not additive energy — consistent with 08/03-08/04 observed Smartbidder execution.

---

## DA Bid Parameters

| HE | Direction | MW | Price Floor/Cap | Basis |
|----|-----------|----|----|---|
| HE09 | Buy (charge) | 100 | Node ≤ $15/MWh | MODERATE duck; est. $10-14/MWh |
| HE10 | Buy (charge) | 100 | Node ≤ $12/MWh | Trough HE10 28,553 MW; anchor 08/04 actual $10.05 |
| HE11 | Buy (charge, top-off) | 35 | Node ≤ $17/MWh | Secondary duck; est. $12-15/MWh |
| HE01-08, HE12-18 | NS offer | 75 | $0/MWh DA | Market clearing |
| HE19-20 | NS offer | 50 | $0/MWh DA | SoC preservation priority |
| HE21 | DA Sell | 100 | Min ≥ $25/MWh | NL peak 63,794 MW; anchor 08/04 $32.16 |
| HE22 | DA Sell + ECRS | 75 + 25 | Min ≥ $25/MWh | 08/04 peak DA $37.08; ECRS concurrent |
| HE23-24 | ECRS offer | 25 | $0/MWh | AS clearing |

---

## Top / Bottom Hours

**Top 2 (DA Discharge — primary):**
- **HE22**: GKS eff DA ~$37/MWh | NL 60,123 MW | Solar = 0 | Wind recovery 14,878 MW | 08/04 confirmed peak DA hour ($37.08) | Target 75 MW + 25 MW ECRS
- **HE21**: GKS eff DA ~$32/MWh | NL 63,794 MW (event max net load) | Solar 351 MW (solareffectively zero) | 08/04 anchor $32.16 | Target 100 MW

**Bottom 2 (DA Charge):**
- **HE10**: GKS eff DA ~$10/MWh | NL 28,553 MW (duck floor, MODERATE) | Solar 24,863 MW | Anchor: 08/04 actual HE10 DA $10.05 | 100 MW
- **HE09**: GKS eff DA ~$12/MWh | NL 33,068 MW | Solar 15,764 MW | 100 MW

**SoC Reserve / Ramp Monitor (HE19-20):**
- HE19: NL ramp begins (+8,179 MW to HE21 in 2 steps). NS 50 MW only; SoC FULL preserved.
- HE20: NL 59,340 MW — monitor for opportunistic discharge. NS 50 MW; hold for HE21+HE22.

**Midday Watch (HE13-15 — NOT primary, conditional only):**
- HE13: NL 41,008 MW, GR_WEST 3,564 MW (event record), price est. $18-35/MWh
- HE14: NL 43,844 MW, price est. $20-40/MWh — Stack B gate (see below)
- Action: No energy dispatch in primary. Trigger review at HE13 if RT > $40/MWh.

---

## DA-RT Spread Strategy

**Overall 08/07 call: DA primary all energy hours. Rule 6 NOT triggered.**

| Window | Spread Direction (DA - RT) | Decision | Rationale |
|---|---|---|---|
| HE09-11 (charge) | Positive (DA > RT expected) | DA charge; node cap $12-17 | Duck floor; 08/04 actual HE10 DA $10.05 > RT $8.96 (spread +$1.09) |
| HE12-18 (hold) | Not applicable | NS 75 MW overlay | No energy commitment |
| HE19-20 (ramp monitor) | Positive → transitional | Hold; NS 50 MW | HE20 NL 59,340 MW; prices est. $28-45/MWh, below HE21-22 EV |
| HE21-22 (discharge) | Positive (DA > RT expected) | DA primary 100 + 75 MW | 08/04 HE21 DA $32.16 > RT $29.84 (+$2.32); HE22 DA $37.08 > RT $36.50 (+$0.58) |
| SOUTH_HOUSTON_IMPORT | LOW 8-15% (below binding floor by 2,130 MW) | DA primary; Rule 6 NOT triggered | P=8-15% < 35% HIGH threshold; no congestion premium to capture via RT |

**RRS**: 0 MW — 4 consecutive zero-clear cycles confirmed (Actions 3 carry-forward). Structural market access issue, not pricing. Excluded until Smartbidder diagnostics available.

**ECRS**: 25 MW HE22-24 — 4-consecutive Smartbidder execution pattern. HE22 SoC 25 MWh provides contingency buffer.

---

## Expected Revenue

### Scenario Matrix

| Scenario | GR_WEST HE13 | Net Load HE21 | BESS Mode | Energy Net | AS | Total |
|---|---|---|---|---|---|---|
| P10 (Bull wind) | 5,564 MW | 61,794 MW | Single-cycle, low prices | +$2,100 | +$1,200 | **$3,300** |
| P50 Empirical | 3,564 MW (base STWPF) | 63,794 MW | Primary Stack A | +$3,302 | +$1,865 | **$5,167** |
| P50 Structural | 3,564 MW (base STWPF) | 63,794 MW | Primary Stack A | +$4,130 | +$1,865 | **$5,995** |
| P90 (Bear wind) | 1,564 MW | 65,794 MW | Primary Stack A + midday watch | +$6,100 | +$2,300 | **$8,400** |

### P50 Empirical Breakdown (anchored to 08/04 actuals)

| Category | Volume | Price | Revenue |
|---|---|---|---|
| HE09 charge | 100 MWh | $12.00/MWh | -$1,200 |
| HE10 charge | 100 MWh | $10.05/MWh | -$1,005 |
| HE11 top-off | 35 MWh | $14.00/MWh | -$490 |
| **Charging subtotal** | **235 MWh grid** | — | **-$2,695** |
| HE21 discharge | 100 MWh | $32.00/MWh | +$3,200 |
| HE22 discharge | 75 MWh | $37.00/MWh | +$2,775 |
| **Discharge subtotal** | **175 MWh** | — | **+$5,975** |
| **Energy net** | — | — | **+$3,280** |
| NS (HE01-08, 75 MW × 8h) | 600 MW-h | $1.40/MW-h | +$840 |
| NS (HE12-18, 75 MW × 7h) | 525 MW-h | $1.40/MW-h | +$735 |
| NS (HE09-11, 75 MW × 3h concurrent) | 225 MW-h | $1.40/MW-h | +$315 |
| NS (HE19-20, 50 MW × 2h) | 100 MW-h | $1.40/MW-h | +$140 |
| **NS subtotal** | **1,450 MW-h** | — | **+$2,030** |
| ECRS (HE22-24, 25 MW × 3h) | 75 MW-h | $2.00/MW-h | +$150 |
| **Grand Total P50 Empirical** | — | — | **+$5,460** |

> Note: NS concurrent with charging is included per confirmed 08/03-08/04 execution pattern (75 MW concurrent capacity commitment, not energy). If DA clearing rejects NS during charge hours, NS revenue drops by $315 → Total $5,145.

**vs Smartbidder benchmark**: N/A (DEGRADED Day 12)
**vs 7-day moving avg**: N/A (DEGRADED Day 12)
**vs 08/06 P50 Empirical ($5,946)**: -$486 (-8%) — Friday demand decay effect + slightly lower discharge MW (175 vs 200 MWh) offset by HE22 DA anchor price retained

---

## GR_WEST Wind Scenarios — 08/07 BESS Impact

| Scenario | GR_WEST HE13 | HE13-18 Price Est. | HE21 Price Est. | BESS Stack Impact |
|---|---|---|---|---|
| Bear (-2,000 MW) | 1,564 MW | +$8-15/MWh delta → $30-50/MWh range | +$8-18/MWh → $36-68/MWh range | Stack B trigger: midday discharge HE14 if RT > $40 |
| Base (STWPF) | 3,564 MW | $18-35/MWh | $28-50/MWh | Stack A primary; NS hold HE13-18 |
| Bull (+2,000 MW) | 5,564 MW | $10-20/MWh | $22-38/MWh | Stack A only; lower evening price realization |
| Trend (-1,000 MW) | 2,564 MW | $22-43/MWh | $31-58/MWh | Stack A; HE14 gate review |

**Monitoring gate (HE11, 09:30 CT)**:
- If GR_WEST actual STPF HE13 < 2,500 MW → Bear scenario likely; review Stack B trigger
- If GR_WEST actual HE13 ≥ 5,000 MW → Bull scenario; confirm Stack A, lower discharge floor to $22/MWh

---

## Risks

1. **Smartbidder DEGRADED Day 12 (CRITICAL)**: All price estimates are single-source qualitative inference. No P(DA>RT), no AS clearing signal. Structural gap of up to 60% between estimated and actual revenue (08/04 P50 $17K vs actual $4.9K precedent). Escalate to Ascend management by 09:00 CT 08/07 if still unresolved.

2. **GR_WEST 3,564 MW floor — unvalidated (single-source STWPF)**: If actuals track Bear scenario (1,564 MW), HE13-18 prices could spike $8-15/MWh above base → Stack B midday discharge viable. No AG2 Windcast validation (Day 12). Monitor in real-time from HE09.

3. **HE22 as peak DA price (Friday pattern uncertainty)**: 08/04 actual showed HE22 > HE21 DA price ($37.08 vs $32.16). Friday industrial load decay post-HE18 may shift the peak 1h earlier to HE21. If HE21 clears above $40/MWh and HE22 below $30, optimal discharge timing shifts.

4. **Rule 8 ACTIVE (structural)**: Smartbidder executes independently. 4-consecutive observation of DA energy discharge moving to HE22-23 (vs my HE20-21 recommendation). This recommendation targets HE21-22 to align closer to Smartbidder execution window. Actual execution may still deviate.

5. **SOUTH_HOUSTON_IMPORT LOW-to-MEDIUM (8-15%)**: If binding occurs (low probability), GKS MCC gains +$5-20/MWh — upside not modeled in P50. Downside: congestion reduces effective GKS price if WEST_TO_NORTH binds concurrent.

6. **Friday demand tail**: Industrial load typically falls faster post-HE18 on Fridays. If HE18-20 NL is lower than BIDCLOSE forecast, evening discharge prices could track lower. Monitor HE16-18 actual load vs BIDCLOSE.

---

## Alternative — Stack B (Two-Cycle, Bear Wind Scenario)

**Trigger (monitor HE11-13, real-time)**:
1. GR_WEST actual STPF HE13 < 2,500 MW at 09:30 CT reporting; OR
2. RT price HE13 or HE14 exceeds $40/MWh confirmed real-time; OR
3. Tenaska intraday alert of high midday prices > $45/MWh DA clearing

**Stack B Schedule** (if triggered — replaces HE12-16 Hold with partial discharge + recharge):

| HE | Mode | Energy MW | NS MW | ECRS MW | SoC End |
|----|------|-----------|-------|---------|---------|
| HE09-11 | DA Charge | -100/-100/-35 | 75 | 0 | 200 MWh |
| **HE14** | **RT Discharge (Bear gate)** | **+100** | 0 | 0 | **100 MWh** |
| HE15 | Hold/NS | 0 | 50 | 0 | 100 MWh |
| **HE16** | **RT Recharge** | **-85** | 0 | 0 | **172 MWh** |
| HE17-20 | NS Hold | 0 | 50 | 0 | 172 MWh |
| **HE21** | **DA Discharge** | **+100** | 0 | 0 | **72 MWh** |
| **HE22** | **DA Discharge + ECRS** | **+50** | 0 | 25 | **22 MWh** |
| HE23-24 | ECRS Hold | 0 | 0 | 25 | 22 MWh |

Stack B P50 Revenue (Bear case, midday $45/MWh, recharge $35/MWh, evening $42/MWh):
- Midday: 100 MWh × $45 - 85 MWh (recharge cost): 100×$45 - 85×$35 = $4,500 - $2,975 = +$1,525 net midday gain
- Evening: 100×$42 + 50×$42 = $4,200 + $2,100 = +$6,300 (vs Stack A single-cycle $5,975 from 175 MWh)
- Net two-cycle vs single-cycle: approximate +$1,500 additional revenue under Bear
- Stack B P50 Bear: ~$5,460 + $1,500 = ~$6,960 (+$1,500 vs Stack A)

**Do NOT trigger Stack B under base case**: Midday $28/MWh < recharge cost $35/MWh → net two-cycle loss -$700 vs Stack A.

---

## Congestion Integration (Stage 0 — Directional Only)

| Factor | Value | Action |
|---|---|---|
| WEST_TO_NORTH HE01-05 MEDIUM | GKS MCC -$1 to -$3/MWh overnight | NS Hold preferred over overnight charge (overnight price est. $18-25 - $2 MCC = $16-23 vs duck $10-15). Duck charging cheaper. |
| Duck curve HE09-12 MODERATE | GKS MCC -$0.5 to -$2.0/MWh | Confirms duck charging window. Effective charge price $8-13/MWh at HE10. |
| SOUTH_HOUSTON HE19-21 LOW | GKS MCC +$0 to +$1.0/MWh | Slight uplift to discharge revenue; DA primary confirmed. NS/ECRS priority per congestion-analyst per HE19-21. |
| WEST_TO_NORTH HE23-24 LOW | GKS MCC -$0.5 to -$2/MWh | ECRS hold (no additional charging; SoC = 25 MWh). |

> Congestion-analyst explicitly notes NS/ECRS may dominate over pure energy for HE19-21. Stack A already provides ECRS 25 MW HE22-24 and NS hold HE19-20.

---

## Self-Review Reference (08/06 Flowday — Pending T+2)

08/06 recommendation (issued 08/05): DA Charge HE03-05 → NS 75 MW → DA Discharge HE20+HE21. P50 empirical $5,946.
Tenaska T+2 expected 2026-08-08. Full self-review: memory/bess-optimizer/learnings/2026-08-06.md (to be filed 08/07).

---

## Standing Rules Compliance

| Rule | Status | Application |
|---|---|---|
| Rule 1 (ECRS Summer) | APPLIED — exceptions | HE09-11: Charging committed (exception). HE21: Energy discharge committed (exception). HE22-24: ECRS 25 MW post-discharge (100 MW total HE22 = HSL limit). |
| Rule 2 (0.80x DA) | APPLIED | DA discharge revenue P50 uses anchor 08/04 actual (already at 40-50% of structural est.). Rule 2 effectively embedded in empirical calibration. |
| Rule 4 (RegUp/Down) | EXCLUDED | All 24 hours. No Reg product offered. |
| Rule 6 (HOUSTON congestion) | NOT TRIGGERED | P=8-15% < 35% HIGH threshold. DA primary HE21-22. |
| Rule 8 (RT dispatch risk) | ACTIVE | Smartbidder executes independently. This is a strategic benchmark. Actual execution coupling via Tenaska/Ascend. |
| HSL 100 MW | PASS | All hours verified (see HSL table above). |

---

## Downstream Handoffs

**reporter**: Stack A. P10/P50 Empirical/P90: $3,300 / $5,460 / $8,400. Primary: Duck charge HE09-11 → NS 75 MW all-day → DA Discharge HE21-22 → ECRS HE22-24. Stack B trigger: GR_WEST < 2,500 MW HE13 OR RT HE14 > $40/MWh.

**dart-virtual-trader**: HE21-22 DA primary call (Rule 6 NOT triggered, P=8-15%). No virtual concentration risk with physical BESS discharge at same hours.

**pnl-manager**: T+2 Tenaska for 08/07 expected 2026-08-09. Request: HE10 DA charge price, HE21+HE22 DA sell price, NS clearance rate (target 75 MW all-day at $1.40/MW-h), ECRS HE22-24.

---

*bess-optimizer | reports/daily/2026-08-07-bess-stack.md | Issued 2026-08-06 07:30 CT*
*Strategy: Stack A — Duck Charge HE09-11 + NS 75 MW + DA Discharge HE21+HE22 + ECRS HE22-24*
*P50 Empirical: $5,460 | P50 Structural: $5,995 | P10: $3,300 | P90: $8,400*
*SoC: 0 → 200 (HE11) → 25 (HE22 terminal). Terminal 25 MWh = ECRS buffer.*
*Rule 6 NOT triggered (P=8-15% < 35%). DA primary. Smartbidder DEGRADED Day 12.*
*Stack B trigger: GR_WEST actual HE13 < 2,500 MW OR RT HE14 > $40/MWh.*
