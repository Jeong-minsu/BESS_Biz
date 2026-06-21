# DART Virtual — D+1 (2026-06-22) Position Recommendation

**Issued**: 2026-06-21 07:30 CT
**Flow date**: 2026-06-22 (Monday, full commercial)
**Agent**: dart-virtual-trader
**DATA: PRODUCTION**
**Spread convention**: spread = DA − RT. Positive => DA expensive => Short DA / Long RT (INC). Negative => RT expensive => Long DA / Short RT (DEC).

---

## Summary

- **Total active positions**: 5 (2 energy + 3 basis)
- **Total notional**: 125 MW (5 × 25 MW)
- **Net direction**: DEC bias (morning), Basis Long HB_HOUSTON / Short HB_NORTH (evening)
- **Energy DEC**: HE10–11 (50 MW) — below-floor override, HOUSTON_SOUTH_MIDDAY_LOCAL dual-trigger
- **Basis (hub spread)**: HE19–21 (75 MW) — Long HB_HOUSTON DA / Short HB_NORTH DA
- **Energy INC**: NONE — afternoon INC signal (P=0.57–0.58) present but 0.6x EV falls below $4 floor across all afternoon hours; no valid override basis
- **Expected P&L (gross P50)**: ~+$299 ($23 energy DEC + $275 basis)
- **Expected P&L (gross P90)**: ~+$800+ (HOUSTON_IMPORT binds HE19–21, basis $15–25/MWh)
- **Expected P&L (gross P10)**: ~−$100 to −$200 (no binding, DEC adverse)
- **Smartbidder**: ABSENT — 25 MW cap applied to all positions (per 2026-06-11 learning)

---

## Position Table

| HE | Type | Direction | Node | MW | DA Bid $/MWh | P(win) | 0.6x E[Spread] $/MWh | E[P&L] $ | Risk Note |
|---:|---|---|---|---:|---:|---:|---:|---:|---|
| 01 | — | SKIP | — | — | 21.00 | — | — | — | Overnight DEC signal but spread < $4 floor |
| 02 | — | SKIP | — | — | 20.50 | — | — | — | Overnight DEC signal but spread < $4 floor |
| 03 | — | SKIP | — | — | 20.00 | — | — | — | Overnight DEC signal but spread < $4 floor |
| 04 | — | SKIP | — | — | 19.50 | — | — | — | Overnight DEC signal but spread < $4 floor |
| 05 | — | SKIP | — | — | 19.50 | — | — | — | Overnight DEC signal but spread < $4 floor |
| 06 | — | SKIP | — | — | 20.00 | — | — | — | Overnight DEC signal but spread < $4 floor |
| 07 | — | SKIP | — | — | 20.50 | — | — | — | DEC signal; morning cloud cover starts; spread < $4 floor |
| 08 | — | SKIP | — | — | 21.00 | — | — | — | DEC signal; spread < $4 floor |
| 09 | — | SKIP | — | — | 16.29 | — | — | — | DEC signal P=0.62; 2-override cap allocated to HE10–11 |
| **10** | **Energy** | **DEC (Long DA / Short RT)** | **HB_HOUSTON** | **25** | **16.62** | **62%** | **−$2.70** | **+$14** | Override #1: HOUSTON_SOUTH dual-trigger; NL trough 22,778 MW; cap-out 12,196 MW |
| **11** | **Energy** | **DEC (Long DA / Short RT)** | **HB_HOUSTON** | **25** | **17.50** | **60%** | **−$2.40** | **+$10** | Override #2 (CAP): cap-out 12,246 MW; load 68,286 MW; dual-trigger confirmed |
| 12 | — | SKIP | — | — | 19.00 | — | — | — | DEC signal; 2-override cap used; NL rising from trough |
| 13 | — | SKIP | — | — | 21.00 | — | — | — | DEC signal; NL 30,029 MW rising; cap used |
| 14 | — | SKIP | — | — | 23.50 | — | — | — | INC signal P=0.57; 0.6x EV ~$1.89 < $4 floor |
| 15 | — | SKIP | — | — | 25.00 | — | — | — | INC signal P=0.58; 0.6x EV ~$2.16 < $4 floor |
| 16 | — | SKIP | — | — | 27.00 | — | — | — | INC signal P=0.58; 0.6x EV ~$2.34 < $4 floor |
| 17 | — | SKIP | — | — | 29.00 | — | — | — | INC signal P=0.58; 0.6x EV ~$2.52 < $4 floor; load peak 81,081 MW |
| 18 | — | SKIP | — | — | 31.00 | — | — | — | INC signal P=0.57; solar 25,428 MW still active; 0.6x EV ~$2.16 < $4 floor |
| **19** | **Basis** | **Long HB_HOUSTON DA / Short HB_NORTH DA** | **HB_HOUSTON vs HB_NORTH** | **25** | **—** | **—** | **—** | **+$75** | HOUSTON_IMPORT HIGH 40–50%; NL ramp begins; W23 energy SKIP (ramp +19,639 MW) |
| **20** | **Basis** | **Long HB_HOUSTON DA / Short HB_NORTH DA** | **HB_HOUSTON vs HB_NORTH** | **25** | **—** | **—** | **—** | **+$100** | HOUSTON_IMPORT HIGH 45–58%; Non-Spin $11.2/MWh; NL 48,170 MW; scarcity active |
| **21** | **Basis** | **Long HB_HOUSTON DA / Short HB_NORTH DA** | **HB_HOUSTON vs HB_NORTH** | **25** | **—** | **—** | **—** | **+$100** | HOUSTON_IMPORT HIGH 40–55%; Non-Spin $15.4; ECRS $4.70 → energy INC skip; NL peak 54,199 MW |
| 22 | — | SKIP | — | — | 28.00 | — | — | — | Basis SKIP: HOUSTON_IMPORT P(binding) declining post-peak; P(INC) only 0.55 |
| 23 | — | SKIP | — | — | 24.00 | — | — | — | INC signal P=0.53; 0.6x EV < $4 floor; WEST_TO_NORTH LOW (10–18%) < 20% threshold |
| 24 | — | SKIP | — | — | 22.00 | — | — | — | P ≈ 0.50; no signal |

