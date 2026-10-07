"""Render the Raven FY2027 draft dashboard to a single self-contained HTML file.
Light theme per skills/dashboard-report.skill. Real data only; missing cells render as em-dash.
"""
import json
from pathlib import Path
import pandas as pd, numpy as np

BASE = Path(__file__).resolve().parents[1]; D = BASE / "derived"
ROOT = Path(__file__).resolve().parents[5]
P = json.load(open(D / "draft_dashboard_payload.json"))
fc = P["forecast"]

dd = pd.read_csv(D / "item1_daily_tb2.csv")
def series(node, mkt):
    s = dd[(dd.node == node) & (dd.market == mkt)].sort_values("flowday")
    return s.flowday.tolist(), [round(float(x), 2) for x in s.tb2]
days_da, rvn_da = series("RVN_RN", "DA"); _, gks_da = series("GKS_BESS_RN", "DA")
days_rt, rvn_rt = series("RVN_RN", "RT"); _, gks_rt = series("GKS_BESS_RN", "RT")

mo = P["monthly_tb2_by_year"]
base27 = [fc["base_2027_monthly_tb2"][str(m)] for m in range(1, 13)]
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

dh = pd.DataFrame(P["dart_hourly"])
peers = pd.DataFrame(P["peers"])
peers2h = peers[(peers.duration_hours >= 1.85) & (peers.duration_hours <= 2.25) & (peers.cap_mw >= 50)]
cg = P["congestion"]; xo = pd.DataFrame(P["crossover"]); rg = pd.DataFrame(P["regime"])
st = P["item1"]["tb2_stats"]

def f(x, d=1, dash="\u2014"):
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return dash
        return format(float(x), ",." + str(d) + "f")
    except Exception:
        return dash

FWD = {"WHARTN": ("검증불가", "amber"), "BLESSI_PAVLOV1_1": ("소멸", "muted"),
       "E_PASP": ("LIVE", "up"), "1710__C": ("은퇴", "down"),
       "HARGRO_TWINBU1_1": ("LIVE", "up"), "STPELM27_1": ("에피소드", "amber"),
       "630__B": ("LIVE", "up"), "STPWAP39_1": ("LIVE", "up"),
       "587__A": ("LIVE", "up"), "50__A": ("에피소드", "amber")}

cong_rows = ""
for i, c in enumerate(cg, 1):
    lab, cls = FWD.get(c["name"], ("\u2014", "muted"))
    pos = "pos" in (c["sign"] or "")
    cum = c["cum"] or {}
    bm = ",".join(str(m) for m in (c["binding_months"] or [])) or "\u2014"
    dv = c["da_vs_rt"] or {}
    bf = dv.get("da_bind_freq")
    cong_rows += (
        '<tr><td class=mono>' + str(i) + '</td><td><b>' + c["name"] + '</b>'
        '<div class=sub>' + (c["element"] or "\u2014") + '</div></td>'
        '<td><span class="pill ' + ("up" if pos else "down") + '">'
        + ("\u25b2 상승" if pos else "\u25bc 하락") + '</span></td>'
        '<td class="num mono ' + ("up" if (cum.get("da") or 0) > 0 else "down") + '">' + f(cum.get("da"), 0) + '</td>'
        '<td class="num mono ' + ("up" if (cum.get("rt") or 0) > 0 else "down") + '">' + f(cum.get("rt"), 0) + '</td>'
        '<td class="num mono">' + (f(bf * 100, 1) if bf is not None else "\u2014") + '%</td>'
        '<td class="num mono">' + f(dv.get("rt_mean_lambda"), 0) + '</td>'
        '<td class=mono>' + bm + '</td>'
        '<td><span class="pill ' + cls + '">' + lab + '</span></td></tr>')

peer_rows = ""
for _, r in peers.head(14).iterrows():
    is2h = 1.85 <= r.duration_hours <= 2.25 and r.cap_mw >= 50
    peer_rows += (
        '<tr class="' + ("hl" if is2h else "") + '"><td><b>' + str(r.resource_name) + '</b>'
        '<div class=sub>' + (str(r.company) if pd.notna(r.company) else "\u2014") + '</div></td>'
        '<td class=mono>' + str(r.settlement_point) + '</td>'
        '<td class="num mono">' + f(r.cap_mw, 0) + '</td>'
        '<td class="num mono">' + f(r.duration_hours, 1) + '</td>'
        '<td class="num mono b">' + f(r.rev_per_mw, 0) + '</td>'
        '<td class="num mono">' + f(r.opt_rate_pct, 1) + '%</td>'
        '<td class="num mono">' + f(r.as_share_pct, 1) + '%</td></tr>')
