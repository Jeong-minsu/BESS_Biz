# Plan: congestion-analyst stage-0-rules.md — 12th Consecutive Miss
# Week 2026-41 | Priority: MAJOR (elevated from CRITICAL per W40) | Registered: 2026-10-12

## Issue

`stage-0-rules.md` is absent for the 12th consecutive week.
W40 plan (`2026-W40.md`) deadline: create file immediately. FAILED.

The file is agent-executable with no external dependencies.
Content is available in learnings files (confirmed by evaluator since W33).
The only required action is consolidation into a single reference document.

Additionally: W41 reporter Oct 11 daily report explicitly notes "stage-0-rules.md absent 12th consecutive week" in the self-feedback section — indicating congestion-analyst is aware of the miss but still not creating the file.

## W41 Evidence

- Oct 6 analysis: DEGRADED-mode, no congestion output
- Oct 8 analysis: `reports/daily/congestion/2026-10-08.md` — high-quality SEVERE duck analysis; no stage-0-rules.md
- Oct 9 analysis: `reports/daily/congestion/2026-10-09.md` — SEVERE duck day 2; no stage-0-rules.md
- Oct 11 analysis: (inferred from reporter integration; NL 979 MW UNPRECEDENTED) — no stage-0-rules.md
- Memory: `memory/congestion-analyst/plans/stage-progress.md` exists — so the agent CAN write to memory. No excuse for stage-0-rules.md absence.

## New W41 Dimension: UNPRECEDENTED Calibration Gap

Oct 11 NL 979 MW exceeds all defined tiers (EXTREME < 22k MW). The Stage 0 model has:
- MILD > 32k MW
- MODERATE 26–32k MW
- SEVERE 22–27k MW
- EXTREME < 22k MW

NL 979 MW is approximately 22× below the EXTREME threshold. No calibration guidance exists for this regime. The stage-0-rules.md, if created, should include a BEYOND_EXTREME tier (NL < 5k MW) with appropriate notes. This is a new content requirement added in W41.

## Required Content for stage-0-rules.md

Minimum viable content (all already described in learnings files):
1. Duck curve tiers: MILD / MODERATE / SEVERE / EXTREME / BEYOND_EXTREME with MW thresholds
2. SOUTH_HOUSTON_IMPORT P(binding) → bess-optimizer Rule 6 decision matrix
3. WEST_TO_NORTH wind haircut rule (GR_WEST > 15k MW)
4. HOUSTON_SOUTH_MIDDAY binding criteria
5. High-outage amplifier (≥ 15k MW outage → +10 ppt binding probability)
6. BEYOND_EXTREME tier: NL < 5k MW → Hub-to-hub spread inversion possible; P(binding) caps may not apply
7. Confidence interval reporting convention

## Action Required

### Agent (immediately — before next daily cycle):
1. Create `memory/congestion-analyst/stage-0-rules.md` (root of memory directory, not in plans/).
2. Copy content from `memory/congestion-analyst/learnings/` consolidating the 7 items above.
3. Add BEYOND_EXTREME tier based on Oct 11 observation.
4. This task requires approximately 30 minutes of agent execution time. There is no blocker.

### User:
- No action required for file creation.
- Suspension consequence clause (triggered W36, unenforced 6 cycles) remains pending user confirmation.
- If W42 also misses, evaluator will recommend suppressing congestion section from Daily Report pending user authorization.

## Success Criteria

W42 evaluation: `memory/congestion-analyst/stage-0-rules.md` exists and contains minimum 7-item content. Includes BEYOND_EXTREME tier.

## References

- W40 plan: `memory/congestion-analyst/plans/2026-W40.md`
- stage-progress.md: `memory/congestion-analyst/plans/stage-progress.md`
- Oct 11 reporter note: `memory/reporter/history/2026-10-11.md` (self-feedback section)
