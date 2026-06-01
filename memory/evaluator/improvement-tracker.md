# Evaluator Improvement Tracker

Last updated: 2026-06-01 (Week 2026-22)

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