g = P["gks_row"]
if g:
    peer_rows += (
        '<tr class=ref><td><b>' + str(g["resource_name"]) + '</b>'
        '<div class=sub>GKS \u00b7 SOUTH (참조)</div></td>'
        '<td class=mono>' + str(g["settlement_point"]) + '</td>'
        '<td class="num mono">' + f(g["cap_mw"], 0) + '</td>'
        '<td class="num mono">' + f(g["duration_hours"], 1) + '</td>'
        '<td class="num mono b">' + f(g["rev_per_mw"], 0) + '</td>'
        '<td class="num mono">' + f(g["opt_rate_pct"], 1) + '%</td>'
        '<td class="num mono">' + f(g["as_share_pct"], 1) + '%</td></tr>')

dart_rows = ""
for _, r in dh.iterrows():
    tr = bool(r.tradeable); side = r.best_side
    ev = r.long_ev_per_mwh if side == "long" else r.short_ev_per_mwh
    pw = r.long_p_win if side == "long" else r.short_p_win
    pl = r.long_pl_ratio if side == "long" else r.short_pl_ratio
    p99 = r.long_loss_p99 if side == "long" else r.short_loss_p99
    badge = ('<span class="pill up">거래가능</span>' if tr else
             ('<span class="pill amber">꼬리위험</span>' if r.tail_flag else '<span class="pill muted">\u2014</span>'))
    dart_rows += (
        '<tr class="' + ("ok" if tr else "") + '"><td class=mono>HE' + str(int(r.HE)) + '</td>'
        '<td><span class="pill ' + ("up" if side == "long" else "down") + '">' + str(side).upper() + '</span></td>'
        '<td class="num mono">' + f(pw * 100, 1) + '%</td>'
        '<td class="num mono">' + f(pl, 2) + '</td>'
        '<td class="num mono ' + ("up" if ev > 0 else "down") + '">' + f(ev, 2) + '</td>'
        '<td class="num mono">' + f(p99, 1) + '</td>'
        '<td class="num mono">' + f(r.t_stat, 2) + '</td>'
        '<td>' + badge + '</td></tr>')

reg_rows = ""
for _, r in rg.iterrows():
    win = "에너지" if r.energy2h_rt > r.as24_rt else "AS 24h"
    reg_rows += (
        '<tr><td><b>' + str(r.tight) + '</b></td><td>' + str(r.cong) + '</td>'
        '<td class="num mono">' + str(int(r.days)) + '</td>'
        '<td class="num mono">' + f(r.tb2_rt) + '</td>'
        '<td class="num mono b">' + f(r.energy2h_rt) + '</td>'
        '<td class="num mono">' + f(r.as4_rt) + '</td>'
        '<td class="num mono">' + f(r.as24_rt) + '</td>'
        '<td class="num mono">' + f(r.ratio, 2) + '</td>'
        '<td><span class="pill ' + ("up" if win == "에너지" else "amber") + '">' + win + '</span></td></tr>')

rv = fc["revenue_usd_per_mw_yr"]; sens = fc["tb_index_sensitivity"]; cap = fc["peer_capture_pct"]
lvl = fc["observed_annual_level_jan_sep_tb2"]
sens_rows = "".join(
    '<tr><td>' + k + '</td><td class="num mono">$' + f(v, 0) + '</td>'
    '<td class="num mono">$' + f(v * cap["base_median"] / 100, 0) + '</td></tr>'
    for k, v in sens.items())

