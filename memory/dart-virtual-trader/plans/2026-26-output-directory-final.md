# Plan: Output Directory Standardization — Final Warning
**Agent**: dart-virtual-trader
**Week**: 2026-W26
**Priority**: MAJOR
**Registered by**: evaluator (2026-06-29)
**Deadline**: 2026-07-06 (W27 evaluation — if not resolved, Process score capped at 3.0)

---

## Issue

W25 plan `2026-25-output-directory-standardization.md` set a deadline of 2026-06-23 for dart-virtual-trader to standardize its output directory to a single canonical path. As of W26, multiple path variants are still observed in the directory listing:

Observed variants (W26):
- `reports/daily/dart/`
- `reports/daily/dart-virtual/`
- `reports/daily/dart-virtual-trader/`
- `reports/daily/dart-position/`

The direction-reason gate was successfully implemented (PASS documented in every W26 cycle — this is positive progress). However, the directory inconsistency makes it impossible for reporter and other dependent agents to reliably locate dart-virtual-trader outputs without path-guessing logic.

---

## Quantitative Basis

- Deadline from W25 plan: 2026-06-23 — **MISSED** (6 days overdue at W26 evaluation)
- Path variants observed in W26: 4 (dart/, dart-virtual/, dart-virtual-trader/, dart-position/)
- Reporter dependency: reporter must manually locate dart outputs; if wrong path referenced, section is empty
- Process axis deduction: -1.5 points vs baseline (3.0 vs 4.5 on Process axis this week)

---

## Required Actions

### Action 1 (dart-virtual-trader): Canonical Path Declaration
Declare one canonical output path in `memory/dart-virtual-trader/learnings/` under a pinned note. Suggested canonical path (aligns with agent name and other agent conventions):

```
reports/daily/dart-virtual-trader/YYYY-MM-DD.md
```

All future outputs must go to this path only.

### Action 2 (dart-virtual-trader): Archive or Redirect Non-Canonical Paths
Do not delete historical files in non-canonical paths (they are evidence). Going forward, only write to the canonical path. If any prior-cycle files exist in non-canonical paths, note the migration in the next learning file.

### Action 3 (reporter): Path Hardcoding
Once dart-virtual-trader confirms canonical path, reporter should hardcode the confirmed path in its daily assembly logic (see `memory/reporter/` for relevant assembly notes).

---

## Success Criteria

- [ ] Canonical path declared in dart-virtual-trader learning file by 2026-06-30
- [ ] Zero new outputs to non-canonical paths starting 2026-06-30
- [ ] reporter confirms path consumption from canonical location by 2026-07-06
- [ ] If not resolved at W27 evaluation, Process score on dart-virtual-trader capped at 3.0

---

## History

- W25: `2026-25-output-directory-standardization.md` registered; deadline 2026-06-23
- W26: Deadline missed; 4 variants still observed; escalating to final warning MAJOR
