"""Rebuild dashboard chapter '운용 전략 ① — 에너지 vs 보조서비스':
  - peer table: only the top-3 Houston sites (WAL, CLO = ESR1+ESR2 combined, LON)
  - NEW: hourly product stack of these peers (RT actual / DA award x site x season), interactive
  - insights from the stack; GKS contrast as a short callout
  - REMOVE the old hourly 'discharge vs AS' chart+table (c2); keep the market-regime table
"""
from pathlib import Path

R = Path(__file__).resolve().parent / "exec_render_html.py"
s = R.read_text(encoding="utf-8")

# ---------------------------------------------------------------- 1. python-side data prep (inserted before tables marker)
PREP = r'''# ------------------------------------------------------------------ Houston top-3 peers: table + hourly stack
pstack = jload("peer_hourly_stack.json")
top3_rows = ""
_pk = pd.DataFrame(P["peers"])
_sites = [("WAL", "Tesla", ["WAL_ESR1"]), ("CLO", "Jupiter Power", ["CLO_ESR1", "CLO_ESR2"]), ("LON", "Tokyo Gas America", ["LON_ESR1"])]
for i, (site, comp, units) in enumerate(_sites, 1):
    u = _pk[_pk.resource_name.isin(units)]
    if u.empty:
        continue
    capmw = float(u.cap_mw.sum()); rev = float(u.total_rev.sum())
    revmw = rev / capmw
    opt = float((u.opt_rate_pct * u.total_rev).sum() / rev)
    asr = float((u.as_share_pct * u.total_rev).sum() / rev)
    top3_rows += (
        '<tr><td class=mono>' + str(i) + '</td><td><b>' + site + '</b><div class=sub>' + comp + (' · 2기 합산' if len(units) > 1 else '') + '</div></td>'
        '<td class="num mono">' + f(capmw, 0) + '</td><td class="num mono b">$' + f(revmw, 0) + '</td>'
        '<td class="num mono">' + f(opt, 1) + '%</td><td class="num mono">' + f(asr, 1) + '%</td></tr>')
_ps = (pstack or {}).get("summary", {})
'''
anchor = "# ------------------------------------------------------------------ tables"
assert anchor in s
s = s.replace(anchor, PREP + "\n" + anchor, 1)

# ---------------------------------------------------------------- 2. chapter HTML
START = "<!-- ============ Ⅴ 에너지 vs 보조 ============ -->"
END = "<!-- ============ Ⅵ DART ============ -->"
i, j = s.index(START), s.index(END)

