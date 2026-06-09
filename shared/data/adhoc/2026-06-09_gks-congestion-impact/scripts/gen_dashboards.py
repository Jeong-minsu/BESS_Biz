#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GKS 혼잡→DART 대시보드 생성기: hub(index) + constraint별(10 full) + slim 카드(4).
datapack_*.json + unified_map_coords.json (../derived/) → reports/ad-hoc/gks-congestion/ HTML.
한글 라벨 + DART(숏/롱) 프레이밍. self-contained (Chart.js + Plotly CDN). 다크 테마."""
import json, os, glob, html

ROOT = r"C:\Users\00904\ERCOT Projects\BESS_Biz"
DER  = os.path.join(ROOT, r"shared\data\adhoc\2026-06-09_gks-congestion-impact\derived")
OUT  = os.path.join(ROOT, r"reports\ad-hoc\gks-congestion")
os.makedirs(OUT, exist_ok=True)

CSS = """
:root{--bg-base:#0d1117;--bg-panel:#131722;--bg-panel-2:#1c2030;--bg-row-alt:#161b27;--border-soft:#2a2e39;
--border-strong:#363a45;--text-primary:#d1d4dc;--text-secondary:#787b86;--text-muted:#5d606b;--accent-up:#26a69a;
--accent-down:#ef5350;--accent-blue:#2962ff;--accent-amber:#ff9800;--accent-purple:#9c27b0;--grid-line:#1e222d;
--short:#ff9800;--long:#2962ff;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg-base);color:var(--text-primary);font-family:'Inter',-apple-system,system-ui,'Pretendard','Noto Sans KR',sans-serif;font-size:13px;line-height:1.5;padding:24px;min-height:100vh;}
.dashboard{max-width:1400px;margin:0 auto;display:flex;flex-direction:column;gap:12px;}
.header{display:flex;justify-content:space-between;align-items:flex-end;padding-bottom:16px;border-bottom:1px solid var(--border-soft);margin-bottom:8px;}
.header h1{font-size:21px;font-weight:600;letter-spacing:-0.01em;}
.header .subtitle{color:var(--text-secondary);font-size:12px;margin-top:4px;}
.back{color:var(--accent-blue);text-decoration:none;font-size:12px;}
.back:hover{text-decoration:underline;}
.status-pill{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border:1px solid var(--border-soft);border-radius:4px;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:var(--text-secondary);background:var(--bg-panel);}
.status-pill::before{content:'';width:6px;height:6px;border-radius:50%;background:var(--accent-up);}
.panel{background:var(--bg-panel);border:1px solid var(--border-soft);border-radius:6px;overflow:hidden;}
.panel-header{padding:11px 16px;border-bottom:1px solid var(--border-soft);display:flex;justify-content:space-between;align-items:center;}
.panel-title{font-size:11px;text-transform:uppercase;letter-spacing:0.06em;color:var(--text-secondary);font-weight:500;}
.panel-sub{font-size:10px;color:var(--text-muted);}
.panel-body{padding:16px;}
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;}
.kpi{background:var(--bg-panel);border:1px solid var(--border-soft);border-radius:6px;padding:14px 16px;}
.kpi-label{font-size:10px;text-transform:uppercase;letter-spacing:0.07em;color:var(--text-secondary);margin-bottom:7px;}
.kpi-value{font-family:'JetBrains Mono','SF Mono',monospace;font-size:22px;font-weight:500;font-variant-numeric:tabular-nums;line-height:1.1;}
.kpi-change{font-family:'JetBrains Mono',monospace;font-size:11px;margin-top:5px;}
.up{color:var(--accent-up);}.down{color:var(--accent-down);}.neutral{color:var(--text-secondary);}.blue{color:var(--accent-blue);}.amber{color:var(--accent-amber);}
.cshort{color:var(--short);}.clong{color:var(--long);}
.two-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}@media(max-width:1000px){.two-grid{grid-template-columns:1fr;}}
.chart-wrap{height:300px;padding:12px;}
table{width:100%;border-collapse:collapse;font-size:12.5px;}
thead th{text-align:left;padding:9px 12px;font-size:10px;letter-spacing:0.03em;color:var(--text-secondary);font-weight:500;border-bottom:1px solid var(--border-soft);}
thead th.num{text-align:right;}
tbody td{padding:8px 12px;border-bottom:1px solid var(--grid-line);}
tbody td.num{text-align:right;font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums;}
tbody tr:nth-child(even){background:var(--bg-row-alt);}
tbody tr:hover{background:var(--bg-panel-2);}
.tag{display:inline-block;font-size:9px;padding:1px 6px;border-radius:3px;font-weight:600;letter-spacing:0.03em;}
.t-live{background:rgba(38,166,154,0.16);color:#4dd0c4;border:1px solid rgba(38,166,154,0.4);}
.t-retired{background:rgba(255,152,0,0.14);color:#ffb74d;border:1px solid rgba(255,152,0,0.38);}
.t-noise{background:rgba(239,83,80,0.14);color:#ef9a9a;border:1px solid rgba(239,83,80,0.4);}
.t-short{background:rgba(255,152,0,0.18);color:#ffb74d;border:1px solid rgba(255,152,0,0.45);}
.t-long{background:rgba(41,98,255,0.18);color:#7aa0ff;border:1px solid rgba(41,98,255,0.45);}
.t-mixed{background:rgba(120,123,134,0.18);color:#a8abb4;border:1px solid rgba(120,123,134,0.4);}
.t-pos{background:rgba(38,166,154,0.13);color:#4dd0c4;border:1px solid rgba(38,166,154,0.35);}
.t-neg{background:rgba(239,83,80,0.13);color:#ef9a9a;border:1px solid rgba(239,83,80,0.35);}
.v-conf{color:var(--accent-up);font-weight:600;}.v-hyp{color:var(--accent-amber);font-weight:600;}
.v-ins{color:var(--text-muted);font-weight:600;}.v-con{color:var(--accent-down);font-weight:600;}.v-qual{color:var(--accent-blue);font-weight:600;}
.rot{border-radius:6px;padding:13px 16px;font-size:12.5px;line-height:1.6;background:rgba(41,98,255,0.07);border:1px solid rgba(41,98,255,0.3);}
.rot b{color:var(--text-primary);}
.rot.dart{background:rgba(156,39,176,0.08);border-color:rgba(156,39,176,0.32);}
.notes{padding:2px 4px;}
.notes li{margin:6px 0;list-style:none;position:relative;padding-left:15px;color:var(--text-secondary);font-size:12px;line-height:1.5;}
.notes li::before{content:'▸';position:absolute;left:0;color:var(--accent-blue);}
.mono{font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums;}
.mh-grid{display:grid;gap:1px;}
.mh-c{font-family:'JetBrains Mono',monospace;font-size:8px;display:flex;align-items:center;justify-content:center;aspect-ratio:1;border-radius:1px;color:rgba(255,255,255,0.82);min-height:14px;}
.mh-h{font-size:8px;color:var(--text-muted);display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace;}
.mh-m{font-size:8.5px;color:var(--text-secondary);display:flex;align-items:center;justify-content:flex-end;padding-right:4px;font-family:'JetBrains Mono',monospace;}
.lgnd{font-size:10px;color:var(--text-secondary);display:flex;gap:14px;align-items:center;padding:0 4px 8px;}
.lgnd i{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:4px;vertical-align:-1px;}
.card{display:block;background:var(--bg-panel);border:1px solid var(--border-soft);border-radius:6px;padding:14px 16px;text-decoration:none;color:inherit;transition:border-color .15s;}
a.card:hover{border-color:var(--accent-blue);}
.card .c-top{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;}
.card .c-id{font-weight:600;font-size:14px;color:var(--text-primary);}
.card .c-el{font-size:11px;color:var(--text-secondary);}
.card .c-val{font-family:'JetBrains Mono',monospace;font-size:17px;font-variant-numeric:tabular-nums;}
.card .c-meta{font-size:11px;color:var(--text-muted);margin-top:6px;line-height:1.45;}
.caveat{background:rgba(255,152,0,0.08);border:1px solid rgba(255,152,0,0.35);border-radius:6px;padding:11px 14px;font-size:11.5px;color:var(--text-secondary);line-height:1.5;}
.caveat b{color:var(--accent-amber);}
"""

_HEAD_PRE = ('<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">'
  '<meta name="viewport" content="width=device-width,initial-scale=1.0"><title>')
_HEAD_MID = ('</title><link rel="preconnect" href="https://fonts.googleapis.com">'
  '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
  '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">')
CJS = '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>'
PLY = '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>'
def head(title, libs):
    return _HEAD_PRE + esc(title) + _HEAD_MID + libs + "<style>" + CSS + "</style></head><body><div class=\"dashboard\">"
def foot(script):
    return "</div>" + script + "</body></html>"

def esc(s): return html.escape(str(s)) if s is not None else ""
def fnum(v, p=1):
    if v is None: return "—"
    try: return f"{float(v):,.{p}f}".rstrip('0').rstrip('.') if p else f"{float(v):,.0f}"
    except: return esc(v)
def usd(v):
    if v is None: return "—"
    return f"${v/1000:+.1f}k" if abs(v) >= 1000 else f"${v:+.0f}"
def verdict_cls(v):
    v = (v or "").upper()
    if "CONFIRMED" in v: return "v-conf"
    if "HYPOTHESIS" in v: return "v-hyp"
    if "INSUFFICIENT" in v: return "v-ins"
    if "CONTRADICT" in v: return "v-con"
    if "QUALIFIED" in v: return "v-qual"
    return "neutral"
def lean_tag(lean):
    l=(lean or "").lower()
    if l=="short": return '<span class="tag t-short">SHORT 우세</span>'
    if l=="long":  return '<span class="tag t-long">LONG 우세</span>'
    return '<span class="tag t-mixed">MIXED(조건부)</span>'
def lean_cls(lean):
    l=(lean or "").lower()
    return "cshort" if l=="short" else ("clong" if l=="long" else "neutral")

HM_JS = """
const MONTHS=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function renderHM(elId,matrix){
  const el=document.getElementById(elId);if(!el)return;
  if(!matrix){el.innerHTML='<div style="color:var(--text-muted);font-size:11px;padding:8px">no data</div>';return;}
  const HC=[];for(let h=5;h<=22;h++)HC.push(h);
  let max=0;matrix.forEach(r=>HC.forEach(h=>{const v=r[h];if(v&&v>max)max=v;}));
  let html='<div class="mh-grid" style="grid-template-columns:22px repeat('+HC.length+',1fr);">';
  html+='<div class="mh-h"></div>';HC.forEach(h=>html+='<div class="mh-h">'+h+'</div>');
  matrix.forEach((row,mi)=>{html+='<div class="mh-m">'+MONTHS[mi]+'</div>';
    HC.forEach(h=>{const v=row[h]||0;const t=max>0?v/max:0;
      const bg=v>0?'rgba(38,166,154,'+(0.10+0.88*t).toFixed(3)+')':'var(--bg-panel-2)';
      const txt=v>=0.05?Math.round(v*100):'';
      html+='<div class="mh-c" style="background:'+bg+'" title="'+MONTHS[mi]+' HE'+h+': '+(v*100).toFixed(1)+'%">'+txt+'</div>';});});
  html+='</div>';el.innerHTML=html;
}
function renderHMdiv(elId,matrix){
  const el=document.getElementById(elId);if(!el)return;
  if(!matrix){el.innerHTML='<div style="color:var(--text-muted);font-size:11px;padding:8px">no data</div>';return;}
  const HC=[];for(let h=5;h<=22;h++)HC.push(h);
  let mx=0;matrix.forEach(r=>HC.forEach(h=>{const v=Math.abs(r[h]||0);if(v>mx)mx=v;}));
  let html='<div class="mh-grid" style="grid-template-columns:22px repeat('+HC.length+',1fr);">';
  html+='<div class="mh-h"></div>';HC.forEach(h=>html+='<div class="mh-h">'+h+'</div>');
  matrix.forEach((row,mi)=>{html+='<div class="mh-m">'+MONTHS[mi]+'</div>';
    HC.forEach(h=>{const v=row[h]||0;const t=mx>0?Math.abs(v)/mx:0;
      let bg='var(--bg-panel-2)';
      if(v>0)bg='rgba(255,152,0,'+(0.10+0.85*t).toFixed(3)+')';      // short
      else if(v<0)bg='rgba(41,98,255,'+(0.10+0.85*t).toFixed(3)+')'; // long
      html+='<div class="mh-c" style="background:'+bg+'" title="'+MONTHS[mi]+' HE'+h+': $'+v.toFixed(2)+(v>0?' (short)':(v<0?' (long)':''))+'"></div>';});});
  html+='</div>';el.innerHTML=html;
}
"""

def render_constraint(dp):
    cid = dp["id"]; sign = dp.get("sign","")
    s1 = dp.get("section1_lambda_summary",{}); da = s1.get("da",{}) or {}; rt = s1.get("rt",{}) or {}
    cum = s1.get("cum_impact_usd_per_mw",{}) or {}
    sf = dp.get("gks_sf",{}) or {}
    s8 = dp.get("section8_dart_spread",{}) or {}
    lean = s8.get("net_lean")
    sign_tag = '<span class="tag t-pos">LMP↑(SF&lt;0)</span>' if sign=="pos" else '<span class="tag t-neg">LMP↓(SF&gt;0)</span>'
    kpis = [
        ("DART net 시그널", f'<span class="{lean_cls(lean)}">{esc((lean or "").upper())}</span>', f"누적 spread {usd(s8.get('cum_spread_usd_per_mw'))}/MW", "neutral"),
        ("DA-vs-RT 우위", esc(s8.get("da_dominant_or_rt","—")), f"숏 {fnum(s8.get('pct_hours_short'))}% · 롱 {fnum(s8.get('pct_hours_long'))}%", "neutral"),
        ("GKS SF", f"{fnum(sf.get('da'),3)}", f"DA · RT {fnum(sf.get('rt'),3)}", "neutral"),
        ("누적 MCC 영향", usd(cum.get("total")), f"DA {usd(cum.get('da'))} · RT {usd(cum.get('rt'))}", "neutral"),
        ("RT λ 중앙값", f"${fnum(rt.get('median'))}", f"최대 ${fnum(rt.get('max'),0)}", "neutral"),
        ("바인딩 시간", f"{fnum(da.get('bind_hrs'),0)}h", f"RT {fnum(rt.get('bind_hrs'),0)}h", "neutral"),
    ]
    kpi_html = "".join(f'<div class="kpi"><div class="kpi-label">{esc(k)}</div><div class="kpi-value {c}">{v}</div><div class="kpi-change neutral">{esc(sub)}</div></div>' for k,v,sub,c in kpis)
    def lrow(mkt,d): return f'<tr><td>{mkt}</td><td class="num">{fnum(d.get("bind_hrs"),0)}</td><td class="num">{fnum(d.get("mean"))}</td><td class="num">{fnum(d.get("median"))}</td><td class="num">{fnum(d.get("p90"))}</td><td class="num">{fnum(d.get("p99"),0)}</td><td class="num">{fnum(d.get("max"),0)}</td></tr>'
    s1tbl = f'<table><thead><tr><th>시장</th><th class="num">바인딩h</th><th class="num">평균</th><th class="num">중앙값</th><th class="num">P90</th><th class="num">P99</th><th class="num">최대</th></tr></thead><tbody>{lrow("DA",da)}{lrow("RT",rt)}</tbody></table>'
    note = cum.get("note","")
    # thresholds
    th = dp.get("section3_thresholds",[]) or []
    CONFCLS = {"HIGH":"conf","MEDIUM":"qual","LOW":"hyp"}
    if th:
        parts=[]
        for t in th:
            ccls=CONFCLS.get((t.get("confidence") or "").upper(),"ins")
            parts.append('<tr><td>%s</td><td class="mono">%s</td><td class="mono">%s</td><td>%s</td><td class="mono">%s</td><td><span class="v-%s">%s</span></td></tr>'%(
                esc(t.get("factor")),esc(t.get("on_breakpoint")),esc(t.get("strong")),esc(t.get("pbind_distribution")),esc(t.get("lambda_cond")),ccls,esc(t.get("confidence"))))
        s3=f'<table><thead><tr><th>팩터</th><th>시작(on)</th><th>강(strong)</th><th>P(bind) 분포</th><th>λ(조건부)</th><th>신뢰도</th></tr></thead><tbody>{"".join(parts)}</tbody></table>'
    else: s3='<div class="panel-body" style="color:var(--text-muted)">임계치 데이터 없음</div>'
    # watchlist
    wl = dp.get("section5_outage_watchlist",{}) or {}
    if wl.get("informative") and wl.get("rows"):
        wrows="".join(f'<tr><td>{esc(r.get("facility"))}</td><td>{esc(r.get("zone"))}</td><td class="num">{fnum(r.get("out_days"),0)}</td><td class="num">{fnum(r.get("co_bind"),0)}</td><td class="num">{fnum(r.get("p_bind_given_out"),2)}</td><td class="num up">{fnum(r.get("seas_lift"),2)}</td><td style="font-size:11px">{esc(r.get("note"))}</td></tr>' for r in wl["rows"])
        s5=f'<table><thead><tr><th>정지 설비</th><th>존</th><th class="num">정지일</th><th class="num">동시바인딩</th><th class="num">P(bind|정지)</th><th class="num">lift</th><th>비고</th></tr></thead><tbody>{wrows}</tbody></table>'
        s5cav=f'<div class="caveat" style="margin:12px 16px 16px"><b>⚠</b> {esc(wl.get("caveat",""))}</div>'
    else:
        s5=''
        _wlc=wl.get("caveat") or "특정 송전정지가 binding을 판별하지 못함 (높은 base-rate / GTC limit이 실질 switch)."
        s5cav='<div class="caveat" style="margin:14px 16px"><b>⚠ outage 미판별(informative=false)</b> — %s</div>'%esc(_wlc)
    # drivers
    dr=dp.get("section6_drivers",[]) or []
    drows="".join(f'<tr><td>{esc(d.get("lens"))}</td><td><span class="{verdict_cls(d.get("verdict"))}">{esc(d.get("verdict"))}</span></td><td style="font-size:11.5px;color:var(--text-secondary)">{esc(d.get("evidence"))}</td></tr>' for d in dr)
    s6=f'<table><thead><tr><th>렌즈</th><th>판정</th><th>근거</th></tr></thead><tbody>{drows}</tbody></table>'
    cavs=dp.get("caveats",[]) or []
    cav_html="".join(f"<li>{esc(c)}</li>" for c in cavs)
    # section8 DART
    s8cavs=s8.get("caveats",[]) or []
    s8cav_html="".join(f"<li>{esc(c)}</li>" for c in s8cavs)
    dart_kpis=[
        ("net 시그널", f'<span class="{lean_cls(lean)}">{esc((lean or "").upper())}</span>', esc(s8.get("da_dominant_or_rt","")), ""),
        ("누적 spread", usd(s8.get("cum_spread_usd_per_mw")), "+는 숏 / −는 롱 우위", ""),
        ("숏 시간 비중", f"{fnum(s8.get('pct_hours_short'))}%", f"gross 숏 {usd(s8.get('gross_short_usd_per_mw'))}", ""),
        ("롱 시간 비중", f"{fnum(s8.get('pct_hours_long'))}%", f"gross 롱 {usd(s8.get('gross_long_usd_per_mw'))}", ""),
    ]
    dart_kpi_html="".join(f'<div class="kpi"><div class="kpi-label">{esc(k)}</div><div class="kpi-value">{v}</div><div class="kpi-change neutral">{esc(sub)}</div></div>' for k,v,sub,c in dart_kpis)

    libs=CJS
    body=f"""
<div class="header"><div><h1>{esc(dp.get('display_name',cid))}</h1>
<div class="subtitle">{esc(dp.get('element'))} · {esc(dp.get('kv'))}kV {esc(dp.get('facility_type'))} · {esc(dp.get('zone_from'))}→{esc(dp.get('zone_to'))} · {esc(dp.get('binding_basis'))} · {sign_tag} {lean_tag(lean)} <span class="tag t-live">LIVE</span></div></div>
<a class="back" href="index.html">← GKS 혼잡→DART 허브</a></div>

<div class="panel" style="margin-bottom:4px"><div class="panel-body" style="font-size:12.5px;color:var(--text-secondary)"><b style="color:var(--text-primary)">메커니즘:</b> {esc(dp.get('mechanism'))}</div></div>

<div class="kpi-row">{kpi_html}</div>

<div class="panel" style="border-color:rgba(156,39,176,0.35)"><div class="panel-header"><span class="panel-title" style="color:#ce93d8">★ DART 스프레드 (숏/롱) 시그널</span><span class="panel-sub">spread=DA−RT · MCC=−SF×λ · +→숏유리 −→롱유리</span></div>
  <div class="panel-body">
  <div class="kpi-row" style="margin-bottom:12px">{dart_kpi_html}</div>
  <div class="rot dart">{esc(s8.get('net_lean_text'))}<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--grid-line)"><b>nuance:</b> {esc(s8.get('nuance_text'))}</div>
  <div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--grid-line)"><b>룰오브썸:</b> {esc(s8.get('dart_rule_of_thumb'))}</div></div>
  <div style="margin-top:14px"><div style="font-size:11px;color:var(--text-primary);font-weight:600;margin-bottom:6px">월×시간 spread 부호 (주황=숏유리 / 파랑=롱유리)</div>
    <div class="lgnd"><span><i style="background:var(--short)"></i>숏유리(DA비쌈)</span><span><i style="background:var(--long)"></i>롱유리(RT비쌈)</span><span><i style="background:var(--bg-panel-2)"></i>무신호</span></div>
    <div id="dart_{cid}"></div></div>
  <ul class="notes" style="margin-top:12px">{s8cav_html}</ul>
  </div></div>

<div class="two-grid">
  <div class="panel"><div class="panel-header"><span class="panel-title">① 그림자가격(λ) 요약 — DA vs RT</span><span class="panel-sub">바인딩 only · RT cap ${esc(s1.get('rt_cap'))}</span></div>
    <div class="panel-body">{s1tbl}<div style="font-size:11px;color:var(--text-muted);margin-top:10px">{esc(note)}</div></div></div>
  <div class="panel"><div class="panel-header"><span class="panel-title">② λ 분포 (중앙값·P90·P99·최대)</span><span class="panel-sub">$/MWh · log</span></div>
    <div class="chart-wrap"><canvas id="lc_{cid}"></canvas></div></div>
</div>

<div class="panel"><div class="panel-header"><span class="panel-title">③ 월 × 시간대 바인딩 확률</span><span class="panel-sub">P(bind) · 행=월 · 열=HE5-22 · 색=패널 내 상대강도</span></div>
  <div class="panel-body"><div class="two-grid">
    <div><div style="font-size:11px;color:var(--text-primary);font-weight:600;margin-bottom:6px">RT</div><div id="hmrt_{cid}"></div></div>
    <div><div style="font-size:11px;color:var(--text-primary);font-weight:600;margin-bottom:6px">DA</div><div id="hmda_{cid}"></div></div>
  </div></div></div>

<div class="panel"><div class="panel-header"><span class="panel-title">④ 핵심 규칙 (Rule of Thumb)</span></div>
  <div class="panel-body"><div class="rot">{esc(dp.get('section4_rule_of_thumb'))}</div>
  <div style="font-size:11.5px;color:var(--text-secondary);margin-top:10px"><b style="color:var(--text-primary)">시즌·시간:</b> {esc(dp.get('seasonality_text'))}</div></div></div>

<div class="panel"><div class="panel-header"><span class="panel-title">⑤ 트리거 임계치</span></div>{s3}</div>

<div class="panel"><div class="panel-header"><span class="panel-title">⑥ 송전정지(Outage) 워치리스트 (계절보정 lift)</span></div>{s5}{s5cav}</div>

<div class="panel"><div class="panel-header"><span class="panel-title">⑦ 드라이버 5-렌즈</span></div>{s6}</div>

<div class="panel"><div class="panel-header"><span class="panel-title">DART Read & 유의사항</span></div>
  <div class="panel-body"><div class="rot dart">{esc(dp.get('section7_gks_read'))}</div>
  <ul class="notes" style="margin-top:12px">{cav_html}</ul></div></div>
"""
    s2=dp.get('section2_month_hour',{}) or {}
    tag=cid.replace('_','')
    script=f"""<script>{HM_JS}
Chart.defaults.color='#787b86';Chart.defaults.borderColor='#1e222d';Chart.defaults.font.family="'Inter',sans-serif";Chart.defaults.font.size=10;
new Chart(document.getElementById('lc_{cid}'),{{type:'bar',data:{{labels:['중앙값','P90','P99','최대'],datasets:[
 {{label:'DA',data:[{da.get('median') or 0},{da.get('p90') or 0},{da.get('p99') or 0},{da.get('max') or 0}],backgroundColor:'rgba(120,123,134,0.55)',borderWidth:0}},
 {{label:'RT',data:[{rt.get('median') or 0},{rt.get('p90') or 0},{rt.get('p99') or 0},{rt.get('max') or 0}],backgroundColor:'rgba(41,98,255,0.7)',borderWidth:0}}
]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:true,position:'top',labels:{{boxWidth:9,boxHeight:9,padding:12}}}},tooltip:{{callbacks:{{label:c=>c.dataset.label+': $'+c.parsed.y}}}}}},
 scales:{{x:{{grid:{{display:false}},border:{{display:false}}}},y:{{type:'logarithmic',grid:{{color:'#1e222d',drawTicks:false}},border:{{display:false}},ticks:{{callback:v=>'$'+v}}}}}}}}}});
const S2_{tag}={json.dumps(s2)};renderHM('hmrt_{cid}',S2_{tag}.rt_pbind);renderHM('hmda_{cid}',S2_{tag}.da_pbind);
const D8_{tag}={json.dumps(s8.get('month_hour_spread'))};renderHMdiv('dart_{cid}',D8_{tag});
</script>"""
    page=head("GKS · "+cid, libs)+body+foot(script)
    with open(os.path.join(OUT,f"constraint_{cid}.html"),"w",encoding="utf-8") as f: f.write(page)
    return cid

SLIM = {
  "1710__C": {"label":"BELCNTY–SALSW 138 (Central TX)","cum":15684,"status":"retired",
              "why":"2026 바인딩 0건 (설비 upgrade/토폴로지 변경 추정). 역대 최대 λ($815 RT)지만 forward 가치 없음."},
  "LARDVN_LASCRU1_1": {"label":"Laredo–LasCruces 138","cum":-49869,"status":"retired",
              "why":"~2025-10 바인딩 붕괴 (Laredo 138 upgrade 추정). 역대 최대 RT 영향이나 현재 dormant."},
  "CATARI_PILONC1_1": {"label":"Piloncillo–Catarina 138","cum":-10577,"status":"retired",
              "why":"~2025-06 은퇴. RT 중앙값 λ $327로 심도 컸으나 현재 dormant."},
  "15060__B": {"label":"VEALMOOR–KOCHTAP 138 (Permian)","cum":2872,"status":"noise",
              "why":"GKS |SF|≈0, DA/RT 부호 뒤집힘(net≈0), 600mi 밖 잔여 민감도. GKS 로직에서 제외."},
}

def render_hub(coords, packs):
    cons=coords.get("constraints",[]); gks=coords.get("gks",{})
    by_id={p["id"]:p for p in packs}
    # DART ranking from live packs
    rank=[]
    for p in packs:
        s8=p.get("section8_dart_spread",{}) or {}
        rank.append((p["id"], s8.get("cum_spread_usd_per_mw") or 0, s8.get("net_lean")))
    rank.sort(key=lambda x:x[1])  # most-long(neg) first
    longs=[r for r in rank if (r[2] or "")=="long"]; shorts=[r for r in rank if (r[2] or "")=="short"]; mixed=[r for r in rank if (r[2] or "")=="mixed"]
    big_long=min(rank,key=lambda x:x[1]); big_short=max(rank,key=lambda x:x[1])
    kpis=[
      ("GKS 노드","SOUTH/Valley","GKS_BESS_RN · COD 2024-07","neutral"),
      ("최대 LONG 시그널",esc(big_long[0]),f"누적 spread {usd(big_long[1])}/MW","clong"),
      ("최대 SHORT 시그널",esc(big_short[0]),f"누적 spread {usd(big_short[1])}/MW","cshort"),
      ("net 분류",f"L{len(longs)} · S{len(shorts)} · M{len(mixed)}","LONG·SHORT·MIXED","neutral"),
      ("공통 패턴","평상 vs 스파이크","만성 DA→/ RT스파이크→반대","neutral"),
      ("Constraint","14","10 LIVE / 4 은퇴·noise","neutral"),
    ]
    kpi_html="".join(f'<div class="kpi"><div class="kpi-label">{esc(k)}</div><div class="kpi-value {c}" style="font-size:{19 if len(str(v))>7 else 22}px">{v}</div><div class="kpi-change neutral">{esc(sub)}</div></div>' for k,v,sub,c in kpis)
    def card_full(cid):
        c=next((x for x in cons if x["id"]==cid),{}); p=by_id.get(cid,{}); s8=p.get("section8_dart_spread",{}) or {}
        lean=s8.get("net_lean"); cs=s8.get("cum_spread_usd_per_mw")
        sgn=p.get("sign"); postag='<span class="tag t-pos">LMP↑</span>' if sgn=="pos" else '<span class="tag t-neg">LMP↓</span>'
        rot=(s8.get("dart_rule_of_thumb") or "")[:90]
        return f'<a class="card" href="constraint_{cid}.html"><div class="c-top"><span class="c-id">{esc(cid)}</span><span class="c-val {lean_cls(lean)}">{usd(cs)}</span></div><div class="c-el">{esc(c.get("label") or p.get("element"))}</div><div class="c-meta">{lean_tag(lean)} {postag} · {esc(s8.get("da_dominant_or_rt",""))} · {esc(rot)}…</div></a>'
    def card_slim(cid):
        s=SLIM[cid]; tg='<span class="tag t-retired">RETIRED</span>' if s["status"]=="retired" else '<span class="tag t-noise">NOISE</span>'
        return f'<div class="card" style="opacity:0.72"><div class="c-top"><span class="c-id">{esc(cid)}</span><span class="c-val neutral">MCC {usd(s["cum"])}</span></div><div class="c-el">{esc(s["label"])}</div><div class="c-meta">{tg} · DART 분석 생략 · {esc(s["why"])}</div></div>'
    long_cards="".join(card_full(r[0]) for r in rank if (r[2] or "")=="long")
    short_cards="".join(card_full(r[0]) for r in rank if (r[2] or "")=="short")
    mixed_cards="".join(card_full(r[0]) for r in rank if (r[2] or "")=="mixed")
    slim_html="".join(card_slim(cid) for cid in SLIM)
    # map (color by net_lean)
    mpts=[]
    for c in cons:
        if c.get("lat") is None: continue
        p=by_id.get(c["id"],{}); s8=p.get("section8_dart_spread",{}) or {}
        mpts.append({"id":c["id"],"label":c.get("label"),"lat":c["lat"],"lon":c["lon"],
            "lean":s8.get("net_lean"),"cs":s8.get("cum_spread_usd_per_mw"),"status":c.get("status")})
    map_json=json.dumps(mpts); gks_json=json.dumps({"lat":gks.get("lat"),"lon":gks.get("lon"),"name":gks.get("name")})
    # ranking bar
    rk_labels=[r[0] for r in rank]; rk_vals=[round(r[1]/1000,2) for r in rank]; rk_lean=[r[2] for r in rank]
    unplaced=[c["id"] for c in cons if c.get("lat") is None]

    body=f"""
<div class="header"><div><h1>GKS 혼잡 → DART 스프레드 허브</h1>
<div class="subtitle">GKS_BESS_RN (SOUTH/Valley) · DART spread = DA−RT 혼잡(MCC) 기여 · 누적 $/MW · 2024-07~2026-06 · 14 constraint deep-dive</div></div>
<div class="status-pill">REAL DATA · YE DATALAKE</div></div>

<div class="kpi-row">{kpi_html}</div>

<div class="panel"><div class="panel-header"><span class="panel-title">DART net 시그널 랭킹 — 롱유리(좌,파랑) ↔ 숏유리(우,주황)</span>
<span class="panel-sub">누적 (MCC_DA − MCC_RT) $/MW · −=롱 +=숏</span></div>
<div class="chart-wrap" style="height:360px"><canvas id="rank"></canvas></div></div>

<div class="panel"><div class="panel-header"><span class="panel-title">통합 Corridor 지도 — GKS + 14 constraint</span>
<span class="panel-sub">파랑=롱우세 주황=숏우세 회색=mixed/은퇴 · 크기=|누적 spread| · 좌표 근사(CEII아님)</span></div>
<div id="map" style="height:480px"></div>
<div style="font-size:11px;color:var(--text-muted);padding:6px 16px 14px">미배치(좌표미상): {esc(', '.join(unplaced) or '없음')} · 421__A는 |SF| 최대(0.32)이나 switch-station 좌표 미상</div></div>

<div class="panel"><div class="panel-header"><span class="panel-title">LONG 우세 (RT가 더 쌈 / RT-dominant)</span><span class="panel-sub">클릭 → 풀 분석</span></div>
  <div class="panel-body" style="display:flex;flex-direction:column;gap:10px">{long_cards or '<div style="color:var(--text-muted)">없음</div>'}</div></div>
<div class="panel"><div class="panel-header"><span class="panel-title">SHORT 우세 (DA가 더 쌈 / RT scarcity 스파이크)</span><span class="panel-sub">클릭 → 풀 분석</span></div>
  <div class="panel-body" style="display:flex;flex-direction:column;gap:10px">{short_cards or '<div style="color:var(--text-muted)">없음</div>'}</div></div>
<div class="panel"><div class="panel-header"><span class="panel-title">MIXED (조건부 — 평상/스파이크 반대)</span><span class="panel-sub">클릭 → 풀 분석</span></div>
  <div class="panel-body" style="display:grid;grid-template-columns:1fr 1fr;gap:10px">{mixed_cards or '<div style="color:var(--text-muted)">없음</div>'}</div></div>

<div class="panel"><div class="panel-header"><span class="panel-title">은퇴 · Noise (forward 저가중 / 제외)</span><span class="panel-sub">풀 분석 생략 — 요약만</span></div>
  <div class="panel-body" style="display:grid;grid-template-columns:1fr 1fr;gap:10px">{slim_html}</div></div>

<div class="panel"><div class="panel-body">
  <div class="caveat"><b>⚠ 방법론·해석:</b> DART spread = constraint별 (MCC_DA − MCC_RT) 누적($/MW). +=숏유리(DA비쌈) −=롱유리(RT비쌈). MCC=−SF×λ, RT는 5분→시간평균. 이는 노드 DA-RT spread의 <b>혼잡(basis) 성분만</b> — 에너지/손실 basis는 별도. 누적 net_lean은 <b>$가중</b>이라 시간-다수와 다를 수 있음(예: STPELM·VALEXP). <b>실제 short/long 포지션 사이징·승률·입찰은 dart-virtual-trader 영역</b>이며 여기선 혼잡-기인 시그널 특성만. 좌표 근사·co-occurrence≠membership·GTC limit 시변.</div>
</div></div>
"""
    script=f"""{PLY}{CJS}<script>
Chart.defaults.color='#787b86';Chart.defaults.borderColor='#1e222d';Chart.defaults.font.family="'Inter',sans-serif";Chart.defaults.font.size=10;
const RLAB={json.dumps(rk_labels)};const RVAL={json.dumps(rk_vals)};const RLEAN={json.dumps(rk_lean)};
function rcolor(l,v){{if(l==='short')return 'rgba(255,152,0,0.85)';if(l==='long')return 'rgba(41,98,255,0.8)';return 'rgba(120,123,134,0.6)';}}
new Chart(document.getElementById('rank'),{{type:'bar',data:{{labels:RLAB,datasets:[{{data:RVAL,backgroundColor:RVAL.map((v,i)=>rcolor(RLEAN[i],v)),borderWidth:0}}]}},
 options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>'$'+c.parsed.x+'k/MW · '+(RLEAN[c.dataIndex]||'').toUpperCase()}}}}}},
 scales:{{x:{{grid:{{color:'#1e222d',drawTicks:false}},border:{{display:false}},ticks:{{callback:v=>'$'+v+'k'}},title:{{display:true,text:'← 롱유리 (RT비쌈)        누적 MCC_DA−MCC_RT ($k/MW)        숏유리 (DA비쌈) →',color:'#787b86',font:{{size:10}}}}}},
 y:{{grid:{{display:false}},border:{{display:false}},ticks:{{font:{{family:"'JetBrains Mono',monospace",size:10}}}}}}}}}}}});
