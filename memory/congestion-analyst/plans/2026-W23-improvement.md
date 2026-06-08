# Plan: congestion-analyst Improvement — Week 2026-W23

**Filed by**: evaluator | **Date**: 2026-06-08 | **Priority**: MAJOR (user action required for W3 blocker)

---

## Issue 1 (MAJOR, ESCALATING): W3 Hub-Pair LMP — 18 Consecutive Cycles Without Data

**Evidence**: `memory/congestion-analyst/learnings/2026-06-07.md` and `memory/congestion-analyst/plans/stage-progress.md`. Hub-pair LMP (W3 item 0.10) has been absent for 18 consecutive daily cycles. The disk space verification (required before beginning W3 item 0.9, the large bus_lmp backfill) has blocked the entire W3 track. However, item 0.10 (hub/zone LMP 15-min, ~1 day effort, dependency: 0.1 only) does NOT require the 60 GB+ disk reservation that 0.9 needs. Item 0.10 can begin NOW.

**Confirmed commercial impact**: The congestion-analyst self-review (2026-06-07) demonstrates direct commercial impact: HOUSTON_IMPORT conditional E[lambda | binding] P90 was called at $15/MWh; realized value was $24-26/MWh — 60-73% underestimate on three consecutive binding cycles. The agent's own analysis attributes this systematic underprediction directly to the absence of empirical hub-pair LMP data ("the true constraint shadow price distribution has a heavier right tail than the heuristic captures without empirical anchor data").

**Required actions**:

1. **User action — disk verification (P1)**: User (jms2527) must confirm available disk space on the execution environment with `df -h`. This has been the stated blocker for 7+ weeks. The evaluator escalates this to P1 for user action. If disk space is insufficient: identify what can be purged or archived to create 60+ GB headroom for item 0.9.

2. **Agent action — begin item 0.10 immediately**: Item 0.10 (hub/zone LMP 15-min) requires only item 0.1 (datalake client, already complete) and approximately 1 day of effort. It has NO large storage prerequisite (hub-level LMP, not bus-level). The agent must begin 0.10 in the next cycle regardless of the 0.9 disk status. The 18-cycle gap has direct financial consequence.

3. **W2.5 DuckDB query — execute this week**: The `constraint_binding_history.parquet` (2,030,085 rows, W1 output) supports a top-N binding frequency query using only existing data. This query (top 20 constraints by historical binding frequency) has been proposed for 5+ cycles and not executed. It requires no new data. Execute using DuckDB: `SELECT CONSTRAINTNAME, COUNT(*) as bind_count FROM constraint_binding_history GROUP BY CONSTRAINTNAME ORDER BY bind_count DESC LIMIT 20`. This will provide Stage 1 constraint prioritization without waiting for W3.

---

## Issue 2 (MAJOR): HOUSTON_IMPORT Lambda Right-Tail Systematic Underprediction — Apply Calibration Fix

**Evidence**: `memory/congestion-analyst/learnings/2026-06-07.md`. Three consecutive cycles where realized GKS RT premium at HE19-21 exceeded the conditional P90 lambda estimate: the issued conditional E[lambda | binding] P90 = $15/MWh was below the realized $24-26/MWh. The agent derived a concrete calibration fix: "when Non-Spin DA at HE21-22 exceeds $4/MWh AND Enverus NL ramp HE18-HE20 exceeds 9,000 MW, apply 1.8x multiplier to HOUSTON_IMPORT conditional E[lambda] P90."

**Required action**: Implement this provisional right-tail calibration rule immediately. Apply the 1.8x multiplier as a Stage 0 carry-forward rule in the next daily congestion report where both conditions are met. Document in learnings when the rule is triggered and track predicted vs realized for 3+ cycles to validate the multiplier.

---

## Issue 3 (MINOR): P(DA>RT) Signal — Confirmed Unreliable for GKS Physical Dispatch

**Evidence**: `memory/congestion-analyst/learnings/2026-06-07.md`. The P(DA>RT) metric is a hub-level probability from Smartbidder that does not account for GKS nodal MCC. The agent correctly identified in W23 that P(DA>RT) at hub level was wrong 2/2 times for GKS physical dispatch direction at HE20-21. Decision to stop using P(DA>RT) as a GKS physical dispatch direction signal was documented and correct.

**Required action**: Confirm this decision is applied in all future daily congestion outputs. Specifically: the GKS MCC view section should state E[MCC] separately from hub-level DA-RT spread direction. Do not use Smartbidder P(DA>RT) as a directional signal for GKS physical operations.

---

## Success Criteria

- W3 item 0.10 (hub/zone LMP 15-min) started within 2 cycles (by 2026-06-11).
- W2.5 DuckDB top-20 binding frequency query executed and results logged in learnings within 3 cycles.
- HOUSTON_IMPORT 1.8x right-tail calibration rule applied in next applicable cycle.
- P(DA>RT) de-listed as GKS physical dispatch direction signal in all subsequent congestion reports.

---

*Evaluator — 2026-06-08 | Supersedes: 2026-22-w3-disk-verification-blocker.md (extends to include confirmed commercial impact and right-tail lambda calibration fix)*
