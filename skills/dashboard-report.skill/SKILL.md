---
name: dashboard-report
description: Build modern, TradingView-style dashboard reports as single-file HTML artifacts in light or dark theme. Use this skill whenever the user asks for a "dashboard," "report," "summary view," "overview," "metrics view," "scorecard," or wants to visualize data with KPI cards, charts, ranked tables, or heatmaps — even if they don't say the word "dashboard." Especially trigger this for ERCOT/energy market reports, portfolio/investment summaries, crypto/stock market analyses, project status reports, or any tabular data the user wants to "see at a glance." Default to this skill for any visual data report unless the user explicitly asks for a different format (e.g., Word doc, slides, plain markdown).
---

# Dashboard Report

Build single-file HTML dashboards with a modern, TradingView-inspired aesthetic. Output is one `.html` file the user can open in a browser, drop in artifacts, or share as an attachment.

## When to use this skill

Use whenever a user wants data presented visually with the look-and-feel of a financial/market dashboard. Examples:

- "Make me a weekly portfolio report"
- "Summarize this CSV as a dashboard"
- "ERCOT BESS revenue dashboard for last month"
- "Crypto market overview"
- "Project status overview"
- "Create a scorecard for my 6대 거장 stock screen"

If the user has not provided data, ask once what they want included, then proceed.

## Theme selection

Two themes are supported. Pick based on user signals:

- **Light (default)** — pick this when user doesn't specify, or says "light", "bright", "라이트", "밝은", "white". TradingView light-mode aesthetic: soft off-white surface, subtle gridlines, still high information density.
- **Dark** — pick this when user says "dark", "dark mode", "다크", "어두운", "Bloomberg-style". TradingView terminal aesthetic.

Both themes share the same structure, layout, typography, and component patterns. Only the color tokens differ. **Always state at the top of your response which theme you chose**, e.g., "Building this in light theme — let me know if you want dark."

## Output contract

The deliverable is **one self-contained HTML file** with:

1. **Header bar** — title, subtitle/date, optional status pill
2. **KPI card row** — 3–6 cards with large number, label, change indicator
3. **Chart area** — at least one chart (line/bar/area). Use Chart.js via CDN.
4. **Data table** — ranked or sortable rows with conditional formatting
5. **Heatmap** — color matrix (if data supports it; otherwise a sector-grid)

Save the file to `/mnt/user-data/outputs/` and present it. No external CSS/JS files — everything inline or via CDN.

## Design system (mandatory)

Use the CSS variables below. Both themes share the same variable *names*, only values differ. Pick one theme per dashboard — do not mix.

### Color tokens — LIGHT theme

```css
:root {
  --bg-base:        #f7f8fa;   /* page background — soft off-white */
  --bg-panel:       #ffffff;   /* card/panel background */
  --bg-panel-2:     #f0f2f5;   /* hover/elevated surface */
  --bg-row-alt:     #fafbfc;   /* alternating table row */
  --border-soft:    #e0e3eb;   /* panel borders, dividers */
  --border-strong:  #c8ccd4;
  --text-primary:   #131722;   /* main text — TradingView light text */
  --text-secondary: #5d606b;   /* labels, captions */
  --text-muted:     #9598a1;
  --accent-up:      #089981;   /* TradingView light-mode green (slightly darker for contrast) */
  --accent-down:    #f23645;   /* TradingView light-mode red */
  --accent-blue:    #2962ff;   /* primary action */
  --accent-amber:   #ff9800;   /* warning / neutral highlight */
  --accent-purple:  #9c27b0;   /* secondary highlight */
  --grid-line:      #eceff3;
  --shadow-card:    0 1px 2px rgba(16, 24, 40, 0.04);
}
```

### Color tokens — DARK theme

```css
:root {
  --bg-base:        #0d1117;
  --bg-panel:       #131722;
  --bg-panel-2:     #1c2030;
  --bg-row-alt:     #161b27;
  --border-soft:    #2a2e39;
  --border-strong:  #363a45;
  --text-primary:   #d1d4dc;
  --text-secondary: #787b86;
  --text-muted:     #5d606b;
  --accent-up:      #26a69a;
  --accent-down:    #ef5350;
  --accent-blue:    #2962ff;
  --accent-amber:   #ff9800;
  --accent-purple:  #9c27b0;
  --grid-line:      #1e222d;
  --shadow-card:    none;     /* dark theme uses borders only, no shadows */
}
```

### Theme-specific notes

