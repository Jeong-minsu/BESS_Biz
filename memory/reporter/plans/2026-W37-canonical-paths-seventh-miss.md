# Improvement Plan — 2026-W37 — canonical-paths.md and Cycle Health Section Absent (7th Week)
**Agent**: reporter
**Priority**: MAJOR
**Issue**: Two structural memory/format items remain absent for the 7th consecutive week: (1) `memory/reporter/canonical-paths.md` — the reference file listing all 8 agents' canonical output paths for cross-check during daily aggregation; (2) "Cycle Health — Path Verification" section in daily reports — the section that would surface directory compliance issues to the user daily. Both items were raised as Major findings in W31 and have not been created.
**Root Cause**: Reporter achieves 7/7 directory compliance for its own output (`reports/daily/YYYY-MM-DD.md`) and 7/7 history coverage in W37, suggesting strong process adherence on core duties. The canonical-paths.md and Cycle Health section are secondary structural requirements that have been deprioritized. Pattern 9: self-identified but not implemented. The absence of Cycle Health section specifically means directory failures by other agents (dart-virtual-trader 11 consecutive weeks, bess-optimizer bess-stack/ regression) are NOT being surfaced in the daily user-facing report.
**Required Action**:
1. AGENT IMMEDIATE: Create `memory/reporter/canonical-paths.md` at next session start (2026-09-14). Content must list each agent's canonical output path, confirm it against the agent definition, and note W37 compliance status as a baseline.
   Required entries:
   - market-analyst: reports/daily/market-briefing/YYYY-MM-DD.md
   - bess-optimizer: reports/daily/bess-optimizer/YYYY-MM-DD.md (NOT bess-stack/)
   - dart-virtual-trader: reports/daily/dart-virtual-trader/YYYY-MM-DD.md (NOT dart/, dart-position/, dart-virtual/)
   - crr-trader: reports/daily/crr/YYYY-MM-DD.md (inactive)
   - congestion-analyst: reports/daily/congestion/YYYY-MM-DD.md
   - pnl-manager: reports/daily/pnl/YYYY-MM-DD.md
   - reporter self: reports/daily/YYYY-MM-DD.md
2. AGENT IMMEDIATE: Add "Cycle Health — Path Verification" section to every daily report starting W38 day 1 (2026-09-14). Format: one-line per agent showing expected path vs actual path found, PASS/FAIL flag.
3. EVALUATOR NOTE: This is a user-facing transparency issue. Without Cycle Health section, dart-virtual-trader's 11-week directory failure is invisible in the daily report unless the user reads evaluator weekly output.
**Success Criterion**: `memory/reporter/canonical-paths.md` exists by 2026-09-14. Cycle Health section appears in all 7 W38 daily reports (Sep 14–20). Each Cycle Health entry shows actual path checked.
**Deadline**: 2026-W38 (by 2026-09-20)
**Escalation**: W38 still absent (8th week) → user-authorized hard-code of Cycle Health section in `.claude/agents/reporter.md` output format.
