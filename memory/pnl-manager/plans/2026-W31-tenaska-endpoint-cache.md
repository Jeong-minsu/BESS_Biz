# Plan: pnl-manager Tenaska Endpoint Cache — Non-Interactive Environment Fix
**Registered by**: evaluator
**Week**: 2026-W31 (evaluated 2026-08-03)
**Priority**: MAJOR (NEW — technical root cause now identified)
**Status**: OPEN — user action required

---

## Issue Description

Tenaska PTP fetch failures have been documented since 2026-05-21 (32nd failure as of 2026-07-31). W31 P&L reports reveal the technical root cause for the first time in specific terms:

From `reports/daily/pnl/2026-07-27.md` and `reports/daily/pnl/2026-07-31.md`:

> "클라우드 실행 환경 IP 화이트리스트 미충족 + `TENASKA_EP_ENERGY_AS` endpoint cache env var 미설정 — 비대화형 환경에서 endpoint 자동 discovery 불가"

**Two distinct failure modes operate simultaneously:**

1. **IP Whitelist failure**: Cloud automation environment IP is not in Tenaska/Ascend whitelist. This requires Tenaska/Ascend admin action (per user's external contact).

2. **Endpoint cache not set (NEW TECHNICAL DETAIL)**: `fetch_pnl_data.py` performs interactive discovery of 4 Tenaska endpoint URLs on first run. In a non-interactive (cloud) environment, this discovery is blocked because it requires stdin input. The discovered endpoints must be cached in `.env` as environment variables (`TENASKA_EP_ENERGY_AS`, and 3 others) to bypass re-discovery. These env vars are currently unset.

**Key insight**: Even if the IP whitelist is resolved, the non-interactive environment will fail discovery unless the endpoint cache env vars are populated from a prior manual (VPN, interactive) run.

---

## Resolution Path

### Step 1 (user action — 1 time manual run)
Run `fetch_pnl_data.py` once from a whitelisted IP environment (local machine, VPN) in interactive mode. During this run, the script will discover the 4 endpoint URLs and print them (or cache them internally).

### Step 2 (user action — after Step 1)
Extract the 4 discovered endpoint URLs and add them to `.env` under the Tenaska section:
```
TENASKA_EP_ENERGY_AS=<discovered_url>
TENASKA_EP_DA_ENERGY_BID=<discovered_url>
TENASKA_EP_DA_ENERGY_OFFER=<discovered_url>
TENASKA_EP_HSL=<discovered_url>
```
(Exact variable names may differ — read `shared/scripts/fetch_pnl_data.py` to confirm the env var names used for endpoint cache bypass.)

### Step 3 (user action)
Verify that `fetch_pnl_data.py` runs successfully in non-interactive mode with the cache vars set:
```bash
TENASKA_EP_ENERGY_AS=<url> python shared/scripts/fetch_pnl_data.py --flowday 2026-07-29
```

### Step 4 (once endpoint cache works)
Run backfill for the 31-day DEGRADED backlog (2026-05-23 through 2026-07-31, 31 days listed in `reports/daily/pnl/2026-07-31.md`).

---

## pnl-manager Agent Action (W32)
- Document the 4 env var names (from reading `fetch_pnl_data.py`) in `memory/pnl-manager/learnings/YYYY-MM-DD.md` when Tenaska fetch is next run successfully.
- Add a note in each DEGRADED report: "Endpoint cache env vars needed: [list]" — so the user has a consistent reminder.

---

## Success Criterion
- 1 successful non-interactive Tenaska fetch after endpoint cache vars are set
- DEGRADED rate drops below 1/7 per week
- 31-day backlog cleared

---

## Note on Smartbidder
Smartbidder MSAL client_secret (separate issue, separate plan: `2026-W30-smartbidder-secret-expired.md`) remains expired as of 2026-08-02 (8+ consecutive days). Both infrastructure issues must be resolved independently.

---

## Cross-Reference
- Tenaska history plan: `memory/pnl-manager/plans/2026-29-tenaska-whitelist-critical.md`
- Smartbidder plan: `memory/pnl-manager/plans/2026-W30-smartbidder-secret-expired.md`
- First technical detail evidence: `reports/daily/pnl/2026-07-27.md` (line re: TENASKA_EP_ENERGY_AS)
- DEGRADED backlog: `reports/daily/pnl/2026-07-31.md` (31-day list)
