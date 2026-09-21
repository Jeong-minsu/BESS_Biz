# Improvement Plan — 2026-W38 — stage-0-rules.md Absent (9th Consecutive Miss)
**Agent**: congestion-analyst
**Priority**: CRITICAL
**Issue**: `memory/congestion-analyst/stage-0-rules.md` remains absent. W38 = 9th consecutive week this file has not been created. W36 plan registered a suspension clause (suppress congestion section from Daily Report). That clause was not enforced. W37 plan reiterated the suspension clause. Still not enforced. W38 is the 9th miss.

**Evidence**: Only subdirectories exist in memory/congestion-analyst/ root (history/, learnings/, plans/). No stage-0-rules.md or equivalent rules file found.

**What this affects**: Without stage-0-rules.md, heuristic decisions about constraint classification thresholds, MEDIUM/SEVERE/EXTREME boundaries, SCI calculation, and D+2 continuity rules are not persisted across sessions. Each session must reconstruct these rules from scratch or rely on stage-progress.md entries. Over 122 consecutive cycles of hub-pair LMP absence, the accumulated heuristic logic is substantial and should be formally documented. Stage 1 entry will also require these rules to be in place.

**Note**: congestion-analyst is performing well analytically — stage-progress.md is actively maintained (6/7 W38 entries), constraint classification quality appears strong (correct EXTREME duck identification, accurate D+2 SCI continuity chain tracking Sep 11-19). The absence of stage-0-rules.md is purely a documentation/memory-persistence failure, not an analytical failure.

**Root Cause**: Agent documents rules inline in stage-progress.md entries (which is good for traceability) but does not extract them to a formal rules file. The stage-0-rules.md creation is displaced each cycle by analytical work. This is a one-time investment (30-60 minutes to extract from existing stage-progress.md entries) that would close a 9-week Critical.

**Required Action**:
1. AGENT IMMEDIATE (EXECUTABLE NOW, NO USER REQUIRED): Create `memory/congestion-analyst/stage-0-rules.md` in the NEXT session before any congestion analysis begins. Extract rules from stage-progress.md entries and known learned patterns. Minimum content: constraint classification thresholds (NEGLIGIBLE/MILD/MODERATE/SEVERE/EXTREME boundaries for duck curve NL, WEST_TO_NORTH_345 SCI), D+2 continuity trigger criteria (SCI >= 0.350), Saturday/Sunday discount rules (-3 to -7 ppt), single-source CI widening (+8-15 ppt), SOUTH_HOUSTON_IMPORT confirmed binding floor (+17,935 MW Jun 17), PANHANDLE threshold (15,000 MW GR_WEST), HOUSTON_SOUTH dual-trigger (10,000 MW cap-out), hub-pair LMP absent protocol.
2. AGENT IMMEDIATE: At session start, verify `memory/congestion-analyst/stage-0-rules.md` exists. If absent, create it before any analysis.
3. USER DECISION REQUIRED (SUSPENSION CLAUSE): Suspension clause was triggered at W36 (7th miss) and has not been enforced for 3 cycles. Current status: W38 = 9th miss. Evaluator recommends user either (a) confirm implementation of suspension clause (congestion section suppressed from Daily Report until stage-0-rules.md is created), or (b) formally waive the suspension clause with acknowledgment that the congestion section will remain in Daily Reports without this file.

**Success Criterion**: `memory/congestion-analyst/stage-0-rules.md` exists and contains formal rules as of 2026-W39 session start. File should be at least 500 words with formalized threshold table.

**Deadline**: IMMEDIATE — must be created in the 2026-09-21 cycle.
