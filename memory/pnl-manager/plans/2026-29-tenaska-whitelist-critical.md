# Plan: Tenaska IP Whitelist — W29 Escalation (26th+ Failure Event)

**Registered by**: evaluator  
**Date**: 2026-07-20  
**Priority**: CRITICAL — User action required (infrastructure, not agent-resolvable)  
**ISO Week**: 2026-W29  
**Status**: OPEN — awaiting user resolution

---

## Issue

The Tenaska PTP endpoint remains inaccessible from the cloud execution environment due to Ascend IP whitelist restrictions. This has caused **26+ cumulative failure events** since 2026-05-21 (9+ weeks). The pnl-manager cannot produce GKS actual P&L on days when the cloud environment executes `fetch_pnl_data.py` from a non-whitelisted IP.

**W29 confirmed failures**:

| Date | P&L Report Status | Evidence |
|---|---|---|
| 2026-07-15 | NO FILE (not even DEGRADED) | `reports/daily/pnl/` directory listing |
| 2026-07-17 | DEGRADED filed | `reports/daily/pnl/2026-07-17.md` |

**W29 confirmed PRODUCTION runs** (when executed from whitelisted IP):

| Date | P&L Report Status | Evidence |
|---|---|---|
| 2026-07-13 | PRODUCTION | `reports/daily/pnl/2026-07-13.md` |
| 2026-07-14 | PRODUCTION | `reports/daily/pnl/2026-07-14.md` |
| 2026-07-16 | Not present (Jul 16 data) — Jul 15 pnl missing | confirmed gap |
| 2026-07-18 | PRODUCTION (-$1,626.85) | `reports/daily/pnl/2026-07-18.md` |
| 2026-07-19 | PRODUCTION (+$6,716.41) | `reports/daily/pnl/2026-07-19.md` |

Cascade effect: on DEGRADED days, all agent self-review loops for vs-actual delta analysis are broken. bess-optimizer, dart-virtual-trader, market-analyst, and congestion-analyst all reference pnl actuals in their learnings files — when DEGRADED, these learnings can only use stale data.

---

## Current Workaround in Use

pnl-manager correctly files a DEGRADED status report when actuals are unavailable, preserving audit trail. The D+1 Smartbidder forecast data (available from cloud) is included in DEGRADED reports as reference.

On 2026-07-15, even the DEGRADED report was absent — this is a secondary process failure (see `reports/daily/2026-07-14.md` Cycle Health table, no pnl entry for Jul 15).

---

## Root Cause

Ascend cloud execution environment IP is not on the Tenaska PTP API whitelist. `fetch_pnl_data.py` must be run from a whitelisted IP (user's local machine or VPN). This is a user-infrastructure issue that has been escalated in every weekly evaluation since W22.

**Prior escalation chain**: W22 → W23 → W24 → W25 → W26 → W27 → W28 → W29 (8 consecutive escalations, no resolution).

---

## Required Actions

### Agent-level (pnl-manager — within scope):
1. **NEVER omit the DEGRADED report**: On any day Tenaska fetch fails, file `reports/daily/pnl/YYYY-MM-DD.md` with DEGRADED status. The Jul 15 missing report was a process failure. Even partial data warrants a filed report.
2. Document in each DEGRADED report: cumulative failure count + date of last PRODUCTION run.

### User-level (infrastructure — outside agent scope):
1. **Ascend whitelist request**: Contact Ascend/Tenaska support to whitelist the cloud execution environment IP range, OR configure `fetch_pnl_data.py` to run only from local/VPN. Either resolves the root cause.
2. **Interim**: Maintain local execution schedule for `fetch_pnl_data.py` until cloud whitelist is confirmed.

---

## User Action Requested

- [ ] Submit Ascend whitelist request (IP range of cloud execution environment) — **OVERDUE since W22**
- [ ] Confirm current workaround: is `fetch_pnl_data.py` being run manually from local on most days? (This explains the pattern of PRODUCTION success mixed with sporadic failures.)
- [ ] Set resolution deadline. If whitelist not resolved by W31 (2026-08-03), evaluate alternative: daily scheduled task on local machine with automated upload to `shared/data/raw/`.