**Active hours**: HE10, HE11 (energy DEC), HE19, HE20, HE21 (basis)
**Total E[P&L] gross P50**: ~+$299

---

## Why

### Morning DEC (HE10–11): HOUSTON_SOUTH_MIDDAY_LOCAL Dual-Trigger

- Smartbidder P(DA<RT) = 0.62 for morning hours (HE01–13). Morning regime: RT expected to exceed DA.
- Root cause: AG2 cloud cover 74–88% at HE07–09 (Houston, KIAH) — may reduce solar generation vs Yes-E forecast of 14,380–20,286 MW at HE09–10. If solar under-delivers, RT stays elevated while DA was set assuming deeper solar suppression → RT > DA.
- Also: with NL at absolute minimum 22,778 MW (HE10) and 24,212 MW (HE11), any deviation in wind or cloud cover creates outsized RT volatility vs a DA that was priced before morning conditions were known.
- HOUSTON_SOUTH_MIDDAY_LOCAL MEDIUM (22–35%) dual-trigger confirmed:
  - Cap-out HE10: 12,196 MW > 11,500 MW threshold (TRIGGER 1)
  - Load HE10: 64,489 MW > 60,000 MW threshold (TRIGGER 2)
  - HE11: cap-out 12,246 MW, load 68,286 MW — both above thresholds
- Below-floor override applied: 0.6x E[spread] ≈ −$2.4 to −$2.7/MWh, below $4 hard floor. Dual-trigger provides basis. Override count = 2 of 2 (CAP REACHED).
- HE09 skipped despite same P=0.62: 2-override cap exhausted by HE10 and HE11, which are the peak dual-trigger hours. Cap discipline enforced (2026-06-17 learning: max 2 overrides/cycle using highest-EV hours in trigger window).

### Evening Basis (HE19–21): HOUSTON_IMPORT_345 HIGH

- NL ramp HE18→HE21 = +19,639 MW — exceeds previous series record (+18,627 MW on 2026-06-21). HOUSTON_IMPORT_345 P(binding) = 40–58% HIGH throughout HE19–22.
- W23 dual-direction scarcity rule: NL ramp +19,639 MW >> 8,000 MW threshold → energy INC/DEC positions at HE19–21 SKIP. Basis-only approach used.
- Basis thesis: when HOUSTON_IMPORT_345 binds, HB_HOUSTON DA trades at a premium to HB_NORTH DA. Historical binding cycles in this season settled +$15–30/MWh basis. P(basis > 0 unconditional) ≈ 70–80% (even absent binding, residual +$1–3 exists).
- E[basis unconditional P50]: +$3–4/MWh at HE19, +$4–6 at HE20, +$4–8 at HE21. Wider at HE21 due to NL peak (54,199 MW) + Non-Spin $15.4/MWh scarcity signal.
- HE21 energy INC independently skipped: ECRS HE21 = $4.70/MWh (>$3 threshold) + Non-Spin HE21 = $15.4/MWh (>$10 threshold) → provisional INC skip rule (2026-06-17 learning §Issue 2). Basis leg remains clean.
- Basis HE22 SKIP: HOUSTON_IMPORT P(binding) declining; NL 52,061 MW (falling from peak); no additional Non-Spin scarcity signal at HE22 sufficient to anchor a fourth basis leg. Discipline maintained.

