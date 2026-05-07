# HTML Template — Base Skeleton (Light & Dark)

Always start from this skeleton. Pick **one theme** per dashboard — copy that `:root` block into your HTML. Keep all other CSS intact.

## Theme: LIGHT (default)

```css
:root {
  --bg-base: #f7f8fa;
  --bg-panel: #ffffff;
  --bg-panel-2: #f0f2f5;
  --bg-row-alt: #fafbfc;
  --border-soft: #e0e3eb;
  --border-strong: #c8ccd4;
  --text-primary: #131722;
  --text-secondary: #5d606b;
  --text-muted: #9598a1;
  --accent-up: #089981;
  --accent-down: #f23645;
  --accent-blue: #2962ff;
  --accent-amber: #ff9800;
  --accent-purple: #9c27b0;
  --grid-line: #eceff3;
  --shadow-card: 0 1px 2px rgba(16, 24, 40, 0.04);
}
```

## Theme: DARK

```css
:root {
  --bg-base: #0d1117;
  --bg-panel: #131722;
  --bg-panel-2: #1c2030;
  --bg-row-alt: #161b27;
  --border-soft: #2a2e39;
  --border-strong: #363a45;
  --text-primary: #d1d4dc;
  --text-secondary: #787b86;
  --text-muted: #5d606b;
  --accent-up: #26a69a;
  --accent-down: #ef5350;
  --accent-blue: #2962ff;
  --accent-amber: #ff9800;
  --accent-purple: #9c27b0;
  --grid-line: #1e222d;
  --shadow-card: none;
}
```

## Full template

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><!-- Report title --></title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  /* PASTE YOUR CHOSEN :root BLOCK HERE (light or dark) */
  :root {
    --bg-base: #f7f8fa;
    --bg-panel: #ffffff;
    --bg-panel-2: #f0f2f5;
    --bg-row-alt: #fafbfc;
    --border-soft: #e0e3eb;
    --border-strong: #c8ccd4;
    --text-primary: #131722;
    --text-secondary: #5d606b;
    --text-muted: #9598a1;
    --accent-up: #089981;
    --accent-down: #f23645;
    --accent-blue: #2962ff;
    --accent-amber: #ff9800;
    --accent-purple: #9c27b0;
    --grid-line: #eceff3;
    --shadow-card: 0 1px 2px rgba(16, 24, 40, 0.04);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg-base);
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, system-ui, sans-serif;
    font-size: 13px;
    line-height: 1.5;
    padding: 24px;
    min-height: 100vh;
  }
  .dashboard {
    max-width: 1400px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  /* ---------- HEADER ---------- */
  .header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-soft);
    margin-bottom: 8px;
  }
  .header h1 {
    font-size: 22px;
    font-weight: 600;
    letter-spacing: -0.01em;
  }
  .header .subtitle {
    color: var(--text-secondary);
    font-size: 12px;
    margin-top: 4px;
    font-variant-numeric: tabular-nums;
  }
  .status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border: 1px solid var(--border-soft);
    border-radius: 4px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-secondary);
    background: var(--bg-panel);
  }
  .status-pill::before {
    content: '';
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--accent-up);
  }
  /* ---------- PANEL ---------- */
  .panel {
    background: var(--bg-panel);
    border: 1px solid var(--border-soft);
    border-radius: 6px;
    overflow: hidden;
    box-shadow: var(--shadow-card);
  }
  .panel-header {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-soft);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .panel-title {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-secondary);
    font-weight: 500;
  }
  .panel-body { padding: 16px; }
  /* ---------- KPI ROW ---------- */
  .kpi-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
  }
  .kpi {
    background: var(--bg-panel);
    border: 1px solid var(--border-soft);
    border-radius: 6px;
    padding: 16px 18px;
    box-shadow: var(--shadow-card);
  }
  .kpi-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-secondary);
    margin-bottom: 8px;
  }
  .kpi-value {
    font-family: 'JetBrains Mono', 'SF Mono', monospace;
    font-size: 28px;
    font-weight: 500;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
    line-height: 1.1;
  }
  .kpi-change {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    margin-top: 6px;
    font-variant-numeric: tabular-nums;
  }
  .up { color: var(--accent-up); }
  .down { color: var(--accent-down); }
  .neutral { color: var(--text-secondary); }
  /* ---------- MAIN GRID ---------- */
  .main-grid {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 12px;
  }
  @media (max-width: 1000px) {
    .main-grid { grid-template-columns: 1fr; }
  }
  .chart-wrap {
    height: 360px;
    padding: 12px;
  }
  /* ---------- HEATMAP ---------- */
  .heatmap {
    display: grid;
    gap: 2px;
    padding: 12px;
  }
  .heatmap-cell {
    aspect-ratio: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-variant-numeric: tabular-nums;
    color: var(--text-primary);
    border-radius: 2px;
    cursor: default;
  }
  .heatmap-axis {
    font-size: 10px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  /* ---------- TABLE ---------- */
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  thead th {
    text-align: left;
    padding: 10px 16px;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-secondary);
    font-weight: 500;
    border-bottom: 1px solid var(--border-soft);
    background: var(--bg-panel);
  }
  thead th.num { text-align: right; }
  tbody td {
    padding: 10px 16px;
    border-bottom: 1px solid var(--grid-line);
  }
  tbody td.num {
    text-align: right;
    font-family: 'JetBrains Mono', monospace;
    font-variant-numeric: tabular-nums;
  }
  tbody tr:nth-child(even) { background: var(--bg-row-alt); }
  tbody tr:hover { background: var(--bg-panel-2); }
  .rank {
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
    width: 32px;
  }
  .ticker { font-weight: 600; letter-spacing: 0.02em; }
