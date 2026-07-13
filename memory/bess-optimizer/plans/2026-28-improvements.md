# Plan: bess-optimizer — W28 Improvements
**Week**: 2026-28 | **Priority**: CRITICAL | **Registered by**: evaluator

---

## Issue 1 (CRITICAL): STRATEGIC BENCHMARK Reclassification Now in Effect

**Trigger**: W27 plan `2026-27-execution-divergence-escalation.md` deadline was 2026-07-13. No user response received. Per the plan's success metric, bess-optimizer is formally reclassified to "STRATEGIC BENCHMARK — NOT OPERATIONALLY COUPLED."

**What this means for the agent**:
- All [EXECUTION-DIVERGENCE] plan series (W23 through W27) are closed as infrastructure-unresolvable.
- The agent continues to produce recommendations as strategic benchmarks — the highest-quality analysis of what the GKS battery *should* do if operated per bess-optimizer's schedule.
- Expected revenue figures in daily reports represent the benchmark achievable under the recommendation. They are explicitly NOT predicted GKS actual revenue (which follows Smartbidder's independent strategy per Pattern 19).
- The Approach axis is scored on methodology quality (currently 3.8*) with the asterisk indicating execution coupling = 0.

**Agent action (by 2026-07-18, end of W29)**:
1. Update daily report header to include: "Status: STRATEGIC BENCHMARK — NOT OPERATIONALLY COUPLED. Expected Revenue = benchmark under recommendation; GKS actual follows Smartbidder 'Mount Blue Sky with Virtuals, RTC Version.'"
2. In learnings, replace [EXECUTION-DIVERGENCE] tags with "Benchmark vs Smartbidder Default" framing — document the delta between recommendation and estimated Smartbidder execution (NS 80 MW flat × 24h + HE14-22 DA sell) to enable apples-to-apples tracking.

---

## Issue 2 (MAJOR): Output Directory Instability Jul 6-7

**W28 observation**: Jul 6 output filed to `reports/daily/bess-stack/2026-07-06.md`. Jul 7 output filed to `reports/daily/bess-schedule/2026-07-07.md`. Both incorrect. Fixed from Jul 8 onward.

**Root cause hypothesis**: Jul 6 was a high-cognitive-load day — new Rules 9 and 10 were formalized in learnings, creating process regression in rote steps (Pattern 21).

**Agent action (permanent)**:
- Add to the *first line* of the daily cycle execution (before any market analysis): "Output file: reports/daily/bess-optimizer/YYYY-MM-DD.md — confirm path."
- This is a one-time structural checklist entry that must survive rule-creation days.

**Success criterion**: 7/7 correct output paths in W29. Any deviation escalates to MAJOR on next evaluation.

---

## Issue 3 (STANDING — MONITORING): AS Playbook Consistently Absent

**Observation**: AS Playbook listed as "ABSENT" in all W28 daily reports (Jul 8, 9, 10, 11, 12). The AS Playbook (from `skills/estimate-bess-energy-as/`) is referenced in bess-optimizer's R&R as an input source. Its persistent absence limits external auditability of AS positioning decisions.

**Context**: bess-optimizer's AS recommendations (NS, RRS, ECRS, RegUp, RegDown) are derived from Rules 1-10 and market-analyst briefings, not from the AS Playbook skill output. The skill output may provide a validation cross-check.

**Agent action (by W29 Day 1)**:
- Investigate whether the AS Playbook skill (`skills/estimate-bess-energy-as/`) is callable in the current environment, or whether its absence is an infrastructure limitation (similar to the Tenaska whitelist issue).
- Document the finding in `memory/bess-optimizer/learnings/2026-07-14.md` under "AS Playbook status."
- If callable: include AS Playbook output in W29 daily reports.
- If not callable: document the constraint and stop listing as "ABSENT" — change to "AS Playbook not available in current environment."

---

## Issue 4 (STANDING — user action required): Smartbidder Recalibration Note

**W27 plan requirement** (from `2026-27-execution-divergence-escalation.md`): "Agent to produce a one-time 'What-If Smartbidder Recalibration' note by 2026-07-10."

**W28 status**: Not observed in W28 outputs. Jul 8-11 were DEGRADED days which may have reduced learnings opportunity. Jul 6-7 were focused on new Rule 9-10 derivation.

**Agent action (by 2026-07-18)**:
- Produce `memory/bess-optimizer/learnings/smartbidder-recalibration-what-if.md`.
- Content: "If bess-optimizer treated NS 80 MW × 24h flat and HE14-22 DA sell as fixed constraints, what would the optimal delta-adjustment look like? Quantify the recommendation delta vs Smartbidder default on the 4 confirmed W28 PRODUCTION days (Jul 6, 7)."
- This is the one-time structural note that closes the W27 agent action item.

---

## Success Metrics for W28 Plan

| Item | Success Criterion | Deadline |
|---|---|---|
| Report header updated (STRATEGIC BENCHMARK) | Appears in W29 Day 1 report | 2026-07-14 |
| Output directory compliance | 7/7 days in bess-optimizer/ in W29 | End of W29 |
| AS Playbook status documented | Learning entry created | 2026-07-14 |
| Smartbidder recalibration note | File created at specified path | 2026-07-18 |
| Execution scope confirmed | User response | User-dependent |
