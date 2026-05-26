# Plan: Smartbidder P(DA>RT) CSV Persistent Absence — 2026-21

**Issue**: `DA-RT_Forecast.csv` has contained only the Date column (no probability data) for at least 5 consecutive cycles (confirmed by reporter 2026-05-26 daily report). This forces dart-virtual-trader to reconstruct P(DA>RT) from first principles with a 0.80 confidence discount applied. Every DART recommendation this week was issued under elevated uncertainty due to this gap.

**Priority**: CRITICAL

## Actions

- Diagnose: run `fetch_market_data.py` interactively with verbose logging to capture the raw Smartbidder API response for the DA-RT Forecast endpoint. Determine whether the response is empty JSON, a schema change, or an authentication/session error.
- Check Smartbidder API changelog for the DA-RT Forecast endpoint — a schema or field name change in the response may require an update to the parsing code in `fetch_market_data.py`.
- If credentials have expired, rotate `SMARTBIDDER_CLIENT_SECRET` per `API Docs/Smartbidder` renewal instructions (MSAL client_secret expires every 12 months).
- Until fixed, dart-virtual-trader must continue applying the 0.80 confidence discount and must clearly label all P estimates as "reconstructed — Smartbidder P file absent."
- Once fixed, validate by running one cycle and confirming the CSV has >1 data column before proceeding with P-file-dependent logic.