NEW = r'''<!-- ============ Ⅴ 에너지 vs 보조 ============ -->
<h2><span class=n>Ⅵ</span>운용 전략 ① — 에너지 vs 보조서비스</h2>
<div class=ans><div class=k>답</div>
<div class=v>에너지와 보조서비스는 양자택일이 아니라 "시간대별로 겹쳐 쌓는" 문제다.
Houston 상위 3사는 설비의 약 60%를 늘 보조서비스에 걸어두면서, 실시간시장에서 하루 약 0.7회(2시간 배터리 기준) 방전한다</div>
<ul>
<li><b>보조서비스를 상시 기본층으로</b> — 시간대와 무관하게 설비의 <b>55~60%</b>가 보조서비스에 배정된다 (RRS가 바닥층, ECRS·NonSpin이 그 위)</li>
<li><b>충전하는 한낮에 상향 예비력을 가장 많이 판다</b> — 충전 중인 출력은 줄이면 곧 공급이 되므로, 충전과 ECRS·NonSpin 판매가 동시에 가능하다</li>
<li><b>에너지는 실시간시장 중심</b> — 방전량의 약 70%를 실시간에서 처리, DA 에너지 매각은 30% 수준 (CLO는 거의 0)</li>
<li><b>여름엔 "한낮 충전 → 17~19시 예비력 대기 → 20~22시 집중 방전"</b>, 겨울·봄엔 <b>아침·저녁 2회 방전</b></li>
<li>보조서비스 가격은 <b>ERCOT 전 지역 단일 가격</b>이라 위치와 무관 — Raven도 Houston 상위사와 같은 조합이 가능하다</li>
</ul></div>

<div class=g11>
<div class=panel><div class=pt>Houston 상위 3개 발전소 (2026년 1~5월 실측)</div>
<div class=pn>Raven 직접 비교군(2시간·50MW 이상) 중 MW당 매출 상위 3개 사이트 · 용량은 실제 운전 기록 기준 · CLO는 동일 사이트 2기 합산</div>
<table><thead><tr><th>#</th><th>발전소</th><th class=num>MW</th><th class=num>MW당 매출</th><th class=num>달성률</th><th class=num>보조 매출 비중</th></tr></thead>
<tbody>''' + '""" + top3_rows + """' + r'''</tbody></table>
<div class=note>최고 성과 발전소 <b>WAL</b>이 위치한 노드는 분석 과정에서 <b>Raven과 가격이 가장 유사한 노드</b>로 확인되었다 — 가장 직접적인 벤치마크 대상이다.
3사 모두 <b>보조서비스가 매출의 38~39%</b>를 차지한다.</div>

<div class=pt style="margin-top:18px">시장 상황별 최적 조합</div>
<div class=pn>MW당 일수익 $ · 실시간시장 기준 · 2026년 여름</div>
<table><thead><tr><th>수급</th><th>혼잡</th><th class=num>일수</th><th class=num>에너지 2h</th><th class=num>보조 4h</th><th class=num>보조 24h</th><th>우위</th></tr></thead>
<tbody>''' + '""" + reg_rows + """' + r'''</tbody></table>
<div class=note>충방전 4시간을 보조서비스로 돌리는 것은 어떤 상황에서도 손해(에너지가 4.5~11.2배)다.
<b>시장이 타이트하고 혼잡이 유리한 날에만</b> 종일 보조서비스 대기가 근소 우위다.</div></div>

<div class=panel><div class=pt>상위 3사의 시간대별 상품 배치</div>
<div class=pn>설비 용량 대비 % · 막대 위쪽 = 방전과 보조서비스, 아래쪽 = 충전 · ERCOT 60일 공시 2025-12-05 ~ 2026-07-17 (220일)</div>
<div class=tabs id=pt1>
<div class="tab on" onclick="psel('site','PEER_AVG',this,'pt1')">3사 평균</div>
<div class=tab onclick="psel('site','WAL',this,'pt1')">WAL</div>
<div class=tab onclick="psel('site','CLO',this,'pt1')">CLO</div>
<div class=tab onclick="psel('site','LON',this,'pt1')">LON</div></div>
<div class=tabs id=pt2>
<div class="tab on" onclick="psel('mkt','rt',this,'pt2')">실시간 실제 배치</div>
<div class=tab onclick="psel('mkt','da',this,'pt2')">전일시장 배정</div>
<span style="width:14px"></span>
<div class="tab on" id=ps_all onclick="psel('season','all',this,'pt3')">전체</div>
<div class=tab onclick="psel('season','겨울·봄(12~5월)',this,'pt3')">겨울·봄</div>
<div class=tab onclick="psel('season','여름(6~7월)',this,'pt3')">여름</div></div>
<div class=chartbox style="height:340px"><canvas id=cps></canvas></div>
<div class=sub id=psnote style="margin-top:6px"></div>
</div>
</div>

<div class=g11>
<div class=panel><div class=pt>시사점 — 상위 3사 운용 방식</div>
<table><thead><tr><th style="width:130px">시간대</th><th>무엇을 하는가 (3사 평균, 실시간 기준)</th></tr></thead><tbody>
<tr><td><b>새벽 1~5시</b></td><td>소량 충전(6~12%) + <b>NonSpin·RRS 대기</b>(합계 25~33%) — 싼 야간 전력으로 일부 채워 둠</td></tr>
<tr><td><b>아침 7~8시</b></td><td><b>1차 방전</b>(10~12%, 겨울·봄 중심) + RegUp 증가 — 아침 수요 급증 대응</td></tr>
<tr style="background:rgba(41,98,255,.06)"><td><b>한낮 9~16시</b></td><td><b>본 충전</b>(최대 18%) + <b>ECRS 20~27% · NonSpin 15~23% 동시 판매</b> — 충전 출력은 줄이면 곧 공급이므로 상향 예비력 판매와 겹칠 수 있다</td></tr>
<tr style="background:rgba(41,98,255,.06)"><td><b>오후 17~19시</b></td><td>방전 준비 — <b>ECRS·NonSpin을 최대로 유지</b>(여름 ECRS 35~38%), 에너지는 아직 소량</td></tr>
<tr style="background:rgba(8,153,129,.08)"><td><b>저녁 20~22시</b></td><td><b>본 방전</b>(최대 25%, 여름 21시 36%) — 이때 보조서비스는 가장 낮게(ECRS 8~12%)</td></tr>
</tbody></table>
<div class="note g"><b>Raven 운용에 주는 시사점</b><br>
① <b>보조서비스를 "남는 시간에 파는 것"이 아니라 상시 기본층</b>으로 설계한다 — 설비의 절반 이상<br>
② <b>충전 시간을 비워두지 않는다</b> — 한낮 충전과 ECRS·NonSpin 판매를 동시에<br>
③ <b>에너지는 실시간 중심</b>으로 가격 급등 기회를 남겨 둔다 — DA 에너지 매각은 일부만<br>
④ <b>계절 전환</b>: 여름은 저녁 1회 집중 방전, 겨울·봄은 아침·저녁 2회</div></div>

<div class=panel><div class=pt>참고 — 우리 GKS와 비교</div>
<div class=pn>같은 기간 · 설비 용량 대비</div>
<table><thead><tr><th>항목</th><th class=num>상위 3사 평균</th><th class=num>GKS</th></tr></thead><tbody>
<tr><td>실시간 방전량 (하루, 설비 가득 방전 시간 환산)</td><td class="num mono b">''' + '""" + f(_ps.get("PEER_AVG", {}).get("rt_discharge_hours_equiv"), 2) + """' + r'''시간</td><td class="num mono down b">''' + '""" + f(_ps.get("GKS", {}).get("rt_discharge_hours_equiv"), 2) + """' + r'''시간</td></tr>
<tr><td>실시간 보조서비스 배정 (평균)</td><td class="num mono b">''' + '""" + f(_ps.get("PEER_AVG", {}).get("avg_as_pct_rt"), 0) + """' + r'''%</td><td class="num mono down b">''' + '""" + f(_ps.get("GKS", {}).get("avg_as_pct_rt"), 0) + """' + r'''%</td></tr>
<tr><td>전일시장 보조서비스 배정 (평균)</td><td class="num mono">''' + '""" + f(_ps.get("PEER_AVG", {}).get("avg_as_pct_da"), 0) + """' + r'''%</td><td class="num mono">''' + '""" + f(_ps.get("GKS", {}).get("avg_as_pct_da"), 0) + """' + r'''%</td></tr>
<tr><td>방전 중 DA 에너지 매각 비중</td><td class="num mono">''' + '""" + f((_ps.get("PEER_AVG", {}).get("da_energy_share_of_rt_discharge") or 0) * 100, 0) + """' + r'''%</td><td class="num mono">0%</td></tr>
</tbody></table>
<div class="note w"><b>GKS는 방전량이 상위 3사의 약 56%에 그치고, 실시간 보조서비스 배정도 3분의 1 수준</b>이다.
대신 전일시장에서 NonSpin을 새벽에 설비의 60%까지 팔고 실시간에서는 대부분 되사는 구조다.
저녁 혼잡(Ⅳ장) 영향도 있지만, <b>운용 방식 자체의 차이</b>가 GKS 달성률(43.7%)이 상위사(60~86%)보다 낮은 이유 중 하나로 보인다.</div>
<div class=note>※ 전일시장 보조서비스 배정은 금융적 약정, 실시간 배정은 실제 대기 책임이다. 두 값이 다르면 그 차이만큼 실시간 가격으로 정산된다.</div>
<div class="note w" style="margin-top:10px">공시 데이터는 60일 지연 발행이라 <b>7월 중순까지</b>만 반영됐다. 2025-12-05(실시간 통합최적화 시행 첫날) 실시간 RegUp·RegDown 기록은 오류값(음수)이라 제외했다.</div></div>
</div>

'''
s = s[:i] + NEW + s[j:]

