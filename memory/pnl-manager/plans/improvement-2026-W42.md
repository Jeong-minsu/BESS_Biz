# pnl-manager Improvement Plan — 2026-W42
**Filed by**: evaluator | **Date**: 2026-10-19 | **Period evaluated**: 2026-10-12 – 2026-10-18

---

## W42 Status Summary

| Axis | Score | Trend |
|---|---|---|
| Process | 3.5/5 | → |
| Approach | N/A (FULLY DEGRADED) | — |
| Resource | 3.5/5 | → |
| Overall | 3.5/5 | → |

**Status**: FULLY DEGRADED for 31 consecutive flowdays (Sep 18 – Oct 18). Tenaska PTP HTTP 401 unresolved. Smartbidder permanently terminated (2026-10). Tyba Shadow asset API inquiry ongoing — no progress documented.
**Coverage**: 6 of 7 days filed (Oct 17 report missing). All DEGRADED protocol correctly applied.

---

## W41 Plan Compliance

| W41 Plan Item | W42 Outcome |
|---|---|
| Tenaska PTP whitelist (P0) | FAILED (external blocker) — user action required |
| Smartbidder MSAL renewal | N/A — permanently terminated 2026-10 |
| Backfill priority list in data-quality.md | UNVERIFIED this evaluation cycle |
| Periodic learnings update (every 2–3 weeks) | FAILED — last learning entry remains 2026-09-01 (7+ weeks silent) |

---

## Improvement Items for W43

### Item 1 — CRITICAL: Tenaska PTP Access (31 consecutive DEGRADED flowdays)

**Issue**: Tenaska PTP HTTP 401 (cloud IP not on Ascend whitelist) since 2026-05-21. Sep 18 – Oct 18 = 31 consecutive unconfirmed flowdays. Last confirmed GKS actual: Sep 17 (-$2,231.14). Cumulative unverified revenue period is now ~150+ flowdays (May–October 2026).

**Impact on other agents**: bess-optimizer SoC initialization using Rule 7 default (100 MWh) every cycle — accumulated error over 31 days. Sep 17 Rule 8 RT dispatch mismatch unresolvable. Evaluator Approach scores for all front-office agents based on methodology only.

**Required user action** (P0 — cannot be resolved by pnl-manager alone):
1. Run `shared/scripts/fetch_pnl_data.py` from a whitelisted IP (user local workstation or company VPN).
2. OR contact Ascend/Tenaska representative to add cloud automation IP to whitelist permanently.
3. When access is restored: bulk-recover Sep 18 – Oct 18 settlement data. Priority order from W40 plan: Sep 17 first (Rule 8 context), then Sep 18–24, then Sep 25–Oct 18.

---

### Item 2 — MAJOR: Tyba Shadow Asset API — Status Update Required

**Issue**: Smartbidder was terminated 2026-10. Tyba Shadow asset API was cited as the replacement benchmark path since at least W38. As of W42, no progress update has been documented.

**Required action**: In next pnl-manager report or learnings update, document the current status of the Tyba Shadow asset API inquiry:
- Has the API been confirmed available?
- What is the expected timeline for activation?
- What data fields will it provide (competitor DA/RT prices? P&L estimates?)?

If no update is available, document "No response from Tyba as of [date]" to make the status visible and actionable.

**Success criterion**: Status documented in `memory/pnl-manager/data-quality.md` or learnings by end of W43.

---

### Item 3 — MINOR: File Oct 17 Report

**Issue**: `reports/daily/pnl/2026-10-17.md` absent. Single gap in otherwise consistent coverage.

**Required action**: File a DEGRADED stub report for Oct 17 flowday (same format as Oct 18 report with corrected date and consecutive day count = 30).

**Success criterion**: Oct 17 pnl report exists.

---

### Item 4 — MINOR: Periodic Learnings Update (7+ weeks silent)

**Issue**: Last pnl-manager learning entry: `memory/pnl-manager/learnings/` — no W42 entries found. Per R&R, daily self-review not required for Back Office agents, but infrastructure status updates every 2–3 weeks are expected. Last entry was 2026-09-01 (7+ weeks ago).

**Required action**: File a brief infrastructure status learning by Oct 26 covering: Tenaska status, Smartbidder termination impact, Tyba inquiry status, and DEGRADED day count.

**Success criterion**: New learning entry filed in `memory/pnl-manager/learnings/` by Oct 26.
