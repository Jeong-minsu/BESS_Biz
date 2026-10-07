"""Replace the dashboard DART chapter with the 3-year proxy + forecast-tightness analysis,
relabel sides as SHORT (DA sell -> RT buy) / LONG (DA buy -> RT sell), and add CSS for heat grids."""
from pathlib import Path

R = Path(__file__).resolve().parent / "exec_render_html.py"
s = R.read_text(encoding="utf-8")

START = "<!-- ============ Ⅵ DART ============ -->"
END = "<!-- ============ Ⅶ 가격차 거래 ============ -->"
i, j = s.index(START), s.index(END)

NEW = r'''<!-- ============ Ⅵ DART ============ -->
<h2><span class=n>Ⅶ</span>운용 전략 ② — 가상거래(DART)</h2>

<div class="panel" style="border-left:4px solid var(--tx);padding:14px 18px">
<div class=pt>용어 — 이 장의 방향 표기</div>
<table style="margin-top:6px"><thead><tr><th style="width:120px">표기</th><th>거래</th><th>수익이 나는 경우</th></tr></thead><tbody>
<tr><td><span class="pill sh">SHORT</span></td><td><b>전일시장(DA)에서 팔고 → 실시간시장(RT)에서 되산다</b></td><td>DA 가격 &gt; RT 가격 (가격차 = DA − RT 가 <b>+</b>)</td></tr>
<tr><td><span class="pill lg">LONG</span></td><td><b>전일시장(DA)에서 사고 → 실시간시장(RT)에서 되판다</b></td><td>RT 가격 &gt; DA 가격 (가격차 = DA − RT 가 <b>−</b>)</td></tr>
</tbody></table>
<div class=sub style="margin-top:6px">가상거래는 실물 발전 없이 두 시장의 가격차만 취하는 금융 거래다. 아래 모든 표·그림에서 <b style="color:#2962ff">파랑 = SHORT 유리</b>, <b style="color:#e68900">주황 = LONG 유리</b>.</div>
</div>

<div class=ans><div class=k>답</div>
<div class=v>Raven 고유의 수익원은 없지만, 3년 데이터에서 "오후·저녁 SHORT"라는 시장 전체의 패턴이 확인됐다.
예측상 계통이 타이트한 날 가장 강하며, 2026년 사후검증에서도 수익이 났다 — 다만 규모는 작다</div>
<ul>
<li><b>3년(2023.12~2026.9) 기준, 오후·저녁 14~19시 SHORT</b>가 3개 연도 모두 같은 방향이고 통계적으로 뚜렷하다 (DA가 RT보다 비싸게 형성되는 경향)</li>
<li><b>입찰 전 발표된 예측</b>(수요·풍력·태양광)상 <b>타이트한 날</b>에는 15~19시 SHORT가 평균 <b>+$3~10/MWh</b> — 여유로운 날의 몇 배</li>
<li>계절별로는 <b>겨울 낮 12~16시</b>, <b>봄·여름 저녁 17~19시</b> SHORT가 강하고, <b>여름 아침 7~8시만 LONG</b>이 작지만 3년 일관</li>
<li><b>2024~2025년 데이터로 고른 규칙을 2026년에 그대로 적용</b>한 결과 흑자. 단 1월 한파 이틀이 수익의 큰 몫이고, 실측 Raven 가격으로는 대리노드 대비 수익이 35~60% 낮다</li>
<li><b>최선안(예측 타이트함 × 시간대)</b>: 실측 가격 기준 평균 <b>+$1.00/MWh</b>, 적중 60% → MW당 연 약 <b>$1.3~2.5천</b>. <b>소규모(10~20MW) 시범 운용</b> 수준이 적정</li>
</ul></div>

<div class=panel><div class=pt>① 3년 시간대별 기본 분석 — 대리 노드 기준</div>
<div class=pn>2023-12-01 ~ 2026-09-13 (1,017일) · 가격차 = DA − RT ($/MWh) · 승률·손익비·손실은 우세 방향 기준 · "급등 제외 평균" = 상하위 1% 시간을 잘라낸 평균 (소수 급등일 의존 여부 확인)</div>
<table><thead><tr><th>시간</th><th>우세 방향</th><th class=num>평균 가격차</th><th class=num>승률</th><th class=num>손익비<div class=sub>평균이익÷평균손실</div></th>
<th class=num>최악 1% 손실</th><th class=num>급등 제외 평균</th><th>연도별 방향<div class=sub>'24 '25 '26</div></th><th>판단</th></tr></thead>
<tbody>''' + '""" + d3_rows + """' + r'''</tbody></table>
<div class=note><b>3년 전체로 보면 하루 24시간 모두 평균적으로 SHORT가 유리</b>하다. 그중 <b>9~12시, 14~15시, 17~19시</b>는 3년 모두 같은 방향이고 급등일을 빼도 유지된다.
반면 <b>6~8시의 큰 평균값은 겨울 한파 며칠이 만든 것</b>이라 급등 제외 시 크게 줄어든다. 20~21시는 평균은 크지만 최악 1% 손실이 $137~199로 위험이 크다.</div>
<div class="note w"><b>앞선 분석(2026년 여름 102일)과 다른 이유</b> — 여름 102일만 보면 "아침 LONG"이 유리했지만, 3년으로 넓히면 <b>SHORT가 기본값</b>이다.
2026년 여름은 가격차가 이례적으로 음(−)이었던 시기였다 (여름 평균: 2024 +1.54, 2025 +2.54, <b>2026 −0.36</b>).</div>
</div>

<div class=g11>
<div class=panel><div class=pt>② 계절 × 시간대</div>
<div class=pn>평균 가격차 $/MWh · <b>굵은 테두리</b> = 통계적으로 뚜렷하고(t≥2) 모든 연도에서 같은 방향 · 칸에 마우스를 올리면 상세</div>
''' + '""" + hg_season + """' + r'''
<div class=note><b>유효한 패턴 (굵은 테두리)</b><br>
· <b>겨울</b>: 9~16시 SHORT — 난방 수요 예측이 DA에 과하게 반영<br>
· <b>봄</b>: 12시, 17~18시 SHORT<br>
· <b>여름</b>: 14시·16~19시 SHORT (19시 +$7.8) / <b>7~8시 LONG</b> (작지만 3년 일관)<br>
· <b>가을</b>: 뚜렷한 패턴 없음</div></div>

<div class=panel><div class=pt>③ 예측 기준 계통 타이트함 × 시간대</div>
<div class=pn>타이트함 = 입찰 전(전날 오전 7~9시) 발표된 ERCOT 예측으로 계산한 <b>다음날 피크 순수요</b>(수요 − 풍력 − 태양광)를 직전 60일과 비교해 상·중·하 3등분 · 계절 영향이 자동 보정됨</div>
''' + '""" + hg_tight + """' + r'''
<div class=note><b>타이트할수록 SHORT가 강해진다.</b> 예측상 타이트한 날 15~19시는 <b>+$3.0~9.5</b>로 뚜렷하고,
여유로운 날은 대부분 ±$1 수준으로 방향성이 약하다. → <b>시장이 타이트할 것으로 예상되면 DA에 희소성 프리미엄이 과하게 붙고,
실제 RT에서는 그만큼 실현되지 않는 경우가 많다</b>는 뜻이다.</div>
<div class=sub style="margin-top:8px">예측 정확도 검증: 예측 피크 순수요와 실제의 상관 0.976, 평균 오차 2.1GW · 1,018일 모두 입찰 마감 전 발표분 사용(사후정보 0건)</div></div>
</div>

<div class=panel><div class=pt>④ 계절 × 예측 타이트함 × 시간 구간</div>
<div class=pn>평균 가격차 $/MWh · 색 표시 = 통계적으로 뚜렷하고 모든 연도 같은 방향인 칸만</div>
<table><thead><tr><th>계절 · 예측 타이트함</th><th class=num>새벽 1–6시</th><th class=num>아침 7–11시</th><th class=num>낮 12–16시</th><th class=num>저녁 17–21시</th><th class=num>밤 22–24시</th></tr></thead>
<tbody>''' + '""" + d3_block_rows + """' + r'''</tbody></table>
<div class="note w">칸을 잘게 나눌수록 표본이 줄어 <b>우연히 좋아 보이는 칸</b>이 섞인다. 아래 ⑤ 사후검증에서 이 방식(④)은 2026년에 1월 외 흑자월이 2개뿐이라 <b>기각</b>했다.
예: 겨울·타이트·아침 +$28은 한파 며칠이 만든 값이다.</div></div>

<div class=panel><div class=pt>⑤ 사후검증 — 과거로 고른 규칙이 미래에도 통하는가</div>
<div class=pn><b>2023.12~2025년 데이터만으로</b> 규칙을 고르고(t≥2, 2024·2025 모두 같은 방향, 급등 제외해도 같은 방향), <b>2026년 1~9월에 그대로 적용</b> · 수익은 MW당 누적 $ · 실측 검증 = 같은 규칙을 6/4~9/13 <b>실제 Raven 가격</b>에 적용</div>
<table><thead><tr><th>규칙 방식</th><th class=num>학습기간<div class=sub>평균수익</div></th><th class=num>2026<div class=sub>평균수익</div></th><th class=num>2026<div class=sub>적중</div></th>
<th class=num>2026 누적<div class=sub>$/MW</div></th><th class=num>급등 3일·최악 3일<div class=sub>제외 시</div></th><th class=num>흑자월</th><th class=num>최대 누적손실</th>
<th class=num>실측 Raven<div class=sub>평균수익</div></th><th>판정</th></tr></thead>
<tbody>''' + '""" + oos_rows_d3 + """' + r'''</tbody></table>
<div class="note g"><b>최선안 ③ — 운용 규칙 (입찰 전 예측만으로 판단 가능)</b><br>
· <b>예측상 타이트한 날</b>: 15~19시 SHORT (학습기간 평균 +$3.4~9.7/MWh)<br>
· <b>보통인 날</b>: 새벽 1시, 9~10시, 12~13시, 15시 SHORT (소폭)<br>
· <b>여유로운 날</b>: 11~14시 SHORT (소폭)<br>
→ 2026년 적용 시 9개월 중 7개월 흑자, 최대 누적손실 MW당 $539, 실측 Raven 가격 기준 평균 +$1.00/MWh, 적중 60%</div>
<div class="note w"><b>⚠ 유의사항</b><br>
· <b>2026년 수익의 상당 부분이 1월 한파(1/25~26)</b>에서 나왔다 — 한파 전 DA가 과열됐다가 RT에서 식은 전형적 사례. 반복되는 패턴이지만 연 1~2회라 변동이 크다<br>
· <b>실측 가격으로는 대리 노드보다 수익이 35~60% 낮다</b> (③: 대리 $811 vs 실측 $526, 6~9월) — 실제 기대치는 실측 기준으로 잡아야 한다<br>
· <b>Raven 고유의 수익이 아니다</b> — Raven 가격차의 95%가 시장 전체에서 오므로, 같은 규칙을 허브에서 해도 결과는 비슷하다. GKS와 합산해 리스크 한도를 관리해야 한다<br>
· 수수료·체결 실패·입찰 가격 설정은 반영하지 않은 이론치다</div>
<div class=note><b>이전 검토(4,394개 전략, "기회 없음")와의 차이</b> — 이전 검토는 입찰 시점에 쓸 수 있는 정보를 <b>지난 가격·지난 혼잡</b>으로 한정했고, 그 신호들은 효과가 없었다.
이번에는 <b>입찰 전 발표된 수요·풍력·태양광 예측</b>을 새로 확보해 구분 기준으로 썼고, 3년 표본으로 넓혔다. 그 결과 <b>예측 타이트함이 실제로 유효한 신호</b>임이 확인됐다.</div>
</div>

<div class=panel><div class=pt>검토 요청 — Raven의 평균 가격차가 GKS보다 낮아서 메리트가 없는 것인가?</div>
<div class=ans style="margin-top:6px"><div class=k>답</div>
<div class=v>아니다 — Raven의 평균 가격차는 오히려 GKS의 2.6배다. 메리트가 제한적인 이유는 "크기"가 아니라 "차별성"이다</div></div>
<div class=g11 style="margin-bottom:0">
<div><table><thead><tr><th>평균 가격차 (DA − RT)<div class=sub>$/MWh · + = SHORT 유리</div></th><th class=num>Raven</th><th class=num>GKS</th><th class=num>시스템</th></tr></thead><tbody>
''' + '""" + ("".join(\n    \'<tr><td>\' + str(r["year"]) + \'</td>\'\n    \'<td class="num mono b">\' + (format(r["RAVEN"]["mean"], "+.2f") if r.get("RAVEN") else "—") + \'</td>\'\n    \'<td class="num mono">\' + (format(r["GKS"]["mean"], "+.2f") if r.get("GKS") else "—") + \'</td>\'\n    \'<td class="num mono">\' + (format(r["HUB_SYS"]["mean"], "+.2f") if r.get("HUB_SYS") else "—") + \'</td></tr>\'\n    for r in (q2 or {}).get("by_year", []) if r["year"] >= 2024)) + """' + r'''
<tr style="background:rgba(41,98,255,.06)"><td><b>3년 전체</b></td><td class="num mono b">+1.44</td><td class="num mono b">+0.55</td><td class="num mono">+1.13</td></tr>
</tbody></table></div>
<div><table><thead><tr><th>가격차 변동 중 노드 고유 요인</th><th class=num>Raven</th><th class=num>GKS</th></tr></thead><tbody>
<tr><td>노드 고유 요인 비중</td><td class="num mono b">4.9%</td><td class="num mono b">98.9%</td></tr>
<tr><td>노드 고유 요인의 평균 기여</td><td class="num mono">+0.32</td><td class="num mono down">−0.61</td></tr>
</tbody></table></div>
</div>
<div class=note><b>Raven의 +1.44는 사실상 시장 전체의 가격차다</b> (Houston 기준가격 +1.37과 거의 동일). GKS가 낮은 이유는 시장 가격차(+1.13)를 <b>자기 노드 혼잡(−0.61)이 상쇄</b>했기 때문이다.
→ Raven 가상거래는 <b>허브나 다른 노드에서 해도 결과가 같으므로</b>, GKS와 별개의 수익원으로 계상하면 <b>같은 시장 리스크를 두 번 세는 것</b>이다.</div>
<div class="note w"><b>⚠ 중간보고 정정</b> — "전날 방향을 따라가는 규칙이 하루 $42 수익"은 <b>미래 정보를 사용한 오류</b>였다.
입찰 마감(전날 10시) 시점에 확정된 정보만 쓰면 <span class=mono>+$42.4/일 → <b>−$2.3/일</b></span>. 해당 규칙은 폐기했다.</div>
</div>

'''
s = s[:i] + NEW + s[j:]

