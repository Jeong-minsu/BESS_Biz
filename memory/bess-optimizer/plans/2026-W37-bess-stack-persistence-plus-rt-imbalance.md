# Improvement Plan — 2026-W37 — bess-stack/ Directory Persistence + RT Structural Imbalance
**Agent**: bess-optimizer
**Priority**: MAJOR
**Issue**: Two distinct problems observed in W37. (1) Directory: bess-stack/ wrong directory persists for Sep 7–8 (2/7 days), and Sep 13 output is missing entirely — only 4/7 days in correct bess-optimizer/ path. (2) RT structural imbalance: Sep 8 PRODUCTION data shows RT energy = -$14,086 offsetting $15,774 DA energy (89% RT offset ratio), producing only $1,688 net DART spread on 415 MWh DA discharge — a structural signal that the DA-RT position sizing logic may need calibration.
**Root Cause**:
(1) Directory: bess-stack/ was the prior output directory before W36 corrective plan. Agent corrected 4/7 days but reverted to bess-stack/ on Sep 7-8 (likely session start without path anchor). Sep 13 missing file suggests early session termination or file save failure. W36 Critical partially resolved (4/7 correct vs prior 0/7) but not fully closed.
(2) RT imbalance: DA energy sales of 415 MWh with only 50 MWh DA purchases implies ~89% of DA obligation was covered by RT dispatch, generating large RT imbalance costs. This pattern may reflect deliberate stack strategy or suboptimal DA quantity calibration — cannot determine without Smartbidder benchmark (DEGRADED). EVALUATOR NOTE: not penalizing for Smartbidder absence; flagging RT ratio as a metric to track once benchmark resumes.
**Required Action**:
1. AGENT IMMEDIATE: First action every session = `echo reports/daily/bess-optimizer/YYYY-MM-DD.md` as path anchor before any analysis. File MUST save to `reports/daily/bess-optimizer/` exclusively. bess-stack/ must never be written.
2. AGENT IMMEDIATE: Sep 13 missing output — create recovery entry if Sep 13 actuals become available, or document in W38 Sep 14 learning that Sep 13 was not produced.
3. AGENT NEXT BENCHMARK AVAILABLE: When Smartbidder resumes, compute RT-offset ratio (RT energy cost / DA energy revenue) for trailing 7 days. Flag if ratio > 70% for ≥3 days as a stack calibration review trigger.
4. USER REQUIRED (LOW PRIORITY): Once Smartbidder client_secret renewed, compare bess-optimizer recommendations against Smartbidder DA quantity suggestions for Sep 7–13 retroactively.
**Success Criterion**: W38 = 7/7 files in bess-optimizer/ (zero bess-stack/ occurrences, zero missing days). RT-offset ratio tracked and documented in learnings when PRODUCTION P&L available.
**Deadline**: 2026-W38 (by 2026-09-20)
