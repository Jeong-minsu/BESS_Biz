# Plan: AS Timing Correction (ECRS Morning / Non-Spin Overnight) — 2026-21

**Issue**: Two consecutive cycles (2026-05-22 and 2026-05-24) confirmed that the Smartbidder AS forecast places ECRS and Non-Spin peak at HE20-22, while actual clearing is:
- ECRS: HE07-10 (morning ramp)
- Non-Spin: overnight (HE01-06) and midday (HE11-18)

The briefing's AS table faithfully reproduces Smartbidder's incorrect timing, which misleads bess-optimizer's AS positioning. The market-analyst self-review (2026-05-24 file) explicitly identifies this as a structural repeated error.

**Priority**: MAJOR

## Actions

- Add a fixed override note to the briefing AS section: "Structural pattern (2 cycles confirmed): ECRS clearing window = HE07-10 morning ramp; Non-Spin primary clearing = overnight (HE01-06) and midday (HE11-18). Smartbidder AS forecast for HE20-22 is likely to overstate clearing in those hours. Use Smartbidder HE20-22 AS figures as upside scenario only."
- In the briefing template, add a separate "Structural AS windows" row above the Smartbidder AS table, pre-populated with the empirical pattern.
- Continue tracking for a third cycle: if ECRS HE07-10 and Non-Spin overnight/midday clears again on 2026-05-26 settlement, elevate to "confirmed structural rule" and update `shared/config.md`.
- Separately: RT 24h average over-estimation (DA error $3/MWh, RT error $7.61/MWh on 2026-05-24) — add a "Smartbidder RT bias note" to the briefing on days when conditions match a prior overestimate (high solar + weekend or holiday).
