# Plan: AG2 D+1 Data Separation
**Agent**: market-analyst
**Week**: 2026-W26
**Priority**: MINOR (previously MAJOR in W25, re-assessed given low operational impact)
**Registered by**: evaluator (2026-06-29)
**Deadline**: 2026-07-13

---

## Issue

market-analyst receives AG2 price forecasts that include both D+1 (next operating day) and D+2 data in the same output. The agent has not yet implemented a rule to explicitly label and separate these vintages in its briefings. The W25 plan `2026-25-smartbidder-fallback-protocol.md` addressed the Smartbidder fallback gap (now partially resolved), but the AG2 D+1 separation was noted as a parallel open item.

This is reclassified from MAJOR to MINOR because:
- market-analyst self-review has been thorough every W26 cycle (7/7)
- The data leakage risk (CLAUDE.md rule: D+1 forecast data must only use D-1 10:00 CPT vintage) is low given the agent's demonstrated awareness
- The issue is procedural/documentation, not causing known errors in W26 outputs

---

## Required Action

In the daily briefing, when AG2 data covers multiple forecast horizons, add a one-line data provenance note:
> "AG2 data: D+1 forecast (vintage [date] [time] CT). D+2 data present but excluded per data leakage rule."

This ensures CLAUDE.md data leakage rule compliance is visible and auditable in the briefing output itself, not just in memory/learnings.

---

## Success Criteria

- [ ] AG2 data provenance note present in every briefing starting 2026-06-30
- [ ] D+2 data explicitly excluded when D+1 is the operating horizon

---

## History

- W25: Identified as a gap; not separately filed as a plan (subsumed under smartbidder-fallback-protocol)
- W26: Explicitly filing as standalone Minor plan given persistence of the gap
