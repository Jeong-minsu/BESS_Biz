# Plan: congestion-analyst — W28 Improvements
**Week**: 2026-28 | **Priority**: MAJOR | **Registered by**: evaluator

---

## Issue 1 (MAJOR): W3 Item 0.10 — 60-Day Milestone Passed, Data Still Blocked

**Quantitative basis**:
- Hub/pair LMP 15-min data blocked: 60+ consecutive cycles as of 2026-07-10
- Original W3 item 0.10 deadline: Week 23 (2026-06-11)
- Days past original deadline: 32 calendar days as of Jul 13
- Evaluator escalation history: W23 MAJOR → W24 CRITICAL → W25 MAJOR → W26 MAJOR → W27 CRITICAL → W28 MAJOR (downgraded from CRITICAL because agent acknowledged the 60-day milestone and filed escalation note)

**W28 agent compliance**:
- Jul 10 congestion report explicitly stated: "60-DAY OVERDUE MILESTONE TODAY. Formal escalation note required. See `plans/2026-07-10-w3-item010-escalation.md` (to be filed by end of day)."
- Evaluator notes this plan reference as evidence of acknowledgment. Verify that the file was actually created at `memory/congestion-analyst/plans/2026-07-10-w3-item010-escalation.md`.

**Agent action (by 2026-07-14, W29 Day 1)**:
1. Confirm `memory/congestion-analyst/plans/2026-07-10-w3-item010-escalation.md` exists. If not, create it with:
   - Status of the data access attempt
   - What specifically is blocked (endpoint, file format, permissions)
   - Whether a workaround (e.g., manual download from ERCOT public API) was attempted
   - What user action is needed to unblock
2. In the W29 Jul 14 congestion report, include one sentence in the W3 item 0.10 tracking section: "Escalation note filed 2026-07-10 (confirm path)."

---

## Issue 2 (MONITORING): Stage 0 Binding Calibration Quality

**W28 positive signals**:
- WEST_TO_NORTH HE01-02 MEDIUM-HIGH (40-55%) with explicit threshold: GR_WEST 16,272 MW above 15k threshold (Jul 10). Better-documented than W27.
- HOUSTON_IMPORT HE19-22 LOW-MEDIUM (22-32%) with 6,511 MW cross-source gap noted (Jul 10). More granular than prior weeks.
- Finding 7 (GKS MCC negative HE09-15) tracked and labeled in all 7 W28 days.

**W28 calibration concerns**:
- Approach score remains 2.5 because no post-hoc binding validation is possible without hub-pair LMP data.
- Pattern 16 (simultaneous multi-constraint days → all calls fail) has not been re-tested in W28 (no heat event observed). The 10-15 ppt simultaneous-constraint haircut rule remains documented but unvalidated.

**Agent action (standing)**:
- Continue applying the GR_WEST threshold (15,000 MW) for WEST_TO_NORTH escalation.
- Continue applying the NL trough threshold (25,000 MW) for Finding 7 classification.
- For HOUSTON_IMPORT: document the cross-source gap (MW difference between Yes Energy and Enverus NL forecasts) in every report where this constraint is flagged. This provides historical calibration data even without hub-pair LMP.

---

## Issue 3 (STRUCTURAL — low priority): Stage 0 Methodology Documentation

**Observation**: Stage 0 heuristic rules are documented in-report each day but not in a persistent reference file. If a new agent instance or reviewer reads only the most recent report, the full rule set is not accessible.

**Agent action (by 2026-07-21, end of W29)**:
- Create `memory/congestion-analyst/learnings/stage-0-rules.md` with the complete Stage 0 binding probability rule set as currently applied:
  - HOUSTON_IMPORT threshold(s) and NL conditions
  - WEST_TO_NORTH threshold(s) (GR_WEST MW levels)
  - Finding 7 conditions
  - Pattern 16 multi-constraint haircut rule
  - Weekend/holiday adjustments (Pattern 11 interaction)
- This is a one-time structural artifact that benefits future evaluation and model transition.

---

## Success Metrics for W28 Plan

| Item | Success Criterion | Deadline |
|---|---|---|
| 2026-07-10 escalation plan confirmed | File exists at `plans/2026-07-10-w3-item010-escalation.md` | 2026-07-14 |
| Cross-source gap documented in HOUSTON_IMPORT reports | MW gap included in every HOUSTON_IMPORT flag | Ongoing W29 |
| Stage-0-rules.md created | File at `memory/congestion-analyst/learnings/stage-0-rules.md` | 2026-07-21 |
| Hub-pair LMP data access | External dependency — user action via ERCOT API or Ascend | User-dependent |
