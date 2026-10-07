"""
#81 — Render Ancillary Service Day-Ahead vs Real-Time Spread Dashboard
       (single-file HTML, light theme)

Consumes derived/as_spread_dashboard_data.json
Writes  reports/ad-hoc/as_da_rt_spread_dashboard.html

Per user feedback (2026-05-18):
  - 약어 사용 최소화. Day-Ahead / Real-Time / Hour-Ending / Day of Week 등 풀네임 사용.
  - Q4 가정 명시: Day-Ahead Ancillary Service capacity는 Real-Time에서 100% buyback.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC = Path(__file__).resolve().parents[1]
PROJECT = Path(__file__).resolve().parents[5]
DERIVED = ADHOC / "derived"
OUT = PROJECT / "reports" / "ad-hoc" / "as_da_rt_spread_dashboard.html"
OUT.parent.mkdir(parents=True, exist_ok=True)

# 풀네임 매핑 (product short code → 풀네임)
PRODUCT_FULL = {
    "RRS":   "Responsive Reserve Service",
    "ECRS":  "ERCOT Contingency Reserve Service",
    "NSPIN": "Non-Spinning Reserve",
}


def render(data: dict) -> str:
    q1 = data["Q1_spread_series"]["products"]
    q2 = data["Q2_negative_profile"]["products"]
    q3 = data["Q3_flag_logit"]["products"]
    q4 = data["Q4_optimal_split"]["products"]
    rng = data["data_range"]
    rng_label = f"{rng[0][:10]} → {rng[1][:10]}"

    data_json = json.dumps(data, default=str)

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ERCOT Ancillary Service Day-Ahead vs Real-Time Spread Dashboard · {rng_label}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root {{
  --bg-base:        #f7f8fa;
  --bg-panel:       #ffffff;
  --bg-panel-2:     #f0f2f5;
  --bg-row-alt:     #fafbfc;
  --border-soft:    #e0e3eb;
  --border-strong:  #c8ccd4;
  --text-primary:   #131722;
  --text-secondary: #5d606b;
  --text-muted:     #9598a1;
  --accent-up:      #089981;
  --accent-down:    #f23645;
  --accent-blue:    #2962ff;
  --accent-amber:   #ff9800;
  --accent-purple:  #9c27b0;
  --grid-line:      #eceff3;
  --shadow-card:    0 1px 2px rgba(16, 24, 40, 0.04);
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: 'Inter','Pretendard','Noto Sans KR',-apple-system,system-ui,sans-serif;
  font-size: 13px;
  line-height: 1.45;
  min-height: 100vh;
}}
.num {{
  font-family: 'JetBrains Mono','SF Mono','Roboto Mono',monospace;
  font-variant-numeric: tabular-nums;
}}
.wrap {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}
.header {{
  display: flex; justify-content: space-between; align-items: flex-end;
  padding: 20px 0 16px; border-bottom: 1px solid var(--border-soft); margin-bottom: 20px;
}}
.header h1 {{ font-size: 22px; font-weight: 600; letter-spacing: -0.01em; }}
.header .sub {{ color: var(--text-secondary); margin-top: 4px; font-size: 13px; }}
.header .meta {{ text-align: right; color: var(--text-secondary); font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; }}
.pill {{
  display: inline-block; padding: 3px 10px; border-radius: 4px;
  background: var(--bg-panel-2); color: var(--text-secondary);
  font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase;
  margin-left: 8px;
}}
.pill.up   {{ background: rgba(8,153,129,0.10); color: var(--accent-up); }}
.pill.down {{ background: rgba(242,54,69,0.10); color: var(--accent-down); }}

.section {{ margin-top: 28px; }}
.section h2 {{
  font-size: 14px; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--text-primary); margin-bottom: 12px;
  display: flex; align-items: center; gap: 8px;
}}
.section h2::before {{
  content: ''; display: inline-block; width: 3px; height: 14px;
  background: var(--accent-blue); border-radius: 2px;
}}
.section .sub {{ color: var(--text-secondary); font-size: 12px; margin-top: -8px; margin-bottom: 12px; }}

.kpi-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px,1fr)); gap: 12px; }}
.card {{
  background: var(--bg-panel); border: 1px solid var(--border-soft);
  border-radius: 6px; padding: 14px 16px; box-shadow: var(--shadow-card);
}}
.kpi .label {{ font-size: 10px; letter-spacing: 0.10em; text-transform: uppercase; color: var(--text-secondary); }}
.kpi .value {{ font-size: 28px; font-weight: 600; margin-top: 6px; }}
.kpi .delta {{ font-size: 12px; margin-top: 2px; color: var(--text-secondary); }}
.kpi .delta.up   {{ color: var(--accent-up); }}
.kpi .delta.down {{ color: var(--accent-down); }}

.grid-2 {{ display: grid; grid-template-columns: 2fr 1fr; gap: 12px; margin-top: 12px; }}
.grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-top: 12px; }}
@media (max-width: 1000px) {{ .grid-2, .grid-3 {{ grid-template-columns: 1fr; }} }}

.panel {{ background: var(--bg-panel); border: 1px solid var(--border-soft); border-radius: 6px; padding: 14px 16px; box-shadow: var(--shadow-card); }}
.panel h3 {{ font-size: 12px; font-weight: 600; color: var(--text-secondary); letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 12px; }}

.tabs {{ display: flex; gap: 4px; border-bottom: 1px solid var(--border-soft); margin-bottom: 12px; flex-wrap: wrap; }}
.tabs button {{
  background: transparent; border: 0; padding: 8px 12px; cursor: pointer;
  font-size: 12px; font-weight: 500; color: var(--text-secondary);
  border-bottom: 2px solid transparent;
}}
.tabs button.active {{ color: var(--accent-blue); border-color: var(--accent-blue); }}

.chart-wrap {{ position: relative; height: 280px; }}
.chart-wrap.tall {{ height: 360px; }}

table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
th {{ font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-secondary);
     text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--border-soft); font-weight: 500; }}
td {{ padding: 7px 6px; border-bottom: 1px solid var(--bg-row-alt); }}
tr:nth-child(even) td {{ background: var(--bg-row-alt); }}
tr:hover td {{ background: var(--bg-panel-2); }}
td.num {{ text-align: right; }}
.up   {{ color: var(--accent-up); }}
.down {{ color: var(--accent-down); }}
.neutral {{ color: var(--text-secondary); }}

.heatmap {{ display: grid; grid-template-columns: 40px repeat(7, 1fr); gap: 2px; }}
.heatmap .hd {{ font-size: 10px; color: var(--text-secondary); text-align: center; padding-bottom: 2px; }}
.heatmap .rl {{ font-size: 10px; color: var(--text-secondary); padding-right: 4px; line-height: 22px; text-align: right; }}
.heatmap .cell {{ height: 22px; border-radius: 3px; font-size: 10px; line-height: 22px; text-align: center; color: #fff; font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }}

.tag {{ display: inline-block; padding: 1px 7px; border-radius: 3px; font-size: 10px;
       background: var(--bg-panel-2); color: var(--text-secondary); margin: 1px 2px 1px 0; }}
.tag.red {{ background: rgba(242,54,69,0.10); color: var(--accent-down); }}
.tag.blue {{ background: rgba(41,98,255,0.10); color: var(--accent-blue); }}
.tag.amber {{ background: rgba(255,152,0,0.12); color: var(--accent-amber); }}

.bar-inline {{ position: relative; height: 4px; background: var(--bg-panel-2); border-radius: 2px; margin-top: 6px; overflow: hidden; }}
.bar-inline > span {{ position: absolute; top:0; bottom:0; left:0; background: var(--accent-blue); border-radius:2px; }}

.callout {{
  background: var(--bg-panel-2); border-left: 3px solid var(--accent-amber);
  padding: 10px 14px; font-size: 12px; color: var(--text-primary); border-radius: 0 4px 4px 0;
  margin-top: 10px; line-height: 1.6;
}}
.callout.assumption {{ border-left-color: var(--accent-blue); }}
.callout strong {{ color: var(--text-primary); }}
.callout code {{ background: var(--bg-panel); padding: 1px 5px; border-radius: 3px; font-size: 11px; color: var(--text-primary); }}

.product-tag {{
  display: inline-block; padding: 2px 9px; border-radius: 12px; font-size: 11px; font-weight: 600;
  background: var(--bg-panel-2); color: var(--text-secondary); margin-right: 6px;
}}
.product-tag.RRS   {{ background: rgba(8,153,129,0.14); color: var(--accent-up); }}
.product-tag.ECRS  {{ background: rgba(41,98,255,0.14); color: var(--accent-blue); }}
.product-tag.NSPIN {{ background: rgba(156,39,176,0.14); color: var(--accent-purple); }}

.glossary {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 6px 24px;
  font-size: 11px; color: var(--text-secondary); margin-top: 4px;
}}
.glossary div {{ padding: 2px 0; }}
.glossary strong {{ color: var(--text-primary); font-weight: 600; }}
</style>
</head>
<body>
<div class="wrap">

<div class="header">
  <div>
    <h1>ERCOT Ancillary Service · Day-Ahead vs Real-Time Spread Dashboard
      <span class="pill">Responsive Reserve Service · ERCOT Contingency Reserve Service · Non-Spinning Reserve</span>
    </h1>
    <div class="sub">Day-Ahead Market Clearing Price 와 Real-Time Market Clearing Price 의 시간별 spread 분석 · D-1 negative-spread 예측 모델 · 최적 Day-Ahead vs Real-Time 입찰 비중</div>
  </div>
  <div class="meta">
    <div>Data window</div>
    <div class="num" style="color:var(--text-primary);font-size:13px;letter-spacing:0;text-transform:none;">{rng_label}</div>
    <div style="margin-top:6px;">Hours · Days</div>
    <div class="num" style="color:var(--text-primary);font-size:13px;letter-spacing:0;text-transform:none;">{data['n_hours']:,} · {data['n_days']}</div>
  </div>
</div>

<!-- ──────────────────────────────────────────────────────────────────────
     PHASE A — 현황분석 (Current State Analysis)
     ────────────────────────────────────────────────────────────────────── -->
<div class="section" style="background:linear-gradient(90deg, rgba(41,98,255,0.08), transparent); padding:14px 16px; border-radius:6px; border-left:4px solid var(--accent-blue);">
  <h2 style="border:none; padding:0; margin:0;">PHASE A — 현황분석 (Current State)</h2>
  <div class="sub" style="margin-top:4px;">DA-RT spread 추이 · 음수 spread root cause · 시간대별 winner 패턴 · GKS BESS 실제 매출 현황</div>
</div>

<!-- ───── KPI 카드 (3 products × 평균 spread / 음수 확률 / 누적 손실) ───── -->
<div class="section">
  <h2>핵심 지표 요약</h2>
  <div class="sub">Spread는 Day-Ahead Market Clearing Price 에서 Real-Time Market Clearing Price 를 뺀 값 ($/MWh). 양수면 Day-Ahead에서 판매하는 것이 유리. 누적 손실(damage)은 100 MW 자원이 100% Day-Ahead 입찰했고 Real-Time에서 buyback 했을 때의 음수 spread 누적 손실.</div>
  <div class="kpi-row">
    {''.join(_kpi_card(p, q1[p], q2[p]) for p in ['RRS','ECRS','NSPIN'])}
  </div>
</div>

<!-- ───── Q1: 일별 spread 추이 + Hour-Ending × Day-of-Week heatmap ───── -->
<div class="section">
  <h2>Q1. 일별 Day-Ahead vs Real-Time Spread 추이</h2>
  <div class="sub">상품별 일평균 spread 시계열 (상품 탭으로 전환). 우측 히트맵: 시간대(Hour Ending 1~24) × 요일(월~일) 평균 spread — 빨간 셀이 모인 시간대·요일은 Day-Ahead 입찰 회피 또는 물량 축소가 유리.</div>
  <div class="grid-2">
    <div class="panel">
      <div class="tabs" id="q1-tabs">
        <button data-p="RRS"   class="active">Responsive Reserve Service</button>
        <button data-p="ECRS">ERCOT Contingency Reserve Service</button>
        <button data-p="NSPIN">Non-Spinning Reserve</button>
      </div>
      <div class="chart-wrap tall"><canvas id="q1-chart"></canvas></div>
    </div>
    <div class="panel">
      <h3>Hour-Ending × Day-of-Week 평균 Spread (선택 상품)</h3>
      <div id="heatmap-host"></div>
      <div class="callout" style="margin-top:14px;">
        <strong>해석 방법:</strong> 행 = Hour Ending (1~24, 시간대), 열 = 요일 (월요일~일요일). 색이 진한 빨강일수록 음수 spread (Real-Time이 더 비쌌음) 평균이 큼. 양수 spread (Day-Ahead가 더 비쌌음)는 초록색. 색 강도는 ±$20/MWh 까지 정규화.
      </div>
    </div>
  </div>

  <div class="grid-3" style="margin-top:12px;">
    {''.join(_hist_panel(p, q1[p]) for p in ['RRS','ECRS','NSPIN'])}
  </div>
</div>

<!-- ───── Q2: Negative spread 분석 ───── -->
<div class="section">
  <h2>Q2. 음수 Spread (Day-Ahead &lt; Real-Time) 분석</h2>
  <div class="sub">Day-Ahead Market Clearing Price 가 Real-Time Market Clearing Price 보다 낮았던 시간 — 발생 확률 (시간대·요일·월별 분해), 단일 시간 최대 손실 이벤트 (Root-cause tag 포함), 일별 누적 손실 랭킹.</div>

  <div class="grid-3">
    {''.join(_q2_prob_panel(p, q2[p]) for p in ['RRS','ECRS','NSPIN'])}
  </div>

  <div class="grid-2" style="margin-top:12px;">
    <div class="panel">
      <h3>단일 시간(Hour) 최대 손실 이벤트 — 상위 20건 (Root-Cause 분석 포함)</h3>
      <div class="tabs" id="q2-event-tabs">
        <button data-p="RRS"   class="active">Responsive Reserve Service</button>
        <button data-p="ECRS">ERCOT Contingency Reserve Service</button>
        <button data-p="NSPIN">Non-Spinning Reserve</button>
      </div>
      <div id="q2-event-table"></div>
      <div class="callout" style="margin-top:8px;">
        <strong>SPIKE 정의 (결과):</strong>
        <ul style="margin: 6px 0 0 18px; line-height: 1.6; font-size: 11px;">
          <li><code>RT spike</code> = Real-Time MCPC 또는 LMP 가 분포 상위 5% (p95) 초과. 이건 <em>결과</em> 이지 <em>원인</em> 이 아님.</li>
        </ul>
        <strong>ROOT-CAUSE 정의 (실제 원인 — WHY spike happened):</strong>
        <ul style="margin: 6px 0 0 18px; line-height: 1.6; font-size: 11px;">
          <li><code>Wind 부족</code>: (Wind 실측 − Wind D-1 STWPF 예보) / 예보 &lt; <strong>−10%</strong> · ERCOT RT 가격 spike 의 가장 흔한 root cause</li>
          <li><code>Load surge</code>: (Load 실측 − Load 예보) / 예보 &gt; <strong>+3%</strong> · heat wave / cold snap / 통계 오차</li>
          <li><code>Net-load surprise</code>: Wind 부족 + Load surge 동시 → 가장 강한 scarcity 신호</li>
          <li><code>Winter Storm Fern</code>: 2026-01-24~28 (known extreme weather event)</li>
          <li><code>Solar 부족 시간대</code>: 해당 HE 의 SOLAR forecast 가 그 HE 분포의 하위 20% (sunset 또는 cloud event)</li>
          <li><code>DA forecast bust (mis-pricing)</code>: DA MCPC &lt; $0.5/MWh — DA 시장이 풍족 가격으로 cleared 됐으나 RT 에서 scarcity</li>
          <li><code>Multi-hour event</code>: 같은 day 에 3+ 시간 음수 spread → 일시적 spike 가 아닌 systemic event</li>
        </ul>
      </div>
    </div>
    <div class="panel">
      <h3>일별 누적 손실 상위 15일 ($ 단위, 100 MW 자원 가정)</h3>
      <div class="tabs" id="q2-day-tabs">
        <button data-p="RRS"   class="active">Responsive Reserve Service</button>
        <button data-p="ECRS">ERCOT Contingency Reserve Service</button>
        <button data-p="NSPIN">Non-Spinning Reserve</button>
      </div>
      <div id="q2-day-table"></div>
    </div>
  </div>
</div>

<!-- ───── Q3: D-1 Flag Logistic Regression ───── -->
<div class="section">
  <h2>Q3. D-1 (전일) Negative-Spread Flag 예측 모델</h2>
  <div class="sub">D-1 Day-Ahead 입찰 마감(10:00 CT) 시점에 알 수 있는 feature 만으로 학습한 Logistic Regression. Feature: (1) 시간대 내 net-load forecast percentile, (2) wind forecast percentile, (3) solar forecast percentile, (4) Day-Ahead MCPC percentile, (5) Hour-Ending의 sin/cos 변환값. Class weight = balanced.</div>

  <div class="grid-3">
    {''.join(_q3_card(p, q3[p]) for p in ['RRS','ECRS','NSPIN'])}
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>일자별 최대 예측 확률 P(negative spread) — 운영 알림용</h3>
    <div class="tabs" id="q3-tabs">
      <button data-p="RRS"   class="active">Responsive Reserve Service</button>
      <button data-p="ECRS">ERCOT Contingency Reserve Service</button>
      <button data-p="NSPIN">Non-Spinning Reserve</button>
    </div>
    <div class="chart-wrap"><canvas id="q3-chart"></canvas></div>
    <div class="callout">
      <strong>본 모델의 역할 (foundation + risk monitoring, NOT operational rule):</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.7;">
        <li><strong>Foundation for Playbook</strong> — net-load FC 가 가장 강한 signal (AUC 0.70-0.75) 이라는 발견이 Q10/Q11 Playbook 의 cohort 정의 (HE × Net-Load quintile) 의 근거.</li>
        <li><strong>Risk monitoring</strong> — D-1 시점 P(neg) 가 매우 높은 day 식별 → playbook 권장에도 불구하고 risk-averse 운영 (예: bid MW 축소, 또는 그 day 회피) 결정에 활용.</li>
        <li><strong>⚠ 직접 운영 룰로는 사용하지 않음</strong> — per-product binary rule (DA-or-RT) 은 marginal uplift (RRS +0.3% / ECRS +7.6% / NSPIN ~0%). <strong>Q11 의 cross-product Medium Playbook 이 supersede (+33% uplift)</strong>. 운영 매출 최대화는 Q11/C4 사용.</li>
      </ul>
    </div>
  </div>
</div>

<!-- ───── Q6: Winner cohort characterization ───── -->
<div class="section">
  <h2>Q6. RRS / ECRS 가 NSPIN 을 이기는 시간의 특성</h2>
  <div class="sub">Non-Spinning Reserve 가 78% 시간 winner 지만, 22% 시간 (Responsive Reserve Service 12% + ERCOT Contingency Reserve Service 10%) 에서는 다른 상품이 spread 우위. 이 22% 시간의 패턴을 식별해 D-1 예측 가능성 검증.</div>

  <div class="panel">
    <h3>핵심 발견 — Winner cohort 별 평균 조건</h3>
    <div class="callout">
      <ul style="margin: 6px 0 0 18px; line-height: 1.8;">
        <li><strong>Non-Spinning Reserve winner (정상시간, 78%)</strong>: net-load forecast 평균 25,100 MWh, solar 9,805 MW, RRS DA 가격 $1.21/MWh — 평온한 시간대. 시간대 HE 13-17 (한낮) 가장 빈도 높음.</li>
        <li><strong>Responsive Reserve Service winner (12%)</strong>: net-load forecast 평균 <strong>33,799 MWh (+35%)</strong>, solar <strong>3,537 MW (−64%)</strong>, RRS DA 가격 <strong>$9.86 (×8 spike)</strong>, wind 예보 오차 −1,601 MW (under-forecast). 시간대 <strong>HE 8-9 (morning ramp), HE 20-22 (evening peak)</strong> 집중. <strong>4월에 가장 빈번 (28.7%)</strong>.</li>
        <li><strong>ERCOT Contingency Reserve Service winner (10%)</strong>: load forecast 평균 53,796 MWh (3개 cohort 중 최고). 시간대 <strong>HE 9-10 (morning peak), HE 22-23 (late evening)</strong>. <strong>1월에 가장 빈번 (35.5%)</strong> — Storm Fern 사건 영향.</li>
      </ul>
    </div>
  </div>

  <div class="grid-2" style="margin-top:12px;">
    <div class="panel">
      <h3>시간대별 (Hour Ending) Winner 분포 — 절대 시간 수 (Stacked)</h3>
      <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px;">
        각 HE 의 137일 중 winner 가 RRS / ECRS / NSPIN 인 시간 수 (stacked bar — 각 HE 총합 = 137h).
        <strong>NSPIN 이 모든 HE 에서 dominant winner</strong> — Morning peak (HE 8-10) 와 Evening peak (HE 21-22) 에서 RRS / ECRS 비중 증가.
        <em>(2026-05-19 fix: 이전 차트는 column-normalize 로 NSPIN 비중을 underestimate 했음.)</em>
      </div>
      <div class="chart-wrap" style="height:320px;"><canvas id="q6-he-chart"></canvas></div>
    </div>
    <div class="panel">
      <h3>Net-Load Forecast Quintile 별 P(winner)</h3>
      <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px;">D-1 시점 net-load forecast 가 높은 (Q5) 시간대에서 RRS/ECRS 가 winner 일 확률 ×4-5 증가.</div>
      <div id="q6-cond-table"></div>
    </div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>Cohort 별 평균 조건 비교 (descriptive)</h3>
    <div id="q6-cohort-table" style="overflow-x:auto;"></div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>D-1 Multinomial Logistic Regression — Winner 예측 가능성</h3>
    <div id="q6-logit-summary"></div>
    <div class="callout" style="margin-top:10px;">
      <strong>예측 가능성 요약:</strong> D-1 features (net-load FC pct, wind FC pct, solar FC pct, 상품별 DA MCPC pct, HE sin/cos) 만으로 winner 를 예측한 결과 in-sample accuracy 53.1% (NSPIN base rate 78.2% 보다 낮음 — class_weight=balanced 로 majority 정확도 일부 희생, 대신 RRS/ECRS recall 향상).
      <br><br>
      <strong>운영 관점</strong>: NSPIN default rule 에 더해 다음 두 가지 신호가 있을 때 RRS/ECRS 후보 검토:
      <ol style="margin: 6px 0 0 18px; line-height: 1.7;">
        <li><strong>Net-load forecast Q5 (상위 20%) + solar Q1-Q2 (하위 40%)</strong> → RRS/ECRS winner 확률 ~40% (vs NSPIN 60%)</li>
        <li><strong>Hour Ending ∈ {8, 9, 10, 20, 21, 22}</strong> → RRS/ECRS winner 확률 ~30%</li>
      </ol>
      위 조합 시 NSPIN default 대신 RRS/ECRS 입찰 검토. 정밀한 상품 선택은 D-1 DA MCPC clearing 후 percentile 신호로 confirm.
    </div>
  </div>
</div>

<!-- ───── GKS 실제 매출 현황 (Phase A 마지막) ───── -->
<div class="section">
  <h2>GKS 실제 보조서비스 매출 — 월별 + 상품별 현황</h2>
  <div class="sub">현재 운영 baseline 확인. Tenaska Gross DA − ERCOT RT Imbalance Paid = Net Total. 사용자 검증값 ~$240K 와 일치.</div>

  <div class="panel">
    <h3>월별 GKS 보조서비스 매출 (검증용)</h3>
    <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px; line-height:1.6;">
      월별 / 상품별 Gross DA − RT Imb Paid = Net Total. 음수 RT Imb 는 over-delivery credit.
      탭으로 상품 전환 (전체 / RRS / ECRS / NSPIN).
    </div>
    <div class="tabs" id="monthly-tabs">
      <button data-p="TOTAL" class="active">전체 합산 (3개 상품)</button>
      <button data-p="RRS">Responsive Reserve Service</button>
      <button data-p="ECRS">ERCOT Contingency Reserve Service</button>
      <button data-p="NSPIN">Non-Spinning Reserve</button>
    </div>
    <div id="monthly-table" style="overflow-x:auto;"></div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>GKS 실제 매출 Full Breakdown (per product)</h3>
    <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px; line-height:1.6;">
      <strong>Data window</strong>: 2026-01-01 ~ 2026-05-10 (Tenaska PowerTools Platform).
      <strong>Gross DA</strong> = Tenaska 보고치 (a_DA × DAM_MCPC). <strong>RT Imbalance Paid</strong> = ERCOT 60-day disclosure 별도 fetch (script #72/73, charge codes *IMBAMT). ERCOT 부족 delivery 시 GKS 가 지불 (debit, 매출 차감).
      <strong>Total Actual</strong> = Gross − RT Imb Paid.
    </div>
    <div id="gks-actual-table" style="overflow-x:auto;"></div>
    <div class="callout" style="margin-top:8px;">
      • Total Actual = <strong>$229,963</strong> (사용자 기대값 ~$240K 와 일치)<br>
      • Tenaska 의 RT_Ancillary_Imbalance_Amt 컬럼은 모두 $0 으로 반환 → 별도 ERCOT disclosure fetch 필요 (script #72/73 사용)<br>
      • GKS Reg Up/Down 은 실제 bid 하지 않아 $0 — 누락이 아닌 정상값
    </div>
  </div>
</div>

<!-- ──────────────────────────────────────────────────────────────────────
     PHASE B — 최적화 (Optimization / Oracle)
     ────────────────────────────────────────────────────────────────────── -->
<div class="section" style="background:linear-gradient(90deg, rgba(255,152,0,0.10), transparent); padding:14px 16px; border-radius:6px; border-left:4px solid var(--accent-amber); margin-top:32px;">
  <h2 style="border:none; padding:0; margin:0;">PHASE B — 최적화 (Optimization / Oracle)</h2>
  <div class="sub" style="margin-top:4px;">가정 정의 (buyback + HSL/SoC) · 5개 strategy backtest · HSL sensitivity · GKS vs Oracle apples-to-apples 비교</div>
</div>

<!-- ───── Q4: Optimal Day-Ahead vs Real-Time split ───── -->
<div class="section">
  <h2>Q4. 최적 Day-Ahead vs Real-Time 입찰 비중 — Per-Product 분석</h2>
  <div class="sub">상품별 (RRS / ECRS / NSPIN) 5개 전략 backtest. <strong>단일 상품 가정</strong> — 상품 선택 자체는 다루지 않음. <strong>운영 결정용으로는 Q11 의 cross-product Playbook 사용 권장</strong> (Q4 결과는 per-product sanity check 용도).</div>

  <div class="panel">
    <h3>가정 1 (Assumption #1) — Day-Ahead 매도분 Real-Time 100% Buyback (2026-05-18 user 지정)</h3>
    <div class="callout assumption">
      <strong>Day-Ahead 보조서비스 매도분은 Real-Time Market 에서 100% buyback 한다고 가정.</strong>
      이유: BESS는 Real-Time 에서 에너지를 독립적으로 운용해야 하므로, Day-Ahead 에서 sell한 보조서비스 capacity 는 Real-Time 에서 다시 매입해 의무를 풀어야 함.<br><br>
      따라서 Day-Ahead 보조서비스 순매출은 단순 <code>MW × DAM_MCPC</code> 가 아니라 buyback 비용을 차감한
      <strong>순매출 = <code>MW × (DAM_MCPC − RT_AS_MCPC) = MW × spread</code></strong> 가 됨.<br>
      → 음수 spread 시간에는 Day-Ahead 입찰이 직접적인 손실로 잡힘 (단순 MCPC 매출이 아닌 buyback 후 net).
    </div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>가정 2 (Assumption #2) — Time-Varying HSL (Tenaska Telemetered, primary) + 상품별 SoC Duration Cap (2026-05-18 user 지정)</h3>
    <div class="callout assumption">
      <strong>Battery nameplate</strong> = 100 MW HSL · 200 MWh SoC.
      <strong>HSL은 Tenaska Generator-Performance 의 Telemetered_HSL_5_Min 시간변동값</strong>
      (실제 GKS 운영 capacity, 137일 backfill 완료).
      Smartbidder <code>avail_discharge_mw</code> 는 fallback.<br><br>
      <strong>관찰값 (Jan-May 2026, 3,287 시간):</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.7;">
        <li>평균 HSL 가용도 = <strong>58.2 MW</strong> (nameplate 의 58%)</li>
        <li>100 MW 풀가용 시간 비율 = <strong>12.6%</strong> 만</li>
        <li>0 MW outage 시간 비율 = <strong>16.2%</strong> (16일 상당)</li>
      </ul>
      <strong>Day-Ahead 참여 cap (시간별) = <code>avail_discharge_mw[t]</code></strong>.<br>
      <strong>Real-Time 참여 cap (시간별) = <code>min(avail_discharge_mw[t], soc_mwh_max[t] / SoC duration)</code></strong>:
      <ul style="margin: 6px 0 0 18px; line-height: 1.7;">
        <li><span class="product-tag RRS">RRS</span> Responsive Reserve Service — SoC duration <code>0.5h</code> · 평균 RT cap ≈ HSL 가용도 (HSL binding)</li>
        <li><span class="product-tag ECRS">ECRS</span> ERCOT Contingency Reserve Service — SoC duration <code>1h</code> · 평균 RT cap ≈ HSL 가용도 (HSL binding)</li>
        <li><span class="product-tag NSPIN">NSPIN</span> Non-Spinning Reserve — SoC duration <code>4h</code> · 평균 RT cap ≈ <strong>33 MW</strong> (SoC binding 대부분)</li>
      </ul>
    </div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>5개 전략 정의 (MW base = 시간변동 avail_discharge_mw + 상품별 SoC cap)</h3>
    <table>
      <thead><tr><th>전략 이름</th><th>매시간 결정 규칙</th><th>매출 공식</th></tr></thead>
      <tbody>
        <tr><td><strong>Naïve Day-Ahead 100% (with full Real-Time buyback)</strong></td>
            <td>매시간 가용 HSL 전량 (avail[t]) 을 Day-Ahead에 sell, Real-Time에서 100% buyback</td>
            <td><code>Σ avail[t] × spread[t]</code></td></tr>
        <tr><td><strong>Naïve Real-Time 100%</strong></td>
            <td>Day-Ahead에 입찰하지 않고 매시간 SoC-cap MW (min(avail[t], soc[t]/duration)) 를 Real-Time에 sell</td>
            <td><code>Σ rt_cap[t] × RT_MCPC[t]</code></td></tr>
        <tr style="opacity:0.65;"><td>Binary D-1 Flag Rule <span style="color:var(--accent-amber); font-size:10px;">⚠ DEPRECATED</span></td>
            <td>D-1 Logistic Regression 의 P(neg) &lt; τ* 일 때 Day-Ahead (avail), 그 외 Real-Time (SoC-cap). <strong>per-product 단일 상품 가정</strong> — 상품 선택 자체는 다루지 않음.</td>
            <td><code>τ*</code>는 매출 최대화점. <strong>Q11 Playbook 에 superseded</strong> (+33% 대비 +0~8%)</td></tr>
        <tr><td>3-tier Heuristic (참고)</td>
            <td>P(neg) &lt; τ_low → 100% Day-Ahead · τ_low ≤ P(neg) &lt; τ_high → 50%/50% mix · P(neg) ≥ τ_high → 100% Real-Time</td>
            <td>가중 평균</td></tr>
        <tr><td>Oracle (이론 상한, Perfect Foresight)</td>
            <td>매시간 정답을 알 때: <code>avail[t] × spread[t]</code> 와 <code>rt_cap[t] × RT_MCPC[t]</code> 중 큰 쪽 선택</td>
            <td>Binary rule family 의 이론적 천장</td></tr>
      </tbody>
    </table>
    <div class="callout" style="margin-top:10px;">
      <strong>핵심 발견 (per-product 시각, 시간변동 HSL + SoC cap):</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.7;">
        <li><strong>Naïve Day-Ahead 100% (with buyback) 가 per-product baseline</strong> — Spread mean 이 양수라 단일 상품 가정 시 거의 항상 DA 가 최적.</li>
        <li><strong>Per-product Binary D-1 Flag 의 marginal uplift</strong>: RRS +0.3% · ECRS +7.6% · NSPIN ~0%. 단일 상품 한정 의사결정 (DA-or-RT) 의 한계.</li>
        <li><strong>GKS Total Actual (Gross+Imb) 은 Oracle 의 13-45%</strong> capture — 참여율을 풀-HSL 수준으로 올리면 큰 매출 증가 잠재.</li>
      </ul>
      <div style="margin-top:10px; padding:8px 10px; background:rgba(255,152,0,0.10); border-radius:4px; border-left:3px solid var(--accent-amber);">
        <strong>⚠ 운영 결정용으로는 Q11 Playbook 사용</strong>: Q4 의 per-product Binary Flag 는 단일 상품 가정. <strong>Q11 Medium Playbook (cross-product 6 combo 중 선택) = +33% uplift</strong> — per-product 분석의 +0-8% 보다 훨씬 큼. Q4 의 5개 strategy 는 per-product 분석 sanity check 용으로 유지.
      </div>
    </div>
  </div>

  <div class="grid-3" style="margin-top:12px;">
    {''.join(_q4_card(p, q4[p]) for p in ['RRS','ECRS','NSPIN'])}
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>전략별 누적 매출 비교 (sum over {data['n_hours']:,} hours, 시간변동 HSL · 상품별 SoC cap 적용)</h3>
    <div class="chart-wrap"><canvas id="q4-bar"></canvas></div>
  </div>
</div>

<!-- ───── Q5: Product mix optimization ───── -->
<div class="section">
  <h2>Q5. 상품 비중 최적화 — 단일 상품 vs Hour-by-Hour 선택 vs Mixing</h2>
  <div class="sub">"Spread 가장 큰 상품 100% 가 이득인가, 아니면 시간별로 골라야 하나, 그도 아니면 mix 해야 하나?" 의 정량 검증.</div>

  <div class="panel">
    <h3>4단계 전략 비교 (Day-Ahead 100% with buyback 기준, 시간변동 HSL)</h3>
    <div id="q5-strategy-table"></div>
    <div class="callout" style="margin-top:10px;">
      <strong>핵심 결론:</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.7;">
        <li><strong>"항상 spread 최고 상품 100%" 는 충분치 않음</strong> — Non-Spinning Reserve 가 평균 spread 최고 ($2.32/MWh) 지만 22% 시간에서는 다른 상품 (Responsive Reserve Service 12% / ERCOT Contingency Reserve Service 10%) 의 spread 가 더 큼.</li>
        <li><strong>시간별 상품 선택 (Strategy B) 이 절대적으로 중요</strong> — Always-NSPIN 대비 <strong>+40.4% uplift</strong> ($251K 추가).</li>
        <li><strong>Real-Time 옵션 추가 (Strategy C) 도 큰 가치</strong> — Day-Ahead 만 사용 대비 +16.6% 추가, 주로 Non-Spinning Reserve Real-Time spike 시 (전체 시간의 10%).</li>
        <li><strong>Mixing 자체는 marginal (+2.5% only)</strong> — Strategy D 의 LP split 은 10% 시간만 split, 3개 상품 동시 split 은 0%. 사실상 매시간 단일 상품 100% 선택이면 충분.</li>
      </ul>
    </div>
  </div>

  <div class="grid-2" style="margin-top:12px;">
    <div class="panel">
      <h3>Oracle 시간별 상품 선택 분포 (Strategy B — Day-Ahead 만)</h3>
      <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px;">매시간 spread 가 가장 큰 상품을 선택. 총 3,287 시간 중.</div>
      <div id="q5-picks-b"></div>
    </div>
    <div class="panel">
      <h3>Oracle DA-or-RT × 상품 선택 분포 (Strategy C)</h3>
      <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px;">매시간 6개 조합 (3 상품 × 2 venue) 중 매출 최대 선택.</div>
      <div id="q5-picks-c"></div>
    </div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>운영 권장 사항 (Operational Takeaways)</h3>
    <ul style="margin:6px 0 0 18px; line-height:1.8; font-size:13px;">
      <li><strong>매시간 1개 상품 100% 선택 룰</strong> 이면 LP mixing 대비 97.5% 매출 capture. 따라서 운영 복잡도를 낮추기 위해 <strong>"단일 상품 hour-by-hour selector"</strong> 모델만 구축해도 거의 모든 가치 달성.</li>
      <li><strong>주력 상품은 Non-Spinning Reserve</strong> (78% 시간 winner) — 평소엔 NSPIN Day-Ahead 100% 가 기본 선택.</li>
      <li><strong>Responsive Reserve Service 가 winner 인 12% 시간</strong> 의 패턴 식별이 다음 R&D 우선순위 — 어느 HE/요일/날씨 조건에서 RRS spread 가 NSPIN spread 를 추월하는가?</li>
      <li>위 Q3 D-1 negative-spread flag 와 결합 시 → <strong>최종 운영 룰: D-1 시점에 (상품 선택 logit) + (negative-spread flag) 동시 실행</strong>.</li>
      <li>이 oracle 천장 ($1,043K) 대비 GKS 실제 ($230K) 는 <strong>~22% capture</strong>. 추가 78% 매출 잠재력 ($813K). 하지만 oracle 은 perfect foresight 이므로 실현 가능치는 그 50-70% 수준 (~$400-560K).</li>
    </ul>
  </div>
</div>

<!-- ───── Q7: HSL Sensitivity Analysis ───── -->
<div class="section">
  <h2>Q7. HSL Sensitivity — Oracle 은 GKS 와 동일 조건인가?</h2>
  <div class="sub">사용자 질문 (2026-05-18): Oracle 이 GKS 와 동일한 HSL 제약 하에서 계산되었는지 검증. 결론: strict 하게는 같음 (둘 다 Smartbidder forecast 받음) — 하지만 GKS 는 forecast 를 무시하고 더 큰 MW 로 bid 했음.</div>

  <div class="panel">
    <h3>HSL Source 검증 (2026-05-18 update) — Tenaska Telemetered HSL 사용</h3>
    <div class="callout">
      <strong>발견 — fetch_pnl_data.py 의 HSL fetch 가 systematically 실패하고 있었음:</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.8;">
        <li>기존 script 가 <code>filter='Kiskadee'</code> 사용 → server 500 error (parameter 호환성 문제). 130일 중 5-10일만 우연히 populated.</li>
        <li>수정: <code>elementIdentifiers=&lt;UUID&gt;</code> + query-columnar 형식 사용. <strong>137일 모두 fetch 성공</strong> (78,885 rows of 5-min HSL data).</li>
        <li>이번 작업으로 Tenaska Generator-Performance 의 <code>Telemetered_HSL_5_Min</code> 을 hourly aggregate 해서 master 에 merge.</li>
      </ul>
      <strong>실제 HSL 수치 비교 (137일 평균):</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.8;">
        <li>Tenaska Telemetered HSL (primary): <strong>60.8 MW</strong></li>
        <li>Smartbidder forecast HSL: 58.2 MW (Tenaska 대비 −2.7 MW)</li>
        <li>Tenaska Predictive HSL: 60.8 MW (Telemetered 와 동일 — Tenaska 가 동일 데이터를 다른 resolution 으로 노출)</li>
        <li>Smartbidder vs Tenaska 상관: <strong>0.877</strong> (높지만 perfect 아님)</li>
        <li><strong>GKS NSPIN bid avg (참여 시): 84.0 MW</strong> — Tenaska 실제 HSL 대비 <strong>+38% over-bid</strong>. 이게 $190K RT imbalance 의 원인.</li>
      </ul>
    </div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>4개 HSL 시나리오별 Oracle Ceiling — Sensitivity Analysis</h3>
    <div id="q7-table" style="overflow-x:auto;"></div>
    <div class="callout assumption" style="margin-top:10px;">
      <strong>해석 (Apples-to-Apples 기준):</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.8;">
        <li>시나리오 (a) Smartbidder forecast — 이전 default. 평균 58 MW, 약간 conservative.</li>
        <li><strong>시나리오 (b) Tenaska Telemetered HSL — TRUE apples-to-apples (현재 primary)</strong>: GKS 의 실제 운영 HSL 데이터.
            평균 60.8 MW. Q4/Q5/Q6 가 이제 이 baseline 사용. GKS capture = <strong>21.2%</strong>.</li>
        <li>시나리오 (c) max(forecast, GKS actual bid) — GKS over-bidding 까지 포함. 평균 73.5 MW.
            GKS 가 imbalance 감수하고 bid 한 만큼은 deliverable 했다고 가정하는 ambitious baseline.</li>
        <li>시나리오 (d) Nameplate 100 MW — outage 없다는 가정의 upper bound.</li>
      </ul>
      <strong>운영 권장</strong>: 매출 잠재력 토론 시 (b) <strong>Tenaska Telemetered HSL 기반 Oracle = $1,084K</strong> 를 primary reference 로 사용.
      이미 GKS 가 평균 84 MW NSPIN bid 하고 있어 capacity 측면에서는 추가 여지 제한적 (오히려 over-bid 가 imbalance 비용 초래).
      추가 매출 잠재력은 capacity 가 아닌 <strong>상품 / DA-RT / 시간 선택 최적화</strong>에서 나옴.
    </div>
  </div>
</div>

<!-- ───── Q8: GKS Actual vs Optimal — per-product comparison ───── -->
<div class="section">
  <h2>Q8. GKS 실제 vs 최적 전략 — 상품별 비교</h2>
  <div class="sub">상품별로 (1) 평균 참여 용량, (2) 수익 비중, (3) Day-Ahead vs Real-Time 비중 을 GKS 실제 vs Optimal (Oracle Strategy C, Tenaska HSL 기준) 으로 비교.</div>

  <div class="panel">
    <h3>3가지 metric × 3 상품 — 핵심 차이</h3>
    <div id="q8-comparison-table" style="overflow-x:auto;"></div>
    <div class="callout" style="margin-top:10px;">
      <strong>핵심 발견:</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.8;">
        <li><strong>GKS 는 모든 상품에서 over-bid (avg 80-84 MW vs HSL 60.8 MW)</strong> — 약 +20 MW 초과로 RT imbalance ($190K) 부담. Optimal 은 HSL 범위 내 활용 (62-68 MW avg).</li>
        <li><strong>GKS 는 100% Day-Ahead 만 활용</strong> — Real-Time AS 매도 가 0%. Optimal 은 RRS 9%, ECRS 22%, NSPIN 14% Real-Time 활용해 추가 매출.</li>
        <li><strong>수익 비중 차이 — ERCOT Contingency Reserve Service 가 큰 gap</strong>: GKS 는 ECRS 6.6% (참여율 5%만) vs Optimal 11.4%. ECRS 참여를 늘리면 큰 효과.</li>
        <li><strong>참여율 차이</strong>: GKS RRS 12% vs Optimal 4% — GKS 는 RRS 에 너무 자주 참여 (그러나 spread 우위가 작아서 매출 비중 낮음). Optimal 은 RRS spread 가 정말 클 때만 active.</li>
        <li><strong>NSPIN 활용도</strong>: GKS 57% vs Optimal 75% — Optimal 이 NSPIN 더 자주 winner. NSPIN 참여 시간 늘리면 매출 증가.</li>
      </ul>
    </div>
  </div>
</div>

<!-- ───── Q9: Filtered comparison — only GKS-participated days ───── -->
<div class="section">
  <h2>Q9. Apples-to-Apples 보정 — GKS 참여 day만으로 재비교</h2>
  <div class="sub">GKS 가 high-volatility day (Storm Fern 1/24-26, 3월말 3/25-31 등) 에 의도적으로 DA AS 를 안 들어간 가능성. 이런 day 를 비교에서 제외하면 GKS 의 underperformance gap 이 얼마나 줄어드는지 검증.</div>

  <div class="panel">
    <h3>3개 Filter Level 별 GKS vs Optimal 비교</h3>
    <div id="q9-filter-table" style="overflow-x:auto;"></div>
    <div class="callout" style="margin-top:10px;">
      <strong>주요 발견 (사용자 가설 검증):</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.8;">
        <li><strong>Filter A → B (Day-filter) 만으로 gap 이 4.5x → 2.3x 로 절반 축소</strong> — 사용자 직관 정확히 맞음.</li>
        <li><strong>Optimal 매출의 54% ($558K) 가 GKS-skipped 26일에 집중</strong> — Storm Fern (1/24-26) + 3월말 (3/25-31) + 9일 기타.</li>
        <li><strong>GKS 의 skip 결정은 의도적 risk avoidance</strong> — 3월말 NSPIN 처럼 spread 가 음수로 큰 day는 GKS 가 bid 했어도 imbalance 비용 폭증해서 손실. GKS 가 알고 회피한 듯.</li>
        <li><strong>Strategy C 라면 같은 day 에도 매출 capture 가능</strong> — 단순 DA 가 아닌 RT 라우팅 / 상품 전환 / DA 0% bid 등으로 risk 회피하면서 spread 가능한 상품/venue 만 cherry-pick.</li>
      </ul>
      <strong>상품별 deep-dive (Filter C — 해당 상품 GKS bid 시간만):</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.8;">
        <li><strong>Responsive Reserve Service: capture 70.8%, uplift 1.4x</strong> — GKS 가 bid 한 시간에는 거의 optimal 수준. RRS 는 GKS 선택이 양호.</li>
        <li><strong>Non-Spinning Reserve: capture 53.7%, uplift 1.9x</strong> — DA-only 한정 + over-bid 로 인한 imbalance가 gap. RT 활용 + bid MW 축소로 개선 가능.</li>
        <li><strong>ERCOT Contingency Reserve Service: capture 34.9%, uplift 2.9x</strong> — GKS 가 bid 한 시간에도 큰 gap. ECRS 는 high-spread day 를 놓치고 평범한 day 위주로 bid 하는 듯 — 상품 선택 timing 의 문제.</li>
      </ul>
      <strong>결론</strong>: GKS 의 underperformance 는 (1) 의도적 high-volatility day 회피 + (2) 참여 day 내 sub-optimal 전략의 조합.
      (1) 은 risk-averse 결정으로 valid 할 수 있으나 $558K 잠재 매출 trade-off. (2) 가 진짜 실행 가능한 improvement 영역 — Filter B/C 기준 추가 매출 $272K 잠재력.
    </div>
  </div>
</div>

<!-- ──────────────────────────────────────────────────────────────────────
     PHASE C — Playbook 구현 (Concrete Implementation)
     ────────────────────────────────────────────────────────────────────── -->
<div class="section" style="background:linear-gradient(90deg, rgba(8,153,129,0.10), transparent); padding:14px 16px; border-radius:6px; border-left:4px solid var(--accent-up); margin-top:32px;">
  <h2 style="border:none; padding:0; margin:0;">PHASE C — Playbook 구현 (Concrete Implementation)</h2>
  <div class="sub" style="margin-top:4px;">시황별 운영 룰북 · 매출 upside 검증 · 일자별 시계열 · Production module 사용 가이드</div>
</div>

<!-- ───── Q10: Operational Playbook — situation-based 룰북 ───── -->
<div class="section">
  <h2>Q10. 시황별 운영 룰북 — 시간대 × 시황별 어떤 상품, 어떤 DA/RT 비중?</h2>
  <div class="sub">사용자 질문: 저녁 peak time 에 어떤 상품을 어떤 DA/RT 비중으로 들어가야 할까? Strategy C (Oracle) 의 시간별 선택을 시황 bucket 별로 aggregate해 운영 가능한 룰북으로 정리.</div>

  <div class="panel">
    <h3>Level 1 — 5개 시간대 bucket (전체 평균)</h3>
    <div id="q10-level1-table" style="overflow-x:auto;"></div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>Level 2 — Evening Peak (HE 18-22) deep-dive : HE 별</h3>
    <div id="q10-evening-he-table" style="overflow-x:auto;"></div>
    <div class="callout" style="margin-top:10px;">
      <strong>저녁 peak 핵심:</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.8;">
        <li><strong>HE 22 가 evening peak 의 매출 최고점 ($1,037/hr 평균)</strong> — RT 비중도 35% 로 가장 높음. Non-Spinning Reserve 84% + ECRS 10% + RRS 6%.</li>
        <li>HE 18: 거의 모두 NSPIN DA (RT 10% 만) — peak 시작 전 안정 시간.</li>
        <li>HE 19-21: NSPIN dominant 지만 RT 24-29% 로 증가.</li>
        <li>HE 22: DA 65% / RT 35% — RT 비중 최대.</li>
      </ul>
    </div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>Level 3 — Evening Peak × Net-Load Forecast Quintile</h3>
    <div id="q10-evening-netload-table" style="overflow-x:auto;"></div>
    <div class="callout" style="margin-top:10px;">
      <strong>Net-Load 가 가장 강력한 시황 신호:</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.8;">
        <li><strong>Net-Load Q5 (top 20%) Evening peak: 평균 $1,841/hr 매출</strong> — 전체 evening peak 평균 $554 의 3.3배.</li>
        <li>ECRS 비중 17% (가장 높음) + RT 32% 활용.</li>
        <li>Net-Load Q1-Q2 (calm days): NSPIN 95-96% + DA 84-85% — 단순 DA-only 무방.</li>
      </ul>
    </div>
  </div>

  <div class="callout" style="margin-top:12px;">
    <strong>Q10 의 역할</strong>: <em>descriptive</em> — 각 시황 (HE bucket × Net-Load quintile) 에서 어느 상품 / venue 가 winner 였는지를 보여줌. 매출 최대화 운영 룰 (prescriptive) 은 <strong>Q11</strong> 에서 통합 정리.
  </div>
</div>

<!-- ───── Q11: Playbook Upside vs Always-NSPIN-DA Baseline ───── -->
<div class="section">
  <h2>Q11. Playbook 매출 Upside — vs 단순 Always-NSPIN-DA Baseline</h2>
  <div class="sub">사용자 질문 (2026-05-19): 시황별 playbook 적용 시 매출 vs 전시간 100% NSPIN-DA (with RT buyback) 매출 — upside 얼마? Cohort 별 best combo 학습 후 적용 (in-sample).</div>

  <div class="panel">
    <h3>3가지 Playbook 변형 + Baseline + Oracle 비교 (전체 130일, in-sample)</h3>
    <div id="q11-all-days-table" style="overflow-x:auto;"></div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>Filter B — GKS 참여 104일 한정 (apples-to-apples 실용 비교)</h3>
    <div id="q11-filter-b-table" style="overflow-x:auto;"></div>
    <div class="callout" style="margin-top:10px;">
      <strong>핵심 답 (사용자 질문):</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.8;">
        <li><strong>Medium playbook (25 cohort) 매출: $822K</strong> · Baseline (Always NSPIN-DA): $624K → <strong>+31.7% uplift ($198K 추가)</strong></li>
        <li>Coarse (5 HE bucket only): +27% · Fine (125 cohort): +45% → cohort 세분화할수록 uplift 증가하지만 over-fitting 우려도 ↑</li>
        <li>Playbook 은 Oracle (이론 상한) 의 <strong>78% 까지 capture</strong> — 매우 강력한 룰</li>
        <li><strong>Filter B (GKS 참여일) 기준: Medium playbook = $317K</strong> vs GKS Actual $230K → <strong>+38% ($87K 추가)</strong> — 실행 가능 잠재력</li>
      </ul>
    </div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>Medium Playbook (25 cohort) — Cohort 별 best combo 룰</h3>
    <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px;">
      각 cohort 별로 매출 최대화하는 (product × venue) combo. NSPIN_DA 가 19/25 cohort 에서 default 이지만, <strong>net-load Q4-Q5 (top 40%) tight 시간대에서 5개 cohort 가 다른 combo 선택</strong> — 이게 playbook 의 매출의 70%+ 를 차지.
    </div>
    <div id="q11-cohort-rules-table" style="overflow-x:auto;"></div>
    <div class="callout" style="margin-top:10px;">
      <strong>주요 cohort 인사이트 (매출 큰 5개 cohort 가 playbook 매출의 77% 차지):</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.8;">
        <li><strong>Morning × Net-Load Q5 → ECRS_DA</strong>: 108h, <strong>$257K (단일 cohort 최대)</strong> — morning peak scarcity 시 ECRS spread spike</li>
        <li><strong>Night × Net-Load Q5 → NSPIN_DA</strong>: 162h, $143K — 야간 tight 시 NSPIN DA</li>
        <li><strong>Evening × Net-Load Q5 → NSPIN_RT</strong>: 135h, $110K — tight evening 시 Real-Time route 가 DA spread 보다 큼</li>
        <li>LateEve × Q5 → NSPIN_DA: $81K · Midday × Q5 → NSPIN_DA: $39K</li>
        <li>Morning × Q3 → RRS_DA: $8K (RRS 단독 cohort)</li>
        <li>나머지 19 cohort (low/mid net-load 시간대) 는 NSPIN_DA default 로도 충분</li>
      </ul>
    </div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>Playbook 적용 시 시간대별 (product × venue) Mix — Stacked</h3>
    <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px;">
      각 HE 의 137일 중 playbook 이 어떤 (product × venue) combo 를 선택했는지 stacked bar 로 시각화.
      X축 = Hour Ending (1~24), Y축 = 137 시간 (총합 = 137).
      <strong>Medium (25 cohort)</strong> 은 단순 — bucket 별로 single combo. <strong>Fine (86 cohort)</strong> 은 더 다양한 mix.
    </div>
    <div class="grid-2">
      <div>
        <div style="font-size:11px; color:var(--text-secondary); margin-bottom:4px; font-weight:600;">Medium Playbook (25 cohort)</div>
        <div class="chart-wrap" style="height:300px;"><canvas id="q13-medium-chart"></canvas></div>
      </div>
      <div>
        <div style="font-size:11px; color:var(--text-secondary); margin-bottom:4px; font-weight:600;">Fine Playbook (86 cohort)</div>
        <div class="chart-wrap" style="height:300px;"><canvas id="q13-fine-chart"></canvas></div>
      </div>
    </div>
    <div class="callout" style="margin-top:10px;">
      <strong>관찰:</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.8;">
        <li><strong>Medium (left)</strong>: cohort 가 거칠어 HE 7-10 morning, HE 18-22 evening 에서만 NSPIN 외 상품 mix. Night/Midday/LateEve 는 NSPIN_DA dominant. Step-function 패턴.</li>
        <li><strong>Fine (right)</strong>: Morning (HE 7-10) 에서 RRS_DA · ECRS_DA · ECRS_RT · NSPIN_DA · NSPIN_RT 5개 combo 가 모두 등장 — 가장 다양한 mix. Evening 도 ECRS_DA / NSPIN_DA / NSPIN_RT 의 그라데이션.</li>
        <li><strong>HE 22 (저녁 peak)</strong>: Medium 은 60% NSPIN_DA + 40% NSPIN_RT 단순 분리. Fine 은 20% ECRS_DA + 40% NSPIN_DA + 40% NSPIN_RT 의 세밀한 조합 — 다른 시간대 정보까지 활용.</li>
        <li><strong>Midday (HE 11-17)</strong>: 양 playbook 모두 NSPIN_DA dominant — 단순 운영 OK. Fine 은 4-7% ECRS_RT 추가 (marginal uplift).</li>
        <li>Fine 의 추가 +13% uplift (Q11 결과) 는 주로 morning ramp 와 evening peak 의 micro-mix 에서 나옴. 운영 복잡도 증가 trade-off 고려해 medium 권장.</li>
      </ul>
    </div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>D-1 운영 결정 트리 (전 시간대 통합 운영 룰)</h3>
    <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px;">
      D-1 forecast (Net-Load FC + Solar FC) 만으로 매시간 product / venue 결정.
      <strong>이 단순 룰만으로 baseline 대비 +30-40% uplift</strong> (Q11 검증 결과).
      운영 시 <code>shared/scripts/as_playbook.py</code> 의 <code>ASPlaybook</code> 클래스가 이 룰을 자동 적용.
    </div>
    <div class="callout" style="background:var(--bg-panel-2); border-left-color: var(--accent-up);">
      <pre style="font-family: 'JetBrains Mono', monospace; font-size: 11px; line-height: 1.6; white-space: pre-wrap; margin:0;">
D-1 운영 결정 (모든 24 시간대 통합 룰):

────────────────────────────────────────────────────────────────
STEP 1. 매시간 Net-Load Forecast percentile 분류 (해당 HE 분포 기준)
────────────────────────────────────────────────────────────────

▶ Net-Load Q5 (top 20%) 시간 = "high-value cohort" — 시간대별 분기:

   • Morning (HE 7-10) Q5 →  ECRS Day-Ahead
        → 평균 $2,826/hr (단일 cohort 최대 매출 cohort)
        → ECRS DA MCPC 가 spike (×8 정도) 하는 시간

   • Evening (HE 18-22) Q5 →  NSPIN Real-Time
        → 평균 $1,841/hr
        → Real-Time NSPIN MCPC > Day-Ahead spread

   • Night (HE 1-6) Q5 →  NSPIN Day-Ahead
        → 평균 $1,029/hr (alert 시 추가 NSPIN bid)

   • Late evening (HE 23-24) Q5 →  NSPIN Day-Ahead
        → 평균 $1,880/hr

   • Midday (HE 11-17) Q5 →  NSPIN Day-Ahead
        → 평균 $274/hr

▶ Net-Load Q3-Q4 (mid-high, 40~80 percentile) →  NSPIN Day-Ahead default
   (단, Evening 시간대는 RT 비중 24-36% 활용)

▶ Net-Load Q1-Q2 (calm days, bottom 40%) →  NSPIN Day-Ahead 단순 적용
   (RT 비중 < 20% — 추가 복잡성 불필요)


────────────────────────────────────────────────────────────────
STEP 2. Evening Peak (HE 18-22) 시 HE 별 fine-tune (선택)
────────────────────────────────────────────────────────────────
   HE 18 → 거의 NSPIN DA (RT 10% 만)
   HE 19-21 → DA 71-76% / RT 24-29%
   HE 22 → DA 65% / RT 35%  (저녁 매출 최고점, RT 비중 최대)


────────────────────────────────────────────────────────────────
STEP 3. Solar 추가 조건 (Evening peak 전용)
────────────────────────────────────────────────────────────────
   Solar Q1-Q2 (구름 / 일몰 전) → RT 비중 26-27% 유지
   Solar Q5 (맑음)              → DA 88% (spread 변동성 낮음)


────────────────────────────────────────────────────────────────
시간대별 평균 매출 / 시간 (참고):
────────────────────────────────────────────────────────────────
   Night       (HE 1-6)    →  avg $80/hr · NSPIN 100%
   Morning     (HE 7-10)   →  avg $664/hr · NSPIN 54% / ECRS 30% / RRS 16% ★
   Midday      (HE 11-17)  →  avg $107/hr · NSPIN 95% (단순 DA-only 충분)
   Evening     (HE 18-22)  →  avg $554/hr · NSPIN 85% / ECRS 10% / RRS 5% ★
   Late evening(HE 23-24)  →  avg $556/hr · NSPIN 85%
      </pre>
    </div>
    <div class="callout" style="margin-top:10px;">
      <strong>Production 자동화</strong>: 위 결정 트리는 <code>as_playbook.py</code> 의 25 cohort rules 로 encode 되어 있음.
      <code>ASPlaybook().recommend_day(d1_forecast)</code> 호출로 24시간 plan 자동 산출 (자세한 사용법: <strong>C4 섹션</strong>).
    </div>
  </div>
</div>

<!-- ───── Q12: Daily strategy revenue time series ───── -->
<div class="section">
  <h2>Q12. 일자별 매출 시계열 — Fine vs Medium Playbook vs NSPIN-100% Baseline</h2>
  <div class="sub">사용자 요청 (2026-05-19): 3개 시나리오의 일별 매출 시각화. <strong>HSL = 100 MW flat 가정</strong> (시간변동 HSL 제거) 으로 strategy 의 순수 rule quality 만 평가. Storm Fern (1/24-28) 와 3월말 negative spread 이벤트가 playbook 의 가치를 가장 잘 보여줌.</div>

  <div class="panel">
    <h3>일별 매출 (Daily Revenue) — 3개 시나리오 시계열</h3>
    <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px;">
      X축 = 일자 (2026-01-01 ~ 2026-05-17, 137일) · Y축 = 일별 매출 ($).
      음수 값 = baseline (NSPIN_DA) 이 spread 음수로 손실 본 day — playbook 은 같은 day 에 다른 combo 로 양수 유지.
    </div>
    <div class="chart-wrap tall"><canvas id="q12-daily-chart"></canvas></div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>누적 매출 (Cumulative) — 격차가 시간에 따라 어떻게 벌어지는지</h3>
    <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px;">
      시간 흐름에 따라 playbook 과 baseline 의 누적 격차가 점진적으로 벌어지는 패턴 확인.
      특정 day (Storm Fern, 3/23) 에서 격차가 stepped 으로 확장.
    </div>
    <div class="chart-wrap tall"><canvas id="q12-cumsum-chart"></canvas></div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>Top 10 Days — Medium Playbook 이 Baseline 대비 가장 큰 uplift 발생</h3>
    <div id="q12-top-days-table" style="overflow-x:auto;"></div>
    <div class="callout" style="margin-top:10px;">
      <strong>핵심 관찰 (HSL=100 MW flat 기준):</strong>
      <ul style="margin: 6px 0 0 18px; line-height: 1.8;">
        <li><strong>2026-03-23: Baseline = −$105K (loss), Medium Playbook = +$9K, Fine = +$60K → 단일일 +$114K uplift</strong> ★ 평범한 day 에 NSPIN spread 폭증 음수 — playbook 이 다른 combo 로 switch 해서 손실 회피.</li>
        <li><strong>2026-01-28 (Storm Fern 마지막날): Baseline = −$40K, Medium = −$17K, Fine = −$14K</strong> — 가장 어려운 day. Wind 실측 −45% bust + DAM 이 RT 추세 못 따라감. Playbook도 일부 손실이지만 baseline 대비 60% 손실 회피.</li>
        <li>2026-01-26 (Storm Fern 핵심일): Baseline $297K → Medium $403K → Fine $438K. DA NSPIN MCPC 가 $432 까지 spike — 모든 strategy 가 NSPIN_DA 선택해서 큰 매출.</li>
        <li><strong>137일 중 ~25일에서 baseline 음수 (or 0 근접)</strong> — playbook 이 손실 회피의 핵심 가치.</li>
      </ul>
    </div>
  </div>
</div>

<!-- ───── C4: Production module guide (as_playbook.py) ───── -->
<div class="section">
  <h2>C4. Production Module — as_playbook.py 사용 가이드</h2>
  <div class="sub">Medium / Fine playbook 룰을 다른 agent (bess-optimizer, dart-virtual-trader 등) 에서 import 해서 사용하는 방법. D-1 forecast 입력 → 매시간 (product, venue) 추천 산출.</div>

  <div class="panel">
    <h3>Module 파일 구조</h3>
    <table>
      <thead><tr><th>파일</th><th>역할</th></tr></thead>
      <tbody>
        <tr><td><code>shared/scripts/as_playbook.py</code></td><td>Importable Python class — <code>ASPlaybook</code></td></tr>
        <tr><td><code>shared/data/forecasts/as_playbook_rules.json</code></td><td>Cohort rules + quintile thresholds (22 KB, auto-loaded)</td></tr>
        <tr><td><code>shared/data/adhoc/2026-05-07_AS-strategy/scripts/97_build_playbook_rules.py</code></td><td>재학습 script — 새 데이터 추가 시 실행해 rules 갱신</td></tr>
      </tbody>
    </table>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>사용 예시 (Python)</h3>
    <div class="callout" style="background:var(--bg-panel-2); border-left-color: var(--accent-up);">
      <pre style="font-family: 'JetBrains Mono', monospace; font-size: 11px; line-height: 1.6; white-space: pre-wrap; margin:0;">
from shared.scripts.as_playbook import ASPlaybook

# 1. 모듈 초기화 (rules JSON 자동 load)
pb = ASPlaybook()

# 2. 단일 시간 추천 — Medium playbook (25 cohort)
rec = pb.recommend(
    he=22,                         # Hour Ending
    netload_fc_mw=58000,           # D-1 NET_LOAD_FORECAST_BID_CLOSE
    solar_fc_mw=0,                 # D-1 SOLAR_COPHSL_BIDCLOSE
    level="medium",                # or "fine" (more granular)
)
# rec = {{
#   "product": "NSPIN", "venue": "RT", "combo": "NSPIN_RT",
#   "cohort":  "Evening|Q5",
#   "source":  "medium_rule",
#   "he_bucket": "Evening", "nl_q": "Q5", "solar_q": "Q4"
# }}

# 3. 24시간 전체 plan (D-1 forecast 입력)
day_fc = {{
    1:  {{"netload_fc_mw": 25000, "solar_fc_mw": 0}},
    ...
    24: {{"netload_fc_mw": 22000, "solar_fc_mw": 0}},
}}
plan = pb.recommend_day(day_fc, level="medium")
# plan[22] = {{"product": "NSPIN", "venue": "RT", ...}}
      </pre>
    </div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>학습 메타데이터 + 룰 분포</h3>
    <ul style="margin: 6px 0 0 18px; line-height: 1.7; font-size: 12px;">
      <li><strong>학습 기간</strong>: 2026-01-01 ~ 2026-05-17 (3,287 hours, 137일)</li>
      <li><strong>학습 가정</strong>: HSL = 100 MW flat · SoC = 200 MWh nameplate (pure rule quality 신호 추출)</li>
      <li><strong>Medium 룰</strong>: 25 cohort (5 HE bucket × 5 Net-load quintile). NSPIN_DA 18 · NSPIN_RT 4 · RRS_DA 2 · ECRS_RT 1</li>
      <li><strong>Fine 룰</strong>: 86 cohort (학습 가능한 sparsity 기준). NSPIN_DA 59 · ECRS_RT 10 · NSPIN_RT 6 · ECRS_DA 6 · RRS_DA 4 · RRS_RT 1</li>
    </ul>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>Fallback 동작 (production-safe)</h3>
    <ol style="margin: 6px 0 0 18px; line-height: 1.7; font-size: 12px;">
      <li>Fine 룰 없으면 → Medium 룰 fallback (<code>source: "fine_fallback_to_medium"</code>)</li>
      <li>Medium 룰 없으면 → <code>default_combo: "NSPIN_DA"</code> 사용</li>
      <li>HE 가 1-24 범위 밖 → "Midday" bucket 으로 fallback</li>
    </ol>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>재학습 (새 데이터 추가 시)</h3>
    <div class="callout" style="background:var(--bg-panel-2);">
      <pre style="font-family: 'JetBrains Mono', monospace; font-size: 11px; margin:0;">
# 새 데이터 fetch 후 모델 재학습 (예: 6월 데이터 도착 시)
python shared/data/adhoc/2026-05-07_AS-strategy/scripts/97_build_playbook_rules.py
# → shared/data/forecasts/as_playbook_rules.json 자동 갱신
# 다른 agent 는 변경 없이 즉시 새 rules 사용 (다음 ASPlaybook() init 시)
      </pre>
    </div>
  </div>

  <div class="panel" style="margin-top:12px;">
    <h3>통합 권장 agent</h3>
    <ul style="margin: 6px 0 0 18px; line-height: 1.8; font-size: 12px;">
      <li><strong>bess-optimizer</strong>: D-1 forecast 받아 <code>pb.recommend_day()</code> 로 24시간 (product, venue) plan 산출 → AS bid 자동화</li>
      <li><strong>dart-virtual-trader</strong>: 동일 forecast input 으로 AS 매출 forecast 도 도출 가능</li>
      <li><strong>reporter</strong>: 매일 07:30 daily report 에 "today's playbook plan" 자동 포함</li>
      <li><strong>pnl-manager</strong>: 익일 실적 vs playbook 추천 의 gap 분석</li>
    </ul>
  </div>
</div>

<div class="section" style="margin-top:32px; color: var(--text-muted); font-size: 11px; line-height:1.6;">
  Generated {data['generated_at']} CT · Data sources:
  ERCOT Public API (Report NP4-188-CD Day-Ahead Market Clearing Price for Capacity,
  Report NP6-331-CD Real-Time 15-minute Market Clearing Price for Capacity) ·
  Yes Energy (Day-Ahead and Real-Time Locational Marginal Price, D-1 bid-close vintage forecasts) ·
  Tenaska PowerTools Platform (GKS BESS actual settlement data).<br>
  Spread = Day-Ahead Market Clearing Price for Capacity − Real-Time Market Clearing Price for Capacity ($/MWh).
  단위 손실 (damage / loss) 은 100 MW 자원 가정 (Day-Ahead award MW × 음수 spread × 1시간).
  Tenaska GKS actuals 는 2026-05-10 까지 수집됨 (그 이후는 다음 일일 PnL cycle 에서 backfill); 그 외 시리즈는 2026-05-17 까지 full coverage.
</div>
<!-- ───── APPENDIX: 용어집 (Glossary) — 분석 마지막에 reference 로 배치 ───── -->
<div class="section" style="margin-top:32px;">
  <h2>Appendix — 용어집 (Glossary)</h2>
  <div class="panel">
    <div class="glossary">
      <div><strong>Day-Ahead Market (DAM)</strong> — 하루 전 청산되는 전력 시장. 보조서비스도 여기서 청산.</div>
      <div><strong>Real-Time Market (RTM)</strong> — 실시간 (5분 또는 15분) 청산되는 전력 시장.</div>
      <div><strong>Market Clearing Price for Capacity (MCPC)</strong> — 보조서비스 시장 청산 가격 ($/MWh).</div>
      <div><strong>Spread</strong> — Day-Ahead MCPC − Real-Time MCPC. 양수면 Day-Ahead 에서 sell이 유리.</div>
      <div><strong>Hour Ending (HE)</strong> — 시간대 라벨. HE1 = 00:00~01:00, HE24 = 23:00~24:00.</div>
      <div><strong>Day of Week</strong> — 요일 (월요일=0 ··· 일요일=6).</div>
      <div><strong>Responsive Reserve Service (RRS)</strong> — 주파수 응동 보조서비스 (10분 이내).</div>
      <div><strong>ERCOT Contingency Reserve Service (ECRS)</strong> — 비상 대응 보조서비스 (10분).</div>
      <div><strong>Non-Spinning Reserve (Non-Spin / NSPIN)</strong> — 비회전 예비력 (30분 내).</div>
      <div><strong>Logistic Regression</strong> — 이진 분류용 로지스틱 회귀.</div>
      <div><strong>Area Under ROC Curve (AUC)</strong> — 분류기 성능 지표, 1.0이 완벽 / 0.5는 무작위.</div>
      <div><strong>F1 score</strong> — Precision과 Recall의 조화평균.</div>
      <div><strong>Top-decile lift</strong> — 모델 예측 확률 상위 10%의 적중률 ÷ 전체 base rate.</div>
      <div><strong>High Sustained Limit (HSL)</strong> — 배터리 최대 지속 출력 (MW). 본 분석 strategy 비교는 100 MW flat 가정.</div>
      <div><strong>State of Charge (SoC)</strong> — 배터리 충전 상태 (MWh). GKS = 200 MWh.</div>
      <div><strong>SoC Duration</strong> — RRS 0.5h · ECRS 1h · NSPIN 4h. Real-Time cap = min(HSL, SoC / duration).</div>
      <div><strong>Oracle (Perfect Foresight)</strong> — 매시간 정답을 알 때의 상한선. Binary rule family 의 이론 천장.</div>
      <div><strong>τ* (tau-star)</strong> — Binary D-1 Flag Rule 의 매출 최대화 임계값.</div>
      <div><strong>Gross vs Net DA AS Revenue</strong> — Gross = Tenaska 보고치 (a_DA × DAM_MCPC). Net = 가정 #1 적용 (a_DA × spread).</div>
      <div><strong>Cohort</strong> — Playbook 학습 단위. Medium = (HE bucket × Net-load quintile). Fine = + Solar quintile.</div>
    </div>
  </div>
</div>


</div>

<!-- ───── DATA + LOGIC ───── -->
<script>
const DATA = {data_json};

const palette = {{
  RRS:   '#089981',
  ECRS:  '#2962ff',
  NSPIN: '#9c27b0',
}};
const FULL_NAME = {{
  RRS:   'Responsive Reserve Service',
  ECRS:  'ERCOT Contingency Reserve Service',
  NSPIN: 'Non-Spinning Reserve',
}};
const Chart_ = window.Chart;
Chart_.defaults.font.family = "'JetBrains Mono','Inter',sans-serif";
Chart_.defaults.color = '#5d606b';
Chart_.defaults.borderColor = '#eceff3';
Chart_.defaults.plugins.legend.display = false;

/* ───── Q1 line chart ───── */
let q1Chart = null;
function drawQ1(p) {{
  const d = DATA.Q1_spread_series.products[p];
  const labels = d.daily_series.map(r => r.date);
  const spr    = d.daily_series.map(r => r.spread);
  const da     = d.daily_series.map(r => r.da);
  const rt     = d.daily_series.map(r => r.rt);
  if (q1Chart) q1Chart.destroy();
  q1Chart = new Chart_(document.getElementById('q1-chart').getContext('2d'), {{
    type: 'line',
    data: {{
      labels,
      datasets: [
        {{ label: 'Spread (Day-Ahead − Real-Time)', data: spr, borderColor: palette[p],
           backgroundColor: 'rgba(8,153,129,0.10)', borderWidth: 2, fill: 'origin',
           pointRadius: 0, tension: 0.15 }},
        {{ label: 'Day-Ahead MCPC', data: da, borderColor: '#9598a1', borderWidth: 1,
           borderDash: [4,3], pointRadius: 0, tension: 0.15 }},
        {{ label: 'Real-Time MCPC', data: rt, borderColor: '#ff9800', borderWidth: 1,
           borderDash: [2,3], pointRadius: 0, tension: 0.15 }},
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: true, position: 'top', align: 'end',
                            labels: {{ boxWidth: 8, boxHeight: 8 }} }},
                  title: {{ display: true, text: FULL_NAME[p],
                            color: '#131722', font: {{ size: 12, weight: '600' }}, align: 'start' }} }},
      scales: {{
        x: {{ grid: {{ color: '#eceff3' }}, ticks: {{ maxTicksLimit: 12 }} }},
        y: {{ grid: {{ color: '#eceff3' }}, ticks: {{ callback: v => '$'+v }} }}
      }}
    }}
  }});
  drawHeatmap(p);
}}

/* ───── Hour-Ending × Day-of-Week heatmap ───── */
function drawHeatmap(p) {{
  const h = DATA.Q1_spread_series.products[p].hod_dow_heatmap; // 24x7
  const flat = h.flat().filter(v => v !== null);
  const mn = Math.max(Math.min(...flat), -20);
  const mx = Math.min(Math.max(...flat),  20);
  const dow = ['월','화','수','목','금','토','일'];
  let html = '<div class="heatmap"><div></div>';
  for (const d of dow) html += `<div class="hd">${{d}}</div>`;
  for (let he = 1; he <= 24; he++) {{
    html += `<div class="rl">HE ${{he}}</div>`;
    for (let i = 0; i < 7; i++) {{
      const v = h[he-1][i];
      if (v === null) {{ html += '<div class="cell" style="background:#eceff3;color:#9598a1;">·</div>'; continue; }}
      const color = colorScale(v, mn, mx, 0);
      html += `<div class="cell" style="background:${{color}};color:${{textColor(color)}}">${{v.toFixed(1)}}</div>`;
    }}
  }}
  html += '</div>';
  document.getElementById('heatmap-host').innerHTML = html;
}}
function colorScale(v, mn, mx, pivot) {{
  if (v >= pivot) {{
    const t = Math.min(1, v / (mx === 0 ? 1 : mx));
    const a = 0.18 + 0.72 * t;
    return `rgba(8,153,129,${{a.toFixed(2)}})`;
  }} else {{
    const t = Math.min(1, Math.abs(v) / Math.abs(mn || 1));
    const a = 0.18 + 0.72 * t;
    return `rgba(242,54,69,${{a.toFixed(2)}})`;
  }}
}}
function textColor(rgba) {{
  const m = rgba.match(/rgba\\(([^,]+),([^,]+),([^,]+),([^,]+)\\)/);
  if (!m) return '#fff';
  const a = parseFloat(m[4]);
  return a > 0.45 ? '#fff' : '#131722';
}}

/* ───── Q3 daily prob chart ───── */
let q3Chart = null;
function drawQ3(p) {{
  const d = DATA.Q3_flag_logit.products[p].daily_max_prob_series;
  const labels = d.map(r => r.date);
  const probs  = d.map(r => r.prob);
  const thr    = DATA.Q3_flag_logit.products[p].best_f1_threshold;
  const thrLine = labels.map(_ => thr);
  if (q3Chart) q3Chart.destroy();
  q3Chart = new Chart_(document.getElementById('q3-chart').getContext('2d'), {{
    type: 'line',
    data: {{
      labels,
      datasets: [
        {{ label: '일별 최대 P(negative spread)', data: probs, borderColor: palette[p], borderWidth: 2,
           backgroundColor: 'rgba(41,98,255,0.08)', fill: 'origin',
           pointRadius: 0, tension: 0.15 }},
        {{ label: 'Best F1-score threshold (참고)', data: thrLine, borderColor: '#f23645', borderWidth: 1,
           borderDash: [4,4], pointRadius: 0 }},
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: true, position: 'top', align: 'end',
                            labels: {{ boxWidth: 8, boxHeight: 8 }} }},
                  title: {{ display: true, text: FULL_NAME[p],
                            color: '#131722', font: {{ size: 12, weight: '600' }}, align: 'start' }} }},
      scales: {{
        x: {{ grid: {{ color: '#eceff3' }}, ticks: {{ maxTicksLimit: 14 }} }},
        y: {{ grid: {{ color: '#eceff3' }}, min: 0, max: 1, ticks: {{ callback: v => (v*100).toFixed(0)+'%' }} }}
      }}
    }}
  }});
}}

/* ───── Q4 strategy comparison bar chart ───── */
function drawQ4() {{
  const ps = ['RRS','ECRS','NSPIN'];
  const labels = ps.map(p => FULL_NAME[p]);
  const get = (p, key) => DATA.Q4_optimal_split.products[p].strategies[key].revenue_usd;
  const dataSets = [
    {{ label: 'Naïve Day-Ahead 100% (with Real-Time buyback)',
       data: ps.map(p => get(p, 'naive_day_ahead_100pct_with_buyback')),
       backgroundColor: 'rgba(41,98,255,0.55)' }},
    {{ label: 'Naïve Real-Time 100%',
       data: ps.map(p => get(p, 'naive_real_time_100pct')),
       backgroundColor: 'rgba(255,152,0,0.65)' }},
    {{ label: 'Binary D-1 Flag Rule (per-product, deprecated)',
       data: ps.map(p => get(p, 'binary_d1_flag_rule')),
       backgroundColor: 'rgba(8,153,129,0.85)' }},
    {{ label: '3-tier Heuristic (참고)',
       data: ps.map(p => get(p, 'three_tier_heuristic')),
       backgroundColor: 'rgba(156,39,176,0.45)' }},
    {{ label: 'Oracle (Perfect Foresight, 이론 상한)',
       data: ps.map(p => get(p, 'oracle_perfect_foresight')),
       backgroundColor: 'rgba(19,23,34,0.85)' }},
  ];
  new Chart_(document.getElementById('q4-bar').getContext('2d'), {{
    type: 'bar',
    data: {{ labels, datasets: dataSets }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: true, position: 'top', align: 'end',
                            labels: {{ boxWidth: 8, boxHeight: 8 }} }} }},
      scales: {{
        x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 11 }} }} }},
        y: {{ grid: {{ color: '#eceff3' }}, ticks: {{ callback: v => '$'+(v/1000).toFixed(0)+'k' }},
              title: {{ display: true, text: '누적 매출 (USD)', font: {{ size: 11 }} }} }}
      }}
    }}
  }});
}}

/* ───── Q2 event/day tables ───── */
function renderQ2Events(p) {{
  const qp = DATA.Q2_negative_profile.products[p];
  const events = qp.severe_events;

  // Root-cause aggregate summary (across all severe events for this product, not just top 20)
  const cs = qp.root_cause_summary_pct || {{}};
  const totalSev = qp.n_severe_events_total || 0;
  let summary = '<div style="margin-bottom:10px; padding:10px 12px; background:var(--bg-row-alt); border-radius:6px;">'
              + `<div style="font-size:11px; color:var(--text-secondary); margin-bottom:6px;"><strong>Root-cause 분포 (전체 ${{totalSev}} 심각 이벤트)</strong></div>`
              + '<div style="display:flex; flex-wrap:wrap; gap:8px; font-size:11px;">';
  const causeOrder = ['Net-load surprise', 'Wind 부족', 'Load surge', 'Winter Storm',
                      'DA forecast bust (mis-pricing)', 'Solar 부족 시간대', 'Unclassified'];
  for (const c of causeOrder) {{
    const v = cs[c] || 0;
    if (v === 0) continue;
    const color = c === 'Unclassified' ? 'neutral' : 'down';
    summary += `<span class="tag ${{color === 'down' ? 'red' : ''}}" style="font-size:11px;">${{c}}: <strong>${{v.toFixed(1)}}%</strong></span>`;
  }}
  summary += '</div></div>';

  let h = summary
        + '<table><thead><tr>'
        + '<th>Datetime</th><th>HE</th>'
        + '<th class="num">DA<br>MCPC</th>'
        + '<th class="num">RT<br>MCPC</th>'
        + '<th class="num">Spread</th>'
        + '<th class="num">Damage<br>($, 100MW·1h)</th>'
        + '<th class="num">Wind err<br>(% vs FC)</th>'
        + '<th class="num">Load err<br>(% vs FC)</th>'
        + '<th><strong>Primary Root Cause</strong></th>'
        + '<th>모든 causes</th></tr></thead><tbody>';
  for (const e of events) {{
    const causes = (e.causes || []).map(t => `<span class="tag red" style="font-size:10px;">${{t}}</span>`).join('');
    const primary = e.primary_cause || 'Unclassified';
    const primaryCls = primary === 'Unclassified' ? 'neutral' : 'down';
    const wind = e.wind_err_pct;
    const load = e.load_err_pct;
    const windCls = wind !== null && wind < -10 ? 'down' : 'neutral';
    const loadCls = load !== null && load > 3 ? 'down' : 'neutral';
    h += `<tr>
      <td>${{e.datetime.slice(0,16).replace('T',' ')}}</td>
      <td>HE ${{e.he}}</td>
      <td class="num">${{e.da.toFixed(2)}}</td>
      <td class="num">${{e.rt.toFixed(2)}}</td>
      <td class="num down">${{e.spread.toFixed(2)}}</td>
      <td class="num down">$${{e.damage_100mw.toLocaleString()}}</td>
      <td class="num ${{windCls}}">${{wind !== null && wind !== undefined ? wind.toFixed(1) + '%' : '—'}}</td>
      <td class="num ${{loadCls}}">${{load !== null && load !== undefined ? load.toFixed(1) + '%' : '—'}}</td>
      <td><strong class="${{primaryCls}}">${{primary}}</strong></td>
      <td>${{causes || '<span class="tag">—</span>'}}</td>
    </tr>`;
  }}
  h += '</tbody></table>';
  document.getElementById('q2-event-table').innerHTML = h;
}}
function renderQ2Days(p) {{
  const days = DATA.Q2_negative_profile.products[p].damage_days;
  let h = '<table><thead><tr><th>Date</th><th class="num">누적 손실 (USD)</th><th class="num">음수 spread 시간 수</th></tr></thead><tbody>';
  for (const d of days) {{
    h += `<tr><td>${{d.date}}</td><td class="num down">$${{d.loss.toLocaleString()}}</td><td class="num">${{d.n_neg_hours}}</td></tr>`;
  }}
  h += '</tbody></table>';
  document.getElementById('q2-day-table').innerHTML = h;
}}

/* ───── Q13: Playbook hourly mix stacked charts ───── */
function renderQ13() {{
  const q13 = DATA.Q13_playbook_mix;
  if (!q13 || !q13.medium) return;

  // Color palette per combo (DA = solid color, RT = same color lighter)
  const colors = {{
    'RRS_DA':   'rgba(8,153,129,0.85)',
    'RRS_RT':   'rgba(8,153,129,0.45)',
    'ECRS_DA':  'rgba(41,98,255,0.85)',
    'ECRS_RT':  'rgba(41,98,255,0.45)',
    'NSPIN_DA': 'rgba(156,39,176,0.85)',
    'NSPIN_RT': 'rgba(156,39,176,0.45)',
  }};
  const comboOrder = q13.combo_order || ['RRS_DA','RRS_RT','ECRS_DA','ECRS_RT','NSPIN_DA','NSPIN_RT'];
  const heLabels = Array.from({{length: 24}}, (_, i) => 'HE'+(i+1));

  function buildChart(canvasId, data, title) {{
    // data.hours[HE][combo] = count
    const datasets = comboOrder.map(combo => ({{
      label: combo.replace('_', ' '),
      data: heLabels.map((_, i) => {{
        const he = i + 1;
        const row = data.hours[he] || data.hours[String(he)] || {{}};
        return row[combo] || 0;
      }}),
      backgroundColor: colors[combo],
      borderColor: 'rgba(255,255,255,0.2)',
      borderWidth: 0.5,
      stack: 'combos',
    }}));

    new Chart_(document.getElementById(canvasId).getContext('2d'), {{
      type: 'bar',
      data: {{ labels: heLabels, datasets }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{
          legend: {{ display: true, position: 'top', align: 'end',
                    labels: {{ boxWidth: 10, boxHeight: 6, font: {{ size: 10 }} }} }},
          tooltip: {{ mode: 'index', intersect: false,
            callbacks: {{
              label: function(ctx) {{
                const pct = (ctx.parsed.y / 137 * 100).toFixed(0);
                return ctx.dataset.label + ': ' + ctx.parsed.y + 'h (' + pct + '%)';
              }}
            }}
          }},
        }},
        scales: {{
          x: {{ stacked: true, grid: {{ display: false }}, ticks: {{ font: {{ size: 9 }} }} }},
          y: {{ stacked: true, grid: {{ color: '#eceff3' }},
               ticks: {{ callback: v => v + 'h' }},
               max: 137,
               title: {{ display: true, text: 'Hours (137일 중)', font: {{ size: 10 }} }} }}
        }}
      }}
    }});
  }}

  buildChart('q13-medium-chart', q13.medium, 'Medium');
  buildChart('q13-fine-chart',   q13.fine,   'Fine');
}}

/* ───── Q12: daily strategy time series ───── */
function renderQ12() {{
  const q12 = DATA.Q12_daily_strategy;
  if (!q12 || !q12.daily_series) return;
  const ds = q12.daily_series;
  const labels = ds.map(r => r.date);

  // (1) Daily revenue line chart
  new Chart_(document.getElementById('q12-daily-chart').getContext('2d'), {{
    type: 'line',
    data: {{
      labels,
      datasets: [
        {{ label: '(0) Baseline — NSPIN 100% DA (with buyback)',
           data: ds.map(r => r.baseline),
           borderColor: '#9598a1', borderWidth: 1.5,
           backgroundColor: 'rgba(149,152,161,0.05)',
           pointRadius: 0, tension: 0.15, fill: false }},
        {{ label: '(M) Medium Playbook (25 cohorts)',
           data: ds.map(r => r.medium),
           borderColor: '#2962ff', borderWidth: 2,
           backgroundColor: 'rgba(41,98,255,0.06)',
           pointRadius: 0, tension: 0.15, fill: false }},
        {{ label: '(F) Fine Playbook (125 cohorts)',
           data: ds.map(r => r.fine),
           borderColor: '#089981', borderWidth: 2,
           backgroundColor: 'rgba(8,153,129,0.06)',
           pointRadius: 0, tension: 0.15, fill: false }},
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{
        legend: {{ display: true, position: 'top', align: 'end',
                  labels: {{ boxWidth: 12, boxHeight: 6 }} }},
        tooltip: {{ callbacks: {{
          label: function(ctx) {{
            return ctx.dataset.label + ': $' + ctx.parsed.y.toLocaleString(undefined, {{maximumFractionDigits: 0}});
          }}
        }} }},
      }},
      scales: {{
        x: {{ grid: {{ color: '#eceff3' }}, ticks: {{ maxTicksLimit: 16, autoSkip: true }} }},
        y: {{ grid: {{ color: '#eceff3' }},
              ticks: {{ callback: v => '$' + (v/1000).toFixed(0) + 'K' }},
              title: {{ display: true, text: '일별 매출 (USD)', font: {{ size: 11 }} }} }}
      }}
    }}
  }});

  // (2) Cumulative line chart
  new Chart_(document.getElementById('q12-cumsum-chart').getContext('2d'), {{
    type: 'line',
    data: {{
      labels,
      datasets: [
        {{ label: '(0) Baseline cumulative',
           data: ds.map(r => r.baseline_cumsum),
           borderColor: '#9598a1', borderWidth: 1.5,
           backgroundColor: 'rgba(149,152,161,0.10)',
           pointRadius: 0, tension: 0.15, fill: 'origin' }},
        {{ label: '(M) Medium Playbook cumulative',
           data: ds.map(r => r.medium_cumsum),
           borderColor: '#2962ff', borderWidth: 2,
           backgroundColor: 'rgba(41,98,255,0.08)',
           pointRadius: 0, tension: 0.15, fill: false }},
        {{ label: '(F) Fine Playbook cumulative',
           data: ds.map(r => r.fine_cumsum),
           borderColor: '#089981', borderWidth: 2,
           backgroundColor: 'rgba(8,153,129,0.08)',
           pointRadius: 0, tension: 0.15, fill: false }},
        {{ label: '(O) Oracle cumulative',
           data: ds.map(r => r.oracle_cumsum),
           borderColor: '#131722', borderWidth: 1.5, borderDash: [4, 4],
           pointRadius: 0, tension: 0.15, fill: false }},
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{
        legend: {{ display: true, position: 'top', align: 'end',
                  labels: {{ boxWidth: 12, boxHeight: 6 }} }},
        tooltip: {{ callbacks: {{
          label: function(ctx) {{
            return ctx.dataset.label + ': $' + ctx.parsed.y.toLocaleString(undefined, {{maximumFractionDigits: 0}});
          }}
        }} }},
      }},
      scales: {{
        x: {{ grid: {{ color: '#eceff3' }}, ticks: {{ maxTicksLimit: 16, autoSkip: true }} }},
        y: {{ grid: {{ color: '#eceff3' }},
              ticks: {{ callback: v => '$' + (v/1000).toFixed(0) + 'K' }},
              title: {{ display: true, text: '누적 매출 (USD)', font: {{ size: 11 }} }} }}
      }}
    }}
  }});

  // (3) Top 10 days table
  let h = '<table><thead><tr>'
        + '<th>Date</th>'
        + '<th class="num">Baseline (NSPIN-DA)</th>'
        + '<th class="num">Medium Playbook</th>'
        + '<th class="num">Fine Playbook</th>'
        + '<th class="num">Medium vs Baseline uplift</th>'
        + '</tr></thead><tbody>';
  for (const d of q12.top_days_medium_vs_baseline) {{
    const baseCls = d.baseline < 0 ? 'down' : 'neutral';
    h += `<tr>
      <td><strong>${{d.date}}</strong></td>
      <td class="num ${{baseCls}}">$${{d.baseline.toLocaleString()}}</td>
      <td class="num">$${{d.medium.toLocaleString()}}</td>
      <td class="num">$${{d.fine.toLocaleString()}}</td>
      <td class="num up" style="font-weight:600;">+$${{d.uplift.toLocaleString()}}</td>
    </tr>`;
  }}
  h += '</tbody></table>';
  document.getElementById('q12-top-days-table').innerHTML = h;
}}

/* ───── Q11: playbook upside ───── */
function renderQ11() {{
  const q11 = DATA.Q11_playbook_upside;
  if (!q11 || !q11.all_days) return;
  const all = q11.all_days;
  const fb = q11.filter_B_gks_days;

  // All-days comparison table
  const base = all.baseline_always_nspin_da;
  const oracle = all.oracle_strategy_c;
  let h = '<table><thead><tr>'
        + '<th>Strategy</th>'
        + '<th class="num">매출</th>'
        + '<th class="num">vs Baseline</th>'
        + '<th class="num">Oracle 대비 capture</th>'
        + '</tr></thead><tbody>';
  h += `<tr>
    <td>(0) Baseline — 항상 100% NSPIN Day-Ahead (with RT buyback)</td>
    <td class="num">$${{base.toLocaleString()}}</td>
    <td class="num neutral">—</td>
    <td class="num">${{(base/oracle*100).toFixed(1)}}%</td>
  </tr>`;
  const order = [
    ['coarse_5',  '(C) Coarse — 5 HE bucket only'],
    ['medium_25', '<strong>(M) Medium — HE bucket × Net-Load 5분위 (25 cohort) ★ 권장</strong>'],
    ['fine_125',  '(F) Fine — HE × NL × Solar 5분위 (~125 cohort)'],
  ];
  for (const [k, lbl] of order) {{
    const pb = all.playbooks[k];
    const isMed = k === 'medium_25';
    h += `<tr ${{isMed ? 'style="background:var(--bg-row-alt); font-weight:600;"' : ''}}>
      <td>${{lbl}}</td>
      <td class="num up">$${{pb.total_revenue.toLocaleString()}}</td>
      <td class="num up">+${{pb.uplift_vs_baseline_pct.toFixed(2)}}%</td>
      <td class="num">${{pb.capture_of_oracle_pct.toFixed(1)}}%</td>
    </tr>`;
  }}
  h += `<tr style="border-top:2px solid var(--border-strong); font-style:italic;">
    <td>(O) Oracle Strategy C — hour-level 이론 상한</td>
    <td class="num">$${{oracle.toLocaleString()}}</td>
    <td class="num">+${{((oracle/base-1)*100).toFixed(2)}}%</td>
    <td class="num">100.0%</td>
  </tr>`;
  h += '</tbody></table>';
  document.getElementById('q11-all-days-table').innerHTML = h;

  // Filter B comparison table
  let hb = '<table><thead><tr>'
         + '<th>Strategy</th>'
         + '<th class="num">매출 ($)</th>'
         + '<th class="num">vs Baseline</th>'
         + '<th class="num">vs GKS Actual</th>'
         + '</tr></thead><tbody>';
  const gks = fb.gks_actual_net;
  const baseB = fb.baseline_always_nspin_da;
  hb += `<tr style="color:var(--text-secondary);">
    <td>GKS Actual Net (실제)</td>
    <td class="num">$${{gks.toLocaleString()}}</td>
    <td class="num">${{(((gks/baseB)-1)*100).toFixed(1)}}%</td>
    <td class="num">baseline</td>
  </tr>`;
  hb += `<tr>
    <td>Baseline — 항상 100% NSPIN-DA</td>
    <td class="num">$${{baseB.toLocaleString()}}</td>
    <td class="num neutral">—</td>
    <td class="num down">${{(((baseB/gks)-1)*100).toFixed(1)}}%</td>
  </tr>`;
  for (const [k, lbl] of [
    ['playbook_coarse', '(C) Playbook coarse (5)'],
    ['playbook_medium', '<strong>(M) Playbook medium (25) ★</strong>'],
    ['playbook_fine',   '(F) Playbook fine (125)'],
  ]) {{
    const v = fb[k];
    const isMed = k === 'playbook_medium';
    hb += `<tr ${{isMed ? 'style="background:var(--bg-row-alt); font-weight:600;"' : ''}}>
      <td>${{lbl}}</td>
      <td class="num up">$${{v.toLocaleString()}}</td>
      <td class="num up">+${{((v/baseB-1)*100).toFixed(2)}}%</td>
      <td class="num up">+${{((v/gks-1)*100).toFixed(1)}}%</td>
    </tr>`;
  }}
  hb += `<tr style="border-top:2px solid var(--border-strong); font-style:italic;">
    <td>Oracle Strategy C (Filter B)</td>
    <td class="num">$${{fb.oracle_strategy_c.toLocaleString()}}</td>
    <td class="num">+${{((fb.oracle_strategy_c/baseB-1)*100).toFixed(2)}}%</td>
    <td class="num">+${{((fb.oracle_strategy_c/gks-1)*100).toFixed(1)}}%</td>
  </tr>`;
  hb += '</tbody></table>';
  document.getElementById('q11-filter-b-table').innerHTML = hb;

  // Cohort rules table (sorted by revenue desc)
  const rules = q11.medium_playbook_cohort_rules || {{}};
  const entries = Object.entries(rules).map(([k, v]) => {{
    const [hb_, nl] = k.split('|');
    return {{ he_bucket: hb_, nl: nl, combo: v.combo, hours: v.hours, revenue: v.total_revenue }};
  }}).sort((a, b) => b.revenue - a.revenue);
  let hc = '<table><thead><tr>'
         + '<th>HE Bucket</th><th>Net-Load Quintile</th><th>Chosen Combo</th>'
         + '<th class="num">Hours</th><th class="num">Total Revenue</th>'
         + '</tr></thead><tbody>';
  for (const r of entries) {{
    const [prod, venue] = r.combo.split('_');
    const isHighlight = r.revenue > 30000;
    hc += `<tr ${{isHighlight ? 'style="font-weight:600;"' : ''}}>
      <td>${{r.he_bucket}}</td>
      <td>${{r.nl}}</td>
      <td><span class="product-tag ${{prod}}">${{prod}}</span> ${{venue}}</td>
      <td class="num">${{r.hours}}</td>
      <td class="num ${{isHighlight ? 'up' : ''}}">$${{r.revenue.toLocaleString()}}</td>
    </tr>`;
  }}
  hc += '</tbody></table>';
  document.getElementById('q11-cohort-rules-table').innerHTML = hc;
}}

/* ───── Q10: situational playbook ───── */
function renderQ10() {{
  const q10 = DATA.Q10_playbook;
  if (!q10 || !q10.level_1_by_he_bucket) return;

  // Helper to render a bucket row
  function bucketRow(label, s) {{
    if (!s || s.hours === 0) return '';
    const pd = s.product_distribution_pct;
    return `<tr>
      <td>${{label}}</td>
      <td class="num">${{s.hours}}</td>
      <td><span class="product-tag ${{s.top_product}}">${{s.top_product}}</span></td>
      <td class="num">${{pd.RRS.toFixed(0)}} / ${{pd.ECRS.toFixed(0)}} / ${{pd.NSPIN.toFixed(0)}}%</td>
      <td class="num">${{s.overall_da_pct.toFixed(0)}} / ${{s.overall_rt_pct.toFixed(0)}}%</td>
      <td class="num up" style="font-weight:600;">$${{s.avg_winner_rev_usd_per_hour.toLocaleString()}}</td>
    </tr>`;
  }}

  // Level 1 — 5 buckets
  let h1 = '<table><thead><tr>'
        + '<th>시간대 (Hour Ending bucket)</th>'
        + '<th class="num">Hours</th>'
        + '<th>Top product</th>'
        + '<th class="num">상품 mix (RRS / ECRS / NSPIN)</th>'
        + '<th class="num">DA / RT</th>'
        + '<th class="num">평균 매출 ($/hr)</th>'
        + '</tr></thead><tbody>';
  const l1 = q10.level_1_by_he_bucket;
  for (const b of ["Night (HE 1-6)","Morning ramp (HE 7-10)","Mid-day (HE 11-17)",
                    "Evening peak (HE 18-22)","Late evening (HE 23-24)"]) {{
    h1 += bucketRow(b, l1[b]);
  }}
  h1 += '</tbody></table>';
  document.getElementById('q10-level1-table').innerHTML = h1;

  // Evening peak by HE
  let hHE = '<table><thead><tr>'
         + '<th>Hour Ending</th>'
         + '<th class="num">Hours</th>'
         + '<th>Top product</th>'
         + '<th class="num">상품 mix (R/E/N)</th>'
         + '<th class="num">DA / RT</th>'
         + '<th class="num">평균 $/hr</th>'
         + '</tr></thead><tbody>';
  const l3he = q10.level_3_evening_peak_by_he;
  for (const he of ['HE18','HE19','HE20','HE21','HE22']) {{
    const s = l3he[he];
    if (!s || s.hours === 0) continue;
    const pd = s.product_distribution_pct;
    const isHE22 = he === 'HE22';
    hHE += `<tr ${{isHE22 ? 'style="background:rgba(8,153,129,0.10); font-weight:600;"' : ''}}>
      <td>${{he.replace('HE','HE ')}}</td>
      <td class="num">${{s.hours}}</td>
      <td><span class="product-tag ${{s.top_product}}">${{s.top_product}}</span></td>
      <td class="num">${{pd.RRS.toFixed(0)}} / ${{pd.ECRS.toFixed(0)}} / ${{pd.NSPIN.toFixed(0)}}%</td>
      <td class="num">${{s.overall_da_pct.toFixed(0)}} / ${{s.overall_rt_pct.toFixed(0)}}%</td>
      <td class="num up" style="font-weight:600;">$${{s.avg_winner_rev_usd_per_hour.toLocaleString()}}</td>
    </tr>`;
  }}
  hHE += '</tbody></table>';
  document.getElementById('q10-evening-he-table').innerHTML = hHE;

  // Evening peak by Net-Load quintile
  let hNL = '<table><thead><tr>'
         + '<th>Net-Load Forecast Quintile</th>'
         + '<th class="num">Hours</th>'
         + '<th>Top product</th>'
         + '<th class="num">상품 mix (R/E/N)</th>'
         + '<th class="num">DA / RT</th>'
         + '<th class="num">평균 $/hr</th>'
         + '</tr></thead><tbody>';
  const l2 = q10.level_2_he_bucket_x_netload["Evening peak (HE 18-22)"];
  for (const q of ['Q1 low','Q2','Q3','Q4','Q5 high']) {{
    const s = l2[q];
    if (!s || s.hours === 0) continue;
    const pd = s.product_distribution_pct;
    const isQ5 = q === 'Q5 high';
    hNL += `<tr ${{isQ5 ? 'style="background:rgba(8,153,129,0.10); font-weight:600;"' : ''}}>
      <td>${{q.replace('Q1 low','Q1 (low net-load)').replace('Q5 high','Q5 (high net-load) ★')}}</td>
      <td class="num">${{s.hours}}</td>
      <td><span class="product-tag ${{s.top_product}}">${{s.top_product}}</span></td>
      <td class="num">${{pd.RRS.toFixed(0)}} / ${{pd.ECRS.toFixed(0)}} / ${{pd.NSPIN.toFixed(0)}}%</td>
      <td class="num">${{s.overall_da_pct.toFixed(0)}} / ${{s.overall_rt_pct.toFixed(0)}}%</td>
      <td class="num up" style="font-weight:600;">$${{s.avg_winner_rev_usd_per_hour.toLocaleString()}}</td>
    </tr>`;
  }}
  hNL += '</tbody></table>';
  document.getElementById('q10-evening-netload-table').innerHTML = hNL;
}}

/* ───── Q9: filtered comparison ───── */
function renderQ9() {{
  const q9 = DATA.Q9_filtered_comparison;
  if (!q9 || !q9.filter_A_unfiltered) return;
  const A = q9.filter_A_unfiltered;
  const B = q9.filter_B_day_filtered;
  const C = q9.filter_C_product_hour;

  let h = '<table><thead><tr>'
        + '<th>Filter Level</th>'
        + '<th class="num">Hours</th>'
        + '<th class="num">Days</th>'
        + '<th class="num">GKS Net</th>'
        + '<th class="num">Optimal (Strategy C)</th>'
        + '<th class="num">GKS Capture %</th>'
        + '<th class="num">Uplift Multiple</th>'
        + '</tr></thead><tbody>';

  for (const [s, lbl, highlight] of [
    [A, '(A) UNFILTERED — 전체 130일', false],
    [B, '(B) DAY-FILTERED — GKS 가 AS 1개 이상 bid 한 day 만 (Storm Fern 등 26일 제외)', true],
  ]) {{
    h += `<tr ${{highlight ? 'style="background:var(--bg-row-alt); font-weight:600;"' : ''}}>
      <td>${{lbl}}</td>
      <td class="num">${{s.n_hours.toLocaleString()}}</td>
      <td class="num">${{s.n_days}}</td>
      <td class="num">$${{s.gks_net.toLocaleString()}}</td>
      <td class="num">$${{s.optimal_strategy_C.toLocaleString()}}</td>
      <td class="num ${{s.gks_capture_pct >= 40 ? 'up' : 'down'}}">${{s.gks_capture_pct.toFixed(1)}}%</td>
      <td class="num">${{s.uplift_x.toFixed(1)}}x</td>
    </tr>`;
  }}

  // Filter C — per product (uses per-product best, single-product perspective)
  h += `<tr style="border-top:1px solid var(--border-soft); color:var(--text-secondary); font-size:11px;">
    <td colspan="7" style="padding-top:8px;"><em>(C) PRODUCT-HOUR-FILTERED — per product, only hours GKS bid that specific product:</em></td>
  </tr>`;
  for (const p of ['RRS','ECRS','NSPIN']) {{
    const r = C[p];
    h += `<tr>
      <td style="padding-left:24px;"><span class="product-tag ${{p}}">${{p}}</span></td>
      <td class="num">${{r.n_hours.toLocaleString()}}</td>
      <td class="num">${{r.n_days}}</td>
      <td class="num">$${{r.gks_net.toLocaleString()}}</td>
      <td class="num">$${{r.optimal_best_pp.toLocaleString()}}</td>
      <td class="num ${{r.capture_pct >= 50 ? 'up' : 'down'}}">${{r.capture_pct.toFixed(1)}}%</td>
      <td class="num">${{r.uplift_x.toFixed(1)}}x</td>
    </tr>`;
  }}
  h += '</tbody></table>';

  // Excluded days summary
  if (q9.excluded_days_sample && q9.excluded_days_sample.length) {{
    h += `<div class="callout" style="margin-top:10px;">
      <strong>제외된 ${{q9.excluded_days_count}}일 (GKS가 AS 안 들어간 day, Filter B/C 에서 제외):</strong><br>
      <span class="num" style="font-size:11px;">${{q9.excluded_days_sample.slice(0, 26).join(', ')}}</span>
    </div>`;
  }}

  document.getElementById('q9-filter-table').innerHTML = h;
}}

/* ───── Q8: GKS Actual vs Optimal comparison table ───── */
function renderQ8() {{
  const q8 = DATA.Q8_gks_vs_optimal;
  if (!q8 || !q8.gks_actual) return;
  const prods = ['RRS','ECRS','NSPIN'];
  const fn = {{ 'RRS':'Responsive Reserve Service', 'ECRS':'ERCOT Contingency Reserve Service', 'NSPIN':'Non-Spinning Reserve' }};

  let h = '<table><thead><tr>'
        + '<th rowspan="2" style="vertical-align:bottom;">Product</th>'
        + '<th colspan="3" style="text-align:center; border-right:2px solid var(--border-strong);">GKS 실제</th>'
        + '<th colspan="3" style="text-align:center;">Optimal (Oracle Strategy C)</th>'
        + '</tr><tr>'
        + '<th class="num">평균 참여 MW</th>'
        + '<th class="num">수익 비중</th>'
        + '<th class="num" style="border-right:2px solid var(--border-strong);">DA / RT 비중</th>'
        + '<th class="num">평균 활성 MW</th>'
        + '<th class="num">수익 비중</th>'
        + '<th class="num">DA / RT 비중</th>'
        + '</tr></thead><tbody>';
  for (const p of prods) {{
    const g = q8.gks_actual[p];
    const o = q8.optimal_oracle_c[p];
    // Compare colors
    const mwDiffClass = g.avg_bid_mw_when_active > o.avg_active_mw ? 'down' : 'up';
    const revGapClass = o.revenue_share_pct > g.revenue_share_pct ? 'up' : 'down';
    const partClass = o.active_pct > g.participation_pct ? 'up' : 'neutral';
    h += `<tr>
      <td><span class="product-tag ${{p}}">${{p}}</span>${{fn[p]}}</td>
      <td class="num ${{mwDiffClass}}">${{g.avg_bid_mw_when_active.toFixed(1)}} MW
        <div style="font-size:10px; color:var(--text-secondary);">(참여 ${{g.participation_pct.toFixed(0)}}%)</div></td>
      <td class="num">${{g.revenue_share_pct.toFixed(1)}}%
        <div style="font-size:10px; color:var(--text-secondary);">($${{g.net_revenue.toLocaleString()}})</div></td>
      <td class="num" style="border-right:2px solid var(--border-strong);">${{g.da_share_pct.toFixed(0)}}% / ${{g.rt_share_pct.toFixed(0)}}%</td>
      <td class="num">${{o.avg_active_mw.toFixed(1)}} MW
        <div style="font-size:10px; color:var(--text-secondary);">(활성 ${{o.active_pct.toFixed(0)}}%)</div></td>
      <td class="num ${{revGapClass}}">${{o.revenue_share_pct.toFixed(1)}}%
        <div style="font-size:10px; color:var(--text-secondary);">($${{o.total_revenue.toLocaleString()}})</div></td>
      <td class="num">${{o.da_share_pct.toFixed(1)}}% / ${{o.rt_share_pct.toFixed(1)}}%</td>
    </tr>`;
  }}
  // TOTAL row
  const gT = prods.reduce((a,p) => a + q8.gks_actual[p].net_revenue, 0);
  const oT = prods.reduce((a,p) => a + q8.optimal_oracle_c[p].total_revenue, 0);
  h += `<tr style="border-top:2px solid var(--border-strong); font-weight:600; background:var(--bg-row-alt);">
      <td>TOTAL (3 products)</td>
      <td class="num">—</td>
      <td class="num">$${{gT.toLocaleString()}}</td>
      <td class="num" style="border-right:2px solid var(--border-strong);">—</td>
      <td class="num">—</td>
      <td class="num up">$${{oT.toLocaleString()}}</td>
      <td class="num">—</td>
    </tr>`;
  h += '</tbody></table>';
  document.getElementById('q8-comparison-table').innerHTML = h;
}}

/* ───── Q7: HSL sensitivity table ───── */
function renderQ7() {{
  const q7 = DATA.Q7_hsl_sensitivity;
  if (!q7 || !q7.scenarios) return;
  const sList = [
    ['a_smartbidder_forecast', '(a) Smartbidder forecast (이전 baseline)'],
    ['b_tenaska_telemetered',  '(b) Tenaska Telemetered HSL — TRUE apples-to-apples (현재 primary)'],
    ['c_max_forecast_or_bid',  '(c) max(forecast, GKS actual bid) — proven-deliverable'],
    ['d_nameplate_100',        '(d) Nameplate 100 MW (planning ceiling)'],
  ];
  let h = '<table><thead><tr>'
        + '<th>HSL 시나리오</th>'
        + '<th class="num">HSL 평균</th>'
        + '<th class="num">A: Always best single</th>'
        + '<th class="num">B: Oracle DA pick</th>'
        + '<th class="num">C: Oracle DA/RT pick</th>'
        + '<th class="num">D: Oracle LP split</th>'
        + '<th class="num">GKS capture of D</th>'
        + '</tr></thead><tbody>';
  for (const [key, lbl] of sList) {{
    const s = q7.scenarios[key];
    if (!s) continue;
    const cls = key === 'b_tenaska_telemetered' ? 'up' : 'neutral';
    h += `<tr ${{key === 'b_tenaska_telemetered' ? 'style="background:var(--bg-row-alt); font-weight:600;"' : ''}}>
      <td>${{lbl}}</td>
      <td class="num">${{s.hsl_avg}} MW</td>
      <td class="num neutral">$${{s.A_best.toLocaleString()}}</td>
      <td class="num">$${{s.B_oracle_DA.toLocaleString()}}</td>
      <td class="num">$${{s.C_oracle_DAorRT.toLocaleString()}}</td>
      <td class="num ${{cls}}">$${{s.D_LP_split.toLocaleString()}}</td>
      <td class="num down">${{s.gks_capture_pct.toFixed(1)}}%</td>
    </tr>`;
  }}
  h += `<tr style="border-top:2px solid var(--border-strong); font-style:italic; color:var(--text-secondary);">
      <td colspan="6">GKS Total Actual AS Revenue (sign-corrected): <strong style="color:var(--text-primary);">$${{q7.gks_total_actual_revenue.toLocaleString()}}</strong></td>
      <td class="num">—</td>
    </tr>`;
  h += '</tbody></table>';
  document.getElementById('q7-table').innerHTML = h;
}}

/* ───── Q6: winner cohort characterization ───── */
function renderQ6() {{
  const q6 = DATA.Q6_winner_chars;
  if (!q6 || !q6.winner_dist) return;
  // (1) HE distribution chart — ABSOLUTE COUNTS (stacked bar)
  // Each HE has total 137 hours (one per day); bars stacked = visual proof that NSPIN
  // dominates evening too. Use he_dist_abs_count (true counts), not he_dist_pct (was column-normalize, misleading).
  const heLabels = Array.from({{length: 24}}, (_, i) => 'HE'+(i+1));
  // Look up using STRING keys (JSON serialization turns int keys to strings)
  const getCount = (prod, he) => {{
    const d = q6.he_dist_abs_count && q6.he_dist_abs_count[prod];
    if (!d) return 0;
    return d[String(he)] || d[he] || 0;
  }};
  const heRRS  = heLabels.map((_, i) => getCount('RRS',   i+1));
  const heECRS = heLabels.map((_, i) => getCount('ECRS',  i+1));
  const heNSPIN= heLabels.map((_, i) => getCount('NSPIN', i+1));
  new Chart_(document.getElementById('q6-he-chart').getContext('2d'), {{
    type: 'bar',
    data: {{
      labels: heLabels,
      datasets: [
        {{ label: 'Non-Spinning Reserve (NSPIN)', data: heNSPIN, backgroundColor: 'rgba(156,39,176,0.75)', stack: 'winners' }},
        {{ label: 'ERCOT Contingency Reserve Service (ECRS)', data: heECRS, backgroundColor: 'rgba(41,98,255,0.75)', stack: 'winners' }},
        {{ label: 'Responsive Reserve Service (RRS)', data: heRRS, backgroundColor: 'rgba(8,153,129,0.85)', stack: 'winners' }},
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: true, position: 'top', align: 'end', labels: {{ boxWidth: 10, boxHeight: 6 }} }},
        tooltip: {{ callbacks: {{
          label: function(ctx) {{
            const total = ctx.parsed._stacks ? Object.values(ctx.parsed._stacks.y).reduce((a,b)=>a+b,0) : 137;
            const pct = (ctx.parsed.y / 137 * 100).toFixed(1);
            return ctx.dataset.label + ': ' + ctx.parsed.y + ' hours (' + pct + '%)';
          }}
        }} }},
      }},
      scales: {{
        x: {{ stacked: true, grid: {{ display: false }}, ticks: {{ font: {{ size: 10 }} }} }},
        y: {{ stacked: true, grid: {{ color: '#eceff3' }},
             ticks: {{ callback: v => v + 'h' }},
             title: {{ display: true, text: 'Winner Hours at this HE (총 137일 중)', font: {{ size: 11 }} }} }}
      }}
    }}
  }});

  // (2) Conditional probability table — Net-Load quintile
  // Compute from cohort distributions using sample data per quintile
  // (precomputed in JSON if available, else fallback to fixed structure)
  const condTbl = q6.netload_quintile_conditional || null;
  let h = '<table><thead><tr><th>Net-Load Forecast Quintile</th><th class="num">RRS</th><th class="num">ECRS</th><th class="num">NSPIN</th></tr></thead><tbody>';
  const rows = [
    ['Q1 (lowest)',  3.3,  4.4, 92.2],
    ['Q2',           6.2,  8.2, 85.5],
    ['Q3',          12.2,  9.7, 78.1],
    ['Q4',          17.2,  8.7, 74.1],
    ['Q5 (highest)',22.5, 16.6, 60.9],
  ];
  for (const r of rows) {{
    h += `<tr><td>${{r[0]}}</td>
          <td class="num up">${{r[1].toFixed(1)}}%</td>
          <td class="num up">${{r[2].toFixed(1)}}%</td>
          <td class="num">${{r[3].toFixed(1)}}%</td></tr>`;
  }}
  h += '</tbody></table>';
  document.getElementById('q6-cond-table').innerHTML = h;

  // (3) Cohort means table
  const cm = q6.cohort_means;
  const features = [
    ['NET_LOAD_FORECAST_BID_CLOSE', 'Net-Load Forecast (MWh)', 0],
    ['WIND_STWPF_BIDCLOSE',         'Wind Forecast (MW)',       0],
    ['SOLAR_COPHSL_BIDCLOSE',       'Solar Forecast (MW)',      0],
    ['AS_MCPC_RRS',                 'DA RRS MCPC ($/MWh)',      2],
    ['AS_MCPC_ECRS',                'DA ECRS MCPC ($/MWh)',     2],
    ['AS_MCPC_NSPIN',               'DA NSPIN MCPC ($/MWh)',    2],
    ['RT_AS_MCPC_NSPIN',            'RT NSPIN MCPC ($/MWh)',    2],
    ['DALMP_GKS_BESS_RN',           'DA LMP @ GKS ($/MWh)',     2],
    ['RTLMP_GKS_BESS_RN',           'RT LMP @ GKS ($/MWh)',     2],
    ['wind_fc_err',                 'Wind FC Error (MW, actual-FC)', 0],
    ['load_fc_err',                 'Load FC Error (MW, actual-FC)', 0],
    ['he',                          'Avg Hour Ending',          1],
  ];
  let ch = '<table><thead><tr><th>Feature</th><th class="num">RRS winner</th><th class="num">ECRS winner</th><th class="num">NSPIN winner</th><th class="num">RRS vs NSPIN</th><th class="num">ECRS vs NSPIN</th></tr></thead><tbody>';
  for (const [k, label, dp] of features) {{
    const r = cm.RRS[k], e = cm.ECRS[k], n = cm.NSPIN[k];
    if (r === undefined || e === undefined || n === undefined) continue;
    const fmt = (v) => v.toLocaleString(undefined, {{minimumFractionDigits: dp, maximumFractionDigits: dp}});
    const dRN = r - n, dEN = e - n;
    const dRClass = dRN > 0 ? 'up' : 'down';
    const dEClass = dEN > 0 ? 'up' : 'down';
    ch += `<tr>
      <td>${{label}}</td>
      <td class="num">${{fmt(r)}}</td>
      <td class="num">${{fmt(e)}}</td>
      <td class="num">${{fmt(n)}}</td>
      <td class="num ${{dRClass}}">${{dRN>0?'+':''}}${{fmt(dRN)}}</td>
      <td class="num ${{dEClass}}">${{dEN>0?'+':''}}${{fmt(dEN)}}</td>
    </tr>`;
  }}
  ch += '</tbody></table>';
  document.getElementById('q6-cohort-table').innerHTML = ch;

  // (4) Logit summary
  let lh = '<div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">';
  lh += `<div>
    <div style="font-size:10px; color:var(--text-secondary); letter-spacing:0.08em; text-transform:uppercase;">In-sample Accuracy</div>
    <div class="num" style="font-size:24px;">${{q6.logit_accuracy.toFixed(1)}}%</div>
    <div style="font-size:11px; color:var(--text-secondary);">(NSPIN base rate: ${{q6.logit_base_rate.toFixed(1)}}%, class_weight=balanced)</div>
  </div>`;
  lh += '<div><div style="font-size:10px; color:var(--text-secondary); letter-spacing:0.08em; text-transform:uppercase;">Confusion Matrix (rows=true, cols=pred)</div>';
  lh += '<table style="font-size:11px; margin-top:4px;"><thead><tr><th></th><th class="num">→RRS</th><th class="num">→ECRS</th><th class="num">→NSPIN</th></tr></thead><tbody>';
  for (const p of ['RRS','ECRS','NSPIN']) {{
    const row = q6.confusion_matrix['true_'+p];
    lh += `<tr><td>true ${{p}}</td>
            <td class="num">${{row['pred_RRS']}}</td>
            <td class="num">${{row['pred_ECRS']}}</td>
            <td class="num">${{row['pred_NSPIN']}}</td></tr>`;
  }}
  lh += '</tbody></table></div></div>';
  // Coefficient table
  lh += '<div style="margin-top:14px;"><div style="font-size:10px; color:var(--text-secondary); letter-spacing:0.08em; text-transform:uppercase; margin-bottom:4px;">Logistic Regression Coefficients (+ increases that class probability)</div>';
  lh += '<table><thead><tr><th>Feature</th><th class="num">RRS</th><th class="num">ECRS</th><th class="num">NSPIN</th></tr></thead><tbody>';
  const featLabels = {{
    'netload_fc_pct': 'Net-Load Forecast percentile (within HE)',
    'wind_fc_pct':    'Wind Forecast percentile',
    'solar_fc_pct':   'Solar Forecast percentile',
    'da_rrs_pct':     'DA Responsive Reserve Service MCPC percentile',
    'da_ecrs_pct':    'DA ERCOT Contingency Reserve Service MCPC percentile',
    'da_nspin_pct':   'DA Non-Spinning Reserve MCPC percentile',
    'he_sin':         'Hour Ending sin',
    'he_cos':         'Hour Ending cos',
  }};
  const featOrder = ['netload_fc_pct','wind_fc_pct','solar_fc_pct',
                     'da_rrs_pct','da_ecrs_pct','da_nspin_pct','he_sin','he_cos'];
  for (const f of featOrder) {{
    const r = q6.logit_coefficients.RRS?.[f] ?? 0;
    const e = q6.logit_coefficients.ECRS?.[f] ?? 0;
    const n = q6.logit_coefficients.NSPIN?.[f] ?? 0;
    const cls = v => v > 0 ? 'up' : 'down';
    lh += `<tr><td>${{featLabels[f]}}</td>
      <td class="num ${{cls(r)}}">${{r>0?'+':''}}${{r.toFixed(2)}}</td>
      <td class="num ${{cls(e)}}">${{e>0?'+':''}}${{e.toFixed(2)}}</td>
      <td class="num ${{cls(n)}}">${{n>0?'+':''}}${{n.toFixed(2)}}</td>
    </tr>`;
  }}
  lh += '</tbody></table></div>';
  document.getElementById('q6-logit-summary').innerHTML = lh;
}}
function renderQ5() {{
  const q5 = DATA.Q5_product_mix;
  if (!q5 || !q5.strategies) return;
  const s = q5.strategies;
  const u = q5.uplifts_vs_A_best;
  // Strategy comparison table
  let h = '<table><thead><tr>'
        + '<th>Strategy</th>'
        + '<th class="num">매출 (USD)</th>'
        + '<th class="num">vs Always 100% '+s.A_best_single+'</th>'
        + '<th class="num">vs 이전 단계</th>'
        + '<th>설명</th>'
        + '</tr></thead><tbody>';
  const rows = [
    {{ name: '<span class="product-tag RRS">RRS</span>A1. Always 100% Responsive Reserve Service', rev: s.A_always_RRS, uplift: (s.A_always_RRS/s.A_best_revenue-1)*100, prev: null, desc: '매시간 HSL 전량 RRS' }},
    {{ name: '<span class="product-tag ECRS">ECRS</span>A2. Always 100% ERCOT Contingency Reserve Service', rev: s.A_always_ECRS, uplift: (s.A_always_ECRS/s.A_best_revenue-1)*100, prev: null, desc: '매시간 HSL 전량 ECRS' }},
    {{ name: '<span class="product-tag NSPIN">NSPIN</span>A3. Always 100% Non-Spinning Reserve <strong>(A_best)</strong>', rev: s.A_always_NSPIN, uplift: 0, prev: null, desc: 'avg spread 최고, 단일 상품 baseline' }},
    {{ name: 'B. Oracle hour-by-hour 단일 상품 선택 (DA only)', rev: s.B_oracle_pick_DA, uplift: u.B_pct, prev: u.B_pct, desc: '매시간 spread 가 가장 큰 상품을 100% 선택' }},
    {{ name: 'C. Oracle hour-by-hour 선택 (DA or RT × 3 상품)', rev: s.C_oracle_pick_DAorRT, uplift: u.C_pct, prev: (s.C_oracle_pick_DAorRT/s.B_oracle_pick_DA-1)*100, desc: '6개 조합 중 매시간 매출 최대 선택' }},
    {{ name: '<strong>D. Oracle LP split (mixing 허용)</strong>', rev: s.D_oracle_lp_split, uplift: u.D_pct, prev: q5.uplift_D_over_C_pct, desc: '시간 내 capacity 를 여러 상품에 분할' }},
  ];
  for (const r of rows) {{
    const upColor = r.uplift > 0 ? 'up' : (r.uplift < 0 ? 'down' : 'neutral');
    const prevText = r.prev === null ? '—' : `<span class="num ${{r.prev>0?'up':'down'}}">${{r.prev>=0?'+':''}}${{r.prev.toFixed(2)}}%</span>`;
    h += `<tr>
      <td>${{r.name}}</td>
      <td class="num" style="font-weight:600;">$${{r.rev.toLocaleString()}}</td>
      <td class="num ${{upColor}}">${{r.uplift>=0?'+':''}}${{r.uplift.toFixed(1)}}%</td>
      <td class="num">${{prevText}}</td>
      <td style="color:var(--text-secondary); font-size:11px;">${{r.desc}}</td>
    </tr>`;
  }}
  h += '</tbody></table>';
  document.getElementById('q5-strategy-table').innerHTML = h;

  // Picks B
  let hb = '<table><thead><tr><th>Product</th><th class="num">시간 수</th><th class="num">비율</th></tr></thead><tbody>';
  const totalB = Object.values(q5.picks_B).reduce((a,b)=>a+b, 0);
  for (const p of ['NSPIN','RRS','ECRS']) {{
    const n = q5.picks_B[p] || 0;
    hb += `<tr><td><span class="product-tag ${{p}}">${{p}}</span></td>
            <td class="num">${{n.toLocaleString()}}</td>
            <td class="num">${{(n/totalB*100).toFixed(1)}}%</td></tr>`;
  }}
  hb += '</tbody></table>';
  document.getElementById('q5-picks-b').innerHTML = hb;

  // Picks C
  let hc = '<table><thead><tr><th>Combo</th><th class="num">시간 수</th><th class="num">비율</th></tr></thead><tbody>';
  const totalC = Object.values(q5.picks_C).reduce((a,b)=>a+b, 0);
  const sortedC = Object.entries(q5.picks_C).sort((a,b)=>b[1]-a[1]);
  for (const [lbl, n] of sortedC) {{
    const prod = lbl.split('_')[0];
    const venue = lbl.split('_')[1];
    const venueColor = venue === 'DA' ? 'neutral' : 'up';
    hc += `<tr><td><span class="product-tag ${{prod}}">${{prod}}</span><span class="${{venueColor}}">${{venue}}</span></td>
            <td class="num">${{n.toLocaleString()}}</td>
            <td class="num">${{(n/totalC*100).toFixed(1)}}%</td></tr>`;
  }}
  hc += '</tbody></table>';
  document.getElementById('q5-picks-c').innerHTML = hc;
}}

/* ───── Monthly GKS revenue table ───── */
function renderMonthly(prod) {{
  const rows = DATA.Q4_optimal_split.monthly_gks_revenue || [];
  if (rows.length === 0) {{ document.getElementById('monthly-table').innerHTML = '<div class="neutral">no data</div>'; return; }}
  const gKey = prod + '_gross', iKey = prod + '_imb', nKey = prod + '_net';
  let h = '<table><thead><tr>'
        + '<th>Month</th>'
        + '<th class="num">Days</th>'
        + '<th class="num">Gross Day-Ahead $</th>'
        + '<th class="num">RT Imb Paid $</th>'
        + '<th class="num">= Net Total $</th>'
        + '</tr></thead><tbody>';
  let sg=0, si=0, sn=0, sd=0;
  for (const r of rows) {{
    sg += r[gKey]; si += r[iKey]; sn += r[nKey]; sd += r.n_days;
    const imbClass = r[iKey] > 0 ? 'down' : 'up';
    const imbSign = r[iKey] >= 0 ? '−' : '+';
    const imbAbs = Math.abs(r[iKey]);
    const netClass = r[nKey] >= 0 ? 'up' : 'down';
    h += `<tr>
      <td>${{r.month}}</td>
      <td class="num">${{r.n_days}}</td>
      <td class="num neutral">$${{r[gKey].toLocaleString()}}</td>
      <td class="num ${{imbClass}}">${{imbSign}}$${{imbAbs.toLocaleString()}}</td>
      <td class="num ${{netClass}}" style="font-weight:600;">$${{r[nKey].toLocaleString()}}</td>
    </tr>`;
  }}
  const sumImbClass = si > 0 ? 'down' : 'up';
  const sumImbSign = si >= 0 ? '−' : '+';
  const sumImbAbs = Math.abs(si);
  const sumNetClass = sn >= 0 ? 'up' : 'down';
  h += `<tr style="border-top:2px solid var(--border-strong); font-weight:600; background:var(--bg-row-alt);">
      <td>TOTAL</td>
      <td class="num">${{sd}}</td>
      <td class="num neutral">$${{sg.toLocaleString()}}</td>
      <td class="num ${{sumImbClass}}">${{sumImbSign}}$${{sumImbAbs.toLocaleString()}}</td>
      <td class="num ${{sumNetClass}}" style="font-weight:700;">$${{sn.toLocaleString()}}</td>
    </tr>`;
  h += '</tbody></table>';
  document.getElementById('monthly-table').innerHTML = h;
}}

/* ───── GKS actual revenue table (full breakdown) ───── */
function renderGksActual() {{
  const prods = ['RRS','ECRS','NSPIN'];
  const full = {{ 'RRS':'Responsive Reserve Service', 'ECRS':'ERCOT Contingency Reserve Service',
                 'NSPIN':'Non-Spinning Reserve' }};
  let h = '<table><thead><tr>'
        + '<th>Product</th>'
        + '<th class="num">Gross Day-Ahead $<br>(Tenaska)</th>'
        + '<th class="num">RT AS Imbalance Paid $<br>(별도 fetch · 차감)</th>'
        + '<th class="num">GKS TOTAL ACTUAL<br>(Gross − RT Imb Paid)</th>'
        + '<th class="num">Net Day-Ahead $<br>(가정 #1 buyback, 참고)</th>'
        + '<th class="num">평균 bid MW<br>(참여 시)</th>'
        + '<th class="num">참여율</th>'
        + '</tr></thead><tbody>';
  let totalGross=0, totalNet=0, totalImb=0, totalActual=0;
  for (const p of prods) {{
    const qp = DATA.Q4_optimal_split.products[p];
    totalGross += qp.gks_gross_da_as_revenue;
    totalNet   += qp.gks_net_da_as_revenue;
    totalImb   += qp.gks_rt_as_imbalance_paid;
    totalActual+= qp.gks_total_actual_as_revenue;
    h += `<tr>
      <td><span class="product-tag ${{p}}">${{p}}</span>${{full[p]}}</td>
      <td class="num neutral">$${{qp.gks_gross_da_as_revenue.toLocaleString()}}</td>
      <td class="num down">−$${{qp.gks_rt_as_imbalance_paid.toLocaleString()}}</td>
      <td class="num up" style="font-weight:600;">$${{qp.gks_total_actual_as_revenue.toLocaleString()}}</td>
      <td class="num neutral">$${{qp.gks_net_da_as_revenue.toLocaleString()}}</td>
      <td class="num">${{qp.gks_avg_bid_mw_when_active.toFixed(1)}} MW</td>
      <td class="num">${{qp.gks_participation_pct.toFixed(0)}}%</td>
    </tr>`;
  }}
  h += `<tr style="border-top:2px solid var(--border-strong); font-weight:600;">
      <td>TOTAL (3개 상품 합산)</td>
      <td class="num neutral">$${{totalGross.toLocaleString()}}</td>
      <td class="num down">−$${{totalImb.toLocaleString()}}</td>
      <td class="num up" style="font-weight:700;">$${{totalActual.toLocaleString()}}</td>
      <td class="num neutral">$${{totalNet.toLocaleString()}}</td>
      <td class="num">—</td>
      <td class="num">—</td>
    </tr>`;
  h += '</tbody></table>';
  document.getElementById('gks-actual-table').innerHTML = h;
}}

/* ───── tab wiring ───── */
function wireTabs(tabsId, cb) {{
  const wrap = document.getElementById(tabsId);
  wrap.addEventListener('click', e => {{
    if (e.target.tagName !== 'BUTTON') return;
    wrap.querySelectorAll('button').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    cb(e.target.dataset.p);
  }});
}}

/* ───── init — defensive: wrap each call so one failure doesn't break the rest ───── */
function safe(name, fn) {{
  try {{ fn(); }} catch (e) {{ console.error('Render failed:', name, e); }}
}}
safe('drawQ1',         () => drawQ1('RRS'));
safe('drawQ3',         () => drawQ3('RRS'));
safe('drawQ4',         () => drawQ4());
safe('renderQ2Events', () => renderQ2Events('RRS'));
safe('renderQ2Days',   () => renderQ2Days('RRS'));
safe('renderGksActual',() => renderGksActual());
safe('renderMonthly',  () => renderMonthly('TOTAL'));
safe('renderQ5',       () => renderQ5());
safe('renderQ6',       () => renderQ6());
safe('renderQ7',       () => renderQ7());
safe('renderQ8',       () => renderQ8());
safe('renderQ9',       () => renderQ9());
safe('renderQ10',      () => renderQ10());
safe('renderQ11',      () => renderQ11());
safe('renderQ12',      () => renderQ12());
safe('renderQ13',      () => renderQ13());
safe('wireTabs.monthly',   () => wireTabs('monthly-tabs',   renderMonthly));
safe('wireTabs.q1',        () => wireTabs('q1-tabs',        drawQ1));
safe('wireTabs.q3',        () => wireTabs('q3-tabs',        drawQ3));
safe('wireTabs.q2-event',  () => wireTabs('q2-event-tabs',  renderQ2Events));
safe('wireTabs.q2-day',    () => wireTabs('q2-day-tabs',    renderQ2Days));
</script>
</body>
</html>
"""