CSS = """
:root{--bg-base:#f7f8fa;--bg-panel:#fff;--bg-panel-2:#f0f2f5;--bg-row-alt:#fafbfc;--border-soft:#e0e3eb;
--border-strong:#c8ccd4;--text-primary:#131722;--text-secondary:#5d606b;--text-muted:#9598a1;
--accent-up:#089981;--accent-down:#f23645;--accent-blue:#2962ff;--accent-amber:#ff9800;
--grid-line:#eceff3;--shadow-card:0 1px 2px rgba(16,24,40,.04);}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg-base);color:var(--text-primary);font-family:'Inter','Pretendard','Noto Sans KR',-apple-system,system-ui,sans-serif;font-size:14px;line-height:1.5}
.wrap{max-width:1400px;margin:0 auto;padding:24px}
.mono{font-family:'JetBrains Mono','SF Mono',monospace;font-variant-numeric:tabular-nums}
header{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px;padding-bottom:16px;border-bottom:1px solid var(--border-soft);margin-bottom:20px}
h1{font-size:22px;font-weight:700;letter-spacing:-.01em}
.sub2{color:var(--text-secondary);font-size:13px;margin-top:4px}
.status{display:inline-block;padding:4px 10px;border-radius:4px;font-size:11px;font-weight:600;letter-spacing:.04em;background:rgba(255,152,0,.12);color:#b26a00;border:1px solid rgba(255,152,0,.3)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:12px}
.kpi{background:var(--bg-panel);border:1px solid var(--border-soft);border-radius:6px;padding:20px;box-shadow:var(--shadow-card)}
.kpi .lab{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-secondary);font-weight:600}
.kpi .val{font-size:30px;font-weight:700;font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums;margin-top:8px;letter-spacing:-.02em}
.kpi .chg{font-size:12px;margin-top:6px;font-weight:500}
.up{color:var(--accent-up)}.down{color:var(--accent-down)}.amber{color:var(--accent-amber)}.muted{color:var(--text-muted)}
.grid2{display:grid;grid-template-columns:2fr 1fr;gap:12px;margin-bottom:12px}
@media(max-width:1000px){.grid2{grid-template-columns:1fr}}
.panel{background:var(--bg-panel);border:1px solid var(--border-soft);border-radius:6px;padding:16px;box-shadow:var(--shadow-card);margin-bottom:12px}
.ptitle{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--text-secondary);margin-bottom:4px}
.pnote{font-size:12px;color:var(--text-muted);margin-bottom:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-secondary);font-weight:600;padding:8px 10px;border-bottom:1px solid var(--border-soft)}
td{padding:8px 10px;border-bottom:1px solid var(--grid-line)}
tbody tr:nth-child(even){background:var(--bg-row-alt)}
tbody tr:hover{background:var(--bg-panel-2)}
.num{text-align:right}.b{font-weight:700}
.sub{font-size:11px;color:var(--text-muted);margin-top:2px}
.pill{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}
.pill.up{background:rgba(8,153,129,.12);color:var(--accent-up)}
.pill.down{background:rgba(242,54,69,.12);color:var(--accent-down)}
.pill.amber{background:rgba(255,152,0,.14);color:#b26a00}
.pill.muted{background:var(--bg-panel-2);color:var(--text-muted)}
tr.hl{background:rgba(41,98,255,.05)!important}
tr.ref td{border-top:2px solid var(--border-strong);background:rgba(255,152,0,.06)!important}
tr.ok{background:rgba(8,153,129,.06)!important}
.hm{display:grid;grid-template-columns:52px repeat(12,1fr);gap:2px}
.hm div{font-size:10px;text-align:center;padding:7px 2px;border-radius:3px;font-family:'JetBrains Mono',monospace}
.hm .hd{color:var(--text-secondary);font-weight:600;background:none}
.hm .yr{text-align:right;padding-right:6px;color:var(--text-secondary);font-weight:600;background:none}
.cv{background:var(--bg-panel);border:1px solid var(--border-soft);border-left:3px solid var(--accent-amber);border-radius:6px;padding:16px}
.cv li{margin-left:18px;font-size:13px;color:var(--text-secondary);margin-bottom:6px}
.fc{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.fcell{border:1px solid var(--border-soft);border-radius:6px;padding:14px;background:var(--bg-row-alt)}
.fcell.main{border-color:var(--accent-blue);background:rgba(41,98,255,.05)}
.fcell .l{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-secondary);font-weight:600}
.fcell .v{font-size:22px;font-weight:700;font-family:'JetBrains Mono',monospace;margin-top:6px}
.fcell .s{font-size:11px;color:var(--text-muted);margin-top:4px}
.chartbox{position:relative;height:300px}
.tabs{display:flex;gap:6px;margin-bottom:10px}
.tab{padding:4px 12px;font-size:12px;border:1px solid var(--border-soft);border-radius:4px;background:var(--bg-panel);cursor:pointer;font-weight:500}
.tab.on{background:var(--accent-blue);color:#fff;border-color:var(--accent-blue)}
"""

