# Plan: W3 Disk Verification Blocker — Week 22

**Issue**: congestion-analyst completed W1 (DA constraint backfill) and W2 (shift factor backfill) during Week 22 — significant infrastructure progress. However, W3 (bus_lmp and hub/zone LMP backfill) has not started. The single blocking item is a disk space verification: 0.9 bus_lmp requires 60 GB+ free disk space before initiating the ~30 GB gzipped download. This verification was flagged as the blocker in every congestion-analyst self-review from 2026-05-27 onward.

The consequence is that hub-pair LMP data has been absent for 10+ consecutive daily operation cycles. Without it, congestion-analyst cannot score any of its own binding/lambda/basis predictions, and the Stage 1 model cannot be initiated.

**Priority**: MAJOR (bottleneck to Stage 1 progression)

**Evidence**: memory/congestion-analyst/plans/stage-progress.md — W3 section shows "NOT STARTED / Disk 60 GB+ verification required". memory/congestion-analyst/learnings/2026-05-30.md Section 6 lists disk verification as item #6 "Initiate W3 disk space verification — the bus_lmp backfill has been blocked for 4+ days. Disk check is a prerequisite for all W3 items."

## Actions

1. **Immediately run disk check**: `df -h` on the execution environment. Document available disk space in `memory/congestion-analyst/history/` for the next cycle.
2. **If disk >= 60 GB free**: Begin W3 item 0.9 (bus_lmp backfill) using the batch pattern from W2 (BATCH_SIZE=8, H1/H2 chunking). Expected download time ~1.5 days.
3. **If disk < 60 GB free**: Identify the largest data directories consuming space (e.g., W2 shift factor parquet files). Evaluate compressing or archiving W2 interim files to free space. Document findings in history.
4. **As a parallel partial action**: Begin W3 item 0.10 (hub/zone LMP 15-min backfill, ~1.0d, much smaller than bus_lmp) immediately — this item resolves the operational 10+ day hub-pair LMP gap in daily briefings and only requires item 0.1 as dependency (already complete).

## Success Criteria

- W3 item 0.10 (hub/zone 15-min LMP) backfill complete within next 7 days.
- Hub-pair LMP (HB_NORTH, HB_WEST, HB_HOUSTON) available in daily congestion briefings starting the week of 2026-06-08.
- W3 item 0.9 (bus_lmp) initiated within 7 days after disk verification confirms available space.

## Owner

congestion-analyst (disk check and W3 initiation are fully within agent scope)
