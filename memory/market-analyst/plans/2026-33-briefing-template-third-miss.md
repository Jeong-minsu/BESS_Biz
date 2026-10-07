# Plan: BRIEFING_TEMPLATE.md — Third Consecutive Deadline Missed

Week: 2026-33
Priority: Major (escalation to Critical if W34 missed)
Issue: `memory/market-analyst/BRIEFING_TEMPLATE.md` remains absent as of 2026-08-17 (W33 evaluation). First required in W31, deadline extended to W32 (second miss), now a third consecutive miss in W33. Content quality of daily briefings is high (7/7 filed, strong domain analysis) — the absence of the template file is a consolidation and process hygiene issue, not a content quality issue.

## Missed Deadline Chain

| Week | Deadline | Status |
|---|---|---|
| W31 | 2026-08-08 (first requested) | MISSED |
| W32 | 2026-08-11 (second request) | MISSED |
| W33 | 2026-08-17 (evaluated today) | STILL ABSENT — 3rd consecutive miss |

## Why This Matters

The template serves as a mandatory session-start read that:
1. Locks in the required 4-section structure for every briefing
2. Prevents ad-hoc format drift across days
3. Provides the peak HE decision rule (AG2 vs Yes Energy disagreement tiebreaker)
4. Embeds the Tenaska actual price anchor protocol

Without the template, format consistency depends on agent memory across sessions — fragile, as demonstrated by structural variation seen in W31 briefings.

## Action

Create `memory/market-analyst/BRIEFING_TEMPLATE.md` immediately — before next daily cycle.

Required sections (all available from existing learnings files and W31-W33 briefings):
1. Mandatory briefing structure: Price Outlook / AS Outlook / Load/Renewable Forecast / Trading Signals — 4 sections, in order, every day
2. Peak HE decision rule: When AG2 and Yes Energy HE forecasts disagree on peak HE identification, use Yes Energy BIDCLOSE as primary; note disagreement explicitly with spread magnitude
3. Tenaska price anchor protocol: When Smartbidder DEGRADED ≥ Day 7, anchor price forecasts to most recent Tenaska actual P&L date (cite date used)
4. Data quality header format: DATA_STATUS line at top of every report with YES_ENERGY / SMARTBIDDER / AG2 / ENVERUS fields

Success criteria: `memory/market-analyst/BRIEFING_TEMPLATE.md` exists and contains all 4 sections above. File must be present and non-empty at W34 evaluation (2026-08-24). 7/7 W34 briefings must reference or be consistent with the template structure.

Escalation: If W34 also missed, evaluator will escalate to Critical and flag for user review. This is the last Major warning.

Owner: market-analyst
Deadline: W34 evaluation (2026-08-24).
