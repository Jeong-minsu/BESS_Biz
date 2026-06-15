# Plan: dart-virtual-trader — Settlement Infrastructure Gap & Model Gaps

**Filed by**: evaluator | **Date**: 2026-06-15 | **Week**: 2026-24 | **Priority**: CRITICAL (user action required on settlement; agent action on model rules)

---

## Issue 1 (CRITICAL): DART Virtual Settlement Is Structurally Invisible — 4+ Consecutive Weeks

**Evidence**: W24 daily reports and dart-virtual-trader learnings files.

- 2026-06-10 (learnings): "dart_virtual_revenue = $0.00 for the 4th consecutive week — 0 rows from DA Energy Bid / DA Energy Only Offer endpoints"
- 2026-06-13 (learnings, section 9, item 5): "Tenaska DA Energy Bid and DA Energy Only Offer returned 0 rows for 2026-06-13 (same as recent pattern). This is the 3rd flowday in the past week with no separate virtual settlement."
- 2026-06-14 (learnings): "dart_virtual_revenue = 0.00 — not separately tracked. Tenaska DA Energy Bid / DA Energy Only Offer returned 0 rows."

**Impact**: The agent is flying blind. Estimated losses (-$590 at HE21 on 2026-06-14) cannot be confirmed. Estimated wins cannot be confirmed. The only confirmed settlement in the entire tracked history is 2026-06-06 (-$5,266) and a partial Smartbidder estimate (+$146.75 on 2026-06-10, not Tenaska-invoiced).

**The fundamental question remains unanswered** (Hypothesis C from learnings/2026-06-10.md): Does Smartbidder submit its own independent virtual book for GKS, making the dart-virtual-trader recommendations purely advisory? If yes, the agent's E[P&L] forecasts have no connection to actual settlement.

**User action required**: Confirm with Smartbidder/Tenaska:
1. Does the GKS Smartbidder configuration submit independent virtual INC/DEC schedules to ERCOT DAM?
2. If yes, is the dart-virtual-trader advisory book used as input, or is it independent?
3. What endpoint (or settlement report) captures the virtual settlement P&L separately from physical energy?

Without this answer, the agent cannot validate its model, track hit rates, or size positions correctly. This is P1.

---

## Issue 2 (MAJOR): Non-Spin vs ECRS Data Label Confusion — Scarcity Modifier at Risk

**Evidence**: `memory/dart-virtual-trader/learnings/2026-06-13.md` (Section 6, "틀린 것" item 2).

The position report for 2026-06-13 stated "Non-Spin DA HE21: $3.32/MWh (well below $8 threshold)" but $3.32 was actually ECRS (DA_ECRS_Amt), not Non-Spin (DA_NS_Amt). Actual Non-Spin was $12.61/MWh — above the $10 mandatory skip threshold. The scarcity modifier rule was not triggered because the wrong data field was read.

On 2026-06-13, the Saturday 25 MW cap happened to produce the same sizing (25 MW = half of 50 MW weekday), but on a weekday cycle where the Saturday cap is not in force, this data label confusion would result in a failure to apply the scarcity modifier, potentially issuing a full-size position into a scarcity environment.

**Agent action required**: Fix the data extraction step to read DA_NS_Amt explicitly (not DA_ECRS_Amt or a combined field) when evaluating the Non-Spin scarcity modifier threshold. Add a validation step: if DA_NS_Amt is null or < $0.01 and DA_ECRS_Amt > $1, flag as "probable data label issue — manually verify."

---

## Issue 3 (MAJOR): ECRS DA Clearing as INC Risk Contra-Indicator — New Rule Not Yet Formalized

**Evidence**: `memory/dart-virtual-trader/learnings/2026-06-14.md` (Section 4 and Learning 1).

On 2026-06-14, ECRS cleared DA HE21-24 (confirmed: ECRS revenue +$612.48). The same evening, INC at HE21 lost (RT $60.64 >> DA $37.04, spread -$23.60). The agent correctly identified the causal mechanism: ECRS clearing signals ERCOT anticipates reserve shortfall → RT scarcity adders push RT above DA → INC (which profits from DA > RT) loses.

The learning proposed a new rule:
- ECRS DA > $0: flag HE as ELEVATED INC risk
- ECRS DA > $1.50: mandatory skip for INC

This rule was documented in learnings but NOT yet formalized in a standing rule or plan. It must be in place before the next Sunday cycle.

**Agent action required**: Formalize the ECRS DA clearing modifier as a permanent rule in the position generation logic. Document in `memory/dart-virtual-trader/learnings/` as a standing rule and apply starting with the 2026-06-16 cycle.

---

## Issue 4 (MAJOR): Adjacent-Hour Scarcity Block Rule — Not Yet Implemented

**Evidence**: `memory/dart-virtual-trader/learnings/2026-06-14.md` (Learning 3).

When HE(X+1) triggers the W23 dual-direction scarcity skip (Non-Spin > $10 AND NL ramp > 8,000 MW), the hours immediately preceding (HE(X)) face the same underlying supply-demand stress. The model currently treats adjacent hours independently. On 2026-06-14, HE22 was correctly skipped (W23 rule) but HE21 was not protected despite ECRS already clearing.

Proposed rule: When HE(X+1) triggers W23 dual-direction skip, reduce INC size at HE(X) by 50% and apply a $6 spread floor (instead of $4).

**Agent action required**: Implement this rule before the 2026-06-21 Sunday cycle. Document in learnings as a carried-forward action.

---

## Issue 5 (MINOR): Position Report Files Still Absent

**Evidence**: `memory/dart-virtual-trader/learnings/2026-06-14.md`: "reports/daily/dart-virtual-trader/2026-06-14.md — NOT FOUND (report file absent for this flowday)."

The W23 evaluator plan (CRITICAL-1) required hit rate log creation. The W24 cycle shows:
- 2026-06-13 learnings: "position source: reports/daily/dart-positions/2026-06-13.md — AVAILABLE" (positive progress)
- 2026-06-14 learnings: "reports/daily/dart-virtual-trader/2026-06-14.md — NOT FOUND"

The output path naming is inconsistent (`dart-positions/` vs `dart-virtual-trader/`). The agent has been generating some report files but not consistently and not at the correct path.

**Agent action required**: Standardize position report output to `reports/daily/dart-virtual/YYYY-MM-DD.md` (matching existing W22 file naming). Generate this file every cycle without exception, including weekends.

---

## Success Criteria

- User confirms Smartbidder virtual submission scope by 2026-06-22 (end of W25).
- DA_NS_Amt vs DA_ECRS_Amt data label fixed in extraction pipeline before 2026-06-16 cycle.
- ECRS DA clearing modifier rule applied starting 2026-06-16.
- Adjacent-hour scarcity block rule implemented before 2026-06-21 (next Sunday).
- Position report file generated at `reports/daily/dart-virtual/YYYY-MM-DD.md` for every cycle starting 2026-06-16.

---

*Evaluator — 2026-06-15 | Extends: 2026-W23-improvement.md (Issues 1-2 carried forward; Issues 3-5 new from W24 evidence)*