**Light theme:**
- Apply a subtle `box-shadow` to panels (`var(--shadow-card)`) — gives a paper-like lift without being heavy. Don't stack shadows.
- Heatmap cell color alphas need bumping up by ~15% vs dark, because light backgrounds wash out low-opacity colors. Use the helpers in the templates.
- Chart `backgroundColor` (area fill under lines) should be `rgba(8, 153, 129, 0.10)` for green and `rgba(242, 54, 69, 0.08)` for red.

**Dark theme:**
- No shadows. Use borders only.
- Slightly lower-saturation greens/reds — already encoded in tokens above.

### Typography (both themes)

- **Numbers/data**: `'JetBrains Mono', 'SF Mono', 'Roboto Mono', monospace` — tabular numbers are non-negotiable
- **UI/labels**: `'Inter', -apple-system, system-ui, sans-serif`
- Numbers right-aligned in tables. Use `font-variant-numeric: tabular-nums`.

### Spacing & layout (both themes)

- 12px panel padding minimum, 20px for top-level cards
- 1px borders, never thicker
- Border radius: 6px on panels, 4px on inner elements
- Grid gap: 12px between panels
- Page max-width: 1400px, centered, 24px outer padding

### Component patterns (both themes)

- **KPI cards**: small uppercase label (10–11px, letter-spacing 0.08em, secondary color) → big number (28–32px, mono, primary color) → change indicator (12px, green/red with arrow ▲/▼)
- **Tables**: header row uppercase 10px secondary color, cells 13px, alternating row backgrounds, no vertical borders, hover state `--bg-panel-2`
- **Charts**: `--grid-line` for gridlines, `--accent-up`/`--accent-down` for series, no chart titles inside the canvas
- **Heatmap cells**: square or near-square, 2px gap between cells, color interpolation from `--accent-down` through neutral to `--accent-up`

### What to avoid (both themes)

- Pastels, purple-on-white gradients
- Sans-serif numbers without tabular alignment
- Heavy drop shadows on cards (subtle only on light theme; none on dark)
- Pie charts (use bar/heatmap instead)
- Generic AI-slop styling (rounded-2xl, gradient buttons, etc.)

## Build process

1. **Pick the theme.** Check user signals; default to light if unclear.
2. **Understand the data.** If a file is uploaded, read it first. If the user describes data in chat, extract structure.
3. **Pick KPIs.** 3–6 headline numbers, each with a comparison if possible.
4. **Pick the chart.** Time series → line/area. Categorical → horizontal bar. Distribution → histogram.
5. **Build the table.** Rank by most important column. 8–20 rows.
6. **Build the heatmap.** Sector × period, hour × day, asset × asset. Or treemap-grid fallback.
7. **Assemble HTML.** See `references/html-template.md`.
8. **Save & present.** Write to `/mnt/user-data/outputs/<descriptive-name>.html` and call `present_files`.

## Layout grid

```
┌───────────────────────────────────────────────────────────┐
│ Header (title, subtitle, status)                          │
├───────────────────────────────────────────────────────────┤
│ [KPI 1]  [KPI 2]  [KPI 3]  [KPI 4]  [KPI 5]               │
├──────────────────────────────────┬────────────────────────┤
│  Main chart (2/3 width)          │  Heatmap (1/3 width)   │
├──────────────────────────────────┴────────────────────────┤
│  Data table (full width, ranked)                          │
└───────────────────────────────────────────────────────────┘
```

For mobile/narrow viewports, everything stacks vertically.

## Worked examples

Reference files in `references/`:

- `references/html-template.md` — base skeleton with both theme `:root` blocks (always read first)
- `references/example-portfolio.md` — stock/crypto portfolio dashboard
- `references/example-ercot.md` — ERCOT market dashboard
- `references/example-generic.md` — generic project/KPI dashboard

## Korean / multilingual content

If the user's data or request is in Korean, render labels and headers in Korean. Numbers and tickers stay Latin. Add `lang="ko"` to `<html>` and ensure font stack includes Korean fallback: `'Pretendard', 'Noto Sans KR', sans-serif`.

## Common mistakes to avoid

- **Don't** use Tailwind via CDN — write plain CSS.
- **Don't** add a footer with "Generated by Claude" or watermarks.
- **Don't** make up data. Use placeholder "—" for missing cells.
- **Don't** mix themes within one dashboard.
- **Don't** ask for clarification on every detail. Make defaults, build, iterate.
