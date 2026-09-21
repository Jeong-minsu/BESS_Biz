# Improvement Plan — 2026-W38 — canonical-paths.md and Cycle Health Section Absent (8th Consecutive Miss)
**Agent**: reporter
**Priority**: MAJOR
**Issue**: `memory/reporter/canonical-paths.md` remains absent. "Cycle Health — Path Verification" section remains absent from all 7 W38 daily reports. W38 = 8th consecutive week both are missing. W37 plan (2026-W37-canonical-paths-seventh-miss.md) recommended agent definition hard-code after 7 misses. W38 = one additional miss beyond that threshold.

**Evidence**: 
- memory/reporter/ contains: history/, learnings/, plans/, template-issues.md. No canonical-paths.md found.
- grep for "Cycle Health", "path verif", "canonical" in W38 daily reports (Sep 14-20) = zero matches.

**Practical impact**: Without the Cycle Health section and canonical-paths.md, the user receives no daily signal about input path compliance. The W38 dart-virtual-trader directory violations (3/7 wrong-dir: dart/ Sep 18, dart-position/ Sep 19-20) and bess-optimizer violations (3/7 wrong-dir: bess-stack/ Sep 18-20) were accepted as valid inputs without user notification. If these were real trading decisions, the reporter's silent acceptance of wrong-path inputs would suppress operational risk visibility.

**What canonical-paths.md should contain**: The canonical expected paths for each agent's daily output (e.g., "dart-virtual-trader: reports/daily/dart-virtual-trader/YYYY-MM-DD.md"), the list of known wrong-dir variants for each agent, and the logic for the Cycle Health check (verify file exists at canonical path; if found at wrong path, flag WARN; if missing entirely, flag MISSING).

**Root Cause**: The Cycle Health section adds reporting overhead to each daily cycle. The reporter is doing its core aggregation work well (7/7 dir, 7/7 coverage) but the cross-agent path-verification duty is consistently omitted. Without canonical-paths.md to reference, the path verification cannot be formalized.

**Required Action**:
1. AGENT IMMEDIATE (EXECUTABLE NOW): Create `memory/reporter/canonical-paths.md` in the NEXT session. Content: table of agent name, canonical output path, known wrong-dir variants, and current compliance status as of most recent week. This is a reference document that can be read at session start to enable the Cycle Health check.
2. AGENT IMMEDIATE: Add a "Cycle Health — Path Verification" section to every daily report. This section should be brief (one table, 7 rows — one per agent) with columns: Agent, Expected Path, File Found At, Status (PASS/WARN/MISSING). Checking this takes 5-10 minutes per cycle.
3. USER OPTIONAL (strongly recommended after 8 misses): Add to `.claude/agents/reporter.md` Section 4 Process: "Step 1: Read memory/reporter/canonical-paths.md. Step 2: Verify each agent's output at canonical path. Step 3: Add Cycle Health section to report." This makes path verification a mandatory first step, not an optional post-step.

**Success Criterion**: As of W39: (a) `memory/reporter/canonical-paths.md` exists; (b) "Cycle Health — Path Verification" section appears in all 7 W39 daily reports with PASS/WARN/MISSING status for each agent.

**Deadline**: IMMEDIATE — canonical-paths.md should be created in the 2026-09-21 reporting cycle.
