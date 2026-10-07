# Plan: BRIEFING_TEMPLATE.md — Fourth Consecutive Miss, Escalated to Critical

Week: 2026-34
Priority: CRITICAL (escalated per W33 plan clause; 4th consecutive miss)
Issue: `memory/market-analyst/BRIEFING_TEMPLATE.md` was not created in W34. W33 plan (`2026-33-briefing-template-third-miss.md`) stated: "escalation to Critical if W34 missed."

## Miss History

| Week | Status |
|---|---|
| W31 | MAJOR — first required |
| W32 | MAJOR — 2nd consecutive miss |
| W33 | MAJOR — 3rd consecutive miss; escalation clause added |
| W34 | CRITICAL — escalation clause triggered (4th miss) |

## What BRIEFING_TEMPLATE.md Must Contain

The file already exists conceptually in the briefing outputs (content has been strong throughout W32-W34). The task is to formalize it into a reference document:

```markdown
# Market Analyst Briefing Template

## Section Order (Mandatory)
1. Headline (max 2 sentences: demand peak + primary structural driver)
2. Demand & Supply (load average, peak HE, net load shape)
3. Solar Profile (ramp rate, plateau duration, cliff HE)
4. Net Load Shape and Critical Hours (trough HE, evening ramp MW range)
5. Capacity Margin / Scarcity Risk (cap-out MW, scarcity HEs)
6. Price Outlook (all 6 windows: overnight, morning ramp, midday, afternoon, evening ramp, late evening)
7. AG2 / Enverus vs Yes Energy Comparison (mandatory multi-source section; note "unavailable" when applicable)
8. Risks / Watch (3-5 bullets; include Smartbidder status if DEGRADED)

## Mandatory Checks
- [ ] AG2 vs YE wind forecast comparison (if AG2 available): cite both numbers
- [ ] Enverus vs YE NL divergence: flag if >2,000 MW
- [ ] Spread rule note: if Smartbidder DEGRADED, add caveat to Price Outlook header
- [ ] Data leakage check: all inputs are D-1 BidClose vintage only
```

## Positive Context

Analytical quality in W34 was strong:
- 7/7 correct directory
- 6/7 learnings
- Heat wave Days 1-4 correctly tracked with NL series peaks documented
- AG2 and Enverus correctly integrated when they returned Aug 21-22 (first multi-source cycle)

The BRIEFING_TEMPLATE.md failure is purely procedural. The formalization into a named template document is essential because:
1. It makes wind divergence check mandatory and auditable (not buried in prose)
2. It prevents section drift on high-pressure days when agents abbreviate
3. It provides a checklist the reporter can verify

## W35 Action Items

1. Create `memory/market-analyst/BRIEFING_TEMPLATE.md` BEFORE first W35 cycle. This is 20-30 minutes of work — consolidate the existing briefing structure into the reference document.
2. Cite the template at the top of each W35 briefing: `*Template: memory/market-analyst/BRIEFING_TEMPLATE.md*`

Success criteria: File exists at `memory/market-analyst/BRIEFING_TEMPLATE.md` by 2026-08-25 07:30 CT.
Deadline: W35 Day 1 (2026-08-25).
Owner: market-analyst.