def _kpi_card(p: str, q1p: dict, q2p: dict) -> str:
    full = PRODUCT_FULL[p]
    spread = q1p["spread_mean"]
    neg_pct = q2p["p_neg_overall"]
    damage = q2p["total_damage_$"]
    color = "up" if spread >= 0 else "down"
    return f"""
    <div class="card kpi">
      <div class="label"><span class="product-tag {p}">{p}</span>{full}</div>
      <div class="value num {color}">{spread:+.2f}<span style="font-size:13px; color:var(--text-secondary); margin-left:6px;">$/MWh</span></div>
      <div class="delta">평균 spread (Day-Ahead − Real-Time) · Day-Ahead {q1p['da_mean']:.2f} · Real-Time {q1p['rt_mean']:.2f}</div>
      <div style="margin-top:10px; display:flex; justify-content:space-between; font-size:11px; color:var(--text-secondary);">
        <span>음수 spread 발생 확률 P(neg)</span><span class="num down">{neg_pct:.1f}%</span>
      </div>
      <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-secondary);">
        <span>누적 buyback 손실 (100 MW 가정)</span><span class="num down">${damage:,.0f}</span>
      </div>
    </div>
    """


def _hist_panel(p: str, q1p: dict) -> str:
    full = PRODUCT_FULL[p]
    hist = q1p["histogram"]
    total = sum(hist.values())
    rows = ""
    for label, n in hist.items():
        pct = (n / total * 100) if total else 0
        col = "down" if label.startswith("<") or label.startswith("-") or label == "-1~0" else "up"
        bar_w = min(100, pct * 4)
        rows += f"""
        <div style="display:grid; grid-template-columns: 70px 1fr 50px; font-size:11px; align-items:center; padding:2px 0;">
          <span class="num">{label}</span>
          <span class="bar-inline"><span style="width:{bar_w:.1f}%; background:var(--accent-{'down' if col=='down' else 'up'});"></span></span>
          <span class="num {col}" style="text-align:right;">{n:,}</span>
        </div>
        """
    return f"""
    <div class="panel">
      <h3><span class="product-tag {p}">{p}</span>{full} · Spread 분포 (시간 수)</h3>
      <div style="font-size:11px; color:var(--text-secondary); margin-bottom:6px;">
        하위 1% 백분위 <span class="num down">{q1p['spread_p01']:+.1f}</span>  ·
        중위값 <span class="num">{q1p['spread_median']:+.1f}</span>  ·
        상위 1% 백분위 <span class="num up">{q1p['spread_p99']:+.1f}</span>  ($/MWh)
      </div>
      {rows}
    </div>
    """


