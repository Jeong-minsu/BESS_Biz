# Plan: market-analyst Improvement — Week 2026-W23

**Filed by**: evaluator | **Date**: 2026-06-08 | **Priority**: MAJOR

---

## Issue 1 (MAJOR): Weekend Evening RT Direction — Systematic Failure 3 Consecutive Weekends

**Evidence**: `memory/market-analyst/learnings/2026-06-07.md`. Three consecutive weekend evenings (Fri 2026-06-05, Sat 2026-06-06, Sun 2026-06-07) where actual RT exceeded DA at HE18-22 by $15-30+/MWh, while Smartbidder P(DA>RT) predicted the opposite direction. For 2026-06-07 specifically: RT 24h mean underforecast by $11/MWh (51%); evening hours by $30/MWh. The agent identified this pattern and wrote the corrective rule ("when prior-Saturday RT exceeded DA by >$15/MWh at HE18-22, treat Sunday HE18-22 as P(RT>DA) base case") but did NOT apply it in the very next Sunday briefing. This is the same pattern identified in W22: rule written but not internalized into base-case language.

**Root cause**: The corrective rule was documented in learnings but the checklist at Step 3 (price view) was not updated to trigger it. The agent identified the failure mode itself: "rule was written but not internalized into base-case language."

**Required actions (agent to implement)**:

1. **Weekend RT regime checklist item**: Add an explicit checklist item that runs at the START of price-view generation on Saturday and Sunday briefings: "Check prior-weekend RT actuals. If Saturday RT exceeded DA by >$15/MWh at HE18-22 → set Sunday P(RT>DA) as BASE CASE. If Friday RT exceeded DA by >$15/MWh → flag Saturday as 'RT-regime uncertain.'" This must be a triggering step before consulting Smartbidder P(DA>RT).

2. **Smartbidder P(DA>RT) weekend override language**: In any weekend evening (Sat/Sun HE17-23) briefing where the prior-day RT>DA pattern applies: write "Smartbidder P(DA>RT) = X% — reference only; historically wrong on weekend evenings in scarcity conditions. Prior actuals suggest P(RT>DA) as base case at HE18-22." This framing must appear explicitly in the Price View section.

3. **Quantitative MAE recovery**: Now that Tenaska data is available for 2026-06-04, 2026-06-05, 2026-06-06, compute the RT price MAE for those 3 days. Summarize the MAE log in the next learnings file. The agent specification requires quantitative accuracy tracking — 17+ cycles without confirmed MAE is the single largest gap relative to the stated R&R.

---

## Issue 2 (MAJOR): AG2 Parsing — 3 Consecutive Skips, Tool Chain Gap

**Evidence**: `reports/daily/2026-06-07.md` Section 7 Open Items: "AG2 3연속 미파싱 — jms2527 에스컬레이션 또는 파이프라인 구축." `memory/market-analyst/learnings/2026-06-07.md` confirms AG2 was not parsed for 3 consecutive cycles. This creates a data triangulation gap specifically for wind forecasting (AG2 vs Yes Energy vs Enverus).

**Required action**: This issue requires user-side infrastructure work (AG2 parsing pipeline). The agent's obligation is to document the data gap status clearly in every briefing until resolved, estimate the impact on wind uncertainty (i.e., the AG2 vs Enverus spread that remains unresolved), and escalate to the user via the daily report action items section. The agent has been doing this correctly in W23 briefings — continue and escalate priority level to P1 in the next report.

---

## Issue 3 (MINOR, OPEN FROM W22): ECRS Morning Ramp and Non-Spin Overnight Template Gap

**Evidence**: Cumulative tracker in market-analyst learnings. Non-Spin overnight (HE01-06) was added to some briefings in W23 (confirmed in 2026-06-03 briefing: "Overnight Non-Spin avg $4.12/MWh (HE01-06) — modest but non-trivial"). ECRS morning ramp (HE07-10) remains inconsistently included. Status: PARTIALLY CLOSED — template inclusion is improving but not uniform.

**Required action**: Confirm ECRS morning ramp (HE07-10) is included in every AS section for the next 5 cycles as a mandatory structural line. Mark this issue CLOSED when 5 consecutive briefings contain it. The agent's W23 self-reviews correctly identify this; the gap is implementation consistency.

---

## Success Criteria

- Weekend RT regime checklist item explicitly documented in the next Saturday and Sunday briefing (2026-06-13, 2026-06-14).
- Quantitative RT price MAE computed for 2026-06-04 through 2026-06-06 and included in the 2026-06-09 learnings file.
- ECRS morning ramp included in 5 consecutive AS sections.

---

*Evaluator — 2026-06-08 | Supersedes: 2026-22-as-template-persistent-gap.md (extends to include weekend RT direction systematic failure)*
