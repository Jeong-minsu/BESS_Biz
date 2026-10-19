# dart-virtual-trader Improvement Plan — 2026-W42
**Filed by**: evaluator | **Date**: 2026-10-19 | **Period evaluated**: 2026-10-12 – 2026-10-18

---

## W42 Status Summary

| Axis | Score | Trend |
|---|---|---|
| Process | 2.5/5 | → |
| Approach | 4.0/5 | → |
| Resource | 3.5/5 | → |
| Overall | 3.3/5 | → CRITICAL |

**W42 directory result**: Oct 14 CORRECT, Oct 15 WRONG (`dart/`), Oct 16 CORRECT, Oct 17 CORRECT, Oct 18 CORRECT = 4/5 correct.
**17th consecutive week** with at least one wrong-directory instance.
**Positive**: Advisory-only mode maintained. Block 2 INC offer floor gap self-identified before consequence. Strong multi-position analysis on Oct 16 EXTREME day.

---

## W41 Plan Compliance

| W41 Plan Item | W42 Outcome |
|---|---|
| 7/7 directory compliance | FAILED — 1/5 wrong (Oct 15 → `reports/daily/dart/`) |
| October DEC gate definition with evidence | PARTIAL — DEC HE01-09 overnight positions filed Oct 17 with synoptic wind rationale; no formal standalone gate document created |
| DEGRADED penalty schedule in persistent file | UNVERIFIED this evaluation cycle |

---

## Improvement Items for W43

### Item 1 — CRITICAL: Output Directory Compliance (17th consecutive miss)

**Issue**: Oct 15 cycle produced `reports/daily/dart/2026-10-15.md`. Canonical path is `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`. The session-context hypothesis is now supported: Oct 15 was a DEGRADED single-source session (Yes Energy only); the truncated session context may not have loaded the correct path from memory. Multi-source sessions (Oct 16) produced the correct path.

**Required action on every cycle, regardless of session type**:
1. Before writing ANY output file, read `memory/dart-virtual-trader/plans/improvement-2026-W42.md` (this file).
2. Confirm canonical path: `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`.
3. Write to canonical path FIRST, then draft content.
4. Do NOT use abbreviated variants: `dart/`, `dart-virtual/`, `dart-position/`, `dart-trader/`, `dart-positions/`.
5. If a file is inadvertently written to a wrong path, immediately move it to the canonical path (bash `mv` command) before closing the session.

**Success criterion**: 5/5 correct path in W43. Any single miss triggers immediate escalation to user for consequence clause enforcement.

**User action still required** (open 11 weeks): Authorize 1-line hard-code in `.claude/agents/dart-virtual-trader.md` Process Step 7 specifying `reports/daily/dart-virtual-trader/YYYY-MM-DD.md` as the output path.

---

### Item 2 — CRITICAL carry-forward: Block 2 INC Offer Floor for Extreme Negative NL

**Issue**: Oct 16 flowday Block 2 INC HB_WEST offers (HE09–12) filed at -$15/MWh static floor. If actual DA_WEST clears below -$15/MWh during extreme negative NL (-345 MW observed; possible range -$30 to -$50/MWh on severe duck days), offers miss scheduling entirely — zero P&L even if direction is correct.

**Self-identified in**: `memory/dart-virtual-trader/learnings/2026-10-17.md`, §3.

**Required action**: Add the following rule to `memory/dart-virtual-trader/advisory-only-mode.md` or a new `standing-rules.md` file:

> **Extreme Duck INC Offer Floor Rule**: When filing INC offers at a western hub (HB_WEST, GKS) during EXTREME duck hours (NL < 5,000 MW), use offer floor -$25/MWh (not -$15/MWh). When NL trough forecast < 0 MW (negative net load), use -$50/MWh as outer bound for offer floor.

**T+2 validation**: Oct 18 learnings scheduled T+2 settlement check for Oct 16 Block 2 offers. File result in learnings as calibration data point.

**Success criterion**: Rule documented in a persistent file (not just learnings) before end of W43.

---

### Item 3 — MAJOR carry-forward: DEGRADED Penalty Schedule Formalization

**Issue**: DEGRADED penalty schedule (Day 0: -2 ppt; Day 8: -3 ppt; Day 15+: -5 ppt; Day 22+: -6 ppt) exists only in daily learnings. With Smartbidder permanently terminated, the applicable penalty tier needs to be defined for the permanent-termination scenario.

**Required action**: Add DEGRADED penalty schedule to `memory/dart-virtual-trader/advisory-only-mode.md`. Include a new row for permanent termination: "Smartbidder PERMANENTLY TERMINATED (2026-10): apply -6 ppt floor reduction indefinitely until a validated replacement probability source (Tyba P(DA>RT) calibration) achieves 30+ training cycles."

**Success criterion**: Penalty schedule visible in a persistent file by end of W43.

---

### Item 4 — Recommended: October DEC Gate Formal Document

**Issue**: Oct 17 DEC HE01–09 overnight positions represent the first formal execution of the synoptic overnight DEC gate. The logic (GR_WEST > 15,000 MW sustained overnight, SCI > 0.350, onset_early flag) is present in learnings but not consolidated as a gate document.

**Required action**: Create `memory/dart-virtual-trader/model/gates-october-2026.md` with:
- INC duck gate (NL < threshold): current thresholds, offer price rules, and extreme duck floor rule from Item 2
- DEC overnight west gate (synoptic): SCI threshold (0.350), onset_early flag definition, size rules
- Evening INC/DEC gates: current thresholds for October

**Success criterion**: File exists with at minimum the overnight DEC and extreme duck INC gates documented.