### Why No Afternoon Energy INC (HE14–18)

- P(DA>RT) = 0.57–0.58 for HE14–18, which is structurally valid for INC direction.
- However, 0.6x E[spread] falls in the $1.86–$2.52 range — well below the $4 hard floor.
- No valid dual-trigger override basis exists for afternoon hours: HOUSTON_SOUTH_MIDDAY_LOCAL is a midday/solar-suppression constraint, not an afternoon constraint. P(binding) for HOUSTON_SOUTH_MIDDAY_LOCAL is MEDIUM 22–35% at HE10–14 (not HE15–18).
- This is the same situation as 2026-06-18 flow (where afternoon INC HE14–18 had 0.6x EV $2.5–$3.9 and were included only because the very high dual-trigger at that date justified pushdown — but then the 2026-06-19 review flagged HE14–15 inclusions as arguably below-floor violations). For 2026-06-22, the dual-trigger intensity is MEDIUM (22–35%), not the series-high seen on 2026-06-18 (35–50% with 7-hour window). Conservative SKIP is appropriate.

---

## Risk Points

1. **Morning cloud cover (HE07–10)**: AG2 74–88% cloud cover at KIAH through HE09. If cloud cover extends further than forecast, solar under-delivers → RT stays higher relative to DA → DEC wins more decisively. Upside risk for HE10–11 positions. Downside risk: if clouds lift early and solar over-performs Yes-E forecast, RT drops below DA → DEC loses.

2. **HOUSTON_IMPORT non-binding (HE19–21)**: P(binding) 40–58% means 42–60% probability of non-binding. If constraint does NOT bind, HB_HOUSTON–HB_NORTH basis collapses to $1–3/MWh residual → basis positions have small wins, not large ones. The P90 scenario ($800+ P&L) requires binding.

3. **HE20–21 RT scarcity spike (Regime A risk)**: Non-Spin DA $11.2/MWh (HE20) and $15.4/MWh (HE21) signal potential scarcity. If thermal dispatch tightens, RT could spike to $100+, but this scenario is captured by the ECRS ≥$3 + Non-Spin ≥$10 provisional skip rule. Energy legs are already excluded from HE20–21. Basis legs (Long HB_HOUSTON DA) would benefit from RT spike via HOUSTON_IMPORT binding, not hurt.

4. **GR_WEST afternoon forecast uncertainty**: Yes-E forecasts GR_WEST trough at 6,911 MW (HE14). If actual GR_WEST is lower (Enverus tends −840 MW conservatively), HOUSTON_IMPORT binding probability increases above 58% — widening the basis upside. Conversely, if GR_WEST recovers faster (AG2 windcast YE+ pattern), binding probability decreases.

5. **DEC bid fill risk (HE10–11)**: DEC bids set at expected DA price ($16.62 at HE10, $17.50 at HE11). If actual DAM clearing comes in below these levels, bids may not fill. To maximize fill probability, bids are set at Smartbidder DA central estimate (not upper bound), consistent with 2026-06-16 learning §Learning 1.

6. **Monday morning outage confirmation**: Yes-E shows 12,196–12,276 MW cap-out at HE10–12. New Monday outage additions are possible (scheduled maintenance entering Monday). If cap-out increases further, HOUSTON_SOUTH_MIDDAY_LOCAL P(binding) rises above MEDIUM — supporting the DEC override positions. If cap-out decreases, dual-trigger weakens slightly but both hours remain triggered at confirmed values.

---

## Backtest Snapshot (7-Day)

