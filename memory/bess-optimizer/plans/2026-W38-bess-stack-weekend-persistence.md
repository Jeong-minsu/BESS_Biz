# Improvement Plan — 2026-W38 — bess-stack/ Directory Persistence (Weekend/DEGRADED Days)
**Agent**: bess-optimizer
**Priority**: MAJOR
**Issue**: W38 produced 4/7 correct directory (bess-optimizer/ Sep 14, 15, 16, 17 only). Sep 18, 19, 20 filed in bess-stack/ (3 wrong-dir files). This is the same 4/7 compliance as W37 — no improvement. The bess-stack/ wrong-dir pattern correlates with weekend days (Sep 18=Fri, 19=Sat, 20=Sun) and DEGRADED data conditions.

**W38 Compliance Breakdown**:
- bess-optimizer/ (CORRECT): Sep 14 (Mon), 15 (Tue), 16 (Wed), 17 (Thu) = 4/7
- bess-stack/ (WRONG): Sep 18 (Fri), 19 (Sat), 20 (Sun) = 3/7
- bess-strategy/, bess-schedule/: 0 wrong-dir files for W38

**Pattern analysis**:
- W37: bess-stack/ on Sep 7 (Mon) and Sep 8 (Tue) — early-week DEGRADED sessions
- W38: bess-stack/ on Sep 18-20 (Fri-Sun) — end-week DEGRADED sessions
- Common factor: bess-stack/ appears on days with Tenaska DEGRADED (Sep 7-8, W37: Tenaska DOWN; Sep 18: Tenaska 401; Sep 19-20: Tenaska 401 + Smartbidder DEGRADED)
- The W36 CRITICAL plan for DA charge failure was SUBSTANTIALLY RESOLVED (DA energy executing correctly) — this remains resolved in W38 (Sep 14-17 show PRODUCTION P&L).

**Root Cause**: DEGRADED data cycles create cognitive-load displacement (Pattern 21 variant): when the agent is processing complex graceful-degradation logic (no Tenaska, no Smartbidder), the mechanical path-selection step is overridden. The agent reverts to bess-stack/ on these days.

**Required Action**:
1. AGENT IMMEDIATE: At session start on any DEGRADED cycle (Tenaska FAILED or Smartbidder DEGRADED), explicitly echo the canonical output path: "OUTPUT PATH: reports/daily/bess-optimizer/YYYY-MM-DD.md" before beginning DEGRADED analysis. The path must be verified twice: once at session start, once at file creation.
2. AGENT IMMEDIATE: On Friday (WDPEAK last day), Saturday (WEPEAK), and Sunday (WEPEAK) sessions, re-confirm output path regardless of data availability. Weekend sessions consistently show higher wrong-dir rate.
3. AGENT IMMEDIATE: The distinction between bess-stack/ (wrong) and bess-optimizer/ (correct) appears to track with data quality — full-data cycles use bess-optimizer/, DEGRADED cycles use bess-stack/. This may reflect that the agent uses different analysis templates for DEGRADED vs PRODUCTION cycles, and the DEGRADED template defaults to bess-stack/. Align the DEGRADED cycle output path with the PRODUCTION path.
4. USER OPTIONAL: If W39 also shows bess-stack/ for Fri/weekend/DEGRADED days, consider agent definition hard-code for output path (same pattern as dart-virtual-trader recommendation).

**Success Criterion**: W39 = 7/7 files in bess-optimizer/ ONLY, including all Friday, Saturday, Sunday sessions and DEGRADED cycles. Zero bess-stack/ files.

**Deadline**: 2026-W39 (by 2026-09-27)
