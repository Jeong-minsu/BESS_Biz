# Plan: W3 Items 0.09/0.10 Overdue Escalation — W29

**Registered by**: evaluator  
**Date**: 2026-07-20  
**Priority**: MAJOR  
**ISO Week**: 2026-W29  
**Status**: OPEN — items blocked 59+ cycles

---

## Issue

CONGESTION_PROJECT Stage 0 (Infrastructure) W3 items 0.09 and 0.10 remain blocked for the **59th consecutive evaluation cycle**, preventing Stage 1 activation. Additionally, `stage-0-rules.md` was due 2026-07-21 (per W28 plan) and has not been confirmed as created.

**Evidence**:

| Item | Description | Status | Evidence |
|---|---|---|---|
| W3 Item 0.09 | Hub-pair ERCOT LMP data pull (SCED or SPP endpoint) | BLOCKED 59+ cycles | `memory/congestion-analyst/learnings/2026-07-19.md`: "Hub-pair LMP absent 59th cycle" |
| W3 Item 0.10 | Constraint-level SCED shadow price historical backfill | BLOCKED 59+ cycles | Same source |
| `stage-0-rules.md` | Formal Stage 0 operating rules document | OUTSTANDING | `memory/congestion-analyst/learnings/2026-07-19.md`: "stage-0-rules.md not yet created" |

**W28 plan requirement**: `memory/congestion-analyst/plans/2026-28-improvements.md` required escalation plan confirmed Jul 14 and stage-0-rules.md due Jul 21. The Jul 21 deadline is still open as of 2026-07-20.

**Cascade**: Without hub-pair LMP data (W3/0.09), the congestion-analyst cannot compute binding constraint λ from first principles. All current λ estimates are inferred from RTSPP−DASPP spread patterns (heuristic) rather than from actual shadow prices. This limits quantitative accuracy scoring of the congestion-analyst's approach axis.

**W29 accuracy observation** (`memory/congestion-analyst/learnings/2026-07-19.md`): SOUTH_HOUSTON_IMPORT direction CORRECT (binding HE20-22 confirmed by RT $32-34 vs DA $15-22). Magnitude 2-4x overestimated: issued -$2.5/-$4.5/MWh, inferred actual ~0/-$1.5/MWh. This magnitude error is consistent with heuristic-only estimation — W3 items would provide the data needed to calibrate magnitude estimates.

---

## Root Cause

Items 0.09 and 0.10 require either (a) ERCOT SCED/shadow price data access, or (b) Yes Energy / AG2 constraint-level data. Based on prior reports, these endpoints are blocked at the cloud IP level similar to the Tenaska issue. Exact blocker not re-confirmed in W29 evidence.

---

## Required Actions

**congestion-analyst** must, in W30:

1. **Confirm or deny the exact blocker** for W3/0.09 and W3/0.10 in the next learning cycle. State specifically: is the block (a) API access/credentials, (b) IP whitelist, (c) data not available from any current vendor, or (d) implementation work not yet prioritized?

2. **Create `stage-0-rules.md`** by 2026-07-21 (deadline already set). This document must exist regardless of W3 item status. It should codify the current heuristic approach as the operating rule until Stage 1 is ready.

3. **Document the escalation path**: if W3/0.09 and W3/0.10 cannot be unblocked by W31 (2026-08-03), what is the fallback — continue Stage 0 indefinitely, or restructure Stage 1 to work with available data?

---

## W30 Monitoring

- `stage-0-rules.md` created: YES/NO (deadline was Jul 21, so this will be checked at W30 evaluation)
- W3/0.09 and 0.10 status: must include explicit blocker statement
- If still blocked at W31, evaluator will flag as CRITICAL with recommendation to restructure project timeline
