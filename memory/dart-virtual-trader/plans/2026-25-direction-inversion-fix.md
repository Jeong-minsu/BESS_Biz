# Plan: Direction Inversion Fix — Reasoning vs Position Alignment (W25)

**Registered by**: evaluator
**Week**: 2026-25
**Priority**: CRITICAL
**Status**: OPEN — agent to implement immediately
**Agent**: dart-virtual-trader

---

## Problem Statement

On two consecutive cycles (2026-06-20 Saturday, 2026-06-21 Sunday), dart-virtual-trader issued
DEC positions (Long DA / Short RT — profits when RT > DA) while simultaneously stating reasoning
that DA was expected to exceed RT (e.g., "P(DA>RT) = 0.58-0.62, DA expensive").

This is an internal contradiction. By the project spread convention (spread = DA − RT):
- Positive spread => DA expensive => INC signal (Short DA / Long RT)
- Negative spread => RT expensive => DEC signal (Long DA / Short RT)

Issuing DEC when the stated reasoning says "DA>RT" means the position will lose money
in exactly the scenario the agent expects to occur.

Per dart-virtual-trader learnings 2026-06-21.md:
"Entire P&L (+$269) came from HE13 which was SKIP'd. DEC at HE19-21 likely all-loss.
Hit rate: ~14-25% confirmed positions won."

This is not a calibration issue — it is a logic inversion that bypasses the core decision rule.

---

## Root Cause Analysis

Two competing hypotheses (agent should determine which applies):

**Hypothesis A — Sign Error in P(DA>RT) Mapping**:
When the agent reads P(DA>RT) from Smartbidder (a value expressing probability that DA > RT),
it may be applying the position rule as "if high P(DA>RT), issue DEC" — which is inverted.
High P(DA>RT) means DA is expected to be expensive → INC (Short DA), not DEC.

**Hypothesis B — Weekend Regime Override Without Documentation**:
On weekends with Non-Spin >$8/MWh, the agent may be applying a "RT scarcity premium" override
that flips direction from INC to DEC — but the written rationale still cites the pre-flip INC logic,
making the output appear contradictory. If this override exists, it must be documented explicitly.

Per Pattern 11 (cross-agent-patterns.md), weekend RT does often exceed DA in scarcity conditions.
If the agent has internalized this pattern and is consciously issuing DEC in scarcity evenings,
it must STATE this override in the rationale (e.g., "Weekend scarcity override: DEC despite P(DA>RT)=0.62
because Non-Spin $18.43 > $8 threshold signals RT spike risk exceeding DA premium").

---

## Required Actions

### Action 1 — dart-virtual-trader agent (immediate)

Add a mandatory pre-issue validation step at the end of the position-building process:

```
FOR EACH proposed position:
  if direction == INC (Short DA / Long RT):
    assert stated_reason includes "DA > RT" or "positive spread" or "P(DA>RT) > 0.50"
  if direction == DEC (Long DA / Short RT):
    assert stated_reason includes "RT > DA" or "negative spread" or "P(DA>RT) < 0.50"
  if assertion fails:
    HALT — do not issue position — add to SKIP table with reason "Direction-reason mismatch, skipped for safety"
```

This validation must appear explicitly in the report output as a checklist line:
"Direction-reason consistency check: PASS / FAIL (positions with FAIL are skipped)"

### Action 2 — dart-virtual-trader agent (documentation)

If the agent intentionally applies a weekend scarcity DEC override (Hypothesis B), document the rule
in `memory/dart-virtual-trader/learnings/` immediately:

```markdown
## Weekend Scarcity Direction Override (NEW RULE — added YYYY-MM-DD)
When ALL of:
  - Day is Saturday or Sunday
  - Non-Spin DA > $8/MWh in target HE window
  - P(RT>DA) implied by pattern 11 > 55%
THEN: Override INC signal to DEC; document explicitly in report rationale
```

### Action 3 — dart-virtual-trader agent (learnings review)

Before the next Saturday/Sunday cycle, re-read:
- `memory/evaluator/cross-agent-patterns.md` Pattern 11
- Own learnings 2026-06-21.md section on direction inversion
- Spread convention in CLAUDE.md: "spread = DA − RT; positive => DA expensive => short DA / long RT (INC)"

---

## Success Criteria

- Zero direction-reason contradictions in W26 outputs
- Direction-reason consistency check line visible in all daily reports
- If weekend DEC override is being used, it is documented in learnings with explicit trigger conditions
- Evaluator can verify consistency between stated rationale and issued position direction in all W26 outputs

---

## Severity Note

This is classified CRITICAL because:
1. It directly causes positions to lose money in the expected scenario
2. It has occurred on 2 consecutive weekends (pattern, not isolated error)
3. It undermines the agent's ability to learn — wrong positions make hit-rate calibration impossible
4. Reporter and evaluator cannot distinguish intentional DEC from inverted INC without explicit documentation
