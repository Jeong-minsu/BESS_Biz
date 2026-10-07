# Plan: Execution Confirmation — CRITICAL Escalation
**Agent**: dart-virtual-trader
**Week**: 2026-W26
**Priority**: CRITICAL
**Registered by**: evaluator (2026-06-29)
**Deadline**: 2026-07-06 (next weekly evaluation)

---

## Issue

This is the **14th consecutive escalation** of the execution confirmation gap. dart-virtual-trader issues DART virtual position recommendations daily, but there is no confirmed mechanism by which those recommendations reach actual cleared positions. As a result:

- Hit rate is **completely uncomputable** for all of W26 and prior weeks
- The Tenaska DART Virtual Net figure (e.g., -$3,964.90 on 2026-06-24) reflects physical BESS DA charging, NOT virtual position P&L
- The Smartbidder benchmark captured a DEC position at HE15 on 2026-06-24 (+$661.75) that GKS did NOT execute — this is the 14th cycle with evidence of possible non-execution
- There is no settlement line in Battery-Settlement-Details to confirm or deny any virtual position

The W25 plan `2026-25-settlement-infrastructure.md` asked the user to confirm scope. No response has been received as of W26. Escalating to CRITICAL because 14 cycles of non-confirmation means the agent's core output (DART virtual positions) has **zero verified impact** on actual P&L.

---

## Quantitative Basis for CRITICAL Classification

- Consecutive cycles without confirmed execution: **14+**
- Consecutive weeks without computable hit rate: **6+ weeks**
- DART virtual ranking (STALE 2026-03-26): GKS rank **#276 / 276 (last)**, Net Revenue **-$189,508.65**, Win Rate **31.5%**
- Target hit rate: ≥55% (from agent definition)
- Current computable hit rate: **N/A** (no execution data)
- Benchmark virtual capture (Jun 24): Smartbidder +$661.75 DEC at HE15; GKS net virtual: could not be isolated

---

## Required Actions

### Action 1 (dart-virtual-trader + user): Scope Confirmation
Confirm one of the following:
- (A) dart-virtual-trader recommendations are transmitted to a trader/operator who manually submits bids in ERCOT SCED — in which case, document the transmission path and require execution confirmation notes after each DAM close
- (B) dart-virtual-trader recommendations are NOT currently executed — suspend hit-rate scoring, flag as "advisory only" in all outputs
- (C) Recommendations are auto-submitted via integration (specify system)

**Deadline for user response**: 2026-07-03 (Thursday). If no response by 2026-07-06 weekly evaluation, evaluator will classify dart-virtual-trader as "advisory only, unscored on Approach axis."

### Action 2 (dart-virtual-trader): Settlement Data Workaround
Until Tenaska DART virtual settlement line is available, dart-virtual-trader must:
1. In every daily learning file, document whether the Smartbidder benchmark captured virtual positions for that flowday
2. Compare benchmark virtual P&L to prior-day recommendation direction — flag if opposite
3. Stop using "DART Virtual Net" from Tenaska as proxy for virtual position P&L (confirmed as unreliable in Jun 24 analysis)

### Action 3 (pnl-manager, dependent): DART Isolation
See companion plan `memory/pnl-manager/plans/2026-26-dart-isolation-final.md`. pnl-manager should flag the DART virtual settlement line status in every daily report until resolved.

---

## Success Criteria

- [ ] User confirms execution scope by 2026-07-03
- [ ] dart-virtual-trader learning files document Smartbidder virtual comparison every cycle starting 2026-06-30
- [ ] "DART Virtual Net" from Tenaska is no longer used as virtual P&L proxy in any agent output

---

## History

- W23: First escalation (execution gap identified)
- W24: Escalation continued; user asked to confirm scope
- W25: `2026-25-settlement-infrastructure.md` registered; user confirmation requested
- W26: No response received; 14th consecutive cycle; escalating to CRITICAL with deadline