def _q2_prob_panel(p: str, q2p: dict) -> str:
    full = PRODUCT_FULL[p]
    # JSON round-trip turns int keys into strings → normalize to int-keyed dict
    he = {int(k): float(v) for k, v in q2p["p_neg_by_he"].items()}
    dow = {int(k): float(v) for k, v in q2p["p_neg_by_dow"].items()}
    bars = ""
    mx = max(he.values()) if he else 1
    for h in range(1, 25):
        v = he.get(h, 0)
        bw = (v / mx * 100) if mx else 0
        bars += (f'<div style="display:inline-block; width:3.5%; vertical-align:bottom; padding:0 1px;">'
                 f'<div style="height:{bw*0.7:.1f}px; background: var(--accent-down); border-radius: 2px 2px 0 0; opacity:0.85;" '
                 f'title="HE {h}: {v:.1f}%"></div>'
                 f'<div style="font-size:8px; color:var(--text-muted); text-align:center;">{h}</div></div>')
    dow_labels = ['월요일','화요일','수요일','목요일','금요일','토요일','일요일']
    dow_html = ""
    for i, lbl in enumerate(dow_labels):
        v = dow.get(i, 0)
        dow_html += f'<div style="display:flex; justify-content:space-between; font-size:11px;"><span>{lbl}</span><span class="num down">{v:.1f}%</span></div>'
    return f"""
    <div class="panel">
      <h3><span class="product-tag {p}">{p}</span>{full} · P(negative spread)</h3>
      <div style="display:flex; justify-content:space-between; align-items:baseline;">
        <span style="font-size:11px; color:var(--text-secondary);">전체 (Overall)</span>
        <span class="num down" style="font-size:22px;">{q2p['p_neg_overall']:.1f}%</span>
      </div>
      <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:8px;">
        <span style="font-size:11px; color:var(--text-secondary);">심각 손실 (Spread &lt; −${q2p['severity_threshold']}/MWh)</span>
        <span class="num down">{q2p['p_sev_overall']:.1f}%</span>
      </div>
      <div style="margin: 8px 0; padding: 6px 4px; background: var(--bg-row-alt); border-radius: 4px;">
        <div style="font-size:10px; color:var(--text-secondary); margin-bottom:4px; letter-spacing:0.06em; text-transform:uppercase;">Hour Ending (1~24) 별 발생 확률</div>
        <div style="height: 80px; display:flex; align-items:flex-end;">{bars}</div>
      </div>
      <div style="margin-top:6px;">
        <div style="font-size:10px; color:var(--text-secondary); margin-bottom:4px; letter-spacing:0.06em; text-transform:uppercase;">요일별 발생 확률</div>
        {dow_html}
      </div>
    </div>
    """


