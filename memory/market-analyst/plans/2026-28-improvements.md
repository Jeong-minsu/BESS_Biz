# Plan: market-analyst — W28 Improvements
**Week**: 2026-28 | **Priority**: MINOR | **Registered by**: evaluator

---

## Issue 1 (MINOR): Smartbidder P(DA>RT) False Negative on Jul 7

**Evidence**: Jul 7 briefing listed Smartbidder P(DA>RT) as "N/A (data unavailable)." Same day, dart-virtual-trader confirmed the file was present and used it for position sizing. Reporter cross-agent consistency check flagged the discrepancy: "[FLAG] Smartbidder P(DA>RT) 파일 불일치."

**Root cause (probable)**: Smartbidder CSV returned after 43+ absent cycles on Jul 5. market-analyst's file detection logic for the P(DA>RT) section may check a different path or use a cached "absent" state that was not reset after the return. dart-virtual-trader reads the CSV directly; market-analyst may be reading from a secondary copy or checking a different filename pattern.

**Agent action (by 2026-07-14, W29 Day 1)**:
1. Identify the exact file path and filename pattern used to detect the Smartbidder P(DA>RT) CSV in market-analyst briefings.
2. Verify it matches the path used by dart-virtual-trader (which confirmed access on Jul 7).
3. Add a daily verification step: "If P(DA>RT) marked absent, cross-check that `shared/data/raw/smartbidder/` does not contain a current-date CSV before publishing."
4. If the detection logic cannot be changed (infrastructure constraint), add a cross-reference note: "P(DA>RT) absent in this source — dart-virtual-trader may have confirmed access via alternate path."

---

## Issue 2 (STANDING — monitoring): AG2 WSI Absence Handling

**W28 observation**: Jul 6 briefing correctly included all 4 sources (Yes Energy, Smartbidder, Enverus, AG2 WSI). Jul 7 correctly noted AG2 absent and used Enverus + Yes Energy as backup. No fabrication of AG2 data observed.

**This is positive compliance**: The W27 plan `2026-27-ag2-smartbidder-fallback.md` requested AG2 CSV parsing and Smartbidder trust rule. Both are now functioning. PARTIALLY CLOSED.

**Remaining gap**: AG2 absence on Jul 7 was noted but the specific reason was not documented (is this a routine pattern on certain days, or a data delivery delay?). If AG2 is systematically absent on Mondays or after weekends, documenting the pattern would enable better source weighting.

**Agent action (ongoing)**:
- When AG2 is absent, note whether the absence appears to follow a day-of-week pattern.
- After 4 consecutive AG2 absences on the same day-of-week, document as a structural pattern in learnings.

---

## Success Metrics for W28 Plan

| Item | Success Criterion | Deadline |
|---|---|---|
| Smartbidder P(DA>RT) detection fix | Briefing matches dart-virtual-trader's confirmed file access | 2026-07-14 (W29 Day 1) |
| AG2 absence pattern tracking | Day-of-week pattern logged if 4 consecutive absences | Ongoing |
| False negative recurrence | Zero recurrences in W29 | End of W29 |
