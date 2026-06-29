# Evaluator Improvement Tracker

Last updated: 2026-06-29 (Week 2026-26)

---

## Week 2026-26 Plans Registered

| Plan File | Agent | Priority | Status | Description |
|---|---|---|---|---|
| `memory/dart-virtual-trader/plans/2026-26-execution-confirmation-critical.md` | dart-virtual-trader | CRITICAL | OPEN — user to confirm execution scope by 2026-07-03 | 14th escalation; hit rate uncomputable 6+ weeks; GKS DART rank #276/276; possible non-execution Jun 24 |
| `memory/pnl-manager/plans/2026-26-tenaska-whitelist-critical.md` | pnl-manager | CRITICAL | OPEN — user to contact Ascend to re-whitelist cloud IP | 17th failure; 50% rate; 16 DEGRADED days; cascades to 4 agents |
| `memory/bess-optimizer/plans/2026-26-execution-divergence-critical.md` | bess-optimizer | CRITICAL | OPEN — user to confirm root cause by 2026-07-03 | 5+ cycles of DA position divergence; Jun 24 -$3,221 vs benchmark; Jun 26 -$446 vs benchmark |
| `memory/congestion-analyst/plans/2026-26-w3-item010-overdue.md` | congestion-analyst | MAJOR | OPEN — user to confirm access path; agent to document workaround by 2026-07-06 | 38 consecutive blocked cycles; 27 days past W23 deadline; trigger date 2026-06-29 reached |
| `memory/dart-virtual-trader/plans/2026-26-output-directory-final.md` | dart-virtual-trader | MAJOR | OPEN — agent to declare canonical path by 2026-06-30 | W25 deadline missed; 4 path variants in W26; final warning |
| `memory/pnl-manager/plans/2026-26-dart-isolation-final.md` | pnl-manager | MAJOR | OPEN — user to contact Tenaska re: virtual settlement endpoint | 14 cycles without DART virtual P&L isolation; Jun 24 "DART Virtual Net" confirmed as physical BESS charging |
| `memory/dart-virtual-trader/plans/2026-26-smartbidder-probability-absent.md` | dart-virtual-trader | MAJOR | OPEN — user to investigate CSV format change; agent to add fallback protocol by 2026-06-30 | 13+ consecutive cycles absent; forced minimum 25 MW cap on all positions |
| `memory/market-analyst/plans/2026-26-ag2-data-separation.md` | market-analyst | MINOR | OPEN — agent to add AG2 data provenance note starting 2026-06-30 | AG2 D+1 data vintage not labeled in briefings; CLAUDE.md data leakage compliance not visibly auditable |
| `memory/reporter/plans/2026-26-section-numbering.md` | reporter | MINOR | OPEN — agent to fix starting 2026-06-29 report | Jun 28 report section numbering starts at "0"; format drift from W26 convention |

---

## Week 2026-26 W25 Plan Compliance Update

| Plan | Agent | W25 Deadline | W26 Status |
|---|---|---|---|
| `2026-25-standing-rules-gap.md` | bess-optimizer | 2026-06-24 | CLOSED — standing-rules.md created 2026-06-23 (1 day late) |
| `2026-25-direction-inversion-fix.md` | dart-virtual-trader | 2026-06-23 | PARTIALLY CLOSED — direction-reason gate implemented and PASS every W26 cycle; execution still unconfirmed |
| `2026-25-output-directory-standardization.md` | dart-virtual-trader | 2026-06-23 | OPEN — deadline MISSED; 4 variants still in W26; superseded by 2026-26-output-directory-final.md |
| `2026-25-tenaska-whitelist-escalation.md` | pnl-manager | User action | OPEN — no resolution; 17th failure; superseded by 2026-26-tenaska-whitelist-critical.md |
| `2026-25-smartbidder-fallback-protocol.md` | market-analyst | 2026-06-24 | PARTIALLY CLOSED — qualitative fallback in use; not formally documented in memory |
| `2026-25-settlement-infrastructure.md` | dart-virtual-trader | User confirm | OPEN — no user response; superseded by 2026-26-execution-confirmation-critical.md |
| `2026-25-w3-item010-critical-escalation.md` | congestion-analyst | Trigger 2026-06-29 | OPEN — trigger date reached; 38 blocked cycles; superseded by 2026-26-w3-item010-overdue.md |
| `2026-25-weekend-high-wind-haircut.md` | congestion-analyst | Next Sat/Sun cycle | CLOSED — haircut applied correctly Jun 27-28 |

