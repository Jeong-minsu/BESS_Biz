# Example: Generic KPI Dashboard

For any non-financial use case — project status, ops metrics, sales pipeline, research outputs, etc. The look-and-feel stays the same; the data and labels change.

## When to use this variant

User says any of:
- "Project status dashboard"
- "Make a scorecard for X"
- "Summarize this CSV / spreadsheet"
- "Weekly report"
- "Team metrics"
- "Sales / pipeline / KPI overview"

## Structure (flexible)

The 4 elements stay: KPI cards, chart, heatmap, table. What changes:

- **KPIs** — pick any 3–6 numbers from the data. Always pair with a comparison if possible (vs target, vs prior period, vs goal).
- **Chart** — time series if the data has dates. Otherwise horizontal bar of top items.
- **Heatmap** — if no obvious 2D dimension exists, use a "treemap-style" grid: boxes sized by weight, colored by performance. See pattern below.
- **Table** — ranked rows of whatever the user is tracking.

## Treemap-style grid (heatmap substitute)

When there's no real 2D matrix, use this:

```html
<div class="treemap" style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 2px; padding: 12px; height: 100%;">
  <div class="tm-cell" style="grid-column: span 6; grid-row: span 4; background: rgba(38,166,154,0.55); padding: 12px;">
    <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em;">Engineering</div>
    <div style="font-family: 'JetBrains Mono', monospace; font-size: 18px; margin-top: 4px;">+24.5%</div>
  </div>
  <div class="tm-cell" style="grid-column: span 6; grid-row: span 2; background: rgba(38,166,154,0.40); padding: 12px;">
    <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Sales</div>
    <div style="font-family: 'JetBrains Mono', monospace; font-size: 16px;">+12.8%</div>
  </div>
  <!-- ... -->
</div>
```

Span the tiles based on weight/importance (e.g., budget share, revenue share).

## KPI examples for non-financial data

Status / ops:

```html
<div class="kpi">
  <div class="kpi-label">Active Projects</div>
  <div class="kpi-value">24</div>
  <div class="kpi-change up">▲ 3 this week</div>
</div>

<div class="kpi">
  <div class="kpi-label">On Track</div>
  <div class="kpi-value">87%</div>
  <div class="kpi-change up">▲ 4pp vs target</div>
</div>

<div class="kpi">
  <div class="kpi-label">Open Issues</div>
  <div class="kpi-value">142</div>
  <div class="kpi-change down">▼ -8 closed today</div>
</div>
```

Note that "down" can be the *good* direction (e.g., reduced issue count). In that case still use the `down`/`up` color matching the *direction of change* — but consider switching to `neutral` if the semantic is opposite to the visual color. The user can always override.

## Status pill variants

For status-heavy reports, replace the live indicator:

```html
<div class="status-pill" style="border-color: var(--accent-up); color: var(--accent-up);">
  <span style="background: var(--accent-up);"></span>On track
</div>
```

Or for warnings:

```html
<div class="status-pill" style="border-color: var(--accent-amber); color: var(--accent-amber);">
  <span style="background: var(--accent-amber);"></span>At risk
</div>
```

(The pill's `::before` dot inherits via the same color override.)

## Inline progress bars in tables

For project tables, replace numeric % cells with progress bars:

```html
<td class="num" style="position: relative; min-width: 120px;">
  <div style="display: flex; align-items: center; gap: 8px;">
    <div style="flex: 1; height: 6px; background: var(--bg-panel-2); border-radius: 3px; overflow: hidden;">
      <div style="height: 100%; width: 67%; background: var(--accent-up);"></div>
    </div>
    <span>67%</span>
  </div>
</td>
```

## Don't get fancy

The whole point is that this looks like a real product. Keep it boring and consistent. Resist:

- Adding emoji to KPI labels
- Mixing accent colors arbitrarily — every color has a meaning (up, down, info, warning)
- Cutesy section headers ("How are we doing? 🎯")
- Comic Sans / handwritten / playful fonts
