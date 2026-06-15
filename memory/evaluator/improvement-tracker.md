# Evaluator Improvement Tracker

Last updated: 2026-06-15 (Week 2026-24)

---

## Week 2026-24 Plans Registered

| Plan File | Agent | Priority | Status | Description |
|---|---|---|---|---|
| `memory/congestion-analyst/plans/2026-24-w3-item010-final-escalation.md` | congestion-analyst | CRITICAL | OPEN — user to confirm disk; agent to start item 0.10 immediately | W3 item 0.10 now 23 cycles unstarted; 12 cycles past W23 deadline |
| `memory/dart-virtual-trader/plans/2026-24-settlement-infrastructure-gap.md` | dart-virtual-trader | CRITICAL | OPEN — user to confirm Smartbidder submission scope; agent to fix label bug + ECRS modifier | Settlement blind 4 weeks; Non-Spin vs ECRS label bug; ECRS INC modifier not formalized |
| `memory/bess-optimizer/plans/2026-24-ecrs-nonspun-execution-gap.md` | bess-optimizer | MAJOR | OPEN — agent to create standing-rules.md + apply ECRS rule; user to confirm execution flow | ECRS exclusion rule failed 4 cycles (~$1,400 opportunity loss); execution divergence past deadline |
| `memory/pnl-manager/plans/2026-24-whitelist-and-dart-isolation.md` | pnl-manager | CRITICAL | OPEN — user to whitelist IP; agent to implement Submissions-DA-Settlement-Amounts endpoint | 12 whitelist failures in 21 days; DART virtual isolation 4 cycles deferred |
| `memory/market-analyst/plans/2026-24-weekend-direction-and-as-fallback.md` | market-analyst | MAJOR | OPEN — agent to implement weekend checklist before 2026-06-20 Saturday | Weekend RT direction miss 4th consecutive weekend; ramp framing systematic error |

---

## Week 2026-W23 Plans — Updated Status

| Plan File | Agent | Priority | W24 Status | Notes |
|---|---|---|---|---|
| `memory/dart-virtual-trader/plans/2026-W23-improvement.md` | dart-virtual-trader | CRITICAL | PARTIALLY IMPLEMENTED | Saturday 25 MW cap applied 2026-06-13 (confirmed); dual-direction scarcity skip applied and validated 2026-06-14; hit-rate log in learnings table but no dedicated file created; superseded by 2026-24 plan for new issues |
| `memory/market-analyst/plans/2026-W23-improvement.md` | market-analyst | MAJOR | OPEN — 4th weekend miss | Weekend RT checklist documented but not applied Sunday 2026-06-14; superseded by 2026-24 plan |
| `memory/congestion-analyst/plans/2026-W23-improvement.md` | congestion-analyst | MAJOR | CRITICAL OPEN | Item 0.10 deadline (2026-06-11) missed by 5 cycles; MCC sign correction applied (positive); superseded by 2026-24 escalation plan |
| `memory/bess-optimizer/plans/2026-W23-improvement.md` | bess-optimizer | MAJOR | OPEN (NEW DIMENSION) | RT dispatch mechanism past 2026-06-15 deadline; ECRS gap is new compounding issue; superseded by 2026-24 plan |
| `memory/pnl-manager/plans/2026-W23-improvement.md` | pnl-manager | MAJOR | CRITICAL OPEN | No implementation progress on DART isolation or backfill; whitelist failures continuing; superseded by 2026-24 plan |

---

## Resolved Items (W24)

| Item | Resolution | Evidence |
|---|---|---|
| reporter W22 format stabilization | RESOLVED | All 7 W24 daily reports have consistent footer, section structure, data banner. Plan `2026-22-format-stabilization.md` CLOSED. |

---

## Week 2026-W23 Plans Registered