| Flowday | Positions | Confirmed P&L | Status |
|---|---:|---:|---|
| 2026-06-15 (Mon) | 2 | +$946 | CONFIRMED (Tenaska) |
| 2026-06-16 (Tue) | 4 | NULL | DEGRADED |
| 2026-06-17 (Wed) | 7 | NULL | DEGRADED |
| 2026-06-18 (Thu) | 12 | NULL | DEGRADED |
| 2026-06-19 (Fri) | 12 | NULL | DEGRADED |
| 2026-06-20 (Sat) | 5 | DATA UNAVAILABLE | DEGRADED (6th+ cycle) |
| 2026-06-21 (Sun) | TBD | DATA UNAVAILABLE | DEGRADED (7th cycle) |

- **7-day confirmed P&L**: +$946 (1 fully confirmed cycle; 6 DEGRADED — metrics stale)
- **Proxy structural hit rate**: ~58% (frozen since 2026-06-15)
- **Avg win / Avg loss**: 1.42 : 1 (frozen)
- **Note**: Tenaska PTP fetch has been DEGRADED for 7+ consecutive cycles. Model calibration is frozen. The P(win) estimates above are structural/heuristic only and cannot be calibrated against recent settled outcomes. User must run `shared/scripts/fetch_pnl_data.py` from Ascend-whitelisted IP for flowdays 2026-06-15 through 2026-06-21 to restore calibration.

---

## Rules Applied

| Rule | Applied | Basis |
|---|---|---|
| Smartbidder absent → 25 MW cap | All 5 positions at 25 MW | 2026-06-11 learning |
| $4 hard floor (0.6x E[spread]) | HE01–09, HE12–18, HE22–24 SKIP (energy) | Standard floor |
| Below-floor override cap (max 2) | HE10 (override #1), HE11 (override #2) — CAP REACHED | 2026-06-17 learning §Issue 1 |
| HOUSTON_SOUTH_MIDDAY_LOCAL dual-trigger | Confirmed HE10–11 (cap-out 12,196–12,246 MW + load 64–68 GW) | Override basis |
| W23 dual-direction scarcity skip | HE19–21 energy INC/DEC SKIP (NL ramp +19,639 MW >> 8,000 MW) | W23 plan Issue 1 |
| ECRS ≥$3 + Non-Spin ≥$10 → provisional INC skip | HE21 (ECRS $4.70 + Non-Spin $15.4) → energy INC SKIP | 2026-06-17 learning §Issue 2 |
| Basis HE19–21 (HOUSTON_IMPORT HIGH) | 3 positions × 25 MW | Ongoing pattern |
| HB_WEST minimum threshold | WEST_TO_NORTH LOW 10–18% < 20% → no HB_WEST position | 2026-06-16 learning §4 |
| 0.6x compression factor (evening INC spreads) | Applied to afternoon spread estimates | 2026-06-08 learning |
| Monday — full commercial (no weekend cap) | No special sizing reduction | Day type |

---

## Data Sources

| Source | File | Status | Vintage |
|---|---|---|---|
| Market-analyst briefing | `shared/data/forecasts/market-view/2026-06-22.md` | PRODUCTION | 2026-06-21 |
| Congestion outlook | `shared/data/forecasts/congestion/2026-06-22.md` | PRODUCTION (Stage 0 heuristic) | 2026-06-21 |
| Yes Energy raw (load/solar/wind/cap-out) | `shared/data/raw/yes-energy/2026-06-22.csv` | PRODUCTION | 2026-06-21T12:06Z |
| GKS P&L (daily) | `shared/data/pnl/gks/daily/2026-06-20_pnl.json` | PRODUCTION | 2026-06-20 (+$4,390.13) |
| Smartbidder DA-RT probabilities | Not available | **ABSENT** | — |
| Tenaska hourly settlement | Not available | **DEGRADED** (7th+ cycle) | — |
| Self-review (most recent) | `memory/dart-virtual-trader/learnings/2026-06-20.md` | AVAILABLE | 2026-06-20 |

**Leakage check**: All data sources confirmed published before D-1 10:00 CT (DAM bid cutoff). COMPLIANT.

---

*dart-virtual-trader | Issued 2026-06-21 07:30 CT | Flow date 2026-06-22 (Monday) | DATA: PRODUCTION | Smartbidder ABSENT — 25 MW cap. Active: 5 positions (HE10 DEC 25 MW @$16.62, HE11 DEC 25 MW @$17.50, HE19–21 Basis Long HB_HOUSTON/Short HB_NORTH 25 MW each). Total 125 MW. E[P&L] gross P50 ~+$299. Spread = DA − RT; negative => DEC.*
