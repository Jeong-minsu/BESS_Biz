# Plan: Self-Review Learnings Gap (Aug 6–7) — Cross-Agent Pattern

Week: 2026-W32
Priority: Major
Issue: All four front/middle agents (market-analyst, bess-optimizer, dart-virtual-trader, congestion-analyst) did not file learnings for 2026-08-06 or 2026-08-07. The Aug 7 daily report cited 2-day-old learnings (2026-08-05). Self-review is mandatory per CLAUDE.md Section 4 for all Front/Middle agents every operational day.
Action: Each front/middle agent must file a learnings file for every day the daily output cycle ran. The learnings file must be dated by production date (the day of writing). If Tenaska settlement data is DEGRADED, the learnings file must still be filed and explicitly state "Tenaska DEGRADED — quantitative delta unavailable" along with qualitative learnings from the day's analytical decisions and any pattern observations.
  - This plan is filed in market-analyst but applies equally to bess-optimizer, dart-virtual-trader, and congestion-analyst.
  - Systemic cause: On Aug 6 and Aug 7, the daily cycle ran (output files exist in correct directories) but the self-review step was skipped. This suggests the learnings step is treated as optional when Tenaska data is unavailable, which is incorrect.
Success criteria: All four front/middle agents file learnings on every day a main output is produced during W33 (Aug 10-16). Zero missing learnings files for operational days. DEGRADED-condition learnings are explicitly allowed and expected.
Owner: market-analyst (primary); applies cross-agent to bess-optimizer, dart-virtual-trader, congestion-analyst

## Missing Learnings (W32)

| Agent | 2026-08-06 | 2026-08-07 |
|---|---|---|
| market-analyst | ABSENT | ABSENT |
| bess-optimizer | ABSENT | ABSENT |
| dart-virtual-trader | ABSENT | ABSENT |
| congestion-analyst | ABSENT | ABSENT |

Note: Aug 8 learnings were retroactively filed (as post-hoc revisions on Aug 9). This retroactive approach is acceptable but not preferred — real-time filing is the standard.
