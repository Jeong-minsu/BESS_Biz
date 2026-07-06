# Plan: pnl-manager — DA Bid/Offer 0 Rows Inquiry
**Week**: 2026-27 | **Priority**: MAJOR | **Registered by**: evaluator

---

## Issue

Tenaska endpoints for DA Energy Bid (`ERCOT_DA_Awards_Prices`) and DA Energy Offer (`DA_Awards_Prices_All`) have returned 0 rows on every PRODUCTION (successfully fetched) day in the evaluation period. This has persisted for at least 5 consecutive production days across W26–W27.

**Evidence:**

| Date | Tenaska Status | DA Bid rows | DA Offer rows |
|---|---|---|---|
| 2026-06-30 | PRODUCTION | 0 rows | 0 rows |
| 2026-07-01 | PRODUCTION | 0 rows | 0 rows |
| 2026-07-02 | PRODUCTION | 0 rows | 0 rows |
| 2026-07-04 | PRODUCTION (July 2 data) | 0 rows | 0 rows |
| 2026-07-05 | PRODUCTION (July 5) | 0 rows | 0 rows |

**Operational consequence**: DART Virtual revenue cannot be separately tracked from DA Energy. When DA bid/offer data is 0 rows, pnl-manager reports "DART Virtual: N/A (DA Energy에 내재)." This makes dart-virtual-trader hit rate validation structurally impossible from the P&L side.

**Unknown**: Is this a Tenaska API issue (endpoints not returning data), a script configuration issue (`fetch_pnl_data.py` calling wrong endpoint or wrong parameters), or an expected behavior (ERCOT does not publish DA bid data at this granularity via Tenaska)?

---

## Action Items

1. **Agent action (immediate — THIS CYCLE)**: In the next `fetch_pnl_data.py` execution, add explicit logging of: (a) the exact URL called for DA bid/offer endpoints, (b) HTTP status code returned, (c) whether the 0 rows are from an empty response body or a non-200 response, (d) whether the endpoint requires different date parameters vs Battery-Settlement-Details.

2. **Agent action (by 2026-07-10)**: Write `memory/pnl-manager/learnings/da-bid-row-diagnosis.md` with findings from the above logging. Include: confirmed root cause, or "inconclusive — user action needed" with specific question.

3. **User action (if inconclusive)**: Confirm with Tenaska/Ascend whether DA bid/offer data is available via the PTP API and under what conditions. If available, provide correct endpoint configuration.

4. **Agent action (if script bug)**: Fix `fetch_pnl_data.py` DA bid/offer section in the next available execution window. Document what was changed.

---

## Success Metric

- Root cause documented by 2026-07-10: CLOSED (regardless of fix availability)
- DA bid/offer data successfully populated on at least 1 day in W28: FULL CLOSED
- Diagnosis doc written, root cause = "Tenaska does not provide this data": CLOSED (expected behavior confirmed)
