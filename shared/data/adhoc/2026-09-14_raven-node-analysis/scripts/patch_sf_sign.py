"""Presentation fix: show shift factors as PRICE-IMPACT sign (= -SF) in the executive dashboard + MD.

ERCOT convention: congestion price component MCC = -SF x shadow price, so a raw SF of +0.241
(E_PASP at GKS) LOWERS that node's price. Executives read "+" as bullish, so we display -SF:
  + = constraint binding raises the node's price (bullish), - = lowers it (bearish).
Verified beforehand: sign(-SF) matches the cumulative congestion contribution for all 11 constraints.
Only presentation strings change; derived analyst files keep the raw ERCOT convention.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
R = Path(__file__).resolve().parent / "exec_render_html.py"
MD = ROOT / "reports/ad-hoc/2026-09-14_Raven_RVN_RN_FY2027_outlook.md"


def sub(text, pairs, label):
    for a, b in pairs:
        assert a in text, f"[{label}] anchor not found: {a[:70]}"
        text = text.replace(a, b)
    return text


r = R.read_text(encoding="utf-8")
r = sub(r, [
    # table cells: flip sign, colour by price direction, no "-0.000"
    ("""            '<td class="num mono">' + f(sr, 3)
            + ('<div class=sub><span class="pill amber" style="font-size:10px">GKS와 반대</span></div>'
               if sf.get("relation_rvn_vs_gks") == "OPPOSING" else '') + '</td>'
            '<td class="num mono">' + f(sg, 3) + '</td>'""",
     """            pi_cell(sr)
            + ('<div class=sub><span class="pill amber" style="font-size:10px">GKS와 반대</span></div>'
               if sf.get("relation_rvn_vs_gks") == "OPPOSING" else '') + '</td>'
            + pi_cell(sg) + '</td>'"""),
    ("""drv_rows = ""
if drivers:""",
     """def pi_cell(raw_sf):
    \"\"\"Price-impact coefficient = -SF (+ bullish / - bearish), as an opening <td>.\"\"\"
    if raw_sf is None:
        return '<td class="num mono muted">—'
    v = -raw_sf
    if abs(v) < 0.0005:
        return '<td class="num mono muted">0.000'
    return '<td class="num mono ' + ("up" if v > 0 else "down") + '">' + format(v, "+.3f")


drv_rows = \"\"
if drivers:"""),
    ("<li><b>가설 확인</b>: STP-WAP 제약에서 정반대 확인 (Raven −0.021 vs GKS +0.094)</li>",
     "<li><b>가설 확인</b>: STP-WAP 제약에서 정반대 확인 — Raven <b>+0.021 (가격 상승)</b> vs GKS <b>−0.094 (가격 하락)</b></li>"),
    ("<li><b>영향계수</b>: 해당 발전소 출력 1MW 변화가 그 송전선 부하에 주는 영향. 부호에 따라 가격이 오르거나 내린다</li>",
     "<li><b>가격 영향계수</b>: 제약이 발생했을 때 해당 노드 가격이 움직이는 방향과 크기. "
     "<b>+ = 가격 상승(유리)</b>, <b>− = 가격 하락(불리)</b>. 예: GKS의 E_PASP −0.241 → 제약 가격 $100당 GKS 가격 $24 하락</li>"),
    ("<th class=num>Raven 영향계수</th><th class=num>GKS 영향계수</th>",
     "<th class=num>Raven 가격 영향<div class=sub>+상승 / −하락</div></th><th class=num>GKS 가격 영향<div class=sub>+상승 / −하락</div></th>"),
    ("또한 <b>E_PASP 제약은 GKS가 Raven보다 8배 민감</b>하다 — 같은 제약이 두 자산에 전혀 다르게 작용한다.<br>",
     "또한 <b>E_PASP 제약은 두 노드 모두 가격을 끌어내리지만 GKS(−0.241)가 Raven(−0.030)보다 8배 크게</b> 받는다 — 같은 제약이 두 자산에 전혀 다른 강도로 작용한다.<br>"),
    ("<div class=r><b>영향계수</b><span>발전소 출력 1MW 변화가 해당 송전선 부하에 주는 영향. 부호에 따라 유불리가 갈린다</span></div>",
     "<div class=r><b>가격 영향계수</b><span>제약 발생 시 해당 노드 가격이 움직이는 방향과 크기. +는 가격 상승, −는 하락. "
     "제약 가격(원) × 계수 = 노드 가격 변화. ERCOT 원자료(shift factor)와 부호가 반대로 표기됨</span></div>"),
], "dashboard")
R.write_text(r, encoding="utf-8")

m = MD.read_text(encoding="utf-8")
m = sub(m, [
    ("| 송전 제약 | Raven 영향계수 | GKS 영향계수 | 방향 |",
     "| 송전 제약 | Raven 가격 영향 | GKS 가격 영향 | 방향 |"),
    ("| **STP-WAP** (제안하신 사례) | −0.021 | **+0.094** | **정반대 ✓** |",
     "| **STP-WAP** (제안하신 사례) | **+0.021** (상승) | **−0.094** (하락) | **정반대 ✓** |"),
    ("| STPELM27_1 | +0.060 | **−0.070** | **정반대 ✓** |",
     "| STPELM27_1 | −0.060 (하락) | **+0.070** (상승) | **정반대 ✓** |"),
    ("*(영향계수 = 해당 발전소 출력 1MW 변화가 그 송전선 부하에 미치는 영향. 부호가 반대면 한쪽에 유리한 혼잡이 다른 쪽엔 불리하다)*",
     "*(가격 영향 = 제약 발생 시 해당 노드 가격이 움직이는 방향과 크기. + 상승 / − 하락. 부호가 반대면 한쪽을 올리는 혼잡이 다른 쪽은 내린다. STP-WAP은 Raven 수익엔 유리, GKS엔 불리)*"),
    ("| 제약 | 대리 노드 추정 | Raven 실측 | 오차 |",
     "| 제약 (가격 영향, + 상승 / − 하락) | 대리 노드 추정 | Raven 실측 | 오차 |"),
    ("| STP-WAP | −0.031 | −0.021 | **50% 과대** |",
     "| STP-WAP | +0.031 | +0.021 | **50% 과대** |"),
    ("| 35055__A | +0.095 | +0.128 | **25% 과소** |",
     "| 35055__A | −0.095 | −0.128 | **25% 과소** |"),
    ("| E_PASP | — | Raven +0.030 vs **GKS +0.241** | **GKS가 8배 민감** |",
     "| E_PASP | — | Raven −0.030 vs **GKS −0.241** | **둘 다 하락, GKS가 8배 크게** |"),
    ("| **영향계수 (shift factor)** | 특정 발전소 출력 1MW 변화가 해당 송전선 부하에 주는 영향. 부호가 양수/음수에 따라 그 발전소가 혼잡에 유리·불리해진다 |",
     "| **가격 영향계수** | 송전 제약 발생 시 해당 노드 가격이 움직이는 방향과 크기. **+는 가격 상승(유리), −는 하락(불리)**. 제약 가격 × 계수 = 노드 가격 변화 (예: GKS의 E_PASP −0.241 → 제약 가격 $100당 GKS 가격 $24 하락). ERCOT 원자료 shift factor와는 부호가 반대로 표기 |"),
], "md")
MD.write_text(m, encoding="utf-8")
print("patched dashboard renderer + MD")