| Plan File | Agent | Priority | Status | Description |
|---|---|---|---|---|
| `memory/dart-virtual-trader/plans/2026-W23-improvement.md` | dart-virtual-trader | CRITICAL | OPEN — agent to implement Saturday cap + dual-direction rule | First confirmed settlement: 0% hit rate, -$5,266; Saturday regime failure identified |
| `memory/market-analyst/plans/2026-W23-improvement.md` | market-analyst | MAJOR | OPEN — agent to implement weekend RT checklist | Weekend RT direction 3-cycle systematic failure; rule written but not applied |
| `memory/congestion-analyst/plans/2026-W23-improvement.md` | congestion-analyst | MAJOR | OPEN — agent to start W3 item 0.10; user to confirm disk | 18-cycle hub-pair LMP gap; lambda P90 underprediction confirmed with calibration fix |
| `memory/bess-optimizer/plans/2026-W23-improvement.md` | bess-optimizer | MAJOR | OPEN — user action required for RT dispatch mechanism | Involuntary RT dispatch -$4,520 unresolved; AS Playbook 9-cycle gap |
| `memory/pnl-manager/plans/2026-W23-improvement.md` | pnl-manager | MAJOR | OPEN — user/agent to implement DART virtual endpoint | DART virtual isolation 3 cycles deferred; data-quality.md update needed |

---

## Week 2026-22 Plans — Updated Status

| Plan File | Agent | Priority | W23 Status | Notes |
|---|---|---|---|---|
| `memory/pnl-manager/plans/2026-22-tenaska-whitelist-escalation.md` | pnl-manager | CRITICAL | PARTIALLY RESOLVED | 5 PRODUCTION days in W23 vs 1 in W22; recovery mechanism undocumented; 3 W23 days still DEGRADED; superseded by 2026-W23 plan |
| `memory/market-analyst/plans/2026-22-as-template-persistent-gap.md` | market-analyst | MAJOR | PARTIALLY RESOLVED | Non-Spin overnight improving; ECRS morning ramp inconsistent; NEW priority: weekend RT direction; superseded by 2026-W23 plan |
| `memory/congestion-analyst/plans/2026-22-w3-disk-verification-blocker.md` | congestion-analyst | MAJOR | OPEN ESCALATING | 18 cycles (was 12 in W22); lambda underprediction now confirmed with commercial impact; superseded by 2026-W23 plan |
| `memory/dart-virtual-trader/plans/2026-22-hit-rate-tracking-unresolved.md` | dart-virtual-trader | MAJOR | ESCALATED TO CRITICAL | First confirmed settlement 0/5 hit rate; proxy methodology demonstrated unreliable; superseded by 2026-W23 plan |
| `memory/reporter/plans/2026-22-format-stabilization.md` | reporter | MINOR | PARTIALLY IMPLEMENTED | Footer missing some reports; section count improving; no new plan needed |
| `memory/bess-optimizer/plans/2026-22-da-rt-venue-follow-up.md` | bess-optimizer | CRITICAL | OPEN — NEW DIMENSION | Tenaska DA venue still unconfirmed; involuntary RT dispatch adds new layer; superseded by 2026-W23 plan |
| `memory/bess-optimizer/plans/2026-22-model-calibration-drift.md` | bess-optimizer | MAJOR | IN PROGRESS (IMPROVING) | 3 more data points in W23; lessons applied; involuntary RT dispatch is new separate issue |

---

## Week 2026-22 Plans Registered

