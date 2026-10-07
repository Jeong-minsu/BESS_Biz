# Plan: Tenaska Whitelist — Week 22 Escalation Status

**Issue**: Tenaska PTP Ascend IP whitelist failure has now reached 7 confirmed failures in 11 operating days (2026-05-21, 05-23, 05-25, 05-26, 05-27, 05-28, 05-30). Successes limited to 2026-05-22, 05-24, 05-29 (3 of 11 days). Pattern in data-quality.md is fully documented. The 2026-21 plan actions (add connectivity pre-check, document whitelisted IP) have not been implemented.

**Priority**: CRITICAL (escalated — unchanged from 2026-21, no progress observed)

**Week 22 status**: OPEN — no new implementation evidence found. All pnl-manager learnings still cite the same root cause (cloud IP not whitelisted). The pre-check code was not added to fetch_pnl_data.py. The IP was not documented in README.

## Updated Actions (beyond 2026-21 plan)

1. Confirm whether the 2026-05-22, 2026-05-24, and 2026-05-29 successful fetches all originated from the same IP. If yes, that is the whitelisted IP — document it in `.env.example` and `shared/scripts/README.md` immediately.
2. Add a minimal connectivity pre-check to `fetch_pnl_data.py`: attempt a lightweight HEAD request to the Tenaska PTP base URL before running the full fetch; print a clear error message with the current execution IP and the remediation steps if the request is blocked (HTTP 403 or connection refused).
3. Formally escalate to Ascend rep via email (user action required) citing 7 failures in 11 days. Include the execution IP that needs whitelisting in the escalation email.
4. Implement a fallback execution path: document a runbook in `shared/scripts/README.md` for the user to trigger a local fetch manually when the cloud environment is blocked.

## Success Criteria

- Zero consecutive DEGRADED P&L days in any future 7-day window due to the whitelist issue.
- fetch_pnl_data.py prints the execution IP and whitelist status on every run.

## Owner

User (for Ascend contact) + pnl-manager (for code changes to fetch_pnl_data.py)
