# Plan: Path Verification Section — Fourth Consecutive Critical Miss

Week: 2026-34
Priority: CRITICAL (4th consecutive miss; escalated from Major in W33)
Issue: The W33 plan (`2026-33-path-verification-critical.md`) required implementing a formal "Cycle Health — Path Verification" section in all 7 W34 daily reports. This was not implemented.

## Evidence of Non-Compliance

1. No "Cycle Health — Path Verification" section found in any W34 daily report examined (Aug 18, Aug 20, Aug 22 reviewed).
2. Aug 20 daily report footer cites `dart/2026-08-20.md` (wrong directory for dart-virtual-trader) without flagging it.
3. Aug 22 daily report body cites `bess-stack/2026-08-22.md` for bess-optimizer without flagging it as a misfiled output.
4. Reporter is actively propagating wrong paths to downstream readers with no correction signal.

## Miss History

| Week | Status |
|---|---|
| W31 | MINOR — first identified |
| W32 | MAJOR — escalated (3rd miss) |
| W33 | CRITICAL — escalated |
| W34 | CRITICAL — 4th consecutive miss |

## Also Noted: Aug 17 Report Missing

The Aug 17 (Monday, W34 Day 1) daily report was not produced. This is the second Monday gap observed in recent weeks. If the Daily Report cycle cannot reliably start on Mondays, a root cause should be identified and documented.

## Required Implementation for W35

Every W35 daily report must include a new section (add after current Section 8 Data Quality):

```
## Cycle Health — Path Verification

| Agent | Expected Path | Actual Path Found | Status |
|---|---|---|---|
| market-analyst | reports/daily/market-briefing/YYYY-MM-DD.md | [actual] | [OK / WRONG DIR] |
| congestion-analyst | reports/daily/congestion/YYYY-MM-DD.md | [actual] | [OK / WRONG DIR] |
| bess-optimizer | reports/daily/bess-optimizer/YYYY-MM-DD.md | [actual] | [OK / WRONG DIR] |
| dart-virtual-trader | reports/daily/dart-virtual-trader/YYYY-MM-DD.md | [actual] | [OK / WRONG DIR] |
| pnl-manager | reports/daily/pnl/YYYY-MM-DD.md | [actual] | [OK / WRONG DIR] |
```

If any row shows [WRONG DIR], the section header changes to [PATH INTEGRITY ALERT] and the specific wrong path is called out explicitly.

## W35 Action Items

1. Implement path verification section in all 7 W35 daily reports.
2. Flag any wrong-directory output with [WRONG DIR] label — do not silently accept misfiled content.
3. Investigate Aug 17 Monday gap and document root cause.

Success criteria: All 7 W35 daily reports include the path verification section. Zero wrong paths cited without [WRONG DIR] flag.
Deadline: W35 evaluation (2026-08-31).
Owner: reporter.
