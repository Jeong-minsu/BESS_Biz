# Example: ERCOT Market Dashboard

A dashboard for ERCOT energy market reports — BESS revenue, LMP analysis, congestion summary, etc. Use as reference for any energy/power market request.

## Structure

- **Header**: "ERCOT Daily Report" + date + ISO/zone
- **5 KPIs**: HB_HOUSTON Avg LMP, Peak LMP, BESS Revenue, DA-RT Spread, Congestion $/MWh
- **Main chart**: 24h LMP curve (DA vs RT, two series)
- **Heatmap**: Hour × Day-of-week LMP heatmap (last 7 days)
- **Table**: Top binding constraints OR top revenue nodes, ranked

## ERCOT-specific KPIs

```html
<div class="kpi">
  <div class="kpi-label">HB_HOUSTON LMP (Avg)</div>
  <div class="kpi-value">$48.21</div>
  <div class="kpi-change up">▲ $4.12 vs 7d avg</div>
</div>

<div class="kpi">
  <div class="kpi-label">Peak Hour Price</div>
  <div class="kpi-value">$284.50</div>
  <div class="kpi-change neutral">HE 18, RT</div>
</div>

<div class="kpi">
  <div class="kpi-label">BESS Daily Rev</div>
  <div class="kpi-value">$12,840</div>
  <div class="kpi-change up">▲ $1,920 (+17.6%)</div>
</div>

<div class="kpi">
  <div class="kpi-label">DA-RT Spread (Avg)</div>
  <div class="kpi-value">-$2.34</div>
  <div class="kpi-change down">▼ RT premium</div>
</div>

<div class="kpi">
  <div class="kpi-label">Congestion $</div>
  <div class="kpi-value">$8.42</div>
  <div class="kpi-change up">▲ binding constraints +3</div>
</div>
```

## DA vs RT chart

24-hour view, x-axis is hour-ending 1–24:

```js
new Chart(ctx, {
  type: 'line',
  data: {
    labels: ['HE1','HE2','HE3','HE4','HE5','HE6','HE7','HE8','HE9','HE10','HE11','HE12',
             'HE13','HE14','HE15','HE16','HE17','HE18','HE19','HE20','HE21','HE22','HE23','HE24'],
    datasets: [
      { label: 'DAM', data: damPrices, borderColor: '#2962ff',
        borderWidth: 1.5, fill: false, pointRadius: 0, tension: 0, stepped: true },
      { label: 'RTM', data: rtmPrices, borderColor: '#26a69a',
        borderWidth: 1.5, fill: false, pointRadius: 0, tension: 0 }
    ]
  },
  options: {
    /* same as base, but add a second y-axis if showing $/MWh and MW dispatch together */
    scales: {
      x: { grid: { color: '#1e222d' }, border: { display: false } },
      y: {
        grid: { color: '#1e222d' }, border: { display: false },
        ticks: { callback: v => '$' + v }
      }
    }
  }
});
```

Use `stepped: true` for DAM (it's hourly blocks) and smooth line for RTM (5-min granular).

## Hour × Day heatmap (TOU pattern)

This is the single most useful visual for ERCOT — shows when prices spike. Grid is 7 columns (days) × 24 rows (hours):

```html
<div class="heatmap" id="touHeatmap"
     style="grid-template-columns: 40px repeat(7, 1fr); grid-template-rows: 24px repeat(24, 1fr);">
  <div class="heatmap-axis"></div>
  <div class="heatmap-axis">Mon</div>
  <div class="heatmap-axis">Tue</div>
  <div class="heatmap-axis">Wed</div>
  <div class="heatmap-axis">Thu</div>
  <div class="heatmap-axis">Fri</div>
  <div class="heatmap-axis">Sat</div>
  <div class="heatmap-axis">Sun</div>
  <!-- For each hour 0..23: axis label + 7 cells -->
</div>
```

Generate cells in JS:

```js
const hours = Array.from({length: 24}, (_, i) => i);
const days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
const grid = document.getElementById('touHeatmap');

// priceData[day][hour] = $/MWh
const max = Math.max(...priceData.flat());
const min = Math.min(...priceData.flat());

hours.forEach(h => {
  const label = document.createElement('div');
  label.className = 'heatmap-axis';
  label.textContent = String(h).padStart(2,'0');
  grid.appendChild(label);
  days.forEach((d, di) => {
    const v = priceData[di][h];
    const norm = (v - min) / (max - min); // 0..1
    const cell = document.createElement('div');
    cell.className = 'heatmap-cell';
    // Cool->warm gradient: blue (low) -> dark (mid) -> green (high) -> red (spike)
    cell.style.background = ercotHeatColor(norm);
    cell.title = `${d} HE${h+1}: $${v.toFixed(2)}/MWh`;
    cell.textContent = v > 100 ? '$' + Math.round(v) : '';  // only label spikes
    grid.appendChild(cell);
  });
});

function ercotHeatColor(t) {
  // t in [0,1]
  if (t < 0.5) {
    // blue -> dark
    const a = t * 2;
    return `rgba(41, 98, 255, ${0.5 - a * 0.4})`;
  } else {
    // dark -> green -> red
    const a = (t - 0.5) * 2;
    if (a < 0.6) return `rgba(38, 166, 154, ${0.2 + a * 0.7})`;
    return `rgba(239, 83, 80, ${0.5 + (a - 0.6) * 1.0})`;
  }
}
```

## Binding constraints table

```html
<table>
  <thead>
    <tr>
      <th class="rank">#</th>
      <th>Constraint</th>
      <th>Contingency</th>
      <th class="num">Hours Bound</th>
      <th class="num">Avg Shadow $</th>
      <th class="num">Max Shadow $</th>
      <th class="num">Direction</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="rank">1</td>
      <td class="ticker">PNHNDL_BPLAINS_1</td>
      <td>BASECASE</td>
      <td class="num">14</td>
      <td class="num">$184.20</td>
      <td class="num">$2,250.00</td>
      <td class="num up">FROM</td>
    </tr>
    <!-- ... -->
  </tbody>
</table>
```

Korean variant: replace headers with 제약명, 기준상정, 구속시간, 평균쉐도우, 최대쉐도우, 방향.

## Variant: BESS revenue dashboard

For revenue-focused reports, swap the binding-constraints table for revenue stack:

| Rank | Asset | DAM Energy | RTM Energy | RegUp | RegDn | RRS | ECRS | Total |

Color the largest revenue source per row green, smallest red — gives a quick read of which markets are paying.
