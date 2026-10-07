# Plan: pnl-manager — W28 Improvements
**Week**: 2026-28 | **Priority**: CRITICAL | **Registered by**: evaluator

---

## Issue 1 (CRITICAL): 4 Consecutive DEGRADED Days (Jul 8-11), 23rd Total Failure

**Quantitative basis**:
- W28 PRODUCTION days: 2 of 7 (Jul 6, Jul 7 only)
- W28 DEGRADED days: 5 of 7 (Jul 8, 9, 10, 11, 12 — note Jul 12 is weekend and may be expected)
- Rolling 4-day DEGRADED streak (Jul 8-11): longest consecutive failure in system history
- Total failures since 2026-05-21: 23 of 45 operating days (~51%)
- Unresolved DEGRADED backlog: 22 days (explicit list in Jul 10 report)

**Root cause (unchanged since W21)**: Cloud execution IP not whitelisted at Ascend/Tenaska. `fetch_pnl_data.py` fails in cloud environment because the outbound IP is not on the Ascend whitelist. Requires one of:
- (A) User contacts Ascend to add the cloud execution IP to the whitelist permanently.
- (B) User runs `fetch_pnl_data.py` from a VPN-whitelisted machine each morning (not scalable per Pattern 18).

**Cascading impact**: All 5 Front/Middle agent self-review anchors go stale when pnl-manager is DEGRADED. bess-optimizer cannot validate recommendations. dart-virtual-trader cannot compute hit rate. market-analyst cannot anchor RT-price bias correction. congestion-analyst cannot confirm binding calls.

**Agent action (no-code, every DEGRADED day)**:
- Continue filing DEGRADED reports as currently done — data absence documented precisely, failure count incremented, backlog list maintained.
- In each DEGRADED report, include: "Recovery requires: Ascend whitelist permanent fix (user action, ticket open since 2026-05-21) OR user VPN execution of fetch_pnl_data.py."

**User action required (highest priority in the system)**:
- Contact Ascend (Tenaska PTP team) to permanently whitelist the cloud execution IP.
- Alternatively, confirm a daily VPN execution commitment as a standing operating procedure.

---

## Issue 2 (MAJOR): DA Bid/Offer 0-Row Root Cause Still Undiagnosed

**W27 deadline**: 2026-07-10 for root cause diagnosis. BLOCKED — Jul 8-11 all DEGRADED.

**New deadline**: First PRODUCTION day after Jul 13 (estimated Jul 14 or later, dependent on Tenaska access).

**Agent action (on first PRODUCTION day)**:
1. Inspect the raw Tenaska data file for the DA Energy Bid and DA Energy Offer fields.
2. Document: (a) Are rows present in the raw JSON but zero, or are the fields absent entirely? (b) Does this affect all hours or specific hours? (c) Does this affect GKS only or all resources?
3. Write findings to `memory/pnl-manager/learnings/da-bid-row-diagnosis.md`.
4. If rows are present but zero: check if bess-optimizer's DA-focused recommendations are not being submitted to ERCOT (consistent with EXECUTION-DIVERGENCE — Smartbidder bypasses DA bids and goes straight to RT co-optimization).
5. If rows are absent entirely: this is a Tenaska data reporting gap, not an execution gap — document as infrastructure issue.

---

## Issue 3 (STANDING — infrastructure): dart_virtual_revenue Isolation Not Available

**Status**: 30th+ consecutive cycle. Tenaska settlement data does not isolate DART virtual revenue from DA+RT Energy physical settlement. The "DART Virtual" line in the P&L table is consistently N/A.

**No agent action available**: Requires user contact with Tenaska to request a separate virtual settlement report or field identifier. This is documented as a standing infrastructure gap.

**In-report handling**: Continue displaying "DART Virtual: N/A" with the note "Tenaska settlement does not isolate virtual P&L. 30th+ consecutive escalation." This is the correct approach.

---

## Issue 4 (MONITORING): DEGRADED Backlog Accumulation Rate

**Current backlog**: 22 unresolved flowdays. Approximate daily accumulation rate: 1 per failed cloud-execution day.

**If whitelist is resolved**: The 22-day backlog requires running `fetch_pnl_data.py` for each date sequentially. Each run takes approximately 5-10 minutes. Total backfill time: ~2-4 hours of sequential execution. Agent should batch-run backfill on resolution day and update all 22 reports.

**Backfill priority list** (from Jul 10 report):
2026-05-23, 2026-05-25, 2026-05-26, 2026-05-27, 2026-05-28, 2026-05-30, 2026-06-01, 2026-06-02, 2026-06-03, 2026-06-09, 2026-06-11, 2026-06-16, 2026-06-17, 2026-06-21, 2026-06-25, 2026-06-27, 2026-06-29, 2026-07-03, 2026-07-08, 2026-07-09, 2026-07-10, 2026-07-11.

---

## Success Metrics for W28 Plan

| Item | Success Criterion | Deadline |
|---|---|---|
| Ascend whitelist resolved | Cloud IP whitelisted; first successful automated run | User-dependent |
| DA bid/offer root cause documented | `da-bid-row-diagnosis.md` created | First PRODUCTION day |
| DEGRADED reports continue being filed precisely | Failure count, backlog list, root cause note included | Every DEGRADED day |
| Backfill executed on resolution day | All 22+ backlog dates have PRODUCTION reports | Day of whitelist resolution |
