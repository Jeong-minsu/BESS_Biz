# Plan: reporter Cycle Health Path Verification

**Registered by**: evaluator  
**Date**: 2026-07-27  
**Priority**: MINOR  
**Status**: OPEN — agent to implement  

---

## Issue

Reporter's Cycle Health tables cite wrong directory paths for dart-virtual-trader (and occasionally bess-optimizer) because the reporter accepts whatever path the upstream agent used, without verifying against the canonical paths. This means the Cycle Health table propagates directory compliance failures rather than flagging them.

## Evidence

- `reports/daily/2026-07-22.md` Cycle Health: bess-optimizer row shows `reports/daily/bess-stack/2026-07-23.md` — WRONG directory.
- `reports/daily/2026-07-22.md` Cycle Health: dart-virtual-trader row shows `reports/daily/dart-position/2026-07-23.md` — WRONG directory.
- `reports/daily/2026-07-24.md` Cycle Health: dart-virtual-trader row shows `reports/daily/dart-virtual/2026-07-24.md` — WRONG directory.

These entries cite existing files (the files do exist at the wrong paths) but the canonical paths are:
- dart-virtual-trader: `reports/daily/dart-virtual-trader/YYYY-MM-DD.md`
- bess-optimizer: `reports/daily/bess-optimizer/YYYY-MM-DD.md`

## Required Action

When building the Cycle Health table, reporter must:
1. Check whether the expected canonical path exists (`reports/daily/<agent>/YYYY-MM-DD.md`).
2. If canonical path ABSENT: check stray paths and cite the stray path with a "[WRONG DIR]" flag.
3. If canonical path PRESENT: cite canonical path normally.

Example corrected Cycle Health row:
```
| dart-virtual-trader | `reports/daily/dart-virtual-trader/2026-07-24.md` [FILE NOT FOUND — stray: dart-virtual/] | WRONG DIR | Advisory-only mode |
```

This makes directory compliance failures visible to the user in the daily report itself, without waiting for the weekly evaluator review.

## W30 Coverage Note

Reporter coverage was 6/7 in W30 (missing 2026-07-23 Saturday). This is an improvement from 5/7 in W29. W29 plan target was 7/7. The Saturday gap is consistent with the orchestration policy question (user confirmation pending from W29 evaluator plan). If Saturday D+1 coverage is not required by policy, the effective target is 6/6 weekday+Sunday reports, which W30 met fully.

## Success Criterion

All Cycle Health tables correctly identify canonical vs stray paths. "[WRONG DIR]" flag appears whenever an upstream agent files to the wrong directory.
