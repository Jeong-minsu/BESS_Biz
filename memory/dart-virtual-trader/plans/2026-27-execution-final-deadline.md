# Plan: dart-virtual-trader — Execution Scope Final Deadline
**Week**: 2026-27 | **Priority**: CRITICAL | **Registered by**: evaluator

---

## Issue

W26 evaluator plan `2026-26-execution-confirmation-critical.md` set a user deadline of 2026-07-03 to confirm execution scope (A: manual, B: advisory-only, C: auto-submit). That deadline passed without response. This is the **20th consecutive escalation** with no resolved execution infrastructure.

**Quantitative basis**:
- Hit rate: uncomputable for 20+ consecutive cycles
- DART virtual ranking (STALE 2026-03-26): GKS #276/276, Win Rate 31.5% (target ≥55%)
- dart-virtual-trader self-classified as "ADVISORY ONLY" since W26 plan
- W26 deadline (2026-07-03): MISSED — no user response

---

## Root Cause Hypothesis

User has not confirmed whether dart-virtual-trader recommendations are: (A) submitted manually by user to ERCOT, (B) used as advisory-only context, or (C) processed through Smartbidder auto-submit. Without this, hit rate validation is impossible and the agent's Approach axis cannot be scored above 1.0.

---

## Action Items

1. **Evaluator action (immediate)**: Formally declare dart-virtual-trader as "ADVISORY ONLY — UNSCORED on Approach axis" in W27 scorecard and all subsequent scorecards until user responds.

2. **User action required by 2026-07-13 (W28 evaluation)**: Confirm execution scope. This is the final escalation before:
   - dart-virtual-trader is re-classified as "advisory context" (not evaluated on hit rate)
   - All open hit-rate-related plans (W21–W27) are closed as "infrastructure unresolvable without user input"

3. **Agent action (immediate)**: Continue issuing positions with methodology improvements (v4 INC veto rule, HE15-17 RT spike skip, Smartbidder calibration on return). These have analytical value even in advisory-only status.

4. **Agent action (by 2026-07-13)**: Create `memory/dart-virtual-trader/advisory-only-mode.md` documenting the advisory-only status, what metrics are tracked under this mode, and what user action would re-activate performance scoring.

---

## Success Metric

- User confirms execution scope by 2026-07-13: CLOSED
- No user response by 2026-07-13: Agent officially re-classified to "ADVISORY ONLY" and Approach axis suspended; plan CLOSED as resolved-by-policy

---

## Supersedes

`memory/dart-virtual-trader/plans/2026-26-execution-confirmation-critical.md` (deadline MISSED)
`memory/dart-virtual-trader/plans/2026-25-settlement-infrastructure.md` (deadline MISSED)