JS = """
Chart.defaults.font.family="'JetBrains Mono',monospace";Chart.defaults.font.size=11;
Chart.defaults.color='#5d606b';
const o={responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
plugins:{legend:{position:'top',align:'end',labels:{boxWidth:10,boxHeight:10,usePointStyle:true,pointStyle:'rect'}}},
scales:{x:{grid:{color:'#eceff3'},ticks:{maxTicksLimit:10}},y:{grid:{color:'#eceff3'},ticks:{callback:v=>'$'+v}}}};
let ch=new Chart(document.getElementById('c1'),{type:'line',data:{labels:DAYS_RT,datasets:[
{label:'RVN_RN',data:RVN_RT,borderColor:'#089981',backgroundColor:'rgba(8,153,129,.10)',fill:true,borderWidth:1.8,pointRadius:0,tension:.25},
{label:'GKS_BESS_RN',data:GKS_RT,borderColor:'#f23645',backgroundColor:'rgba(242,54,69,.08)',fill:true,borderWidth:1.8,pointRadius:0,tension:.25}]},options:o});
function sw(m,el){document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));el.classList.add('on');
ch.data.labels=m=='RT'?DAYS_RT:DAYS_DA;ch.data.datasets[0].data=m=='RT'?RVN_RT:RVN_DA;
ch.data.datasets[1].data=m=='RT'?GKS_RT:GKS_DA;ch.update();}
new Chart(document.getElementById('c2'),{type:'bar',data:{labels:XO.map(r=>'HE'+r.he),datasets:[
{label:'방전마진 (에너지)',data:XO.map(r=>r.dis_margin_rt),backgroundColor:'rgba(8,153,129,.65)',borderWidth:0},
{label:'최선 AS 가격 (기회비용)',data:XO.map(r=>r.best_up_rt),backgroundColor:'rgba(255,152,0,.75)',borderWidth:0}]},
options:{...o,scales:{...o.scales,y:{...o.scales.y,title:{display:true,text:'$/MWh'}}}}});
const hm=document.getElementById('hm');let all=[];Object.values(MO).forEach(a=>a.forEach(v=>{if(v!=null&&v<200)all.push(v)}));
B27.forEach(v=>all.push(v));const mn=Math.min(...all),mx=Math.max(...all);
function col(v){if(v==null)return['#f0f2f5','#9598a1'];const t=Math.max(0,Math.min(1,(v-mn)/(mx-mn)));
return ['rgba(8,153,129,'+(0.10+t*0.75).toFixed(2)+')', t>0.55?'#fff':'#131722'];}
hm.innerHTML+='<div class="hd yr"></div>'+M.map(m=>'<div class=hd>'+m+'</div>').join('');
['2024','2025','2026'].forEach(y=>{hm.innerHTML+='<div class=yr>'+y+'</div>'+
(MO[y]||[]).map(v=>{const c=col(v);return '<div style="background:'+c[0]+';color:'+c[1]+'">'+(v==null?'\\u2014':Math.round(v))+'</div>';}).join('');});
hm.innerHTML+='<div class=yr style="color:#2962ff">2027E</div>'+B27.map(v=>{const c=col(v);
return '<div style="background:'+c[0]+';color:'+c[1]+';outline:1px solid #2962ff">'+Math.round(v)+'</div>';}).join('');
"""

DATA_JS = (
    "const DAYS_DA=" + json.dumps(days_da) + ",RVN_DA=" + json.dumps(rvn_da) + ",GKS_DA=" + json.dumps(gks_da) + ";\n"
    "const DAYS_RT=" + json.dumps(days_rt) + ",RVN_RT=" + json.dumps(rvn_rt) + ",GKS_RT=" + json.dumps(gks_rt) + ";\n"
    "const XO=" + json.dumps(json.loads(xo.to_json(orient="records"))) + ";\n"
    "const MO=" + json.dumps(mo) + ",B27=" + json.dumps(base27) + ",M=" + json.dumps(MONTHS) + ";\n")

