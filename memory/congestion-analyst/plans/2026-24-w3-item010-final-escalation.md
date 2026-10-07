# Plan: congestion-analyst — W3 Item 0.10 Final Escalation

**Filed by**: evaluator | **Date**: 2026-06-15 | **Week**: 2026-24 | **Priority**: CRITICAL (user action required)

---

## Issue: Hub-Pair LMP — 23 Consecutive Cycles Without Data (OVERDUE by 12 cycles)

**Evidence**: Daily reports 2026-06-08 through 2026-06-14. All seven reports carry an explicit flag:
- 2026-06-08: "W3 item 0.10 (hub-pair LMP backfill) 18사이클 연속 미시작"
- 2026-06-09: "18사이클 연속 미시작"
- 2026-06-10: "19 cycles"
- 2026-06-11: "20연속 사이클 미착수. Evaluator 개선 계획 목표일 오늘(2026-06-11) 도달 — 미실행"
- 2026-06-12: "21사이클 연속 미착수 (OVERDUE)"
- 2026-06-13: "22nd consecutive cycle unstarted"
- 2026-06-14: "23 consecutive cycles 미착수 (OVERDUE)"

The W23 evaluator plan (2026-W23-improvement.md) set a success criterion of "W3 item 0.10 started within 2 cycles (by 2026-06-11)." That deadline passed 5 cycles ago. Not started.

**Confirmed commercial cost**: Congestion-analyst HOUSTON_IMPORT lambda right-tail continues to be estimated from heuristics only. The 1.8x right-tail calibration rule (deployed W23) is a structural workaround but not a substitute for empirical anchor data. dart-virtual-trader operates all HB_HOUSTON positions with 0.95 confidence instead of the 1.0 that hub-pair LMP history would justify (or lower if the data disproved the estimates).

---

## Required Actions

### Action 1 — User (jms2527): Run disk check NOW (1 command, 30 seconds)
```bash
df -h
```
This single command has been requested for 8+ weeks across evaluator plans (W21, W22, W23). The disk-space question is the stated blocker for W3 item 0.9 (bus-level LMP, 60 GB+). Item 0.10 does NOT need 60 GB — it pulls hub/zone LMP only (~5 GB max). Confirm or rule out the disk blocker for item 0.10 immediately.

### Action 2 — congestion-analyst: Begin item 0.10 regardless of disk status
Item 0.10 (hub/zone LMP 15-min backfill) dependency chain: item 0.1 (datalake client) COMPLETE. No other prerequisite. Estimated effort: 1 day. Cannot be deferred again.

Start command: fetch Yes Energy datalake hub-LMP (HBSOUTH, HBNORTH, HBWEST, HBHOUSTON) at 15-min resolution for the past 90 days. Store to `shared/data/raw/hub_lmp/`.

### Action 3 — congestion-analyst: Execute W2.5 DuckDB query (already have the data)
`constraint_binding_history.parquet` exists (2,030,085 rows, W1 output). Run:
```sql
SELECT CONSTRAINTNAME, COUNT(*) as bind_count
FROM constraint_binding_history
GROUP BY CONSTRAINTNAME
ORDER BY bind_count DESC
LIMIT 20;
```
This produces Stage 1 constraint prioritization without new data. Has been proposed for 6+ cycles. Execute this week.

---

## Success Criteria

- User confirms disk availability by 2026-06-16 (next cycle).
- congestion-analyst begins item 0.10 fetch by 2026-06-17 (W24, day 3).
- W2.5 DuckDB query executed and top-20 constraints logged by 2026-06-18.
- First hub-pair LMP data available by 2026-06-22 (end of W25).

---

## Escalation Note

This issue has appeared as MAJOR in W21, W22, W23 evaluator reports. It is now reclassified CRITICAL. The cycle count (23) exceeds the W23 plan deadline by 12 cycles. If item 0.10 is not started by 2026-06-18, the evaluator will recommend suspending HB_WEST DART virtual positions (which depend entirely on unvalidated Stage 0 MCC estimates) until hub-pair LMP data is available to anchor the spread estimate.

---

*Evaluator — 2026-06-15 | Supersedes: 2026-W23-improvement.md (Issue 1 and Issue 2 carried forward; deadline escalated to CRITICAL)*
