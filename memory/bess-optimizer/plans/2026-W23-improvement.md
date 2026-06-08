# Plan: bess-optimizer Improvement — Week 2026-W23

**Filed by**: evaluator | **Date**: 2026-06-08 | **Priority**: MAJOR (one item requires user action)

---

## Issue 1 (MAJOR, USER ACTION REQUIRED): Involuntary RT Dispatch — Unmodeled Risk, Confirmed $4,520 Impact

**Evidence**: `memory/bess-optimizer/learnings/2026-06-07.md`. On 2026-06-05, GKS experienced large RT charging at HE13-15 at RTSPP $28-44/MWh that was NOT in the recommended schedule. Estimated impact: -$4,520, making the primary driver of the -$5,974 actual-vs-recommended miss. The agent identified three candidate explanations: (a) ERCOT automated demand response dispatch, (b) Smartbidder RT layer override, (c) settlement artifact. This remains unresolved.

This is the most dangerous open item in the bess-optimizer's current state: a hidden P&L risk in every recommendation that may repeat, and whose origin and magnitude cannot be predicted or hedged without knowing the mechanism.

**User action required**: Owner (jms2527) must confirm with Tenaska/Smartbidder what dispatched GKS in RT at HE13-15 on 2026-06-05. Specifically: is the bess-optimizer recommendation advisory-only to the operator, or does it configure the Smartbidder bid submission? Does Smartbidder have a separate RT layer that overrides the DA recommendation? Has GKS been registered for any ERCOT demand response program that could auto-dispatch?

**Agent action**: Until the mechanism is confirmed, add an explicit risk line to every recommendation: "UNRESOLVED RISK: RT dispatch at non-recommended hours has been observed (2026-06-05, estimated -$4,520). This risk is present in every cycle. Base-case revenue estimate does not account for it."

---

## Issue 2 (MAJOR): AS Playbook Missing — 9 Consecutive Cycles of Self-Judgment

**Evidence**: All W23 daily reports (`reports/daily/bess-optimizer/`) note "AS Playbook: NOT AVAILABLE (recommend_as_position.py unavailable — self-judgment applied)" for every cycle. The agent's self-judgment on AS product selection (NonSpin HE12-18 bridge, RRS HE22-24, ECRS selective hours) appears reasonable and is improving, but it is systematically unvalidated against the quantitative playbook output. This has been flagged in every report since at least W22. 9 consecutive cycles without the playbook is a structural process gap.

**User action required**: Install `recommend_as_position.py` or confirm it is deprecated and document the replacement process. If the script is not being maintained, bess-optimizer should document the manual AS selection criteria formally in a standing rules file to make self-judgment traceable and reviewable.

**Agent action**: Create `memory/bess-optimizer/learnings/as-standing-rules.md` documenting the current self-judgment AS rules as a standing reference, so they can be reviewed and improved systematically.

---

## Issue 3 (MINOR): Revenue Model — Apply RTE Correctly in SOC Accounting

**Evidence**: `memory/bess-optimizer/learnings/2026-06-07.md` Improvement 3. The 2026-06-07 plan correctly applies RTE eta (0.9220) in the SOC accounting for partial discharge. This is an improvement on prior cycles that assumed 100 MW = 100 MWh round-trip without efficiency loss. Confirm the RTE = 0.9220 value is the correct GKS-specific efficiency factor (or the ERCOT standard) and document it as a standing model parameter.

---

## W23 Progress Confirmed (No New Plan Needed)

The following W22 improvement items show evidence of implementation in W23:
- RTS > NonSpin HE22-23 rule: applied in 2026-06-02 plan, maintained through W23.
- 0.80x Smartbidder DA calibration haircut: consistently applied in all W23 cycles.
- RT Energy Optionality line ($1,500-$3,000 upside) now standard in all revenue summaries.
- SOC_MIN explicit constraint calculation: implemented starting 2026-06-07 plan.
- ECRS = $0 allocation: maintained as a standing rule (confirmed 4+ consecutive $0 actuals).
- Charge window optimization (midday vs overnight): adapted correctly on 2026-06-07 based on SCI signal.

The model calibration drift plan (2026-22-model-calibration-drift.md) is IN PROGRESS — agent is actively applying learnings. The 3-data-point rule before changing calibration parameters is being followed.

---

## Success Criteria

- Involuntary RT dispatch mechanism confirmed with Tenaska/Smartbidder (user action, target: by 2026-06-15).
- Unresolved RT risk line included in recommendations until mechanism is confirmed.
- AS standing rules document created in memory by 2026-06-11.
- RTE parameter documented as a model constant.

---

*Evaluator — 2026-06-08 | Supplements: 2026-22-model-calibration-drift.md and 2026-22-da-rt-venue-follow-up.md (adds involuntary RT dispatch as new critical open item)*
