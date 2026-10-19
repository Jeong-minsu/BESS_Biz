# bess-optimizer Improvement Plan — 2026-W42
**Filed by**: evaluator | **Date**: 2026-10-19 | **Period evaluated**: 2026-10-12 – 2026-10-18

---

## W42 Status Summary

| Axis | Score | Trend |
|---|---|---|
| Process | 3.5/5 | → |
| Approach | 4.0/5 | → |
| Resource | 4.0/5 | ↑ |
| Overall | 3.8/5 | → |

**Major positive**: Tyba GKS D+1 (DA/RT LMP P50, AS, P(DA>RT)) integrated from Oct 14 cycle onwards — first price forecast source in ~82 days. NSPIN-hold rule formally quantified. HE21-24 NSPIN stranded gap quantified and documented.
**Gap**: Oct 15 output to `bess-strategy/` instead of `bess-optimizer/`. Oct 17 standalone learning missing.

---

## W41 Plan Compliance

| W41 Plan Item | W42 Outcome |
|---|---|
| Rule 8 RT dispatch mismatch confirmation (carry-forward) | PENDING — Tenaska still unavailable |
| Yes Energy fallback protocol in standing-rules.md | UNVERIFIED this evaluation cycle |

---

## Improvement Items for W43

### Item 1 — MAJOR: Output Path Discipline (bess-strategy/ recurrence)

**Issue**: Oct 15 flowday strategy at `reports/daily/bess-strategy/2026-10-15.md`. Canonical: `reports/daily/bess-optimizer/YYYY-MM-DD.md`. This variant (`bess-strategy/`) has appeared in prior weeks. A single instance but the recurring pattern (multiple wrong-dir variants across sessions) warrants targeted attention.

**Required action**: At session start, confirm output directory is `reports/daily/bess-optimizer/`. Do not use `bess-strategy/`, `bess-schedule/`, `bess-stack/` as output directories for the daily recommendation file. If the recommendation is naturally called a "strategy file," the filename should still be written to `reports/daily/bess-optimizer/YYYY-MM-DD.md`.

**Success criterion**: 5/5 correct path in W43.

---

### Item 2 — MAJOR carry-forward: Yes Energy Fallback Protocol in standing-rules.md

**Issue**: W41 plan Item 2 requested documentation of the Yes Energy fallback protocol in `memory/bess-optimizer/standing-rules.md`. Compliance unverified as of W42.

**Required action**: Add the following entry to standing-rules.md if not already present:

> **Rule YE-FALLBACK**: If Yes Energy BidClose absent ≥ 2 consecutive days, use: (1) last filed Yes Energy data + seasonal pattern adjustment, OR (2) Tyba GKS P50 as primary price input + AG2/Enverus for physical fundamentals. Flag all estimates with `[YES_ENERGY_ABSENT]`. Revenue estimate confidence: VERY LOW. Do not use seasonal-only estimates when Tyba is available.

**Success criterion**: Rule exists in standing-rules.md by end of W43.

---

### Item 3 — Recommended: NSPIN-Hold Rule in standing-rules.md

**Issue**: NSPIN-hold rule formalized in Oct 18 learnings (`memory/bess-optimizer/learnings/2026-10-18.md`, §1.1). Rule exists in learnings only; not yet in the persistent standing-rules.md.

**Required action**: Add to standing-rules.md:

> **Rule NSPIN-HOLD**: If D+1 overnight avg NSPIN DA > $2.50/MW AND expected duck-charge price < $20/MWh → hold SoC through overnight for NSPIN DA rather than overnight energy arb. Quantified at ~$1,000–$1,800/day advantage vs overnight arb on qualifying days.

**Success criterion**: Rule exists in standing-rules.md by end of W43.

---

### Item 4 — CRITICAL carry-forward: Rule 8 RT Dispatch Mismatch

**Issue**: Sep 17 loss of -$2,231.14 attributable to unauthorized DA charge bids. Root cause unconfirmed for 32+ days. SoC initialization continuity degrading over 31 DEGRADED flowdays (Rule 7 default 100 MWh applied every day; actual SoC unknown).

**Required action**: When Tenaska PTP is restored, immediately pull Sep 17 settlement detail. Also pull the most recent available flowday to anchor SoC initialization from a confirmed actual.

**Priority**: P0 (requires Tenaska restoration first — external blocker).
