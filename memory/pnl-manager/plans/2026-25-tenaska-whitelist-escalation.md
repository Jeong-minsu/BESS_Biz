# Plan: Tenaska PTP Whitelist — CRITICAL Escalation (W25)

**Registered by**: evaluator
**Week**: 2026-25
**Priority**: CRITICAL
**Status**: OPEN — user action required
**Supersedes**: `memory/pnl-manager/plans/2026-24-whitelist-and-dart-isolation.md`

---

## Problem Statement

Tenaska PTP returned 0 rows for pnl-manager on approximately 5 of 7 W25 operating days.
Per the 2026-06-21 P&L report, this is the 15th occurrence since 2026-05-21 — a 52% cloud execution failure rate.

The root cause is confirmed: the cloud execution environment's egress IP is not on the Ascend/Tenaska IP whitelist.
The API returns 0 rows (empty resultset) rather than an explicit error, requiring the agent to infer failure.

This is the single highest-impact infrastructure issue in the entire agent fleet. Every cloud-execution cycle
without whitelisted IP produces DEGRADED P&L data, which cascades into:

- pnl-manager: no GKS actuals, no delta vs benchmark, no cycle accounting
- bess-optimizer: no SoC verification, no plan-vs-actual calibration
- dart-virtual-trader: no settlement verification, hit rate remains uncalculable
- congestion-analyst: no realized lambda data, binding hit rate remains uncalculable (30+ cycles)
- market-analyst: no RT price actuals for self-review calibration

**Cumulative backlog**: 13+ DEGRADED days outstanding as of 2026-06-21 (earliest: 2026-05-23).

---

## W25 Status Update vs W24 Plan

The W24 plan (`2026-24-whitelist-and-dart-isolation.md`) had two actions:

1. User to whitelist cloud IP — **NOT COMPLETED** (15th failure confirms no change)
2. Agent to implement Submissions-DA-Settlement-Amounts endpoint for DART isolation — **STATUS UNKNOWN**
   (Tenaska DEGRADED on all DART-relevant days in W25; cannot verify)

Neither action has had measurable impact. This plan escalates with a tighter deadline and explicit fallback.

---

## Required Actions

### Action 1 — User (CANNOT be done by agent)

Submit IP whitelist request to Ascend/Tenaska support.

- Identify the cloud execution environment's outbound IP (or CIDR range)
- Send to Ascend support contact: `ascend.support@tenaska.com` (or confirmed contact)
- Request: add IP(s) to the Battery-Settlement-Details and ERCOTNodal endpoint access list
- Target: at least 1 whitelisted IP operational before 2026-06-29 (next Monday cycle)

If whitelisting is architecturally impossible (e.g., dynamic IP assignment), request a static-IP proxy
or VPN tunnel solution from Ascend, or arrange for pnl-manager to run on the user's local machine
(already whitelisted) for the daily fetch step.

### Action 2 — pnl-manager agent

Implement a pre-fetch IP check as Step 0 of each daily cycle:

```python
# At top of fetch_pnl_data.py, before any API call:
import requests
my_ip = requests.get("https://api.ipify.org").text.strip()
# Log my_ip to shared/data/raw/ip-log.jsonl with timestamp
# If my_ip not in KNOWN_WHITELISTED_IPS list, print WARN and exit early
```

This prevents wasted API calls and makes the failure explicit in logs.

**Deadline**: next PRODUCTION daily cycle after user confirms whitelist change.

### Action 3 — pnl-manager agent (backfill)

Once whitelisting is in place, re-fetch and produce updated P&L reports for all 13+ DEGRADED days
(2026-05-23 through the most recent DEGRADED day) from the whitelisted environment.

Priority order for backfill:
1. Days where DART Virtual revenue is non-zero in Smartbidder estimate (provides baseline for hit rate)
2. Days with large Smartbidder benchmark (>$5,000) where actual delta is most material
3. All remaining days in chronological order

---

## Success Criteria

- 0 DEGRADED P&L reports in W26 due to whitelist failure
- Backfill for all 13+ outstanding DEGRADED days completed by 2026-07-06 (end of W26)
- IP pre-check log running in `shared/data/raw/ip-log.jsonl`

---

## Impact If Not Resolved by W26

If the whitelist failure continues:
- dart-virtual-trader hit rate will remain uncalculable indefinitely (40+ positions unresolved)
- congestion-analyst binding hit rate stays at 0 confirmed events (32+ cycles)
- bess-optimizer plan-vs-actual delta remains calibrated on stale 2026-05-24 data
- pnl-manager cannot validate whether GKS revenue meets contractual thresholds
- Evaluator scoring for Approach axis will continue to be blocked for 4 of 7 agents
