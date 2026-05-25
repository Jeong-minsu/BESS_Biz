# Plan: Hit Rate and P&L Tracking Infrastructure — 2026-21

**Issue**: dart-virtual-trader cannot compute a confirmed 7-day hit rate because DART virtual P&L is not isolatable from Tenaska DA_Energy_Amt (pnl-manager's known limitation). Hit rate tracking is currently based on directional inference only. The agent is operating without quantitative feedback on its primary performance metric.

**Priority**: MAJOR

## Actions

- Short-term: use Smartbidder DART virtual benchmark P&L (available from pnl-manager output when PRODUCTION data is present) as the best-available proxy for hit rate. Log each cycle's Smartbidder DART virtual P&L in `memory/dart-virtual-trader/history/` against the corresponding position book.
- Per-cycle tracking format: for each flow date with production Tenaska data, log: (a) positions issued, (b) Smartbidder DART virtual benchmark P&L for that date, (c) directional inference hits/misses from Tenaska hourly data, (d) provisional hit rate.
- When Tenaska virtual isolation is resolved (per pnl-manager plan), migrate to confirmed per-hour hit rate.
- Maintain a rolling 7-day hit rate field in `memory/dart-virtual-trader/history/` even if populated by proxy data, so evaluator can score it weekly.
- Target: 55% confirmed hit rate over any 7-day window as the minimum threshold per evaluator's scoring criteria.
