# Plan: Tenaska Whitelist Permanent Fix — 2026-21

**Issue**: Tenaska PTP fetch failed on 2026-05-21 (DEGRADED) and recurred on 2026-05-23 (PARTIAL), causing 2 of 5 observable P&L days to have no actuals. Cloud execution IP is not on Ascend whitelist; 2026-05-22 succeeded from a different execution environment.

**Priority**: CRITICAL

## Actions

- Identify the static IP (or IP range) of the production execution environment used on 2026-05-22 (the successful run) and request Ascend to permanently whitelist that IP via Tenaska PTP support channel.
- Document the whitelisted IP in `.env.example` and `shared/scripts/README.md` so any new execution environment knows to check whitelist status before running `fetch_pnl_data.py`.
- Add a pre-run connectivity check to `fetch_pnl_data.py`: ping Tenaska PTP `/ping` or a lightweight endpoint before the full fetch; print a clear error with remediation instructions if blocked.
- Set up a weekly audit: pnl-manager to confirm in its Monday history file whether the prior week had any DEGRADED/PARTIAL P&L days and flag if consecutive failures occur.
- Escalate: if whitelist registration takes >3 business days, contact Ascend rep with Tenaska account details (`.env` `[Tenaska]` section).