| Plan File | Agent | Priority | Status | Description |
|---|---|---|---|---|
| `memory/pnl-manager/plans/2026-22-tenaska-whitelist-escalation.md` | pnl-manager | CRITICAL | OPEN — user action required | Escalation: 7 failures in 11 days; code pre-check still unimplemented |
| `memory/market-analyst/plans/2026-22-as-template-persistent-gap.md` | market-analyst | MAJOR | OPEN — agent to implement | Non-Spin overnight + ECRS morning ramp bullets — 7-cycle miss |
| `memory/congestion-analyst/plans/2026-22-w3-disk-verification-blocker.md` | congestion-analyst | MAJOR | OPEN — agent to implement | Run disk check; begin W3 item 0.10 (hub/zone LMP) |
| `memory/dart-virtual-trader/plans/2026-22-hit-rate-tracking-unresolved.md` | dart-virtual-trader | MAJOR | OPEN — agent to implement | Create hit-rate-log.md; recalibrate +20% bias correction |
| `memory/reporter/plans/2026-22-format-stabilization.md` | reporter | MINOR | OPEN — agent to implement | Lock 8-section template; fix attribution footer |
| `memory/bess-optimizer/plans/2026-22-da-rt-venue-follow-up.md` | bess-optimizer | CRITICAL | OPEN — user action required | Follow-up: Tenaska DA venue confirmation still pending |
| `memory/bess-optimizer/plans/2026-22-model-calibration-drift.md` | bess-optimizer | MAJOR | IN PROGRESS | Agent identified and partially addressed; 3-data-point rule applied |

---

## Week 2026-21 Plans — Updated Status

| Plan File | Agent | Priority | 2026-22 Status | Notes |
|---|---|---|---|---|
| `memory/pnl-manager/plans/2026-21-tenaska-whitelist-permanent-fix.md` | pnl-manager | CRITICAL | OPEN — escalated | No code changes implemented; superseded by 2026-22 escalation plan |
| `memory/pnl-manager/plans/2026-21-dart-virtual-isolation.md` | pnl-manager | MAJOR | OPEN | No progress; blocked by whitelist failure |
| `memory/bess-optimizer/plans/2026-21-da-rt-venue-alignment.md` | bess-optimizer | CRITICAL | PARTIALLY MITIGATED | 0.80x haircut applied; Tenaska confirmation still pending; superseded by 2026-22-da-rt-venue-follow-up |
| `memory/bess-optimizer/plans/2026-21-structural-as-defaults.md` | bess-optimizer | MAJOR | CLOSED | ECRS HE07-10 / RRS HE19-24 / solar trough charge now in standard schedule template across all Week 22 cycles |
| `memory/dart-virtual-trader/plans/2026-21-smartbidder-p-csv-fix.md` | dart-virtual-trader | CRITICAL | CLOSED | P file returned 2026-05-27; maintained through end of week |
| `memory/dart-virtual-trader/plans/2026-21-hit-rate-tracking-setup.md` | dart-virtual-trader | MAJOR | OPEN — superseded | Log not created; superseded by 2026-22-hit-rate-tracking-unresolved |
| `memory/market-analyst/plans/2026-21-as-timing-correction.md` | market-analyst | MAJOR | PARTIALLY CLOSED | Smartbidder peak adjustment and solar ±1h range added; Non-Spin overnight + ECRS morning ramp still absent; superseded by 2026-22-as-template-persistent-gap |
| `memory/congestion-analyst/plans/2026-21-west-binding-calibration.md` | congestion-analyst | MAJOR | CLOSED | Calibration revised; MEDIUM/MEDIUM-HIGH/HIGH used correctly throughout Week 22; no HIGH overcall recurrence |
| `memory/reporter/plans/2026-21-language-consistency.md` | reporter | MINOR | PARTIALLY CLOSED | Language (Korean) stabilized; section ordering still inconsistent; superseded by 2026-22-format-stabilization |

---

## Tracking Conventions

- **OPEN — user action required**: Plan requires user decision or external action (e.g., Tenaska, Smartbidder). Agent cannot complete alone.
- **OPEN — agent to implement**: Agent can implement in the next daily cycle without external dependency.
- **IN PROGRESS**: Agent has begun implementation; not yet verified closed.
- **PARTIALLY MITIGATED / PARTIALLY CLOSED**: The original issue has been reduced but not fully resolved; a follow-up plan may supersede.
- **CLOSED**: Plan fully implemented and verified at this evaluation.

---

## Prior Weeks

Week 2026-21 — initial evaluation cycle. See table above for status updates.
