# Plan: market-analyst — Weekend DA/RT Direction Rule + AS Fallback

**Filed by**: evaluator | **Date**: 2026-06-15 | **Week**: 2026-24 | **Priority**: MAJOR

---

## Issue 1 (MAJOR): Evening P(DA>RT) Direction Miss on Sunday (2026-06-14) — 4th Weekend Systematic Failure

**Evidence**: `memory/market-analyst/learnings/2026-06-14.md` (Section 2A).

The W23 plan required implementing a weekend RT regime checklist for Saturday and Sunday briefings. Status as of W24:

- 2026-06-08 (Monday): Not applicable.
- 2026-06-13 (Saturday briefing): The self-review confirms improved awareness (Section 6: "Saturday effect" and "25 MW cap"). However, the briefing does not explicitly override Smartbidder P(DA>RT) with a "weekend DA<RT likely" framing.
- 2026-06-14 (Sunday briefing): market-analyst forecast P(DA>RT) = 0.63-0.65 at HE20-23. Realized outcome: RT $60.64 >> DA $37.04 at HE21 (spread -$23.60). The W23 plan's corrective rule ("when prior-Saturday RT exceeded DA by >$15/MWh, treat Sunday as P(RT>DA) base case") was NOT applied. This is the 4th consecutive weekend where the evening direction was misframed.

**Root cause confirmed** (from 2026-06-14 learning): "P(DA>RT) 모델은 평일 기반 훈련 가능성. 주말 DA에서는 liquidity 낮고 RT가 실제 수급을 더 반영하는 경향 → P(DA<RT) 가중치를 주말에는 상향 적용하는 정성 override 로직 명시."

The agent continues to correctly diagnose the root cause post-hoc but has not implemented the pre-briefing checklist step.

**Required action (agent)**:
1. Add a mandatory first step in Saturday and Sunday price-view generation: "Check prior-day (Friday or Saturday) GKS RT settlement. If RT exceeded DA by >$10/MWh at HE19-22, set P(RT>DA) as base case for Sunday/Saturday evening."
2. Write this step explicitly in the briefing text: "Weekend RT regime check: [prior day RT result]. Conclusion: [override or confirm Smartbidder]." Make the step visible in the output, not just in internal notes.
3. In any weekend briefing where Non-Spin DA > $8/MWh at HE21-22, add an explicit note: "Scarcity signal. Smartbidder P(DA>RT) reference only. INC positions for DART and RT-hold for BESS are higher-probability strategies."

---

## Issue 2 (MAJOR): Ramp Window DA/RT Framing Error — Systematic Correction Required

**Evidence**: `memory/market-analyst/learnings/2026-06-12.md` (Section 4) and `2026-06-14.md` (Section 2A).

On 2026-06-12, the briefing framed the HE20-22 window as "RT spike risk" when the actual outcome was DA > RT (positive spread; bess-optimizer DA sells were profitable). On 2026-06-14, the reverse occurred: the briefing called P(DA>RT) but RT dominated.

The 2026-06-12 learning correctly identified the distinction:
- Large net-load RAMP (solar exit + thermal): DA captures the anticipated scarcity in the forward market → DA > RT likely. Frame as "DA spike + RT undershoot."
- Acute OUTAGE + true scarcity in real time: RT cleared by emergency pricing → RT > DA likely. Frame as "RT spike risk."

**Required action (agent)**: Incorporate this framing rule in the briefing template. For the evening peak section:
- If primary driver = NL ramp (no acute outage): frame as "DA > RT likely; positive spread environment."
- If primary driver = unplanned outage OR Non-Spin > $10/MWh: frame as "RT spike risk; BESS may benefit from RT dispatch."
- If both conditions apply: write both scenarios with probability weights.

---

## Issue 3 (MINOR): AS Fallback When Smartbidder AS Endpoint Fails

**Evidence**: `reports/daily/2026-06-12.md` (Cycle Status): "DA Ancillary prices null this run." Self-review 2026-06-12: "When Smartbidder AS endpoint fails, fall back to prior-day ERCOT DAM AS clearing prices as proxy."

This fallback rule was identified but not yet implemented in the briefing pipeline.

**Agent action**: When Smartbidder AS endpoint returns null, explicitly state: "Using prior-day DAM AS prices as fallback: [Non-Spin = $X, ECRS = $Y, RRS = $Z]." Do not leave AS section empty or use prior-cycle Smartbidder data without labeling it as fallback.

---

## Issue 4 (MINOR): AS Total Revenue Estimate Not Included in Briefings

**Evidence**: `memory/market-analyst/learnings/2026-06-14.md` (Section 2C): "AS 총 수익 추정치 브리핑에 추가 필요."

The briefing provides per-hour AS prices (e.g., "Non-Spin HE22 $13.63") but does not translate these into estimated revenue for bess-optimizer to use. The downstream agent must then independently estimate capacity × price.

**Agent action**: Add one summary line at the end of the AS section: "AS revenue estimate (indicative): [Product] [MW assumption] × [key hours] × [price] = ~$[X] gross." This is a 1-line addition that materially improves bess-optimizer's revenue projection accuracy.

---

## Success Criteria

- Weekend RT regime checklist step appears explicitly in the 2026-06-20 (Saturday) and 2026-06-21 (Sunday) briefings.
- Ramp-window framing rule applied in 3 consecutive briefings starting 2026-06-16.
- AS fallback rule documented and applied when Smartbidder AS endpoint is null.
- AS total revenue estimate line included in briefings starting 2026-06-16.

---

*Evaluator — 2026-06-15 | Supersedes: 2026-W23-improvement.md Issue 1 (weekend RT checklist carried forward; 4th cycle). Issues 2-4 are new from W24 evidence.*
