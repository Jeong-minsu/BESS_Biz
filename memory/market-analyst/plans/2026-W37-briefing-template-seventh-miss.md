# Improvement Plan — 2026-W37 — BRIEFING_TEMPLATE.md Absent (7th Consecutive Week)
**Agent**: market-analyst
**Priority**: CRITICAL
**Issue**: `memory/market-analyst/BRIEFING_TEMPLATE.md` has been absent for 7 consecutive weeks (W31–W37). The agent definition explicitly requires this file as a structural anchor for the 5-6 bullet briefing format. Without it, output format consistency depends entirely on in-session recall.
**Root Cause**: The file was never created despite being referenced in the agent definition. The agent produces correct output (7/7 dir in W37, content quality 4.0/5.0) but the absence of a persisted template means format drift is possible under high-cognitive-load conditions (e.g., DEGRADED data days). Pattern 9: agent self-identifies the gap but does not implement the structural change.
**Required Action**:
1. AGENT IMMEDIATE: Create `memory/market-analyst/BRIEFING_TEMPLATE.md` at next session start. Content must include: (a) canonical 5-6 bullet structure with section headings, (b) duck curve severity thresholds (SEVERE ≤ 25,000 MW NL trough; EXTREME ≤ 22,000 MW), (c) Scarcity Cliff threshold (NL ≥ 60,000 MW), (d) spread sign convention (DA−RT positive = short DA signal), (e) data source priority (Yes Energy PRODUCTION > Smartbidder > heuristic), (f) DEGRADED fallback language template.
2. AGENT IMMEDIATE: Confirm template creation in the W38 Monday learning entry (`memory/market-analyst/learnings/2026-09-14.md`).
3. EVALUATOR NOTE: If W38 check still shows BRIEFING_TEMPLATE.md absent, escalate to user for agent definition hard-code (same precedent as dart-virtual-trader directory path).
**Success Criterion**: `memory/market-analyst/BRIEFING_TEMPLATE.md` exists and is ≥ 200 words by 2026-09-14 (W38 day 1). File persists through all 7 days of W38.
**Deadline**: 2026-W38 (by 2026-09-20)
**Escalation**: W38 still absent → user-authorized hard-code in `.claude/agents/market-analyst.md` Section 4.
