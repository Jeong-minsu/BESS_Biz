# Plan: reporter canonical-paths.md — 11th Consecutive Miss
# Week 2026-41 | Priority: MAJOR | Registered: 2026-10-12

## Issue

`canonical-paths.md` is absent for the 11th consecutive week.
W40 plan (`2026-W40.md`): create file immediately + add Cycle Health section to all W41 reports. PARTIALLY FAILED.

- canonical-paths.md: ABSENT (11th miss)
- Cycle Health section: PRESENT in W41 reports (Oct 8, Oct 11 confirmed) — IMPROVEMENT
- W40 additional item (W40 weekly report not filed): STATUS UNKNOWN — not confirmed filed

## W41 Reporter Evidence

W41 coverage: 3 confirmed daily reports (Oct 6, Oct 8, Oct 11). Oct 7 gap (orchestration-level).
- Oct 6: DEGRADED. All-DEGRADED flag. Self-feedback table present.
- Oct 8: PRODUCTION. Strong cross-agent consistency. Self-feedback from all 4 agents.
- Oct 11: PRODUCTION PARTIAL. Data quality table. Self-feedback from 5 agents including congestion. Cycle Health present.

Improvement noted: Reporter correctly flagged Oct 8 dart-virtual-trader output as filed in wrong directory (WRONG DIR noted). This is meaningful progress on path verification.

Remaining gap: canonical-paths.md file itself still absent; the path verification is in-report rather than in a persistent reference document.

## Required canonical-paths.md Content

Minimum viable content:
1. Canonical report output paths for all 7 agents:
   - market-analyst: `reports/daily/market-briefing/YYYY-MM-DD.md`
   - bess-optimizer: `reports/daily/bess-optimizer/YYYY-MM-DD.md`
   - dart-virtual-trader: `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`
   - congestion-analyst: `reports/daily/congestion/YYYY-MM-DD.md`
   - pnl-manager: `reports/daily/pnl/YYYY-MM-DD.md`
   - reporter: `reports/daily/YYYY-MM-DD.md` (integrated) + `memory/reporter/history/YYYY-MM-DD.md`
   - crr-trader: `reports/daily/crr/YYYY-MM-DD.md`
2. Known wrong-directory variants (for each agent that has had path issues)
3. Weekly report paths for each agent
4. Evaluator report path: `reports/weekly/evaluator/YYYY-WW.md`

## Action Required

### Agent (immediately — before next daily cycle):
1. Create `memory/reporter/canonical-paths.md` with 4-section content above.
2. This is a documentation consolidation task; content is fully known. No external dependency.
3. Continue including path verification in daily reports (positive W41 trend).
4. Verify and flag WRONG DIR instances before they appear in integrated reports.

### Additionally (carry-forward from W40):
5. Confirm whether W40 weekly report was filed. If not, file retroactively.
6. Continue Cycle Health section in all W42 daily reports.

## Success Criteria

W42 evaluation:
- `memory/reporter/canonical-paths.md` EXISTS with 4-section content.
- Cycle Health section present in all W42 reports.
- Zero propagated wrong-directory paths (without [WRONG DIR] flag) in integrated reports.

## References

- W40 plan: `memory/reporter/plans/2026-W40.md`
- W40 W39 plan: `memory/reporter/plans/2026-W39-canonical-paths-ninth-miss.md`
- Oct 11 reporter report: `memory/reporter/history/2026-10-11.md`
