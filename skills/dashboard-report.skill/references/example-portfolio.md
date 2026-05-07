# Example: Portfolio Dashboard

A dashboard showing a stock/crypto portfolio. Use as reference for any "my holdings," "watchlist," "trade summary" type request.

## Structure

- **Header**: "Portfolio Overview" + date range
- **5 KPIs**: Total Value, Day P&L, MTD P&L, YTD Return, Cash %
- **Main chart**: Equity curve (line, area-fill) over selected period
- **Heatmap**: Sector × time period (week / month / quarter / YTD returns)
- **Table**: Holdings ranked by position size, with ticker, name, qty, price, day chg, weight, % of portfolio

## KPI patterns

```html
<div class="kpi">
  <div class="kpi-label">Total Value</div>
  <div class="kpi-value">$842,361</div>
  <div class="kpi-change up">▲ $12,481 (+1.50%)</div>
</div>

<div class="kpi">
  <div class="kpi-label">Day P&amp;L</div>
  <div class="kpi-value">+$3,204</div>
  <div class="kpi-change up">▲ 0.38%</div>
</div>

<div class="kpi">
  <div class="kpi-label">YTD Return</div>
  <div class="kpi-value">+18.42%</div>
  <div class="kpi-change up">▲ vs SPX +6.20%</div>
</div>
```

For losing positions, use the `down` class and `▼` arrow.

## Sector heatmap pattern

```html
<div class="heatmap" id="heatmap" style="grid-template-columns: 80px repeat(4, 1fr);">
  <div class="heatmap-axis"></div>
  <div class="heatmap-axis">1W</div>
  <div class="heatmap-axis">1M</div>
  <div class="heatmap-axis">QTD</div>
  <div class="heatmap-axis">YTD</div>

  <div class="heatmap-axis" style="justify-content: flex-start;">Tech</div>
  <div class="heatmap-cell" style="background: rgba(38,166,154,0.55)">+2.4%</div>
  <div class="heatmap-cell" style="background: rgba(38,166,154,0.75)">+8.1%</div>
  <div class="heatmap-cell" style="background: rgba(38,166,154,0.65)">+12.3%</div>
  <div class="heatmap-cell" style="background: rgba(38,166,154,0.80)">+24.7%</div>

  <div class="heatmap-axis" style="justify-content: flex-start;">Energy</div>
  <div class="heatmap-cell" style="background: rgba(239,83,80,0.45)">-1.2%</div>
  <!-- ... -->
</div>
```

Use the `heatColor(v)` JS helper to compute backgrounds programmatically when there are many cells. Cap at ~6 rows × ~5 columns for readability.

## Holdings table

```html
<table>
  <thead>
    <tr>
      <th class="rank">#</th>
      <th>Ticker</th>
      <th>Name</th>
      <th class="num">Qty</th>
      <th class="num">Price</th>
      <th class="num">Day Chg</th>
      <th class="num">Mkt Value</th>
      <th class="num">Weight</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="rank">1</td>
      <td class="ticker">NVDA</td>
      <td>NVIDIA Corp</td>
      <td class="num">120</td>
      <td class="num">$485.20</td>
      <td class="num up">+1.84%</td>
      <td class="num">$58,224</td>
      <td class="num">6.91%</td>
    </tr>
    <!-- ... -->
  </tbody>
</table>
```

For crypto-only portfolios, swap "Ticker"/"Name" for "Symbol"/"Asset" and add a "24h Vol" column. Add weight bars inline by replacing the weight cell with:

```html
<td class="num" style="position: relative;">
  <div style="position: absolute; left: 0; top: 0; bottom: 0; width: 6.91%; background: rgba(38,166,154,0.15);"></div>
  <span style="position: relative;">6.91%</span>
</td>
```

## Chart pattern

For equity curve, use single area-filled line with `--accent-up`. If showing benchmark comparison (e.g., portfolio vs SPX), add a second dataset with `--accent-blue`, no fill, dashed:

```js
datasets: [
  { label: 'Portfolio', data: portfolioData, borderColor: '#26a69a',
    backgroundColor: 'rgba(38,166,154,0.08)', fill: true, borderWidth: 1.5, pointRadius: 0, tension: 0.25 },
  { label: 'S&P 500', data: spxData, borderColor: '#2962ff',
    borderDash: [4, 4], fill: false, borderWidth: 1.5, pointRadius: 0, tension: 0.25 }
]
```

Add a small legend in the panel header instead of using Chart.js's default legend.