# ---------------------------------------------------------------- 3. JS: remove old c2 chart, add stack chart
old_c2_start = s.index("new Chart(document.getElementById('c2')")
old_c2_end = s.index("});", old_c2_start) + 3
s = s[:old_c2_start] + s[old_c2_end:]

JS_ADD = r'''
const PSC=[['dis','방전','#089981'],['chg','충전','#9ed9cf'],['regup','RegUp','#2962ff'],['regdn','RegDown','#7aa2ff'],
 ['rrs','RRS','#6d4c9f'],['ecrs','ECRS','#ff9800'],['nonspin','NonSpin','#ffcc80']];
let PST={site:'PEER_AVG',mkt:'rt',season:'all'};
function pdata(){
  const src=PST.season==='all'?PS.profiles:(PS.profiles_season[PST.season]||{});
  const p=src[PST.site]||src['PEER_AVG']; const m=PST.mkt;
  const key=k=>k==='dis'?m+'_dis':k==='chg'?m+'_chg':m+'_'+k+'_mw';
  return PSC.map(([k,l,c])=>({label:l,data:(p?p[key(k)]:[]).map(v=>+(+v).toFixed(1)),backgroundColor:c,borderWidth:0,stack:'s'}));
}
const pchart=new Chart(document.getElementById('cps'),{type:'bar',data:{labels:[...Array(24)].map((_,i)=>(i+1)+'시'),datasets:pdata()},
 options:{...o,plugins:{...o.plugins,tooltip:{callbacks:{label:c=>c.dataset.label+': '+c.parsed.y.toFixed(1)+'%'}}},
 scales:{x:{stacked:true,grid:{display:false}},y:{stacked:true,grid:{color:'#eceff3'},ticks:{callback:v=>v+'%'},title:{display:true,text:'설비 용량 대비 %'}}}}});
function pnote(){
  const n=document.getElementById('psnote'); const s=PST.season!=='all';
  n.textContent=(PST.site==='PEER_AVG'?'3사 동일가중 평균':PST.site+' 단독')+' · '+(PST.mkt==='rt'?'실시간 실제 출력과 실시간 보조서비스 배정':'전일시장 에너지 낙찰과 보조서비스 낙찰')+' · '+(s?PST.season:'전체 기간')+(PST.site!=='PEER_AVG'&&s?' (계절 분리는 3사 평균만 제공)':'');
}
function psel(k,v,el,grp){
  PST[k]=v;
  const box=document.getElementById(grp==='pt3'?'pt2':grp);
  box.querySelectorAll('.tab').forEach(t=>{
    const isSeason=['전체','겨울·봄','여름'].includes(t.textContent);
    if((grp==='pt3')===isSeason) t.classList.remove('on');
  });
  el.classList.add('on');
  if(k==='site'&&v!=='PEER_AVG'&&PST.season!=='all'){PST.season='all';box.parentNode.querySelectorAll('#pt2 .tab').forEach(t=>{if(['겨울·봄','여름'].includes(t.textContent))t.classList.remove('on')});document.getElementById('ps_all').classList.add('on');}
  pchart.data.datasets=pdata(); pchart.update(); pnote();
}
pnote();
'''
anchor_js = "const hm=document.getElementById('hm');"
assert anchor_js in s
s = s.replace(anchor_js, JS_ADD + anchor_js, 1)

anchor_data = '    "const GKSBASIS=" + json.dumps(gks_basis_he) + ";\\n"'
assert anchor_data in s
s = s.replace(anchor_data, anchor_data + '\n    "const PS=" + json.dumps(pstack or {}, ensure_ascii=False) + ";\\n"', 1)

R.write_text(s, encoding="utf-8")
print("energy-vs-AS chapter rebuilt; c2 removed; stack chart added")
