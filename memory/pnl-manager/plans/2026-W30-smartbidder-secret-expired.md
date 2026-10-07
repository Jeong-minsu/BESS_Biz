# Plan: Smartbidder MSAL client_secret Expired — W30 New Critical

**Registered by**: evaluator  
**Date**: 2026-07-27  
**Priority**: CRITICAL (NEW — first occurrence)  
**Status**: OPEN — user action required  
**Agent primarily affected**: pnl-manager (benchmark), bess-optimizer (self-review), dart-virtual-trader (Floor calculation)

---

## Issue

Smartbidder MSAL client_secret expired during W30, causing Smartbidder API failures on 2026-07-25 and 2026-07-26 (AADSTS7000222 error). CLAUDE.md explicitly warns: "Smartbidder MSAL: client_secret 12개월마다 만료 → Ascend rep에 갱신 요청."

This is a user-action-only resolution — the agent cannot renew the client_secret.

## Evidence

- `reports/daily/pnl/2026-07-25.md`: "Smartbidder Benchmark: DEGRADED — client_secret 만료 (AADSTS7000222). 비교 불가."
- `reports/daily/pnl/2026-07-26.md`: "양 소스 모두 실패 — Tenaska PTP FAILED + Smartbidder FAILED (AADSTS7000222, 2번째 연속)."
- `memory/bess-optimizer/learnings/2026-07-26.md`: "Smartbidder benchmark: DEGRADED — client_secret 만료. All benchmark columns are N/A."
- stage-progress.md (congestion-analyst): references "Smartbidder FAILED client_secret expired — Ascend rep renewal required" on 2026-07-27.

## Impact

1. **pnl-manager**: Cannot compare GKS actual vs Smartbidder benchmark for 07-25 and 07-26. Benchmark delta tracking interrupted.
2. **bess-optimizer**: Cannot reference Smartbidder benchmark in self-review for 07-25 (as noted in 07-26 learnings). Recalibration note ("STRATEGIC BENCHMARK" label) still works, but no benchmark comparison row available.
3. **dart-virtual-trader**: If Smartbidder DA-RT probability CSV is also unavailable (fetched via same MSAL token), Floor calculations revert to no-SB regime. July 25 position report may have used last-known probabilities.
4. **market-analyst**: Cannot use Smartbidder price forecasts for D+1 briefings if outage continues into W31. DA/RT price estimates would fall back to YE + Enverus only.

## Required User Action

Contact Ascend rep to renew the Smartbidder MSAL client_secret immediately. Reference CLAUDE.md: "Ascend rep에 갱신 요청." The secret appears to have expired approximately 2026-07-25 (first AADSTS7000222 error). Expiry cycle is 12 months — last renewal was approximately 2025-07 per this timeline.

## Interim Agent Fallback (until renewed)

Each agent should apply its no-SB fallback protocol:
- pnl-manager: Mark Smartbidder rows as N/A; do not interpolate or estimate.
- bess-optimizer: Use YE + congestion-analyst as primary inputs; note Smartbidder DEGRADED in header.
- dart-virtual-trader: Revert to no-SB regime (v3 model only; no-SB P floor applies).
- market-analyst: Use YE BIDCLOSE + Enverus + AG2 WSI for price view; note absence in briefing header.

## Resolution Deadline

User to contact Ascend rep within 3 business days (target: 2026-07-30). If unresolved by W31 evaluation (2026-08-03), evaluator will escalate to highest priority.

## Success Criterion

Smartbidder MSAL authentication succeeds (HTTP 200 from all four Smartbidder endpoints); pnl-manager 07-25 and 07-26 benchmark values backfilled with note.