</style>
</head>
<body>
<div class="dashboard">

  <!-- Header / KPIs / Main grid / Table -->
  <!-- See structure in SKILL.md and example files -->

</div>

<script>
  // Theme-aware Chart.js defaults
  // For LIGHT theme:
  Chart.defaults.color = '#5d606b';        // = --text-secondary
  Chart.defaults.borderColor = '#eceff3';  // = --grid-line
  // For DARK theme:
  // Chart.defaults.color = '#787b86';
  // Chart.defaults.borderColor = '#1e222d';
  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.font.size = 11;

  // Example chart
  new Chart(document.getElementById('mainChart'), {
    type: 'line',
    data: {
      labels: [/* ... */],
      datasets: [{
        label: 'Series',
        data: [/* ... */],
        borderColor: '#089981',  // light: #089981, dark: #26a69a
        backgroundColor: 'rgba(8, 153, 129, 0.10)',  // light alpha 0.10, dark 0.08
        borderWidth: 1.5,
        fill: true,
        tension: 0.25,
        pointRadius: 0,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'var(--grid-line)', drawTicks: false }, border: { display: false } },
        y: { grid: { color: 'var(--grid-line)', drawTicks: false }, border: { display: false }, ticks: { padding: 8 } }
      },
      interaction: { mode: 'index', intersect: false }
    }
  });

  // Heatmap color helper — pass v in [-1, 1]
  // Theme-aware: pick the right alpha range based on which theme you're using.
  function heatColorLight(v) {
    v = Math.max(-1, Math.min(1, v));
    if (v >= 0) return `rgba(8, 153, 129, ${0.20 + v * 0.65})`;
    return `rgba(242, 54, 69, ${0.20 + (-v) * 0.65})`;
  }
  function heatColorDark(v) {
    v = Math.max(-1, Math.min(1, v));
    if (v >= 0) return `rgba(38, 166, 154, ${0.15 + v * 0.65})`;
    return `rgba(239, 83, 80, ${0.15 + (-v) * 0.65})`;
  }
</script>
</body>
</html>
```

## Theme switch checklist

When converting a light-themed dashboard to dark (or vice versa):

1. Swap the `:root` block.
2. Update `Chart.defaults.color` and `Chart.defaults.borderColor` (see comments in the script section).
3. Update each chart dataset's `borderColor` and `backgroundColor` to use the correct theme's accent values:
   - Light green: `#089981` / fill `rgba(8, 153, 129, 0.10)`
   - Dark green: `#26a69a` / fill `rgba(38, 166, 154, 0.08)`
   - Light red: `#f23645` / fill `rgba(242, 54, 69, 0.08)`
   - Dark red: `#ef5350` / fill `rgba(239, 83, 80, 0.08)`
4. Use the appropriate `heatColorLight` or `heatColorDark` function for heatmap cells.
5. That's it — every other element reads from CSS variables and adapts automatically.

## Notes

- The chart uses `tension: 0.25` for a subtle smoothing.
- For multi-series charts, alternate `--accent-up`, `--accent-blue`, `--accent-amber`, `--accent-purple`. Never reuse green and red for non-directional series.
- For ERCOT or any time-of-day data, prefer the heatmap as hour × day. For portfolio data, use sector × period.
- If a heatmap dataset has fewer than 5 categorical items, switch to a horizontal bar chart instead.
