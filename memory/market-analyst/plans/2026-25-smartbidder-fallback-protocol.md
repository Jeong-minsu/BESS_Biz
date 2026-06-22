# Plan: Smartbidder Fallback Protocol (W25)

**Registered by**: evaluator
**Week**: 2026-25
**Priority**: MAJOR
**Status**: OPEN — agent to implement by 2026-06-24
**Agent**: market-analyst

---

## Problem Statement

Smartbidder DA run was absent on at least 3 days in W25 (2026-06-16, 2026-06-20, 2026-06-21).
On these days, market-analyst could not provide:
- P(DA>RT) by hour (the primary input to dart-virtual-trader's INC/DEC decision)
- DA Non-Spin, RRS, ECRS price forecasts (the primary inputs to bess-optimizer AS stack)
- DA-RT spread distribution by hour

The Smartbidder absence is partly systemic (MSAL credential issues, 12-month expiration cycle),
and partly episodic (weekend lower-priority runs, off-cycle timing).

Currently, when Smartbidder is absent, market-analyst provides qualitative estimates only
("price likely elevated" / "scarcity possible") without the quantitative structure downstream
agents require. This is not sufficient — it forces dart-virtual-trader and bess-optimizer
to operate without their primary quantitative inputs.

---

## Required Actions

### Action 1 — Define a Formal Fallback Hierarchy

When Smartbidder DA run is absent, market-analyst must follow this explicit fallback sequence:

**Level 1 — AG2 WSI (primary fallback)**:
Read `skills/fetch-ercot-data/SKILL.md` for AG2 endpoint. AG2 provides:
- Hourly DA price forecast (24-hour vector)
- Net load forecast by hour
- Derive implicit P(DA>RT): if AG2_DA[HE] > (Yes_Energy_RT_avg + buffer), P(DA>RT) > 0.55

**Level 2 — Yes Energy Historical Pattern (secondary fallback)**:
Use the same-DOW (day-of-week) prior 4-week average for the equivalent HE:
- Retrieve from `shared/data/forecasts/` the last 4 Monday (or Saturday/Sunday) Yes Energy
  DA and RT settlement data
- Compute HE-level P(DA>RT) as fraction of prior 4 weeks where DA > RT
- Label as "HISTORICAL PATTERN (4-week DOW average)" — not a forecast

**Level 3 — Non-Spin Proxy for AS (tertiary fallback)**:
If no AS data available, use the prior-week same-DOW Non-Spin DA price as the baseline estimate.
Apply summer multiplier +15% if forecasted NL peak > 65 GW (heat event).
Label as "PROXY ESTIMATE — Smartbidder absent, prior-week same-DOW".

### Action 2 — Mandatory Output Format When Fallback Active

When any fallback level is used, the market briefing must include a table:

```markdown
## Quantitative Estimates (FALLBACK MODE — Smartbidder absent)

| Hour | P(DA>RT) Source | P(DA>RT) | DA Price Est. | Non-Spin Est. | Confidence |
|------|-----------------|----------|---------------|---------------|------------|
| HE20 | AG2 WSI proxy   |   0.55   | $52/MWh       | $8.40/MWh     | LOW        |
| HE21 | AG2 WSI proxy   |   0.58   | $61/MWh       | $9.10/MWh     | LOW        |
| HE22 | Historical DOW  |   0.51   | $55/MWh est.  | $7.80/MWh     | VERY LOW   |
```

This allows dart-virtual-trader to make explicit decisions rather than skip entirely.
SKIP due to Smartbidder absence is acceptable only if ALL three fallback levels are unavailable.

### Action 3 — AG2 WSI Retry on Failure

On 2026-06-16, both Smartbidder and AG2 were absent. market-analyst learnings noted this
but did not implement a retry. Going forward:

If AG2 fails on first attempt, retry once after 15 minutes before declaring it absent.
Log the retry attempt and result in the briefing data quality table.

### Action 4 — Escalate MSAL Renewal

When Smartbidder is absent for 3+ consecutive cycles, market-analyst should add a flag
to the briefing top-of-report banner:

"SMARTBIDDER ABSENT 3+ CONSECUTIVE CYCLES — MSAL credential renewal may be required.
User action: contact Ascend rep for client_secret renewal."

---

## Success Criteria

- Next Smartbidder-absent day: fallback table present in briefing with at least Level 1 or Level 2 estimates
- dart-virtual-trader receives a quantitative P(DA>RT) estimate (even if labeled LOW confidence) on all days
- bess-optimizer receives a Non-Spin DA estimate on all days
- MSAL escalation flag appears after 3 consecutive absent cycles

---

## Note on Weekend Direction Error

The 2026-06-21 learnings identified an evening ramp spike miss: congestion-analyst called
HOUSTON_IMPORT HIGH but RT actually crashed. market-analyst framed this as "peak likely elevated"
without flagging the simultaneous high-GR_WEST condition.

Separate cross-reference: when GR_WEST forecast > 15,000 MWh for any HE in HE19-23 window,
market-analyst must add a note: "High GR_WEST wind may suppress evening RT — spike scenario
confidence reduced per evaluator pattern (W25 finding)." This connects to the
congestion-analyst weekend-high-wind-haircut plan.
