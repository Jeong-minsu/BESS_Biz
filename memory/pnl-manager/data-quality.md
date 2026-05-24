# pnl-manager Data Quality Log

| Date | Source | Issue | Resolution |
|---|---|---|---|
| 2026-05-22 | Tenaska PTP | Fetch FAILED for 2026-05-21 flowday — cloud execution IP not on Ascend whitelist. No raw data written to shared/data/raw/. 2026-05-21 P&L report marked DEGRADED. | Re-run fetch from whitelisted IP; then re-run pnl-manager for 2026-05-21. |
| 2026-05-24 | Tenaska PTP + Smartbidder benchmark | Fetch FAILED for 2026-05-23 flowday — cloud execution IP not on Ascend whitelist. No raw data written to shared/data/raw/tenaska/. Smartbidder benchmark also absent (fetch_market_data.py retrieved D+1 forecast only, not prior-day benchmark). 2026-05-23 P&L report marked PARTIAL. Third incident in this pattern (2026-05-21 and 2026-05-23 both failed; 2026-05-22 succeeded from presumably whitelisted environment). | Re-run fetch_pnl_data.py from whitelisted IP for 2026-05-23 flowday; then re-run pnl-manager to generate actuals. |
