# Plan: bess-optimizer Rule 8 RT Dispatch Incident — Day 129 Unresolved
# Week 2026-41 | Priority: MAJOR | Registered: 2026-10-12

## Issue

Jun 5, 2026 Rule 8 incident: −$4,520 from prohibited AS during energy dispatch hours.
As of W41 (Oct 12): Day 129 since incident. Root cause never confirmed via Tenaska data.

Rule 8 states: No AS bids during charge/discharge energy hours.
Jun 5 violation: AS bids were submitted (or cleared) during an energy dispatch hour, causing negative P&L.

Status of data needed for diagnosis:
- Tenaska PTP: HTTP 401 since May 21 → Jun 5 actuals NOT recoverable until whitelist restored
- Smartbidder benchmark: MSAL expired Jul 25 → benchmark comparison NOT available
- Result: Root cause cannot be confirmed from current data availability

## W41 Context

W41 reports show Rule 8 PROHIBITED BID SLOTS section is now present in bess-optimizer outputs:
- Oct 8 report: explicit Rule 8 gate with charge/discharge hour identification
- Oct 9 report: Rule 8 gates applied to bid slot allocation
- Oct 11 report: Rule 8 applied with PANHANDLE noted

This confirms the rule is operationally applied going forward. The unresolved item is the historical confirmation and root cause documentation.

## Action Required

### Agent (when Tenaska data becomes available):
1. On first successful Tenaska data fetch (post-whitelist restoration), retrieve Jun 5 flowday data.
2. Identify whether the −$4,520 was due to:
   a. AS cleared during energy hour (market mechanism), OR
   b. Agent recommendation error (AS bid in hours with DA energy), OR
   c. ERCOT dispatch instruction override
3. Document root cause in `memory/bess-optimizer/learnings/rule8-incident-postmortem.md`.
4. Confirm Rule 8 gate prevents recurrence by checking Oct 6–11 bid slots against the gate.

### Agent (current — no external dependency):
5. Document the Rule 8 gate logic explicitly in `memory/bess-optimizer/standing-rules.md`:
   - Prohibited bid combination: AS + DA energy in same hour
   - Prohibited bid combination: AS + RT energy in same hour
   - If SoC < 50 MWh: No Reg-Down during discharge hours
   - Gate verification: cross-check every hourly position before output

### User:
- Whitelist restoration (Tenaska PTP HTTP 401) remains P0 blocker for incident confirmation.
- Jun 5 is now 22 days BEFORE the Tenaska data gap onset (May 21 was the gap start; Jun 5 is after).
  - Correction: Tenaska 401 onset was May 21, 2026. Jun 5 is after that date, so Jun 5 data is in the gap.
  - This means Jun 5 actuals are in the 22+ flowday unconfirmed window.
  - P0 action: whitelist restoration + backfill retrieval from Jun 5.

## Success Criteria

RESOLVED when: Jun 5 Tenaska data retrieved AND root cause documented in learnings postmortem.
PARTIALLY RESOLVED when: Rule 8 gate formally documented in standing-rules.md (no external dependency).

## References

- W40 plan (carry-forward): `memory/bess-optimizer/plans/2026-W40.md`
- standing-rules.md: `memory/bess-optimizer/standing-rules.md` (verify current content)
- pnl-manager Tenaska status: `reports/daily/pnl/2026-10-09.md` (Day 77+ DEGRADED)