HTML = """<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Raven (RVN_RN) 노드 분석 &amp; FY2027 매출 전망 — Draft</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>""" + CSS + """</style></head><body><div class=wrap>

<header><div><h1>Raven (RVN_RN) 노드 분석 &amp; FY2027 매출 전망</h1>
<div class=sub2>100MW / 200MWh (2h) · HOUSTON zone · 분석일 2026-09-14 · 실데이터 (Yes Energy Datalake + ERCOT 60일 공시)</div></div>
<div><span class=status>DRAFT — 피어 하절기 공시 미포함</span></div></header>

<div class=kpis>
<div class=kpi><div class=lab>하절기 DA TB2 · Raven</div><div class="val">$""" + f(st["DA"]["RVN_RN"]["mean"], 2) + """</div>
<div class="chg up">▲ GKS $""" + f(st["DA"]["GKS_BESS_RN"]["mean"], 2) + """ 대비 +""" + f(st["DA"]["RVN_minus_GKS"]["mean"], 2) + """ (+56%)</div></div>
<div class=kpi><div class=lab>하절기 RT TB2 · Raven</div><div class="val">$""" + f(st["RT"]["RVN_RN"]["mean"], 2) + """</div>
<div class="chg up">▲ GKS $""" + f(st["RT"]["GKS_BESS_RN"]["mean"], 2) + """ 대비 +""" + f(st["RT"]["RVN_minus_GKS"]["mean"], 2) + """ (+26%)</div></div>
<div class=kpi><div class=lab>FY2027 Base 매출</div><div class="val">$""" + f(rv["base_median"] / 1000, 1) + """k</div>
<div class="chg muted">$/MW-yr · 100MW 기준 $""" + f(rv["base_median"] * 100 / 1e6, 2) + """M</div></div>
<div class=kpi><div class=lab>TB2 다년 하락</div><div class="val down">−33%</div>
<div class="chg down">▼ Jan–Sep 평균 $""" + f(lvl["2024"]) + """ → $""" + f(lvl["2026"]) + """ (시스템 전반)</div></div>
<div class=kpi><div class=lab>Proxy 재현오차 (OOS)</div><div class="val">$""" + f(fc["proxy"]["oos_tb2_da_mae"], 2) + """</div>
<div class="chg up">▲ DA TB2 MAE · 45일 out-of-sample (~1%)</div></div>
<div class=kpi><div class=lab>DART 거래가능 시간</div><div class="val">7<span style="font-size:15px;color:var(--text-muted)"> /24</span></div>
<div class="chg muted">전부 LONG · 노드 고유 엣지 없음</div></div>
</div>

<div class=grid2>
<div class=panel><div class=ptitle>일별 TB2 — Raven vs GKS (2026 하절기)</div>
<div class=pnote>$/MWh · 상위 2시간 평균 − 하위 2시간 평균 · 기간종료 CT</div>
<div class=tabs><div class="tab on" onclick="sw('RT',this)">RT</div><div class=tab onclick="sw('DA',this)">DA</div></div>
<div class=chartbox><canvas id=c1></canvas></div></div>
<div class=panel><div class=ptitle>월별 RT TB2 히트맵</div><div class=pnote>$/MWh · proxy 재구성 · 2027은 Base 전망</div>
<div class=hm id=hm></div>
<div style="margin-top:12px;font-size:11px;color:var(--text-muted)">2023년은 9월부터라 제외 (Sep-23 $447 = 스카시티 이상치)</div></div>
</div>

<div class=panel><div class=ptitle>FY2027 Base 전망 — Raven 100MW/200MWh</div>
<div class=pnote>TB index (2h, 추세반영) × Houston 2h 피어 capture rate · 에너지+AS, DART 제외</div>
<div class=fc>
<div class=fcell><div class=l>2026 실측 수준</div><div class=v>$""" + f(lvl["2026"]) + """</div><div class=s>Jan–Sep 평균 TB2 $/MWh</div></div>
<div class=fcell><div class=l>2027 가정 수준</div><div class=v>$""" + f(fc["base_2027_level_tb2"]) + """</div><div class=s>×""" + str(fc["decay_assumption_2027"]) + """ (하락 지속·둔화)</div></div>
<div class=fcell><div class=l>TB index 2027</div><div class=v>$""" + f(fc["tb_index_2027_usd_per_mw_yr"], 0) + """</div><div class=s>$/MW-yr 이론최대</div></div>
<div class=fcell><div class=l>피어 capture (중앙값)</div><div class=v>""" + f(cap["base_median"]) + """%</div><div class=s>Houston 2h · n=""" + str(len(peers2h)) + """</div></div>
<div class="fcell main"><div class=l>Base 매출</div>
<div class="v" style="color:var(--accent-blue)">$""" + f(rv["base_median"], 0) + """</div><div class=s>$/MW-yr = $""" + f(rv["base_median"] * 100 / 1e6, 2) + """M</div></div>
</div>
<table style="margin-top:16px"><thead><tr><th>시나리오</th><th class=num>capture</th><th class=num>$/MW-yr</th><th class=num>100MW 합계</th><th>비고</th></tr></thead><tbody>
<tr><td>Low (피어 p25)</td><td class="num mono">""" + f(cap["low_p25"]) + """%</td><td class="num mono">$""" + f(rv["low_p25"], 0) + """</td><td class="num mono">$""" + f(rv["low_p25"] * 100 / 1e6, 2) + """M</td><td class=sub>AS 비중 낮은 운용 / 저가동</td></tr>
<tr style="background:rgba(41,98,255,.05)"><td class=b>Base (피어 중앙값)</td><td class="num mono b">""" + f(cap["base_median"]) + """%</td><td class="num mono b">$""" + f(rv["base_median"], 0) + """</td><td class="num mono b">$""" + f(rv["base_median"] * 100 / 1e6, 2) + """M</td><td class=sub>Houston 2h 피어 전형</td></tr>
<tr><td>High (피어 p75)</td><td class="num mono">""" + f(cap["high_p75"]) + """%</td><td class="num mono">$""" + f(rv["high_p75"], 0) + """</td><td class="num mono">$""" + f(rv["high_p75"] * 100 / 1e6, 2) + """M</td><td class=sub>상위 운용</td></tr>
</tbody></table>
<div style="margin-top:14px"><div class=ptitle>지배적 불확실성 — 2027 하락률 가정</div>
<table><thead><tr><th>가정</th><th class=num>TB index $/MW-yr</th><th class=num>Base capture 적용 매출</th></tr></thead><tbody>
""" + sens_rows + """</tbody></table></div></div>

<div class=panel><div class=ptitle>Houston zone BESS 실제 상품조합 — 2026-01-01 ~ 05-25</div>
<div class=pnote>ERCOT 60일 공시 실측 · 파란 행 = 2h·50MW+ (Raven 직접 비교군) · capacity는 SCED 실측 HSL 기준 ·
<b>하절기는 공시 미발행 구간이라 미포함</b></div>
<table><thead><tr><th>Resource</th><th>Node</th><th class=num>MW</th><th class=num>Dur(h)</th><th class=num>$/MW</th><th class=num>Opt%</th><th class=num>AS 비중</th></tr></thead>
<tbody>""" + peer_rows + """</tbody></table>
<div style="margin-top:10px;font-size:12px;color:var(--text-secondary)">
Houston 중앙값: <b class=mono>$""" + f(P["fleet_median"]["hou_rev_per_mw"], 0) + """</b>/MW · opt <b class=mono>""" + f(P["fleet_median"]["hou_opt"]) + """%</b> ·
AS 비중 <b class=mono>""" + f(P["fleet_median"]["hou_as_share"]) + """%</b> &nbsp;|&nbsp; 전체 fleet 중앙값 $""" + f(P["fleet_median"]["all_rev_per_mw"], 0) + """/MW</div></div>

<div class=panel><div class=ptitle>Raven 위치 영향 Top-10 Congestion (3개년, proxy 기준)</div>
<div class=pnote>누적 MCC $/MWh-h per MW · 부호 = Raven LMP에 미치는 방향 · forward = '27년 적용가능성</div>
<table><thead><tr><th>#</th><th>Constraint</th><th>Raven 영향</th><th class=num>누적 DA</th><th class=num>누적 RT</th><th class=num>DA bind%</th><th class=num>RT λ평균</th><th>Binding 월</th><th>Forward</th></tr></thead>
<tbody>""" + cong_rows + """</tbody></table>
<div style="margin-top:10px;font-size:12px;color:var(--text-secondary)">
구조적 패턴: <b>DA congestion은 매년 순(+), RT는 매년 순(−)</b> → short-DA / long-RT 편향. 10개 중 9개가 금액 기준 DART-short 방향.</div></div>

<div class=grid2>
<div class=panel><div class=ptitle>DART virtual 시간대별 — RVN_RN</div>
<div class=pnote>2026-06-04~09-13 (102일) · 우세 방향 기준 · 초록 = 거래가능 판정</div>
<table><thead><tr><th>HE</th><th>방향</th><th class=num>승률</th><th class=num>P/L</th><th class=num>EV $/MWh</th><th class=num>손실 p99</th><th class=num>t</th><th>판정</th></tr></thead>
<tbody>""" + dart_rows + """</tbody></table></div>
<div class=panel><div class=ptitle>에너지 vs AS — 레짐별 (하절기 RT)</div>
<div class=pnote>$/MW-day · energy2h = 2h 차익거래 · AS 4h = 사이클 시간 파킹 · AS 24h = 종일 파킹</div>
<table><thead><tr><th>Tightness</th><th>Congestion</th><th class=num>일수</th><th class=num>TB2</th><th class=num>에너지2h</th><th class=num>AS 4h</th><th class=num>AS 24h</th><th class=num>배율</th><th>우위</th></tr></thead>
<tbody>""" + reg_rows + """</tbody></table>
<div style="margin-top:12px;font-size:12px;color:var(--text-secondary)">
에너지 2h는 <b>사이클 4시간 AS 파킹 대비 항상 우위</b> (4.5~11.2배). 단 <b>TIGHT+POS 레짐에서만 종일 AS 파킹이 근소 우위</b>
(185 vs 188 $/MW-day) — 이 구간만 AS 비중을 높일 근거가 있음.</div></div>
</div>

<div class=panel><div class=ptitle>시간대별 방전마진 vs AS 기회비용 (하절기 RT)</div>
<div class=pnote>$/MWh · 방전마진 = 해당시간 RT − 당일 최저2시간/효율 · AS는 최선 상향상품</div>
<div class=chartbox style="height:260px"><canvas id=c2></canvas></div></div>

<div class=cv><div class=ptitle style="color:#b26a00">한계 및 유의사항 (Draft)</div><ul>
<li><b>피어 하절기 공시 미포함</b> — ERCOT 60일 공시는 D+60 발행이라 오늘(9/14) 기준 ~7/15까지만 존재. 피어 capture rate는 <b>1~5월(동절기·봄)</b> 실측이며, 가장 타이트했던 8월 피어 행동은 빠져 있음.</li>
<li><b>2027 하락률(×0.90)이 전망의 지배적 변수</b> — 위 민감도 표 참조. 관측된 YoY는 2025/24 0.765, 2026/25 0.875.</li>
<li><b>Proxy는 하절기 ~100일로만 검증됨</b> — 동절기·환절기 재구성은 미검증 (±$2–3 TB2). 또한 blend의 41%가 SOUTH zone(CBEC_ALL)이라 동절기 basis는 Raven의 것이 아닐 수 있음.</li>
<li><b>WHARTN</b>은 3개년 누적 1위 constraint이나 Raven 노출 여부를 <b>검증할 수 없음</b> — 마지막 bind가 RVN 가격 개시 직전(2026-06-02). 별도 민감도 필요.</li>
<li><b>Raven은 congestion 프리미엄 노드가 아님</b> — TB2가 HB_HOUSTON과 동등, 시스템 평균(HB_BUSAVG)보다 낮음. GKS 대비 +56%를 그대로 곱하면 과대추정.</li>
<li>TB index는 2 MWh/MW/일 · 왕복효율 미반영 기준. 피어 opt_rate도 동일 기준이라 비율은 정합적.</li>
<li>신규 ERCOT 저장장치 유입 · AS 가격 감쇠 · RTC+B 효과는 추세에 암묵적으로만 반영됨 (명시적 모델링 아님).</li>
<li>DART virtual 수익은 전망치에서 <b>제외</b> — 노드 고유 엣지가 확인되지 않음.</li>
</ul></div>

</div><script>""" + DATA_JS + JS + """</script></body></html>"""

out = ROOT / "reports/ad-hoc/2026-09-14_Raven_RVN_RN_FY2027_outlook_DRAFT.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(HTML, encoding="utf-8")
print("wrote", out, "(", format(len(HTML), ","), "bytes )")
