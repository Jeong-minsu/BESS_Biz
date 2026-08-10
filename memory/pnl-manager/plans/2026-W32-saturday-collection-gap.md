# Plan: Saturday T+2 Collection Gap — Structural Fix

Week: 2026-W32
Priority: Minor
Issue: `reports/daily/pnl/2026-08-06.md` (Friday Aug 6 flowday) is absent. T+2 settlement for Friday flowday falls on Sunday (Aug 8), but the daily cycle was not running on Saturday (Aug 7) when T+1 data would have been available, nor on Sunday when T+2 would have been confirmed. Result: Friday flowday P&L is systematically uncollected.
Action: Confirm whether pnl-manager should run on Saturday and Sunday independently of the main daily reporting cycle. Recommended approach:
  1. If the user confirms pnl-manager should run 7 days/week: implement a standalone weekend fetch (without requiring the full 07:30 CT daily cycle).
  2. If the user confirms weekend pnl collection is optional: document this policy explicitly in `memory/pnl-manager/data-quality.md`.
  3. Minimum requirement: file a DEGRADED-mode pnl report even on days when T+2 settlement is not yet received, to maintain file continuity.
Success criteria: Either (a) pnl/2026-08-06.md backfilled if data becomes available, or (b) formal policy documented in data-quality.md within W33. No consecutive-week gap in pnl directory.
Owner: pnl-manager (with user policy decision)

## Collection Gap Pattern

Friday flowdays where T+2 collection falls on Sunday (weekend gap):
- 2026-08-06: MISSING (identified this week)
- Check prior Fridays during Saturday-cycle-skip periods for similar gaps.

Related: W30 plan `2026-W30-saturday-coverage.md` identified Saturday coverage as unconfirmed. Now Friday coverage is also flagged as a downstream effect.