const PTS={map_json};const GKS={gks_json};
function msize(cs){{const a=Math.abs(cs||0);return 8+Math.sqrt(a/1000)*3.0;}}
function lcolor(l){{return l==='short'?'#ff9800':(l==='long'?'#2962ff':'#787b86');}}
const groups={{long:[],short:[],mixed:[]}};PTS.forEach(p=>{{(groups[p.lean]||(groups[p.lean]=[])).push(p);}});
function tr(arr,name,color){{return {{type:'scattergeo',mode:'markers+text',name:name,lon:arr.map(p=>p.lon),lat:arr.map(p=>p.lat),
  text:arr.map(p=>p.id),textposition:'top center',textfont:{{size:8.5,color:'#9598a1'}},
  marker:{{size:arr.map(p=>msize(p.cs)),color:color,opacity:arr.map(p=>p.status==='live'?0.9:0.4),line:{{width:0.5,color:'#0d1117'}}}},
  hovertext:arr.map(p=>p.label+'<br>'+(p.lean||'?').toUpperCase()+' · spread '+(p.cs>0?'+':'')+'$'+((p.cs||0)/1000).toFixed(1)+'k/MW'),hoverinfo:'text'}};}}
const traces=[tr(groups.long||[],'롱우세','#2962ff'),tr(groups.short||[],'숏우세','#ff9800'),tr(groups.mixed||[],'mixed','#787b86'),
 {{type:'scattergeo',mode:'markers+text',name:'GKS',lon:[GKS.lon],lat:[GKS.lat],text:['GKS'],textposition:'bottom center',
   textfont:{{size:11,color:'#ffd54f'}},marker:{{size:16,color:'#26a69a',symbol:'star',line:{{width:1,color:'#0d1117'}}}},hovertext:['GKS_BESS_RN (SOUTH/Valley)'],hoverinfo:'text'}}];