CSS_ADD = """
.pill.sh{background:rgba(41,98,255,.13);color:#2962ff}
.pill.lg{background:rgba(255,152,0,.16);color:#b26a00}
.yb{display:inline-block;width:26px;text-align:center;font-size:10.5px;font-family:'JetBrains Mono',monospace;border-radius:3px;margin-right:2px;padding:1px 0;background:var(--pnl2);color:var(--tx3)}
.yb.sh{background:rgba(41,98,255,.15);color:#2962ff;font-weight:600}.yb.lg{background:rgba(255,152,0,.18);color:#b26a00;font-weight:600}
.hg{display:grid;grid-template-columns:78px repeat(24,minmax(22px,1fr));gap:2px;overflow-x:auto;margin-bottom:6px}
.hg div{font-size:10px;text-align:center;padding:6px 0;border-radius:2px;font-family:'JetBrains Mono',monospace}
.hg .hh{color:var(--tx2);font-weight:600;background:none;padding:2px 0}
.hg .hr{text-align:right;padding-right:6px;color:var(--tx2);font-weight:600;background:none;font-family:inherit;font-size:11px;white-space:nowrap}
"""
anchor = ".gl .r b{color:var(--tx)}.gl .r span{color:var(--tx2)}"
assert anchor in s
s = s.replace(anchor, anchor + CSS_ADD, 1)
R.write_text(s, encoding="utf-8")
print("DART chapter replaced; CSS added")