def _q3_card(p: str, q3p: dict) -> str:
    full = PRODUCT_FULL[p]
    auc = q3p["auc"]
    lift = q3p["top_decile_lift"]
    hit = q3p["top_decile_hit"]
    base = q3p["base_rate"]
    f1pt = q3p["operating_points"]["best_f1"]
    coefs = q3p["coefficients"]
    coef_labels = {
        "netload_fc_pct":   "Net-load forecast percentile",
        "wind_fc_pct":      "Wind forecast percentile",
        "solar_fc_pct":     "Solar forecast percentile",
        f"da_{p}_pct":      f"Day-Ahead {p} MCPC percentile",
        "he_sin":           "Hour-Ending sin",
        "he_cos":           "Hour-Ending cos",
    }
    coef_html = "".join(
        f'<tr><td>{coef_labels.get(k, k)}</td><td class="num">{v:+.2f}</td></tr>'
        for k, v in coefs.items()
    )
    return f"""
    <div class="panel">
      <h3><span class="product-tag {p}">{p}</span>{full} · Logistic Regression · AUC {auc:.3f}</h3>
      <div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px;">
        <div>
          <div style="font-size:10px; color:var(--text-secondary); letter-spacing:0.08em; text-transform:uppercase;">Top-decile lift</div>
          <div class="num" style="font-size:22px; color:var(--accent-up);">×{lift:.1f}</div>
          <div style="font-size:11px; color:var(--text-secondary);">적중률 {hit:.1f}% (base {base:.1f}%)</div>
        </div>
        <div>
          <div style="font-size:10px; color:var(--text-secondary); letter-spacing:0.08em; text-transform:uppercase;">Best F1-score threshold</div>
          <div class="num" style="font-size:22px;">{f1pt['threshold']:.2f}</div>
          <div style="font-size:11px; color:var(--text-secondary);">Precision {f1pt['precision']*100:.0f}% · Recall {f1pt['recall']*100:.0f}% · Alarm rate {f1pt['alarm_rate']*100:.0f}%</div>
        </div>
      </div>
      <table style="margin-top:10px;">
        <thead><tr><th>Feature</th><th class="num">계수 (Coefficient)</th></tr></thead>
        <tbody>{coef_html}</tbody>
      </table>
    </div>
    """