Plotly.newPlot('map',traces,{{geo:{{scope:'usa',showland:true,landcolor:'#161b27',showsubunits:true,subunitcolor:'#363a45',
   lonaxis:{{range:[-102.5,-95.5]}},lataxis:{{range:[25.5,33]}},bgcolor:'rgba(0,0,0,0)',coastlinecolor:'#363a45',countrycolor:'#363a45'}},
   paper_bgcolor:'rgba(0,0,0,0)',margin:{{l:0,r:0,t:0,b:0}},showlegend:true,
   legend:{{x:0.01,y:0.99,bgcolor:'rgba(19,23,34,0.7)',bordercolor:'#2a2e39',borderwidth:1,font:{{color:'#787b86',size:10}}}},
   font:{{family:'Inter,sans-serif',color:'#787b86'}}}},{{responsive:true,displayModeBar:false}});
</script>"""
    page=head("GKS 혼잡→DART 허브","")+body+foot(script)
    with open(os.path.join(OUT,"index.html"),"w",encoding="utf-8") as f: f.write(page)

packs=[]
for fp in sorted(glob.glob(os.path.join(DER,"datapack_*.json"))):
    with open(fp,encoding="utf-8") as f: packs.append(json.load(f))
ids=[render_constraint(dp) for dp in packs]
with open(os.path.join(DER,"unified_map_coords.json"),encoding="utf-8") as f: coords=json.load(f)
render_hub(coords, packs)
print(f"Generated index.html + {len(ids)} constraint pages + {len(SLIM)} slim cards in:\n{OUT}")
print("Full:", ", ".join(ids))
