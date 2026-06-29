# Plan: Tenaska Whitelist Failure — CRITICAL Escalation
**Agent**: pnl-manager
**Week**: 2026-W26
**Priority**: CRITICAL
**Registered by**: evaluator (2026-06-29)
**Deadline**: User action required (no agent-only resolution path)

---

## Issue

The cloud-IP / Ascend whitelist failure pattern is now in its **17th occurrence** across approximately 34 operating days. Failure rate: **~50%**. This is a persistent infrastructure failure, not a transient data issue.

W25 plan `2026-25-tenaska-whitelist-escalation.md` was registered but required user action (re-whitelisting the cloud execution IP with Ascend). No resolution has occurred as of 2026-06-29.

---

## Quantitative Impact

| Metric | Value |
|---|---|
| Total Tenaska fetch failures | 17 |
| Operating days elapsed | ~34 |
| Failure rate | ~50% |
| Outstanding DEGRADED flowdays | 16 |
| Oldest unresolved DEGRADED day | 2026-05-23 (37 days ago) |
| Cascaded impact: agents unable to compute | bess-optimizer (execution delta), dart-virtual-trader (hit rate), congestion-analyst (settlement validation), evaluator (Approach scores) |

Outstanding DEGRADED days: 2026-05-23, 2026-05-25, 2026-05-26, 2026-05-27, 2026-05-28, 2026-05-30, 2026-06-01, 2026-06-02, 2026-06-03, 2026-06-09, 2026-06-11, 2026-06-16, 2026-06-17, 2026-06-21, 2026-06-25, 2026-06-27.

---

## Cascade Effects

This failure is the root cause of several other W26 issues:
- bess-optimizer "Open Issue 1" (execution delta unresolvable without actuals)
- dart-virtual-trader hit rate completely uncomputable
- congestion-analyst settlement validation impossible
- evaluator Approach scores partially degraded for 4 agents
- P&L reconstruction for 16 days impossible without backfill

---

## Required Actions (User-Level)

### Action 1 (User): Re-whitelist Cloud IP with Ascend
Contact the Ascend/Tenaska representative to add the current cloud execution IP to the Tenaska PTP whitelist. Provide the IP address used in `shared/scripts/fetch_pnl_data.py` execution environment.

**Script**: `shared/scripts/fetch_pnl_data.py`
**Error pattern**: "Cloud execution IP not on Ascend/Tenaska whitelist. Interactive endpoint discovery not possible in cloud environment."
**First occurrence**: 2026-05-21 (5+ weeks ago, 1 day after first escalation on 2026-05-22)

### Action 2 (User): Backfill 16 Outstanding DEGRADED Days
Once whitelist is resolved, run `shared/scripts/fetch_pnl_data.py` for each of the 16 outstanding DEGRADED flowdays, then re-run pnl-manager to regenerate those reports.

Priority backfill order (most recent first, to support current evaluation cycles):
1. 2026-06-27, 2026-06-25
2. 2026-06-21, 2026-06-17, 2026-06-16, 2026-06-11, 2026-06-09
3. 2026-06-03, 2026-06-02, 2026-06-01, 2026-05-30
4. 2026-05-28, 2026-05-27, 2026-05-26, 2026-05-25, 2026-05-23

### Action 3 (pnl-manager): Interim Tracking
Until resolved, pnl-manager will:
- Continue cumulative DEGRADED day count in every report header
- Flag the cascade impact on dependent agents in each DEGRADED report
- Document in `memory/pnl-manager/data-quality.md` every new occurrence

---

## Secondary Issue: DA Bid/Offer 0 Rows

A secondary data pattern has emerged: `DA_Energy_Bid` and `DA_Energy_Only_Offer` endpoints return 0 rows on at minimum 4 confirmed days (2026-06-08, 2026-06-12, 2026-06-22, 2026-06-26). This does NOT block settlement reporting (DA_Energy_Amt is present in Battery-Settlement-Details) but prevents bid/offer detail analysis.

pnl-manager should flag this to the user if it persists beyond **5 consecutive production days**. If confirmed at next available data pull, notify Tenaska/Ascend that the DA bid/offer endpoint may have a configuration issue.

---

## Success Criteria

- [ ] User contacts Ascend to re-whitelist cloud execution IP
- [ ] Zero new DEGRADED days in next 7-day cycle (W27)
- [ ] Backfill of 16 DEGRADED days initiated within 2 weeks of whitelist resolution
- [ ] DA bid/offer 0-row pattern flagged to Tenaska if confirmed ≥5 consecutive production days

---

## History

- W22 (2026-05-22): First escalation registered
- W23: Escalation continued
- W24: Escalation continued
- W25: `2026-25-tenaska-whitelist-escalation.md` registered; user action required
- W26: 17th failure, 50% rate, 16 DEGRADED days — re-escalating CRITICAL; adding 2-week backfill deadline
