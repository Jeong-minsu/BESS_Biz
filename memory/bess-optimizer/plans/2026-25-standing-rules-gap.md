# Plan: Standing Rules Document — Overdue Commitment (W25)

**Registered by**: evaluator
**Week**: 2026-25
**Priority**: MAJOR
**Status**: OPEN — agent to implement by 2026-06-24
**Agent**: bess-optimizer

---

## Problem Statement

In W24 plan `2026-24-ecrs-nonspun-execution-gap.md`, bess-optimizer committed to create
`memory/bess-optimizer/standing-rules.md` by 2026-06-16. As of 2026-06-22 (W25 end), this
file does not exist. This is 6 days past the committed deadline.

The standing-rules document was intended to:
1. Formalize the ECRS exclusion rule with explicit conditions (overriding "zero clearing" heuristic)
2. Document the 0.80x RT dispatch haircut for revenue projections
3. Document the 3-data-point calibration threshold before updating parameters
4. Record the Non-Spin DA overnight premium rule (50% boost on high Non-Spin days)
5. Establish the ECRS clearing rule for June-September heat season (per Pattern 14)

Without this document, bess-optimizer's rule set is ad-hoc and cannot be:
- Referenced by other agents (dart-virtual-trader needs ECRS modifier; congestion-analyst needs NonSpin rule)
- Reviewed by evaluator for consistency
- Used as a source for self-review calibration

---

## Required Actions

### Action 1 — Create standing-rules.md (immediate)

Path: `memory/bess-optimizer/standing-rules.md`

Minimum required content (draft template):

```markdown
# bess-optimizer Standing Rules

Last updated: YYYY-MM-DD

## Rule 1: ECRS Inclusion (Summer Heat Season)
- Condition: June 1 – September 30 AND ECRS DA price > $0.50/MWh in Smartbidder forecast
- Action: Include ECRS as a competing AS product in HE07-10 (morning ramp) and HE20-24 (evening peak)
- Override: Never exclude ECRS solely because it cleared $0 on prior day(s) during June–September
- Source: evaluator Pattern 14 (W24); confirmed 4/7 W24 days ECRS cleared

## Rule 2: RT Dispatch Haircut
- Condition: All revenue projections
- Action: Apply 0.80x multiplier to DA Energy revenue projections (RT execution has historically
  differed from DA plan; actual RT P&L often exceeds or understates DA projection)
- Note: Haircut is calibrated on 2026-05-24 data; update when 3+ new PRODUCTION days available

## Rule 3: Non-Spin DA Overnight Premium
- Condition: Non-Spin DA price > $8/MWh for any HE in HE20-24 window
- Action: Flag as high-scarcity day; reduce DART virtual INC size recommendation to 50% of standard
  (coordinate with dart-virtual-trader)
- Action: Increase NonSpin clearing probability estimate by 20% for affected hours

## Rule 4: 3-Data-Point Calibration Threshold
- Condition: Before updating any multiplier (0.80x haircut, Non-Spin premium, etc.)
- Requirement: Need 3+ new PRODUCTION confirmed data points
- Do not update based on 1-2 data points

## Rule 5: DA Energy Row-Count Discrepancy
- Status: UNRESOLVED — DA Energy P&L exists without matching DA bid/offer rows
- Interim rule: Do not adjust recommendations based on this discrepancy; flag in each report
- Escalate to user if discrepancy persists > 7 consecutive cycles
```

### Action 2 — Apply ECRS Rule in Next Cycle

On 2026-06-23 (next daily cycle), if ECRS clearing is observed in Smartbidder forecast:
- Include ECRS in HE07-10 stack with the same weight as Non-Spin
- Document as "ECRS Rule 1 applied" in the recommendation

### Action 3 — Cross-Reference in Daily Reports

In each daily recommendation, include a line:
"Standing rules applied: [list of rules by number that affected this day's recommendation]"
"Standing rules not applicable today: [list of rules that did not trigger]"

---

## Success Criteria

- `memory/bess-optimizer/standing-rules.md` exists by 2026-06-24
- All 5 rules above (or agent's equivalent) documented with explicit conditions and actions
- ECRS Rule 1 applied in at least 1 W26 daily cycle
- Standing rules cross-reference visible in W26 daily recommendation outputs

---

## Note

The Pattern 15 cross-agent finding (structural changes deferred indefinitely) applies here.
This is the second evaluator cycle noting the standing-rules deadline as missed.
If not created by 2026-06-29, this will be escalated to CRITICAL.
