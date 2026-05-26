# Plan: DART Virtual P&L Isolation from Tenaska DA_Energy_Amt — 2026-21

**Issue**: Tenaska Battery-Settlement-Details embeds DART virtual P&L inside `DA_Energy_Amt`. The DART virtual line cannot be separately reported from pnl-manager output, preventing accurate per-agent performance attribution. Smartbidder benchmark reports DART virtual separately (+$1,807 on 2026-05-22; +$1,481 on 2026-05-24), creating an apples-to-oranges comparison.

**Priority**: MAJOR

## Actions

- Request from Tenaska/Ascend whether a separate virtual book endpoint exists in the PTP API (distinct from Battery-Settlement-Details) that returns DA virtual positions and their settlement amounts by HE.
- If a separate endpoint is unavailable, implement a reconciliation method: for hours where GKS DA_Sales_Qty and DA_Purchase_Qty can be isolated and a physical schedule is known, the residual DA_Energy_Amt is attributable to virtual positions. Document this calculation method in `memory/pnl-manager/learnings/`.
- Until resolved, pnl-manager must clearly annotate every P&L report: "DART Virtual: embedded in DA Energy (not separable from Tenaska data); Smartbidder shows $X separately — total comparison is valid, product-level is not."
- Coordinate with dart-virtual-trader: provide the Smartbidder DART virtual line from benchmark data as the best available proxy for dart-virtual-trader hit-rate calculations.
