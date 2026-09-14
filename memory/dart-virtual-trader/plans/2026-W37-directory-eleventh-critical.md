# Improvement Plan — 2026-W37 — Directory Compliance (11th Consecutive Week — NEW VARIANT REGRESSION)
**Agent**: dart-virtual-trader
**Priority**: CRITICAL
**Issue**: W37 produced 1/7 correct directory (dart-virtual-trader/ Sep 9 only). 4 files in dart/ (Sep 7, 8, 10, 13) and 2 files in a brand-new dart-virtual/ directory (Sep 11, 12) — a third distinct wrong-dir variant that appeared for the first time in W37. 11 consecutive weeks of non-compliance. Total wrong-dir variants now observed: dart/, dart-position/, dart-virtual/ (new), plus the correct dart-virtual-trader/.
**Root Cause**: Agent does not read or reliably apply the canonical output path at session start. High-cognitive-load cycles (rule changes, new trigger conditions) displace the mechanical path-verification step (Pattern 21). The dart-virtual/ variant in W37 is a regression — the agent is generating NEW wrong directories, not converging toward the correct one. 11 weeks of plans have not resolved this without a structural hard-code in the agent definition.
**Required Action**:
1. AGENT IMMEDIATE: Every session, first step before any analysis is `echo "reports/daily/dart-virtual-trader/YYYY-MM-DD.md"` as a path anchor. File must be saved to `reports/daily/dart-virtual-trader/` exclusively.
2. USER REQUIRED (AUTHORIZATION): Hard-code the canonical path `reports/daily/dart-virtual-trader/YYYY-MM-DD.md` in `.claude/agents/dart-virtual-trader.md` — specifically in Section 4 Process Step 7 as an explicit absolute path requirement. 11 weeks without this change confirms the agent cannot self-correct. This is a 1-line agent definition edit that would permanently resolve a 11-week Critical.
3. USER REQUIRED: Decide on consequence for continued non-compliance — W36 consequence clause (reporter exclusion) has not been enforced for 3 consecutive weeks.
4. AGENT IMMEDIATE: T+2 settlement backlog (Sep 3-11, 9 flowdays overdue) must be resolved as soon as Tenaska PTP becomes available. pnl-manager escalation required.
**Success Criterion**: W38 = 7/7 files in dart-virtual-trader/ ONLY. Zero occurrences of dart/, dart-position/, dart-virtual/, or any other variant. T+2 backlog Sep 3-11 resolved.
**Deadline**: 2026-W38 (by 2026-09-20)
**Escalation**: If W38 is also < 7/7, recommend suspending dart-virtual-trader Section 5 from Daily Report until agent definition is hard-coded. This is the same consequence clause triggered at W34 for congestion-analyst. User confirmation required.
