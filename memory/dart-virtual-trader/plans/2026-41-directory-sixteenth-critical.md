# Plan: dart-virtual-trader Output Directory — 16th Consecutive Critical
# Week 2026-41 | Priority: CRITICAL | Registered: 2026-10-12

## Issue

Oct 8, 2026 report filed to `reports/daily/dart-virtual/2026-10-08.md` (WRONG).
Canonical path is `reports/daily/dart-virtual-trader/`.
W41 compliance: 1/4 run-days correct (Oct 6, Oct 9, Oct 11 correct; Oct 8 wrong).
Cumulative miss streak: 16 consecutive weeks with at least one wrong-directory instance.

Prior W40 plan: `2026-W40.md` — compliance target was 7/7 in W41.
W41 result: FAILED (Oct 8 wrong; Oct 7/Oct 10 gaps also reduce effective coverage).

## Pattern Diagnosis

- Oct 6 (Tue) and Oct 9 (Fri) and Oct 11 (Sun): `dart-virtual-trader/` CORRECT
- Oct 8 (Thu): `dart-virtual/` WRONG — 3rd or 4th recurrence of this specific variant
- No clear session-type correlation remains; Thursday LIVE-data sessions also regress
- Wrong-dir rate has decreased (from 0/2, 0/7 in worst weeks to 1/4 wrong now)
- But absolute compliance (7/7) has never been achieved; the 1/4 wrong instance is unacceptable for an agent-executable task

## Consequence Clause Status

- Suspension consequence clause: triggered W36, unenforced W36–W41 (6 consecutive non-enforcement cycles)
- User authorization for agent-definition hard-code: requested W32, unreceived as of W41
- Evaluator recommendation (unchanged since W38): suspend DART virtual section from Daily Report until 7/7 achieved or agent definition is hard-coded
- This is now the 16th consecutive Critical on this item

## Action Required

### Agent (next cycle):
1. Read this plan at session start. Verify current working directory.
2. Confirm canonical path: `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`.
3. Write to correct path FIRST before drafting any content.
4. Do NOT create abbreviated directories (`dart-virtual/`, `dart/`, `dart-position/`, `dart-trader/`).
5. If any session produces a file in the wrong directory, immediately move it to the correct path.

### User:
- **Decision required (open 10 weeks)**: Authorize agent definition hard-code that embeds the canonical path as a non-overridable instruction.
- **Decision required (open 6 weeks)**: Confirm or override consequence clause (suspend DART section until compliance).
- Without user authorization, the evaluator registers this as escalated to FINAL NOTICE level. Next occurrence will be flagged as process failure requiring operational review.

## Success Criteria

W42 evaluation: zero wrong-directory instances on all run days. If any run day in W42 files to wrong directory, consequence clause takes effect immediately (reporter exclusion pending user authorization).

## References

- W40 plan: `memory/dart-virtual-trader/plans/2026-W40.md`
- W39 plan: `memory/dart-virtual-trader/plans/2026-W39-directory-thirteenth-suspension-final.md`
- Canonical path defined in: `.claude/agents/dart-virtual-trader.md`
