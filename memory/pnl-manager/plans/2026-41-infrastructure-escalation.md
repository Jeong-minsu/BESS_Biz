# Plan: pnl-manager Infrastructure Escalation — Day 144+ Tenaska, Day 79+ Smartbidder
# Week 2026-41 | Priority: CRITICAL | Registered: 2026-10-12

## Issue Status

As of W41 end (2026-10-11):

| Source | Failure Mode | Days Since Last Success | Consequence |
|---|---|---|---|
| Tenaska PTP | HTTP 401 (cloud IP not whitelisted) | 144+ days (since 2026-05-21) | 22+ consecutive unconfirmed flowdays (Sep 18–Oct 9) |
| Smartbidder MSAL | client_secret AADSTS7000222 expired | 79+ days (since 2026-07-25) | Zero benchmark comparisons since Jul 24 |

Prior escalation history:
- W22 (2026-05-27): First whitelist plan registered
- W29 (2026-07-21): CRITICAL escalation
- W30 (2026-07-28): Smartbidder added as CRITICAL
- W35 through W40: OPEN — user action required, no resolution

## Operational Impact

- 22 consecutive flowdays (Sep 18 – Oct 9) with ZERO actual P&L data
- Last confirmed GKS actual: Sep 17 total = −$2,231.14
- bess-optimizer cannot validate strategy effectiveness vs benchmark (Smartbidder absent)
- dart-virtual-trader hit rate unverifiable (no settlement data)
- Evaluator cannot score bess-optimizer or dart-virtual-trader on quantitative accuracy axis
- Reporter cannot include actual vs estimated comparison

Oct 8 flowday report: NOT GENERATED (pnl daily cycle not run Oct 9). This adds a process gap on top of the data gap.

## Action Required

### User (P0 — cannot be completed by agent alone):
1. **Tenaska PTP whitelist**: Contact Ascend representative (jms2527@gmail.com is account holder). Request cloud automation IP to be added to the Ascend portal whitelist. This has been open since May 21, 2026 (144+ days).
   - Impact: Restores actual P&L data for all flowdays. Enables Rule 8 Jun 5 postmortem.
   - Backfill scope: Sep 18 – Oct 11 (24 flowdays minimum).
2. **Smartbidder MSAL secret**: Contact Ascend representative. Request client_secret renewal (AADSTS7000222). Secret expired 2026-07-25.
   - Impact: Restores benchmark comparison (bess-optimizer vs Smartbidder). Enables evaluator quantitative scoring.
   - Backfill scope: Jul 25 – Oct 11 (78 flowdays).
3. **Interim option**: Run `fetch_pnl_data.py` from a whitelisted IP (user local machine or VPN) to retrieve actuals while cloud whitelist is pending.

### Agent (when data becomes available):
4. On first successful Tenaska fetch: retrieve all backfill flowdays Sep 18–present; generate daily pnl reports retroactively.
5. On first successful Smartbidder fetch: retrieve benchmark data Jul 25–present; generate delta comparisons.
6. File `memory/pnl-manager/learnings/backfill-YYYY-MM-DD.md` with analysis of 22+ day gap period.

### Agent (current — process gap):
7. Ensure Oct 8 flowday has a FULLY DEGRADED report stub even if data is unavailable. Do not skip daily cycle without generating at least a DEGRADED placeholder.

## Escalation Note

This is the 6th+ time this issue has been registered as CRITICAL or P0. The evaluator records this as an external dependency requiring user escalation to Ascend. No further agent-side plans will resolve this. The only resolution path is the user contacting Ascend.

## Success Criteria

RESOLVED when: Tenaska HTTP 200 on at least one cloud-executed fetch AND Smartbidder MSAL token successfully acquired.
MILESTONE: Any successful Tenaska fetch (even from VPN) that produces confirmed actuals for at least one Sep/Oct flowday.

## References

- W40 plan: `memory/pnl-manager/plans/2026-W40.md`
- Oct 9 P&L report: `reports/daily/pnl/2026-10-09.md` (FULLY DEGRADED — Day 77)
- pnl-manager W30 Smartbidder plan: `memory/pnl-manager/plans/2026-W30-smartbidder-secret-expired.md`
