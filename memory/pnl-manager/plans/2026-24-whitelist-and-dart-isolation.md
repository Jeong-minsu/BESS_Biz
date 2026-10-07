# Plan: pnl-manager — Tenaska Whitelist + DART Virtual Isolation (W24 Update)

**Filed by**: evaluator | **Date**: 2026-06-15 | **Week**: 2026-24 | **Priority**: CRITICAL (user action required)

---

## Issue 1 (CRITICAL): Tenaska/Ascend IP Whitelist — 12 Failures in 21 Operating Days, No Resolution

**Evidence**: 
- `reports/daily/2026-06-11.md` (Cycle Status): "pnl-manager DEGRADED — 11th consecutive Tenaska/Ascend IP whitelist failure."
- `reports/daily/2026-06-13.md` Section 7: "Tenaska/Ascend IP whitelist failure — P1 CRITICAL — 12 failures in 21 operating days. Chronically unresolved P1."
- `memory/pnl-manager/learnings/2026-06-11.md`: "This is the 12th confirmed failure of this pattern in 21 operating days (~57% failure rate since 2026-05-21)."

W24 confirmed PRODUCTION data for: 2026-06-08, 2026-06-10, 2026-06-12, 2026-06-13 (partial/Saturday).
W24 confirmed DEGRADED data for: 2026-06-09, 2026-06-11 (12th failure), 2026-06-14 (DA bid/offer 0 rows, partial).

Outstanding backfill list as of 2026-06-12: 11 days pending (2026-05-23, 2026-05-25 through 2026-05-28, 2026-05-30, 2026-06-01 through 2026-06-03, 2026-06-09, 2026-06-11).

**Pattern analysis**: Tenaska PTP fetch succeeds when executed from a whitelisted IP (user's local machine or company VPN). The cloud execution environment IP is not whitelisted. The W23 evaluator plan required documenting the recovery mechanism — this has not been done (data-quality.md last updated 2026-06-04).

**User action required**:
1. Confirm with Ascend: permanently whitelist the cloud execution IP for api.ptp.energy. Provide IP to Ascend rep.
2. If cloud execution IP changes frequently: configure a static outbound IP for the cloud execution environment, then whitelist it.
3. Run backfill from a whitelisted IP for all 11+ outstanding DEGRADED days.
4. Update `memory/pnl-manager/data-quality.md` with W24 status (last entry was 2026-06-04).

---

## Issue 2 (CRITICAL, CARRIED FROM W21/W22/W23): DART Virtual Revenue Isolation Still Not Implemented

**Evidence**: Across all W24 daily reports, the "DART Virtual" line appears as either "ESTIMATE," "NOT AVAILABLE," "null," or $0.00. The Tenaska `DA Energy Bid / DA Energy Only Offer` endpoints returning 0 rows is the consistent pattern.

- 2026-06-10 pnl (daily report): DART Virtual = $146.75 ESTIMATE (Smartbidder, not Tenaska invoiced)
- 2026-06-12 actuals: DART virtual net = -$301.19 (physical energy net, not separately isolated virtual book)
- 2026-06-13 (Saturday): DART virtual = null (no separate virtual tracking)
- 2026-06-14: DART virtual = $0.00

This gap has been carried as MAJOR since W21, escalated to MAJOR in W22, and noted as CRITICAL in W23. Zero implementation progress in 3 evaluation cycles.

**Impact update (W24)**: Given the dart-virtual-trader submitted an estimated loss of -$590 on 2026-06-14 (INC HE21 25 MW, spread -$23.60), and the total DART virtual revenue line showed $0.00 — the GKS total P&L for 2026-06-14 ($9,819.75) does not include this estimated loss. The true net could be $9,230. Without isolation, total P&L accuracy is unknowable when dart-virtual-trader positions are active.

**Required action**: Implement `Submissions-DA-Settlement-Amounts` endpoint call in `fetch_pnl_data.py`. This is a code change requiring approximately 20 lines of Python. The endpoint discovery was completed in W21 (per plans/2026-21-dart-virtual-isolation.md). There is no technical blocker remaining beyond implementation time.

---

## Issue 3 (MINOR): data-quality.md Update Overdue

**Evidence**: `memory/pnl-manager/learnings/2026-06-11.md`. The data-quality.md log was last updated 2026-06-04. Eleven additional data points (successes and failures) have not been recorded.

**Agent action required**: Update data-quality.md with all W24 fetch attempts (2026-06-08 through 2026-06-14), noting success/failure, data rows returned, and execution environment.

---

## Success Criteria

- Ascend whitelist confirmed for cloud execution IP by 2026-06-22.
- data-quality.md updated with W24 entries by 2026-06-16.
- `Submissions-DA-Settlement-Amounts` endpoint implemented in fetch_pnl_data.py by 2026-06-22.
- At least 5 backfill days resolved by 2026-06-22.

---

*Evaluator — 2026-06-15 | Supersedes: 2026-W23-improvement.md Issues 1-3. All three issues carried forward with updated evidence. DART virtual isolation has been deferred for 4 consecutive evaluation cycles — no further deferral acceptable.*
