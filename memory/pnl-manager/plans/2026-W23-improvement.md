# Plan: pnl-manager Improvement — Week 2026-W23

**Filed by**: evaluator | **Date**: 2026-06-08 | **Priority**: CRITICAL (user action required)

---

## Issue 1 (CRITICAL, ONGOING): Tenaska PTP Whitelist — 10 of 16 Operating Days Failed in W22-W23 Combined

**Evidence**: `memory/pnl-manager/data-quality.md`. As of 2026-06-04 (the last logged entry), 10 confirmed failures out of 16 operating days since 2026-05-21 (62.5% failure rate). The log records failures through 2026-06-03 execution (10th occurrence). W23 partial recovery: Tenaska data returned for 2026-05-31, 2026-06-04, 2026-06-05, 2026-06-06, 2026-06-07 (confirmed via reports/daily/pnl/ files). Failures persisted for 2026-06-01, 2026-06-02, 2026-06-03.

**W23 status update**: Tenaska IS reachable for some execution cycles in W23 (2026-06-04 through 2026-06-07 all show PRODUCTION data). The pattern appears to be intermittent rather than total block — this is either (a) the whitelist was partially resolved, (b) the user ran manual fetches from a whitelisted IP for some days, or (c) the cloud execution IP changed. The data-quality.md log has not been updated beyond 2026-06-04 entry, so the recovery mechanism is not documented.

**Required actions**:

1. **Document the recovery**: Update `memory/pnl-manager/data-quality.md` with entries for 2026-06-04 through 2026-06-07 executions (4 successes). Note which IP or environment was used. This documentation is critical to prevent re-regression.

2. **User action required**: Confirm with Ascend whether the cloud execution IP was whitelisted during the W23 window, or whether the successful fetches were manual. If manual: the whitelist escalation is still open and re-automation requires the fix. If whitelisted: document the whitelisted IP in a config file so the fix is preserved across execution environment changes.

3. **Backfill outstanding DEGRADED days**: At least 8 confirmed DEGRADED days remain from W22-W23 (2026-05-23, 2026-05-25, 2026-05-26, 2026-05-27, 2026-05-28, 2026-05-30, 2026-06-01, 2026-06-02, 2026-06-03). These need to be fetched from a whitelisted environment and the pnl reports regenerated.

---

## Issue 2 (MAJOR): DART Virtual Revenue Isolation Still Not Implemented

**Evidence**: `memory/pnl-manager/history/2026-06-07.md` and `reports/daily/pnl/2026-06-05.md`. The DA_Energy_Amt in Tenaska Battery-Settlement-Details bundles physical DA energy and potential DART virtual into a single line. DART virtual revenue cannot be isolated without the `Submissions-DA-Settlement-Amounts` endpoint. As of 2026-06-07, da_energy_bid.json returned 0 rows (endpoint not fetching) and DART virtual revenue is still shown as NOT AVAILABLE.

**Direct commercial impact**: dart-virtual-trader confirmed DART positions ARE submitted and settled (2026-06-06 confirmed -$5,266 loss). But this loss does not appear in the GKS total from Tenaska Battery-Settlement-Details. The total GKS P&L as reported by pnl-manager is systematically incomplete — either understating losses (if DART virtual is net negative) or understating gains (if net positive).

**Required actions**:

1. **Implement the `Submissions-DA-Settlement-Amounts` endpoint call** in `fetch_pnl_data.py`. This endpoint returns DA settlement by product, enabling DART virtual isolation. This was identified in the 2026-21 plan (`memory/pnl-manager/plans/2026-21-dart-virtual-isolation.md`) and has been pending for 3 evaluation cycles (W21, W22, W23). It cannot remain deferred.

2. **Escalate to user**: This endpoint fix requires code changes. If the endpoint discovery is complete (endpoint URL known), implement immediately. If not, coordinate with user to identify the correct endpoint.

---

## Issue 3 (MINOR): HSL Endpoint Not Fetched — Cycle Utilization Metrics Unavailable

**Evidence**: Multiple pnl-manager history files (2026-06-05, 2026-06-06, 2026-06-07) all note "hsl.json not fetched." HSL (High Sustained Limit) availability is required to compute cycle utilization percentage. Without it, the "HSL availability %" metric shown in the W22 report is missing in W23.

**Required action**: Add hsl endpoint fetch to `fetch_pnl_data.py` or to pnl-manager's post-processing step. The endpoint was previously identified in prior fetch attempts (Tenaska PTP discovery). Include HSL-derived cycle availability in pnl reports.

---

## Success Criteria

- data-quality.md updated with W23 recovery status (success/failure, IP context) by 2026-06-09.
- Submissions-DA-Settlement-Amounts endpoint implemented and DART virtual revenue isolated in the next PRODUCTION pnl report.
- At least 3 DEGRADED backfill days resolved by 2026-06-15.

---

*Evaluator — 2026-06-08 | Supersedes: 2026-22-tenaska-whitelist-escalation.md (extends to W23 partial recovery; adds DART isolation as separate critical track)*
