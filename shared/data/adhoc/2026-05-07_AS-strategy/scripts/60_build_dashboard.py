"""Generate single-file HTML dashboard for AS-strategy ad-hoc analysis (v2 — AS-market focused)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC = Path(__file__).resolve().parents[1]
DERIVED = ADHOC / "derived"
PROJECT_ROOT = Path(__file__).resolve().parents[5]
OUT = PROJECT_ROOT / "reports" / "ad-hoc" / "2026-05-07_AS-strategy.html"

with open(DERIVED / "dashboard_data.json", encoding="utf-8") as f:
    D = json.load(f)

PRODS = ["REGUP", "REGDN", "RRS", "ECRS", "NSPIN"]

# Build Q2 split LP comparison rows (delivery vs pure-arb)
split_rows = ""
for p in PRODS:
    arb = D["split_lp"]["per_product"][p]
    dev = D["deliv_lp"]["per_product"][p]
    split_rows += f"""
    <tr>
      <td><span class="ticker">{p}</span></td>
      <td class="num">{dev['a_DA_mean']:.1f}</td>
      <td class="num">{dev['a_RT_mean']:.1f}</td>
      <td class="num up"><strong>{dev['DA_share']*100:.0f}%</strong></td>
      <td class="num">${dev['net_revenue']:>10,.0f}</td>
      <td class="num neutral">{arb['DA_share']*100:.0f}%</td>
      <td class="num neutral">${arb['net_revenue']:>10,.0f}</td>
    </tr>
    """


def fmt_money(v):
    if abs(v) >= 1_000_000: return f"${v/1_000_000:,.2f}M"
    if abs(v) >= 1_000:     return f"${v/1_000:,.0f}K"
    return f"${v:,.0f}"


def fmt_pct(v):
    return f"{v*100:,.1f}%"


# ============= KPIs =============
totals = D["as_totals"]
always_dam_pct = totals["always_dam"] / totals["optimal"]
always_rt_pct  = totals["always_rt"]  / totals["optimal"]

kpi_html = f"""
<div class="kpi">
  <div class="kpi-label">AS Optimal (DAM vs RT 시간별 best)</div>
  <div class="kpi-value">{fmt_money(totals['optimal'])}</div>
  <div class="kpi-change neutral">100MW × 5종 × 60일 ex-post</div>
</div>
<div class="kpi">
  <div class="kpi-label">Always-DAM 전략</div>
  <div class="kpi-value up">{fmt_pct(always_dam_pct)}</div>
  <div class="kpi-change up">{fmt_money(totals['always_dam'])} (Optimal의 {fmt_pct(always_dam_pct)})</div>
</div>
<div class="kpi">
  <div class="kpi-label">Always-RT 전략</div>
  <div class="kpi-value down">{fmt_pct(always_rt_pct)}</div>
  <div class="kpi-change down">{fmt_money(totals['always_rt'])} — RT 우선은 손해</div>
</div>
<div class="kpi">
  <div class="kpi-label">DAM &gt; RT 시간 (5종 평균)</div>
  <div class="kpi-value">~85%</div>
  <div class="kpi-change neutral">대다수 시간에 DAM 우세</div>
</div>
<div class="kpi">
  <div class="kpi-label">RT &gt; DAM driver</div>
  <div class="kpi-value">Wind Bust</div>
  <div class="kpi-change neutral">NSPIN/ECRS/RRS corr -0.13~-0.22</div>