---

## Week 2026-25 Plans Registered

| Plan File | Agent | Priority | Status | Description |
|---|---|---|---|---|
| `memory/pnl-manager/plans/2026-25-tenaska-whitelist-escalation.md` | pnl-manager | CRITICAL | OPEN — user to submit IP whitelist to Ascend; agent to add IP pre-check | 15th whitelist failure; 52% cloud failure rate; 13+ DEGRADED day backlog; cascades to 4 agents |
| `memory/dart-virtual-trader/plans/2026-25-output-directory-standardization.md` | dart-virtual-trader | CRITICAL | OPEN — agent to implement by 2026-06-23 | 6 path variants used in W25; canonical path is reports/daily/dart-virtual-trader/ |
| `memory/dart-virtual-trader/plans/2026-25-direction-inversion-fix.md` | dart-virtual-trader | CRITICAL | OPEN — agent to add direction-reason consistency check by 2026-06-23 | DEC issued with DA>RT rationale on 2 consecutive weekend cycles; hit rate ~14-25% |
| `memory/congestion-analyst/plans/2026-25-w3-item010-critical-escalation.md` | congestion-analyst | MAJOR | OPEN — agent to start immediately; user to confirm data access | 11 days past evaluator deadline; 32 consecutive blocked cycles; escalates to CRITICAL if not started by 2026-06-29 |
| `memory/market-analyst/plans/2026-25-smartbidder-fallback-protocol.md` | market-analyst | MAJOR | OPEN — agent to implement by 2026-06-24 | Smartbidder absent 3+ W25 days; no fallback quantitative estimates provided; downstream agents left without P(DA>RT) |
| `memory/dart-virtual-trader/plans/2026-25-settlement-infrastructure.md` | dart-virtual-trader | MAJOR | OPEN — user to confirm DART execution scope; agent to create hit-rate-log.md | 40+ positions unresolved; hit rate uncalculable; below-floor cap violated 2026-06-18 |
| `memory/bess-optimizer/plans/2026-25-standing-rules-gap.md` | bess-optimizer | MAJOR | OPEN — agent to implement by 2026-06-24 | standing-rules.md 6 days past self-committed deadline; ECRS rule not formalized |
| `memory/congestion-analyst/plans/2026-25-weekend-high-wind-haircut.md` | congestion-analyst | MAJOR | OPEN — agent to implement in next Sat/Sun cycle | GR_WEST >15,000 MW suppresses HOUSTON_IMPORT binding; 10-15 ppt haircut needed; WEST_TO_NORTH timing +1hr bias |

---

## Week 2026-24 Plans Registered

| Plan File | Agent | Priority | Status | Description |
|---|---|---|---|---|
| `memory/congestion-analyst/plans/2026-24-w3-item010-final-escalation.md` | congestion-analyst | CRITICAL | OPEN — 0% started, 11 days past deadline; superseded by 2026-25 plan | W3 item 0.10 now 32 cycles unstarted |
| `memory/dart-virtual-trader/plans/2026-24-settlement-infrastructure-gap.md` | dart-virtual-trader | CRITICAL | OPEN — no confirmed progress; superseded by 2026-25 plan | Settlement blind now 6+ weeks; 40+ positions unresolved |
| `memory/bess-optimizer/plans/2026-24-ecrs-nonspun-execution-gap.md` | bess-optimizer | MAJOR | PARTIALLY OPEN — ECRS awareness improved in learnings; standing-rules.md not created; superseded by 2026-25 plan | standing-rules.md missed 2026-06-16 deadline |
| `memory/pnl-manager/plans/2026-24-whitelist-and-dart-isolation.md` | pnl-manager | CRITICAL | OPEN — 15th failure in W25; no IP whitelist change; superseded by 2026-25 plan | Now 52% cloud failure rate; 13+ day backlog |
| `memory/market-analyst/plans/2026-24-weekend-direction-and-as-fallback.md` | market-analyst | MAJOR | PARTIALLY OPEN — weekend checklist in learnings; Smartbidder fallback not implemented; superseded by 2026-25 plan | Smartbidder absent 3+ W25 days; no fallback quantitative output |

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