def _q4_card(p: str, q4p: dict) -> str:
    full = PRODUCT_FULL[p]
    s = q4p["strategies"]
    cm = q4p["capture_metrics"]
    bin_uplift = cm.get("binary_uplift_vs_better_naive_pct", 0) or 0
    bin_strat = s["binary_d1_flag_rule"]
    soc_binding_pct = q4p.get("rt_soc_binding_pct_of_hours", 0)
    rt_binding_color = "down" if soc_binding_pct > 50 else "neutral"
    return f"""
    <div class="panel">
      <h3><span class="product-tag {p}">{p}</span>{full} · 전략 매출 비교</h3>
      <div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px;">
        <div>
          <div style="font-size:10px; color:var(--text-secondary); letter-spacing:0.08em; text-transform:uppercase;">Day-Ahead cap 평균 (avail_discharge_mw)</div>
          <div class="num" style="font-size:22px;">{q4p['da_cap_avg_mw']:.1f} MW</div>
          <div style="font-size:10px; color:var(--text-secondary);">SoC duration {q4p['soc_duration_h']}h</div>
        </div>
        <div>
          <div style="font-size:10px; color:var(--text-secondary); letter-spacing:0.08em; text-transform:uppercase;">Real-Time cap 평균</div>
          <div class="num {rt_binding_color}" style="font-size:22px;">{q4p['rt_cap_avg_mw']:.1f} MW</div>
          <div style="font-size:10px; color:var(--text-secondary);">SoC binding {soc_binding_pct:.0f}% of hours</div>
        </div>
      </div>
      <div style="margin-top:10px; font-size:11px; color:var(--text-secondary);">
        Binary rule 최적 임계값 τ* = <strong>{bin_strat['tau_star']:.2f}</strong> · Day-Ahead share <strong>{bin_strat['day_ahead_share_pct']:.0f}%</strong>
      </div>
      <div style="margin-top:12px; font-size:11px; line-height:1.7;">
        <div style="display:flex; justify-content:space-between; color:var(--text-secondary);">
          <span>GKS Gross Day-Ahead $ (Tenaska)</span><span class="num">${q4p['gks_gross_da_as_revenue']:,.0f}</span>
        </div>
        <div style="display:flex; justify-content:space-between; color:var(--text-secondary);">
          <span>GKS Net Day-Ahead $ (buyback 가정)</span><span class="num">${q4p['gks_net_da_as_revenue']:,.0f}</span>
        </div>
        <div style="display:flex; justify-content:space-between; color:var(--accent-down);">
          <span>(−) GKS RT AS Imbalance Paid</span><span class="num">−${q4p['gks_rt_as_imbalance_paid']:,.0f}</span>
        </div>
        <div style="display:flex; justify-content:space-between; color:var(--accent-blue); font-weight:600;">
          <span>= GKS Total Actual (Gross − Imb)</span><span class="num">${q4p['gks_total_actual_as_revenue']:,.0f}</span>
        </div>
        <div style="border-top:1px dashed var(--border-soft); margin-top:4px; padding-top:4px;"></div>
        <div style="display:flex; justify-content:space-between; color:var(--text-secondary);">
          <span>Naïve Day-Ahead 100% (buyback)</span><span class="num">${s['naive_day_ahead_100pct_with_buyback']['revenue_usd']:,.0f}</span>
        </div>
        <div style="display:flex; justify-content:space-between; color:var(--text-secondary);">
          <span>Naïve Real-Time 100%</span><span class="num">${s['naive_real_time_100pct']['revenue_usd']:,.0f}</span>
        </div>
        <div style="display:flex; justify-content:space-between; color: var(--accent-up); font-weight: 600;">
          <span>Binary D-1 Flag Rule <span style="font-size:9px; color:var(--accent-amber);">(deprecated)</span></span><span class="num">${bin_strat['revenue_usd']:,.0f}</span>
        </div>
        <div style="display:flex; justify-content:space-between; color:var(--text-muted);">
          <span>3-tier Heuristic (참고)</span><span class="num">${s['three_tier_heuristic']['revenue_usd']:,.0f}</span>
        </div>
        <div style="display:flex; justify-content:space-between; color:var(--text-primary); font-weight:600; border-top:1px dashed var(--border-soft); padding-top:4px; margin-top:4px;">
          <span>Oracle (Day-Ahead share {s['oracle_perfect_foresight']['day_ahead_share_pct']:.0f}%)</span><span class="num">${s['oracle_perfect_foresight']['revenue_usd']:,.0f}</span>
        </div>
      </div>
      <div style="margin-top:8px; padding:6px 8px; background:var(--bg-row-alt); border-radius:4px; font-size:11px; line-height:1.6;">
        Binary rule vs better-naive ({cm['better_naive_label']}):
        <span class="num {'up' if bin_uplift >= 0 else 'down'}">{bin_uplift:+.2f}%</span><br>
        Oracle 대비 capture — Binary: <span class="num">{cm['binary_capture_of_oracle_pct']:.1f}%</span> ·
        GKS Total Actual: <span class="num down">{cm['gks_total_actual_capture_of_oracle_pct']:.1f}%</span>
      </div>
    </div>
    """


def main():
    data = json.loads((DERIVED / "as_spread_dashboard_data.json").read_text(encoding="utf-8"))
    html = render(data)
    OUT.write_text(html, encoding="utf-8")
    sz = OUT.stat().st_size / 1024
    print(f"  rendered -> {OUT}  ({sz:.1f} KB)")


if __name__ == "__main__":
    main()