</div>
"""

# ============= Q1: Updated LP AS allocation table =============
q1_rows = ""
for p in PRODS:
    expost = D["expost_as_by_product"][p]
    actual = D["actual_as_by_product"][p]
    pct = (actual / expost * 100) if expost > 0 else 0
    q1_rows += f"""
    <tr>
      <td><span class="ticker">{p}</span></td>
      <td class="num">{fmt_money(expost)}</td>
      <td class="num">{fmt_money(actual)}</td>
      <td class="num {'up' if pct > 100 else 'down' if pct < 50 else 'neutral'}">{pct:.0f}%</td>
      <td class="num">{D['gks_award_hrs'][p]}</td>
    </tr>
    """

# ============= Q2: DAM vs RT level table =============
q2_level_rows = ""
for r in D["as_levels"]:
    p = r["product"]
    ratio = r["dam_mean"] / r["rt_mean"] if r["rt_mean"] > 0 else float("inf")
    pct_dam_win = r["n_dam_gt_rt"] / (r["n_dam_gt_rt"] + r["n_rt_gt_dam"] + r["n_equal"])
    q2_level_rows += f"""
    <tr>
      <td><span class="ticker">{p}</span></td>
      <td class="num">${r['dam_mean']:.2f}</td>
      <td class="num">${r['rt_mean']:.2f}</td>
      <td class="num up">{ratio:.1f}×</td>
      <td class="num">{r['n_dam_gt_rt']:,}</td>
      <td class="num">{r['n_rt_gt_dam']:,}</td>
      <td class="num up">{pct_dam_win*100:.0f}%</td>
    </tr>
    """

# ============= Q2: per-product strategy revenue =============
q2_strat_rows = ""
for r in D["as_strategies"]:
    p = r["product"]
    q2_strat_rows += f"""
    <tr>
      <td><span class="ticker">{p}</span></td>
      <td class="num">{fmt_money(r['always_dam_revenue'])}</td>
      <td class="num">{fmt_money(r['always_rt_revenue'])}</td>
      <td class="num">{fmt_money(r['optimal_revenue'])}</td>
      <td class="num up">{r['dam_pct_of_optimal']*100:.0f}%</td>
      <td class="num down">{r['rt_pct_of_optimal']*100:.0f}%</td>
    </tr>
    """

# ============= Q3: RT > DAM characterization =============
q3_summary_rows = ""
for r in D["rt_gt_dam_summary"]:
    p = r["product"]
    pct_rt_win = r["n_rt_ge_dam"] / 1440 * 100
    wind_err = r.get("mean_wind_fc_err_in_spike") or 0
    q3_summary_rows += f"""
    <tr>
      <td><span class="ticker">{p}</span></td>
      <td class="num">{r['n_rt_ge_dam']:,}</td>
      <td class="num">{pct_rt_win:.1f}%</td>
      <td class="num">{r['n_rt_spike_5plus']}</td>
      <td class="num">${r['mean_rt_minus_dam_when_rt_wins']:.2f}</td>
      <td class="num down">{wind_err:+,.0f}</td>
    </tr>
    """

# ============= Q3: Top RT > DAM spike events =============
q3_spike_rows = ""
for r in D["top_rt_dam_spikes"][:12]:
    q3_spike_rows += f"""
    <tr>
      <td>{r['date']}</td>
      <td class="num">{int(r['he'])}</td>
      <td><span class="ticker">{r['max_spread_prod']}</span></td>
      <td class="num down">+${r['max_spread']:.1f}</td>
      <td class="num">${r['DALMP_GKS_BESS_RN']:.0f}</td>
      <td class="num">${r['RTLMP_GKS_BESS_RN']:.0f}</td>
      <td class="num">{r['load_fc_err']:+,.0f}</td>
      <td class="num down">{r['wind_fc_err']:+,.0f}</td>
    </tr>
    """

# ============= Worst gap days =============
worst_rows = ""
for r in D["worst_gap_days"]:
    worst_rows += f"""
    <tr>
      <td>{r['date']}</td>
      <td class="num">{fmt_money(r['lp_total'])}</td>
      <td class="num">{fmt_money(r['actual_total'])}</td>
      <td class="num down">{fmt_money(r['gap'])}</td>
    </tr>
    """

# ============= Charts data JSON =============
charts = {
    "mean_mcpc_dam": D["mean_mcpc_dam_by_he"],
    "mean_mcpc_rt":  D["mean_mcpc_rt_by_he"],
    "dam_win_share_by_he": D["dam_win_share_by_he"],
    "lp_as_alloc": D["lp_as_alloc"],
    "energy_da_share": D["energy_da_share_by_he"],
    "daily_pnl": D["daily_pnl"],
    "corr_table": D["corr_table"],
}
charts_json = json.dumps(charts, ensure_ascii=False)

HTML = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ERCOT BESS — 최적 보조서비스 전략 분석 (v4)</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Noto+Sans+KR:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {{
  --bg-base:#f7f8fa; --bg-panel:#fff; --bg-panel-2:#f0f2f5; --bg-row-alt:#fafbfc;
  --border-soft:#e0e3eb; --border-strong:#c8ccd4;
  --text-primary:#131722; --text-secondary:#5d606b; --text-muted:#9598a1;
  --accent-up:#089981; --accent-down:#f23645; --accent-blue:#2962ff;
  --accent-amber:#ff9800; --accent-purple:#9c27b0;
  --grid-line:#eceff3; --shadow-card:0 1px 2px rgba(16,24,40,0.04);
}}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ background:var(--bg-base); color:var(--text-primary);
  font-family:'Inter','Noto Sans KR',-apple-system,system-ui,sans-serif;
  font-size:13px; line-height:1.5; padding:24px; min-height:100vh; }}
.dashboard {{ max-width:1400px; margin:0 auto; display:flex; flex-direction:column; gap:12px; }}
.header {{ display:flex; justify-content:space-between; align-items:flex-end;
  padding-bottom:16px; border-bottom:1px solid var(--border-soft); margin-bottom:8px; }}
.header h1 {{ font-size:22px; font-weight:600; letter-spacing:-0.01em; }}
.header .subtitle {{ color:var(--text-secondary); font-size:12px; margin-top:4px;
  font-variant-numeric:tabular-nums; }}
.status-pill {{ display:inline-flex; align-items:center; gap:6px;
  padding:4px 10px; border:1px solid var(--border-soft); border-radius:4px;
  font-size:11px; text-transform:uppercase; letter-spacing:0.08em;
  color:var(--text-secondary); background:var(--bg-panel); }}
.status-pill::before {{ content:''; width:6px; height:6px; border-radius:50%;
  background:var(--accent-up); }}
.panel {{ background:var(--bg-panel); border:1px solid var(--border-soft);
  border-radius:6px; overflow:hidden; box-shadow:var(--shadow-card); }}
.panel-header {{ padding:12px 16px; border-bottom:1px solid var(--border-soft);
  display:flex; justify-content:space-between; align-items:center; }}
.panel-title {{ font-size:11px; text-transform:uppercase; letter-spacing:0.08em;
  color:var(--text-secondary); font-weight:500; }}
.panel-body {{ padding:16px; }}
.kpi-row {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(200px,1fr)); gap:12px; }}
.kpi {{ background:var(--bg-panel); border:1px solid var(--border-soft);
  border-radius:6px; padding:16px 18px; box-shadow:var(--shadow-card); }}
.kpi-label {{ font-size:10px; text-transform:uppercase; letter-spacing:0.1em;
  color:var(--text-secondary); margin-bottom:8px; }}
.kpi-value {{ font-family:'JetBrains Mono','SF Mono',monospace; font-size:28px;
  font-weight:500; color:var(--text-primary); font-variant-numeric:tabular-nums;
  line-height:1.1; }}
.kpi-change {{ font-family:'JetBrains Mono',monospace; font-size:11px; margin-top:6px;
  font-variant-numeric:tabular-nums; }}
.up {{color:var(--accent-up);}} .down {{color:var(--accent-down);}}
.neutral {{color:var(--text-secondary);}}
.section-title {{ font-size:14px; font-weight:600; margin-top:8px; margin-bottom:4px;
  padding:8px 0 4px; border-bottom:1px dashed var(--border-soft); }}
.section-title small {{ font-size:11px; font-weight:400; color:var(--text-secondary);
  margin-left:8px; }}
.main-grid {{ display:grid; grid-template-columns:2fr 1fr; gap:12px; }}
.half-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
@media (max-width:1000px) {{ .main-grid, .half-grid {{ grid-template-columns:1fr; }} }}
.chart-wrap {{ height:320px; padding:12px; }}
.chart-wrap.tall {{ height:380px; }}
.heatmap-grid {{ display:grid; gap:2px; padding:12px;
  grid-template-columns:60px repeat(24, 1fr); }}
.heatmap-cell {{ aspect-ratio:1; display:flex; align-items:center; justify-content:center;
  font-family:'JetBrains Mono',monospace; font-size:9px;
  font-variant-numeric:tabular-nums; color:var(--text-primary);
  border-radius:2px; cursor:default; }}
.heatmap-axis {{ font-size:9px; color:var(--text-secondary); text-transform:uppercase;
  letter-spacing:0.05em; display:flex; align-items:center; justify-content:center; }}
.heatmap-axis.row-label {{ justify-content:flex-end; padding-right:8px; font-size:10px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
thead th {{ text-align:left; padding:10px 16px; font-size:10px;
  text-transform:uppercase; letter-spacing:0.08em; color:var(--text-secondary);
  font-weight:500; border-bottom:1px solid var(--border-soft); background:var(--bg-panel); }}
thead th.num {{ text-align:right; }}
tbody td {{ padding:9px 16px; border-bottom:1px solid var(--grid-line); }}
tbody td.num {{ text-align:right; font-family:'JetBrains Mono',monospace;
  font-variant-numeric:tabular-nums; }}
tbody tr:nth-child(even) {{ background:var(--bg-row-alt); }}
tbody tr:hover {{ background:var(--bg-panel-2); }}
.ticker {{ font-weight:600; letter-spacing:0.02em; }}
.callout {{ padding:12px 16px; background:var(--bg-panel-2);
  border-left:3px solid var(--accent-amber); border-radius:4px;
  font-size:12px; margin:8px 0; }}
.callout.green {{ border-left-color:var(--accent-up); }}
.callout.red {{ border-left-color:var(--accent-down); }}
.callout.blue {{ border-left-color:var(--accent-blue); }}
.callout strong {{ font-weight:600; }}
ul.findings {{ list-style:none; padding-left:0; }}
ul.findings li {{ padding:6px 0 6px 18px; position:relative;
  font-size:13px; line-height:1.6; }}
ul.findings li::before {{ content:'▸'; position:absolute; left:0;
  color:var(--accent-blue); font-weight:600; }}
ul.findings li.warn::before {{ color:var(--accent-down); }}
ul.findings li.good::before {{ color:var(--accent-up); }}
.method-block {{ font-size:11px; color:var(--text-secondary); line-height:1.7;
  background:var(--bg-panel-2); padding:14px; border-radius:4px;
  border-left:3px solid var(--accent-blue); }}
.method-block strong {{ color:var(--text-primary); }}
.method-block code {{ font-family:'JetBrains Mono',monospace; background:var(--bg-panel);
  padding:1px 4px; border-radius:3px; font-size:10px; }}
</style>
</head>
<body>
<div class="dashboard">

  <div class="header">
    <div>
      <h1>ERCOT BESS — 최적 보조서비스 전략 분석 (v4)</h1>
      <div class="subtitle">
        2026-01-01 ~ 2026-03-06 (60일, post-RTC+B, <strong>Winter Storm Fern 1/24-28 제외</strong>) |
        GKS_BESS_RN 100MW/200MWh |
        D-1 08:30 CT decision |
        DAM AS는 SoC telemetry 검사 없음 (RT only)
      </div>
    </div>
    <div class="status-pill">v4 · 2026-05-07 · DA+RT split LP</div>
  </div>

  <!-- ==================== KPI ==================== -->
  <div class="kpi-row">{kpi_html}</div>

  <!-- ==================== LP Methodology ==================== -->
  <div class="section-title">LP Optimal — 정의 + 방법론</div>
  <div class="method-block">
    <strong>정의:</strong> 60일간 매일 24시간 ex-post (가격 perfect foresight) 100MW/200MWh BESS의 수익 상한.<br><br>
    <strong>Decision variables (HE 별):</strong>
    <code>discharge[h]</code> ∈ [0,100], <code>charge[h]</code> ∈ [0,100],
    <code>discharge_DA[h]</code> ∈ [0, discharge], <code>charge_DA[h]</code> ∈ [0, charge],
    <code>a_p[h]</code> for p ∈ &#123;REGUP, REGDN, RRS, ECRS, NSPIN&#125;, <code>soc[h]</code> ∈ [0, 200].<br><br>
    <strong>제약:</strong>
    (1) Capacity gen: <code>discharge + a_REGUP + a_RRS + a_ECRS + a_NSPIN ≤ 100 MW</code> ·
    (2) Capacity load: <code>charge + a_REGDN ≤ 100 MW</code> ·
    (3) SoC dynamics: <code>soc[h] = soc[h-1] + 0.922×charge − discharge/0.922</code> (RTE 85%) ·
    (4) <strong>SoC reservation 미적용</strong> (사용자 정정 2026-05-07):
    DAM AS commit은 ERCOT가 SoC telemetry 검사 안 함 (RT만 telemetry 기반 award 제한). 본 LP는 DAM AS만 모델링하므로 SoC reservation 제약 없음.
    예: DAM에서 100 MW NSpin 입찰 가능 (SoC 무관). 단 RT NSpin은 telemetry 기반 — SoC 100 MWh이면 RT NSpin award 최대 25 MW (4hr sustain 기준).<br>
    (5) Init <code>soc[0]=100</code>, terminal <code>soc[24]≥50</code>.<br><br>
    <strong>Objective:</strong>
    max Σh [<code>discharge_DA × DA_LMP − charge_DA × DA_LMP + (discharge−discharge_DA) × RT_LMP − (charge−charge_DA) × RT_LMP + Σp a_p × DAM_AS_MCPC_p</code>].<br><br>
    <strong>Solver:</strong> <code>scipy.optimize.linprog</code> (HiGHS), 일별 60회 풀이.<br>
    <strong>주의:</strong> 현 LP는 <em>DAM AS만 가정</em> — RT AS commit option은 미반영. 따라서 LP의 AS 부분은 always-DAM의 ex-post optimal 수준.
  </div>

  <!-- ==================== Q1: Optimal AS Product ==================== -->
  <div class="section-title">
    Q1 · 최적 AS 상품 (Hourly, SoC-aware)
    <small>NSpin 4× / RRS 2× / ECRS 1× SoC 제약 반영</small>
  </div>

  <div class="callout green">
    <strong>요약 (정정 v3):</strong> DAM AS commit은 ERCOT가 SoC를 검사하지 않으므로 (RT만 telemetry 적용)
    LP는 SoC reservation 제약 없이 capacity 한도 (100 MW) 내에서 자유롭게 AS 배분.
    LP optimal AS = <strong>{fmt_money(D['expost_as_total'])}</strong>
    (NSPIN $103K · REGDN $89K · REGUP $22K · ECRS $17K · RRS $2K).
    GKS 실적 <strong>{fmt_money(D['actual_as_total'])}</strong> = LP의
    <strong>{D['actual_as_total']/D['expost_as_total']*100:.0f}%</strong> capture.
    GKS는 NSpin에서 LP 대비 추가 50% 더 commit ($156K vs $103K) — 에너지 기회 비용을 감수하고 NSpin 우선 전략.
  </div>

  <div class="main-grid">
    <div class="panel">
      <div class="panel-header"><span class="panel-title">Mean DAM MCPC ($/MW) · HE × Product Heatmap</span></div>
      <div class="panel-body">
        <div id="damHeatmap" class="heatmap-grid"></div>
        <div style="font-size:10px;color:var(--text-muted);padding:8px 0 0;">색이 짙을수록 시간대별 mean MCPC 高. 새벽/저녁 NSpin, 오전(7-10) ECRS·RRS·REGUP, 오후(14-17) REGDN.</div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">Ex-post LP vs GKS 실적 (AS 별)</span></div>
      <div class="panel-body" style="padding:0;">
        <table>
          <thead><tr>
            <th>Product</th>
            <th class="num">LP (DAM only)</th>
            <th class="num">GKS Actual</th>
            <th class="num">Capture %</th>
            <th class="num">Award Hrs</th>
          </tr></thead>
          <tbody>{q1_rows}</tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="panel">
    <div class="panel-header"><span class="panel-title">LP Optimal AS Allocation (SoC-aware) · Mean MW per HE</span></div>
    <div class="panel-body chart-wrap"><canvas id="lpAsAlloc"></canvas></div>
  </div>

  <!-- ==================== Q2: DAM vs RT split per product ==================== -->
  <div class="section-title">
    Q2 · AS 상품별 DAM vs RT 시장 비중
    <small>"어디에 capacity 할당해야 유리한가?"</small>
  </div>

  <div class="callout green">
    <strong>핵심 답:</strong> 5종 모두 DAM이 RT 대비 평균 1.8~3.3× 비싸고, <strong>DAM &gt; RT 빈도가 70-96%</strong>.
    "Always-DAM" 단순 전략이 ex-post optimal의 <strong>{always_dam_pct*100:.1f}%</strong>를 capture (perfect-foresight switching 대비 +11%만 손해).
    "Always-RT"는 {always_rt_pct*100:.1f}%만 capture 손해 큼.<br>
    <strong>예외</strong>: REGDN의 HE 7-8 + 18-20 (solar ramp), REGUP의 HE 18 (저녁 peak) — DAM win share 0.12-0.40으로 RT 우세 빈도 높음.
  </div>

  <div class="panel">
    <div class="panel-header"><span class="panel-title">Level Comparison: DAM vs RT MCPC per Product (60일)</span></div>
    <div class="panel-body" style="padding:0;">
      <table>
        <thead><tr>
          <th>Product</th>
          <th class="num">DAM mean</th>
          <th class="num">RT mean</th>
          <th class="num">DAM/RT</th>
          <th class="num">DAM &gt; RT (hrs)</th>
          <th class="num">RT &gt; DAM (hrs)</th>
          <th class="num">DAM win %</th>
        </tr></thead>
        <tbody>{q2_level_rows}</tbody>
      </table>
    </div>
  </div>

  <!-- ===== Q2 v4: DA/RT split LP — 사용자 핵심 질문에 대한 직접 답 ===== -->
  <div class="callout red">
    <strong>★ Q2 핵심 답 (DA + RT commit + buyback LP):</strong> 모든 5종 AS에 대해 <strong>DA commit 비중 73-99%</strong>가 평균적 최적.
    REGDN/REGUP에서만 RT 18-27% 의미있고, RRS/ECRS/NSPIN은 95%+ DA 권장.
    Trade-off 모델: DA paid DAM_MCPC, RT 이행 못하면 RT_MCPC buyback. SoC capability 한도 (NSpin soc/4, RRS 2×soc, etc.) 반영.
    <br><strong>전체 평균 DA share ≈ 87% (revenue-weighted)</strong>. 즉 평소 DA 우선, RT는 backstop으로 ~13%.
  </div>

  <div class="panel">
    <div class="panel-header"><span class="panel-title">★ 사용자 질문 답: 평균 최적 DA/RT split per product (delivery-required LP)</span></div>
    <div class="panel-body" style="padding:0;">
      <table>
        <thead><tr>
          <th>Product</th>
          <th class="num">a_DA mean (MW)</th>
          <th class="num">a_RT mean (MW)</th>
          <th class="num">★ DA share (deliverable)</th>
          <th class="num">Net Rev (deliv-LP)</th>
          <th class="num">DA share (pure-arb)</th>
          <th class="num">Net Rev (arb-LP)</th>
        </tr></thead>
        <tbody>{split_rows}</tbody>
      </table>
      <div style="font-size:11px;color:var(--text-secondary);padding:12px 16px;line-height:1.6;">
        <strong>Delivery-LP</strong>: BESS가 commit한 모든 물량을 RT에서 이행할 수 있어야 (s_DA = 0 강제). 컴플라이언스 친화 시나리오.<br>
        <strong>Pure-arb LP</strong>: DA에 무한정 commit 가능, 부족분만 RT_MCPC로 buyback. 수학적 상한선 (real-world에서는 ERCOT 컴플라이언스로 제약).<br>
        둘 다 결론은 같음: <strong>DA 우선 commit</strong>. 차이는 절대 commit 양 (delivery는 SoC capability 한도, arb는 100MW 풀 활용).
      </div>
    </div>
  </div>

  <div class="panel">
    <div class="panel-header"><span class="panel-title">전략 비교 · 100 MW capacity per product, 60일 ($)</span></div>
    <div class="panel-body" style="padding:0;">
      <table>
        <thead><tr>
          <th>Product</th>
          <th class="num">Always-DAM</th>
          <th class="num">Always-RT</th>
          <th class="num">Optimal (Switch)</th>
          <th class="num">DAM %</th>
          <th class="num">RT %</th>
        </tr></thead>
        <tbody>{q2_strat_rows}</tbody>
      </table>
    </div>
  </div>

  <div class="panel">
    <div class="panel-header"><span class="panel-title">HE × Product · DAM이 우세한 시간 비율 (heatmap)</span></div>
    <div class="panel-body">
      <div id="damWinHeatmap" class="heatmap-grid"></div>
      <div style="font-size:10px;color:var(--text-muted);padding:8px 0 0;">
        진한 녹색일수록 DAM commit이 거의 항상 우세. <strong>REGDN HE 7-8 + 18-20</strong>이 짙은 회색~빨강 (RT가 자주 이김 — solar ramp 시간대).
      </div>
    </div>
  </div>

  <!-- ==================== Q3: RT > DAM characterization ==================== -->
  <div class="section-title">
    Q3 · RT &gt; DAM 시간대 특성 + D-1 예측 가능성
    <small>"언제 DAM commit을 보류하고 RT 잔류해야 하는가?"</small>
  </div>

  <div class="callout blue">
    <strong>요약:</strong> Wind forecast bust가 <strong>NSPIN/ECRS/RRS/REGUP</strong>의 RT 우세 시간대 driver
    (Pearson corr -0.13~-0.22 · spike 시 wind err 평균 -2~-3 GW).
    <strong>REGDN은 다른 구조</strong> — wind err corr 거의 0 — solar ramp (HE 7-8, 18-20) 시간대에 패턴화.
    이는 D-1 morning에 일정 부분 사전 인지 가능 (날씨 예보 + 시간대 패턴).
  </div>

  <div class="main-grid">
    <div class="panel">
      <div class="panel-header"><span class="panel-title">RT &gt; DAM Frequency &amp; Driver per Product</span></div>
      <div class="panel-body" style="padding:0;">
        <table>
          <thead><tr>
            <th>Product</th>
            <th class="num">RT≥DAM hrs</th>
            <th class="num">% of 1440h</th>
            <th class="num">Spike (&gt;$5)</th>
            <th class="num">Avg RT-DAM gap</th>
            <th class="num">Wind err (spike)</th>
          </tr></thead>
          <tbody>{q3_summary_rows}</tbody>
        </table>
      </div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">상관계수 (RT-DAM gap vs Features)</span></div>
      <div class="panel-body chart-wrap"><canvas id="corrChart"></canvas></div>
    </div>
  </div>

  <div class="panel">
    <div class="panel-header"><span class="panel-title">Top 12 RT &gt;&gt; DAM Spike Hours (5종 중 max spread)</span></div>
    <div class="panel-body" style="padding:0;">
      <table>
        <thead><tr>
          <th>Date</th>
          <th class="num">HE</th>
          <th>Product</th>
          <th class="num">RT-DAM gap</th>
          <th class="num">DA LMP</th>
          <th class="num">RT LMP</th>
          <th class="num">Load FC Err</th>
          <th class="num">Wind FC Err</th>
        </tr></thead>
        <tbody>{q3_spike_rows}</tbody>
      </table>
    </div>
  </div>

  <!-- ==================== Daily P&L (Energy + AS) ==================== -->
  <div class="section-title">
    참고 · 일별 P&amp;L (Energy + AS 통합 LP vs GKS Actual)
    <small>SoC-aware LP, Storm Fern 제외</small>
  </div>

  <div class="callout">
    <strong>참고:</strong> 통합 LP optimal {fmt_money(D['expost_total'])} / GKS actual {fmt_money(D['actual_total'])} ({D['gks_pct']*100:.1f}%).
    Energy 부분 capture {D['actual_energy']/D['expost_energy']*100:.1f}% — 진짜 개선 영역.
    AS 부분은 LP 대비 over-perform (위 Q1 참조).
  </div>

  <div class="panel">
    <div class="panel-header"><span class="panel-title">Daily P&amp;L Trajectory · LP vs Actual</span></div>
    <div class="panel-body chart-wrap tall"><canvas id="dailyPnlChart"></canvas></div>
  </div>

  <div class="panel">
    <div class="panel-header"><span class="panel-title">Worst Gap Days · GKS가 LP 대비 가장 많이 놓친 날 (Top 10)</span></div>
    <div class="panel-body" style="padding:0;">
      <table>
        <thead><tr>
          <th>Date</th>
          <th class="num">LP Optimal</th>
          <th class="num">GKS Actual</th>
          <th class="num">Gap</th>
        </tr></thead>
        <tbody>{worst_rows}</tbody>
      </table>
    </div>
  </div>

  <!-- ==================== Recommendations ==================== -->
  <div class="section-title">전략 시사점 (Strategic Recommendations)</div>

  <div class="panel">
    <div class="panel-body">
      <ul class="findings">
        <li class="good"><strong>Q2 답: AS는 DAM에 commit이 default 정답</strong> — Always-DAM이 ex-post optimal의 89.4% capture. 매번 정확히 DAM/RT 선택해도 추가 +11% — 의사결정 비용 대비 ROI 낮음. GKS의 NSPIN-DAM 전략은 이 측면에서 합리적.</li>
        <li class="warn"><strong>Q2 예외 — REGDN의 HE 7-8 + 18-20 (solar ramp)</strong>은 RT 우세 빈도 높음 (DAM win share 0.12-0.40). Solar 예보가 높은 날에는 해당 시간대 REGDN을 RT에 잔류 검토. 단 REGDN 자체가 가격 낮아 ($1.15/MW) 절대값 기여는 작음.</li>
        <li><strong>Q3 답: RT &gt; DAM의 driver는 wind bust</strong> (NSPIN/ECRS/RRS corr -0.13~-0.22). D-1 08:30 CT wind STWPF&lt;5 GW 또는 Net-load FC&gt;50 GW 시간대는 (i) AS DAM commit 신중 (ii) 일부 RT 잔류 — 단 표본 적어 정밀 예측 어려움.</li>
        <li class="good"><strong>NSpin "수수께끼" 해소 (v3 정정)</strong> — 사용자 정정에 따라 DAM AS commit은 ERCOT가 SoC telemetry 검사 안 함 (RT only 적용). LP에서 SoC reservation 제약 제거 후 NSpin LP optimal $20K → $103K로 정상화. GKS NSpin $156K는 LP 대비 50% 추가 — energy 기회 비용 감수하고 NSpin commit 우선 전략. RT AS는 별도 모델링 필요 (현재 미구현).</li>
        <li class="good"><strong>핵심 개선 영역은 Energy round-trip</strong> — Q2 분석은 AS-only지만, 통합 LP에서 Energy gap이 전체 gap의 대부분 ({(D['expost_energy']-D['actual_energy'])/D['gap_total']*100:.0f}%). GKS DA Energy +$596K / RT Energy −$327K → DA 과다 commit 후 RT 손실 패턴. 우선순위: (i) DA commit volume 점검 (ii) HSL 변동 모니터링 (iii) RT dispatch 응답성.</li>
        <li><strong>다음 단계 데이터 needs</strong>: (a) ERCOT NSpin actual deployment 빈도 (post-RTC), (b) 60-day SCED disclosure로 GKS RT base point 추적, (c) ORDC adder 5-min — 실제로 NSpin SoC가 strict하게 적용되는지 검증.</li>
      </ul>
    </div>
  </div>

  <div class="panel">
    <div class="panel-header"><span class="panel-title">Methodology Notes</span></div>
    <div class="panel-body" style="font-size:11px;color:var(--text-secondary);line-height:1.7;">
      <strong>데이터:</strong> Yes Energy DataSignals (DA/RT LMP @ GKS_BESS_RN, HB_HOUSTON, hourly forecasts),
      ERCOT Public API NP4-188-CD (DAM AS MCPC) + <strong>NP6-331-CD (RT 15-min AS MCPC)</strong>,
      Tenaska PTP (GKS hourly Energy &amp; AS detail).
      <br><strong>RT AS aggregation:</strong> 15-min settlement intervals → hourly mean (4 intervals).
      <br><strong>SoC reservation (v3 정정 2026-05-07):</strong> DAM AS는 SoC 검사 없음 → LP에서 제약 미적용. RT AS는 telemetry 기반 award 제한 (4hr NSpin / 0.5hr RRS / 1hr ECRS / 1hr Reg) — 별도 모델링 필요, 본 LP에서는 미구현.
      <br><strong>제외:</strong> Winter Storm Fern 5일 (2026-01-24~28) tail-event 영향 분리.
      <br><strong>한계:</strong> ex-post perfect foresight LP는 상한선 — 실전 30-50% capture가 typical;
      AS deployment income 비계산; NSpin SoC 4× 가정의 실제 적용 여부 미검증;
      60-day SCED disclosure / ORDC adder 미포함.
    </div>
  </div>

</div>

<script>
const D = {charts_json};
const c_up='#089981', c_down='#f23645', c_blue='#2962ff', c_amber='#ff9800', c_purple='#9c27b0';
Chart.defaults.color='#5d606b'; Chart.defaults.borderColor='#eceff3';
Chart.defaults.font.family="'Inter',sans-serif"; Chart.defaults.font.size=11;

function heatColor(v) {{
  v = Math.max(0, Math.min(1, v));
  return `rgba(8, 153, 129, ${{0.10 + v * 0.75}})`;
}}
function divergingColor(v) {{
  // v in [0,1]: 0=red, 0.5=neutral, 1=green
  if (v >= 0.5) return `rgba(8, 153, 129, ${{0.10 + (v-0.5) * 1.5}})`;
  return `rgba(242, 54, 69, ${{0.10 + (0.5-v) * 1.5}})`;
}}
const products = ['REGUP','REGDN','RRS','ECRS','NSPIN'];

// ============= DAM MCPC heatmap =============
function buildHeatmap(containerId, dataObj, products, colorFn, valueFmt) {{
  const c = document.getElementById(containerId);
  c.innerHTML = '';
  const corner = document.createElement('div');
  corner.className='heatmap-axis row-label'; corner.textContent='';
  c.appendChild(corner);
  for (let h=1; h<=24; h++) {{
    const lbl = document.createElement('div');
    lbl.className='heatmap-axis'; lbl.textContent=h;
    c.appendChild(lbl);
  }}
  products.forEach(p => {{
    const arr = dataObj[p];
    const allVals = products.flatMap(pp => dataObj[pp]);
    const maxv = Math.max(...allVals) || 1;
    const lbl = document.createElement('div');
    lbl.className='heatmap-axis row-label'; lbl.textContent=p;
    c.appendChild(lbl);
    arr.forEach((v, i) => {{
      const cell = document.createElement('div');
      cell.className='heatmap-cell';
      cell.style.background = colorFn(v / maxv, v);
      cell.textContent = valueFmt(v);
      cell.title = `${{p}} HE${{i+1}}: ${{v}}`;
      c.appendChild(cell);
    }});
  }});
}}

buildHeatmap('damHeatmap', D.mean_mcpc_dam,
  products,
  (norm, v) => heatColor(norm),
  v => v >= 10 ? Math.round(v) : v.toFixed(1));

// DAM win share (0=RT wins, 1=DAM wins) — diverging color
const dwsObj = {{}};
products.forEach(p => dwsObj[p] = D.dam_win_share_by_he[p]);
buildHeatmap('damWinHeatmap', dwsObj,
  products,
  (norm, v) => divergingColor(v),  // use raw v (already in [0,1])
  v => Math.round(v*100));

// ============= LP AS Allocation (stacked bar) =============
new Chart(document.getElementById('lpAsAlloc'), {{
  type:'bar',
  data:{{
    labels:D.lp_as_alloc.he,
    datasets:[
      {{label:'NSPIN', data:D.lp_as_alloc.NSPIN, backgroundColor:c_up, borderWidth:0}},
      {{label:'REGDN', data:D.lp_as_alloc.REGDN, backgroundColor:c_blue, borderWidth:0}},
      {{label:'REGUP', data:D.lp_as_alloc.REGUP, backgroundColor:c_amber, borderWidth:0}},
      {{label:'ECRS',  data:D.lp_as_alloc.ECRS,  backgroundColor:c_purple, borderWidth:0}},
      {{label:'RRS',   data:D.lp_as_alloc.RRS,   backgroundColor:c_down, borderWidth:0}},
    ]
  }},
  options:{{ responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{position:'bottom', labels:{{usePointStyle:true, font:{{size:10}}}} }} }},
    scales:{{
      x:{{ stacked:true, grid:{{display:false}}, title:{{display:true, text:'HE', font:{{size:10}}}} }},
      y:{{ stacked:true, grid:{{color:'#eceff3'}}, title:{{display:true, text:'Mean MW', font:{{size:10}}}} }}
    }}
  }}
}});

// ============= Correlation chart =============
const corrLabels = ['load_fc_err','wind_fc_err','RTLMP_GKS_BESS_RN','DALMP_GKS_BESS_RN','RTLOAD','WIND_RTI'];
new Chart(document.getElementById('corrChart'), {{
  type:'bar',
  data:{{
    labels:corrLabels,
    datasets: products.map((p, i) => ({{
      label:p,
      data:corrLabels.map(f => D.corr_table[p][f]),
      backgroundColor:[c_up,c_blue,c_amber,c_purple,c_down][i],
      borderWidth:0,
    }}))
  }},
  options:{{ responsive:true, maintainAspectRatio:false, indexAxis:'y',
    plugins:{{ legend:{{position:'top', labels:{{usePointStyle:true, font:{{size:9}}}} }} }},
    scales:{{
      x:{{ min:-0.3, max:0.3, grid:{{color:'#eceff3'}},
           title:{{display:true, text:'Pearson corr', font:{{size:10}}}} }},
      y:{{ grid:{{display:false}}, ticks:{{font:{{size:9}}}} }}
    }}
  }}
}});

// ============= Daily P&L =============
new Chart(document.getElementById('dailyPnlChart'), {{
  type:'line',
  data:{{
    labels:D.daily_pnl.date,
    datasets:[
      {{label:'LP Optimal', data:D.daily_pnl.lp_total, borderColor:c_up,
        backgroundColor:'rgba(8,153,129,0.08)', borderWidth:1.5, fill:false,
        tension:0.2, pointRadius:0}},
      {{label:'GKS Actual', data:D.daily_pnl.actual_total, borderColor:c_down,
        backgroundColor:'rgba(242,54,69,0.08)', borderWidth:1.5, fill:false,
        tension:0.2, pointRadius:0}},
    ]
  }},
  options:{{ responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{position:'top', labels:{{usePointStyle:true, font:{{size:10}}}} }} }},
    scales:{{
      x:{{ grid:{{display:false}}, ticks:{{maxTicksLimit:12, font:{{size:9}}}} }},
      y:{{ grid:{{color:'#eceff3'}}, title:{{display:true, text:'$ per day', font:{{size:10}}}},
           ticks:{{callback:v=>'$'+(v/1000).toFixed(0)+'K'}} }}
    }},
    interaction:{{ mode:'index', intersect:false }}
  }}
}});
</script>
</body>
</html>
"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(HTML, encoding="utf-8")
print(f"Saved -> {OUT}")
print(f"  size: {OUT.stat().st_size:,} bytes")
